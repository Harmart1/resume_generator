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
from flask import url_for


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

    # --- Route Existence and Basic Access Tests ---
    def test_contact_route_exists(self):
        """Test if the contact route URL can be generated."""
        with app.test_request_context(): # Use app.test_request_context for url_for
            try:
                url = url_for('contact')
                self.assertIsNotNone(url)
                self.assertEqual(url, '/contact')
            except Exception as e:
                self.fail(f"url_for('contact') failed to resolve: {e}")

    def test_register_route_exists(self):
        """Test if the register route URL can be generated."""
        with app.test_request_context():
            try:
                url = url_for('register')
                self.assertIsNotNone(url)
                self.assertEqual(url, '/register')
            except Exception as e:
                self.fail(f"url_for('register') failed to resolve: {e}")

    def test_login_route_exists(self):
        """Test if the login route URL can be generated."""
        with app.test_request_context():
            try:
                url = url_for('login')
                self.assertIsNotNone(url)
                self.assertEqual(url, '/login')
            except Exception as e:
                self.fail(f"url_for('login') failed to resolve: {e}")

    def test_logout_route_exists(self):
        """Test if the logout route URL can be generated."""
        with app.test_request_context():
            try:
                url = url_for('logout')
                self.assertIsNotNone(url)
                self.assertEqual(url, '/logout')
            except Exception as e:
                self.fail(f"url_for('logout') failed to resolve: {e}")

    def test_user_profile_route_exists(self):
        """Test if the user_profile route URL can be generated."""
        with app.test_request_context():
            try:
                url = url_for('user_profile')
                self.assertIsNotNone(url)
                self.assertEqual(url, '/profile')
            except Exception as e:
                self.fail(f"url_for('user_profile') failed to resolve: {e}")

    def test_edit_account_route_exists(self):
        """Test if the edit_account route URL can be generated."""
        with app.test_request_context():
            try:
                url = url_for('edit_account')
                self.assertIsNotNone(url)
                self.assertEqual(url, '/account/edit')
            except Exception as e:
                self.fail(f"url_for('edit_account') failed to resolve: {e}")

    def test_edit_account_route_get_unauthenticated(self):
        """Test GET /account/edit redirects to login if user is not authenticated."""
        with app.test_request_context(): # Ensure url_for works correctly
            # No need to use self.client.get() with app.test_request_context() for this check,
            # self.client.get already sets up its own context.
            # The with app.test_request_context() is more for direct url_for calls if not using client.
            pass # client.get will handle context

        response = self.client.get(url_for('edit_account'))
        self.assertEqual(response.status_code, 302) # Should redirect
        # Check if the redirection location contains the login URL path.
        # This is more robust than checking the full URL if domain/port might vary.
        self.assertIn(url_for('login', _external=False), response.location)


    # --- Placeholder for Authenticated Route Tests ---
    # def test_edit_account_route_get_authenticated(self):
    #     """Test GET /account/edit is successful and contains correct data for an authenticated user."""
    #     with app.app_context():
    #         # Register and log in a user
    #         self._register_user('authed_user@example.com', 'password123')
    #         login_response = self.client.post(url_for('login'), data={
    #             'email': 'authed_user@example.com',
    #             'password': 'password123'
    #         }, follow_redirects=True)
    #         self.assertEqual(login_response.status_code, 200) # Ensure login was successful
    #
    #         # Now access the protected route
    #         # Use 'with self.client:' to maintain the session context from login
    #         with self.client:
    #             response = self.client.get(url_for('edit_account'))
    #             self.assertEqual(response.status_code, 200)
    #             self.assertIn(b"Account Information", response.data)
    #             self.assertIn(b"authed_user@example.com", response.data) # Check if user's email is present

if __name__ == '__main__':
    unittest.main()

# --- Conceptual Tests (for manual testing or future automation if UI testing framework is added) ---

# Test Name: test_nav_bar_display_logged_out
# Description: Verify that when a user is not logged in, the nav bar in app_base.html shows "Login" and "Register" links.
# How to test: Manually run the app, log out, and inspect the navigation bar.
# Expected: "Login" and "Register" links are visible. "User Account Button" is not visible.

# Test Name: test_nav_bar_display_logged_in
# Description: Verify that when a user is logged in, the nav bar in app_base.html shows the "User Account Button" (with username/email)
#              and does NOT show "Login" or "Register" links.
# How to test: Manually run the app, log in, and inspect the navigation bar.
# Expected: "User Account Button" is visible, displaying the correct username or email. "Login" and "Register" links are not visible.

# Test Name: test_user_account_dropdown_links_and_functionality
# Description: Verify the correct links and basic functionality of the user account dropdown menu in app_base.html.
# How to test:
#   1. Manually run the app and log in.
#   2. Hover over/click the "User Account Button" to reveal the dropdown.
#   3. Check links:
#      - "View/Edit Account" should point to /account/edit. Click it and verify it loads the Account Information page.
#      - "View Tier / Upgrade" should point to the main page's pricing section. Click it and verify.
#      - "Sign Out" should log the user out and redirect, typically to the homepage or login page. Click and verify.
# Expected: Dropdown appears, links are correct and navigate to the expected pages/functionality.

# Test Name: test_sso_button_styles_on_homepage
# Description: Verify that the Single Sign-On (SSO) buttons on new_homepage.html (or where they are implemented)
#              have the updated dark styles.
# How to test: Manually run the app, navigate to the page with SSO buttons (likely new_homepage.html or login/register pages).
#              Use browser developer tools to inspect the CSS applied to `.sso-options .button`.
# Expected: `background-color` should be `#2C3E50` (Dark Slate Gray), and `color` should be `#FFFFFF` (White).
#           Hover styles should show `background-color: #1A252F` (Darker Slate Gray).

# Test Name: test_edit_account_page_content_display
# Description: Verify that the content on the /account/edit page (edit_account.html) correctly displays current_user's information.
# How to test: Manually run the app, log in with a test user that has distinct username, email, tier, contact_phone, and industry_preference.
#              Navigate to /account/edit.
# Expected: The page should display the correct email, username (or "Not set"), tier, contact phone (or "Not set"),
#           and industry preference (or "Not set") for the logged-in user.
#           The links "View Full Profile" and "Manage Subscription / Upgrade" should be present.
