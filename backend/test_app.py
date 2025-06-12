import unittest
import json
from unittest.mock import patch, MagicMock
from types import SimpleNamespace # Added for mocking Stripe object attributes
from backend.app import app, db, User, UserCredit

class AppTestCase(unittest.TestCase):

    def setUp(self):
        """Set up a test client and initialize the database."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing forms
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        # Set dummy Stripe Price IDs for tests if they are accessed directly in webhook logic
        app.config['STRIPE_STARTER_PRICE_ID'] = 'price_starter_dummy'
        app.config['STRIPE_PRO_PRICE_ID'] = 'price_pro_dummy'
        app.config['STRIPE_CREDIT_PACK_PRICE_ID'] = 'price_credit_pack_dummy'
        app.config['STRIPE_WEBHOOK_SECRET'] = 'whsec_dummy_secret' # For webhook construction mocking

        self.client = app.test_client()

        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up the database after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # --- Registration Tests ---
    def test_successful_registration(self):
        """Test user registration with valid data."""
        with app.app_context():
            response = self.client.post('/register', data={
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200) # Should redirect to login, then 200

            # Check if user is in database
            user = User.query.filter_by(email='test@example.com').first()
            self.assertIsNotNone(user)
            self.assertTrue(user.check_password('password123'))
            self.assertEqual(user.tier, 'free') # Default tier
            # Check for flash message (optional, depends on how robust you want the test)
            # For flash messages, you might need to use response.data to check HTML content
            self.assertIn(b'Your account has been created! You can now log in.', response.data)

            # Check if UserCredit entry was created
            user_credit = UserCredit.query.filter_by(user_id=user.id).first()
            self.assertIsNotNone(user_credit)
            self.assertEqual(user_credit.credits_remaining, 0)


    def test_registration_existing_email(self):
        """Test registration with an email that already exists."""
        with app.app_context():
            # Create a user first
            existing_user = User(email='test@example.com')
            existing_user.set_password('password123')
            db.session.add(existing_user)
            db.session.commit()

            response = self.client.post('/register', data={
                'email': 'test@example.com',
                'password': 'newpassword123',
                'confirm_password': 'newpassword123'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200) # Stays on registration page
            self.assertIn(b'Email already exists.', response.data)

            # Ensure no new user was created with this email
            users_count = User.query.filter_by(email='test@example.com').count()
            self.assertEqual(users_count, 1)

    def test_registration_password_mismatch(self):
        """Test registration with mismatched passwords."""
        with app.app_context():
            response = self.client.post('/register', data={
                'email': 'test2@example.com',
                'password': 'password123',
                'confirm_password': 'password321'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200) # Stays on registration page
            self.assertIn(b'Passwords must match.', response.data)

            user = User.query.filter_by(email='test2@example.com').first()
            self.assertIsNone(user) # User should not be created

    # --- Login/Logout Tests ---
    def _register_user(self, email, password):
        """Helper function to register a user."""
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit() # Commit user to get ID

        # Create initial credits for user
        user_credit = UserCredit(user_id=user.id, credits_remaining=0) # Now user.id is available
        db.session.add(user_credit)
        db.session.commit() # Commit UserCredit
        return user

    def test_successful_login_logout(self):
        """Test successful login and then logout."""
        with app.app_context():
            self._register_user('login_test@example.com', 'securepassword')

            # Test Login
            response_login = self.client.post('/login', data={
                'email': 'login_test@example.com',
                'password': 'securepassword'
            }, follow_redirects=True)
            self.assertEqual(response_login.status_code, 200)
            self.assertIn(b'Login successful!', response_login.data)

            # Verify current_user is authenticated - this needs to be checked within a request context
            # A simple way is to try accessing a @login_required route or check session.
            # For now, we'll assume the flash message and redirect are good indicators.
            # A more direct test of current_user would involve a test route.

            # Test Logout
            response_logout = self.client.get('/logout', follow_redirects=True)
            self.assertEqual(response_logout.status_code, 200)
            self.assertIn(b'You have been logged out.', response_logout.data)
            # To properly test current_user after logout, you'd make another request
            # to a page and see if current_user is anonymous.
            # For example, accessing the main page again:
            response_after_logout = self.client.get('/')
            self.assertNotIn(b'User: login_test@example.com', response_after_logout.data)


    def test_login_invalid_email(self):
        """Test login with an email that is not registered."""
        with app.app_context():
            response = self.client.post('/login', data={
                'email': 'nonexistent@example.com',
                'password': 'password123'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200) # Stays on login page
            self.assertIn(b'Login Unsuccessful. Please check email and password.', response.data)

    def test_login_incorrect_password(self):
        """Test login with a correct email but incorrect password."""
        with app.app_context():
            self._register_user('user_pass_test@example.com', 'correctpassword')

            response = self.client.post('/login', data={
                'email': 'user_pass_test@example.com',
                'password': 'wrongpassword'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200) # Stays on login page
            self.assertIn(b'Login Unsuccessful. Please check email and password.', response.data)

    # --- Stripe Webhook Tests ---
    # We need to mock Stripe API calls for these tests
    # unittest.mock.patch and MagicMock are already imported at the top

    def test_webhook_checkout_session_completed_new_user_starter_tier(self):
        """Test 'checkout.session.completed' for a new user subscribing to Starter tier."""
        with app.app_context():
            mock_event_payload = {
                'id': 'evt_test_webhook',
                'object': 'event',
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'id': 'cs_test_session',
                        'object': 'checkout.session',
                        'client_reference_id': 'new_user_starter_123', # This will be our User.id
                        'customer': 'cus_test_customer_starter',
                        'subscription': 'sub_test_subscription_starter',
                        'payment_intent': None, # For subscriptions, PI is usually on invoice
                        'mode': 'subscription'
                    }
                }
            }
            # Mock for stripe.checkout.Session.list_line_items
            mock_line_items = MagicMock()
            mock_line_items.data = [MagicMock(price=MagicMock(id=app.config['STRIPE_STARTER_PRICE_ID']))]

            # Pre-create the user as the webhook expects User.query.get(user_id)
            test_user_id = 999 # Use an integer ID
            test_user = User(id=test_user_id, email='new_starter@example.com')
            test_user.set_password('password')
            user_credit_entry = UserCredit(user_id=test_user_id, credits_remaining=0)
            db.session.add_all([test_user, user_credit_entry])
            db.session.commit()

            # Update client_reference_id in payload to be string representation of the integer ID
            mock_event_payload['data']['object']['client_reference_id'] = str(test_user_id)

            # Corrected mock for stripe.checkout.Session.list_line_items to return a list of dicts
            mock_list_items_return_starter = MagicMock()
            mock_list_items_return_starter.data = [
                {
                    'price': {
                        'id': app.config['STRIPE_STARTER_PRICE_ID']
                    }
                }
            ]

            with patch('stripe.Webhook.construct_event', return_value=mock_event_payload) as mock_construct_event, \
                 patch('backend.app.stripe.checkout.Session.list_line_items', return_value=mock_list_items_return_starter) as mock_list_items:

                response = self.client.post('/stripe_webhook',
                                            data=json.dumps(mock_event_payload),
                                            content_type='application/json',
                                            headers={'Stripe-Signature': 'dummy_sig_for_mock'})

                self.assertEqual(response.status_code, 200, f"Webhook failed with data: {response.get_data(as_text=True)}")
                mock_construct_event.assert_called_once()
                mock_list_items.assert_called_once_with(mock_event_payload['data']['object']['id'], limit=1) # Reinstated

                user_reloaded = User.query.get(test_user_id)
                self.assertIsNotNone(user_reloaded, "User should exist after webhook processing.")
                self.assertEqual(user_reloaded.tier, 'starter')
                self.assertEqual(user_reloaded.stripe_customer_id, 'cus_test_customer_starter')
                self.assertEqual(user_reloaded.stripe_subscription_id, 'sub_test_subscription_starter')

                user_credit = UserCredit.query.filter_by(user_id=user_reloaded.id).first()
                self.assertIsNotNone(user_credit)
                self.assertEqual(user_credit.credits_remaining, 1)


    def test_webhook_checkout_session_completed_existing_user_credit_pack(self):
        """Test 'checkout.session.completed' for an existing user buying a credit pack."""
        with app.app_context():
            existing_user = self._register_user('credit_user@example.com', 'password123')
            initial_credits = 2
            user_credit = UserCredit.query.filter_by(user_id=existing_user.id).first()
            user_credit.credits_remaining = initial_credits
            db.session.commit()

            mock_event_payload = {
                'id': 'evt_test_webhook_credits',
                'object': 'event',
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'id': 'cs_test_session_credits',
                        'object': 'checkout.session',
                        'client_reference_id': str(existing_user.id),
                        'customer': 'cus_test_customer_credits',
                        'subscription': None, # No subscription for one-time payment
                        'payment_intent': 'pi_test_payment_intent_credits',
                        'mode': 'payment'
                    }
                }
            }

            # Corrected mock for stripe.checkout.Session.list_line_items to return a list of dicts
            mock_list_items_return_credits = MagicMock()
            mock_list_items_return_credits.data = [
                {
                    'price': {
                        'id': app.config['STRIPE_CREDIT_PACK_PRICE_ID']
                    }
                }
            ]

            with patch('stripe.Webhook.construct_event', return_value=mock_event_payload) as mock_construct_event, \
                 patch('backend.app.stripe.checkout.Session.list_line_items', return_value=mock_list_items_return_credits) as mock_list_items:

                response = self.client.post('/stripe_webhook',
                                            data=json.dumps(mock_event_payload),
                                            content_type='application/json',
                                            headers={'Stripe-Signature': 'dummy_sig_for_mock_credits'})
                self.assertEqual(response.status_code, 200, f"Webhook failed with data: {response.get_data(as_text=True)}")
                mock_construct_event.assert_called_once()
                # Reinstate mock call assertions
                self.assertTrue(mock_list_items.called, "stripe.checkout.Session.list_line_items should have been called.")
                mock_list_items.assert_called_with(mock_event_payload['data']['object']['id'], limit=1)


                user_credit_updated = UserCredit.query.filter_by(user_id=existing_user.id).first()
                self.assertIsNotNone(user_credit_updated)
                self.assertEqual(user_credit_updated.credits_remaining, initial_credits + 5) # Expect 5 credits to be added

    def test_webhook_invoice_payment_failed_downgrade_tier(self):
        """Test 'invoice.payment.failed' webhook downgrades user tier."""
        with app.app_context():
            pro_user = self._register_user('pro_user_fail@example.com', 'password123')
            pro_user.tier = 'pro'
            pro_user.stripe_customer_id = 'cus_pro_user_fail'
            pro_user.stripe_subscription_id = 'sub_pro_user_fail_active'
            db.session.commit()

            mock_event_payload = {
                'id': 'evt_test_invoice_fail',
                'object': 'event',
                'type': 'invoice.payment_failed',
                'data': {
                    'object': { # This is an invoice object
                        'object': 'invoice',
                        'customer': 'cus_pro_user_fail',
                        'subscription': 'sub_pro_user_fail_active',
                        # ... other invoice details ...
                    }
                }
            }
            with patch('stripe.Webhook.construct_event', return_value=mock_event_payload) as mock_construct_event:
                response = self.client.post('/stripe_webhook',
                                            data=json.dumps(mock_event_payload),
                                            content_type='application/json',
                                            headers={'Stripe-Signature': 'dummy_sig_invoice_fail'})
                self.assertEqual(response.status_code, 200)
                mock_construct_event.assert_called_once()

                user_downgraded = User.query.filter_by(email='pro_user_fail@example.com').first()
                self.assertIsNotNone(user_downgraded)
                self.assertEqual(user_downgraded.tier, 'free') # Assuming downgrade to 'free'

if __name__ == '__main__':
    unittest.main()
