import unittest
from flask import Flask
from unittest.mock import patch # Added
from backend.forms import LoginForm, RegistrationForm # Added RegistrationForm

class TestAuthForms(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for form testing
        self.app.config['SECRET_KEY'] = 'test-secret-key' # Required for session, etc.
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_login_form_valid_data(self):
        with self.app.test_request_context(): # For URL generation if any field needs it
            form = LoginForm(email='test@example.com', password='password123')
            self.assertTrue(form.validate(), msg=f"Form validation failed with errors: {form.errors}")

    def test_login_form_missing_email(self):
        with self.app.test_request_context():
            form = LoginForm(password='password123')
            self.assertFalse(form.validate())
            self.assertIn('email', form.errors)
            self.assertIn('This field is required.', form.errors['email'])

    def test_login_form_invalid_email(self):
        with self.app.test_request_context():
            form = LoginForm(email='not-an-email', password='password123')
            self.assertFalse(form.validate())
            self.assertIn('email', form.errors)
            self.assertIn('Invalid email address.', form.errors['email']) # Default Flask-WTF Email validator message

    def test_login_form_missing_password(self):
        with self.app.test_request_context():
            form = LoginForm(email='test@example.com')
            self.assertFalse(form.validate())
            self.assertIn('password', form.errors)
            self.assertIn('This field is required.', form.errors['password'])

    # --- RegistrationForm Tests ---

    def test_registration_form_valid_data(self):
        with self.app.test_request_context(), \
             patch('backend.forms.User.query') as mock_query: # Path to User in forms.py
            mock_query.filter_by().first.return_value = None # Simulate username/email not taken
            form = RegistrationForm(
                username='newuser',
                email='new@example.com',
                password='password123',
                confirm_password='password123'
            )
            self.assertTrue(form.validate(), msg=f"Validation failed: {form.errors}")

    def test_registration_form_missing_username(self):
        with self.app.test_request_context():
            form = RegistrationForm(email='new@example.com', password='password123', confirm_password='password123')
            self.assertFalse(form.validate())
            self.assertIn('username', form.errors)

    def test_registration_form_password_mismatch(self):
        with self.app.test_request_context():
            form = RegistrationForm(
                username='newuser',
                email='new@example.com',
                password='password123',
                confirm_password='password456' # Mismatch
            )
            self.assertFalse(form.validate())
            self.assertIn('confirm_password', form.errors)
            self.assertIn('Passwords must match.', form.errors['confirm_password'])

    @patch('backend.forms.User.query') # Path to User in forms.py
    def test_registration_form_username_taken(self, mock_query):
        with self.app.test_request_context():
            # Simulate User.query.filter_by(username=...).first() returning a mock User object
            mock_user_instance = True # Could be an actual mock User() if fields are accessed
            mock_query.filter_by().first.return_value = mock_user_instance

            form = RegistrationForm(
                username='existinguser',
                email='new@example.com',
                password='password123',
                confirm_password='password123'
            )
            self.assertFalse(form.validate())
            self.assertIn('username', form.errors)
            self.assertIn('That username is taken. Please choose a different one.', form.errors['username'])

    @patch('backend.forms.User.query') # Path to User in forms.py
    def test_registration_form_email_taken(self, mock_query):
        with self.app.test_request_context():
            # If username is checked first by the form's field order (username then email):
            # mock_query.filter_by(username=...).first.return_value = None (for username check)
            # mock_query.filter_by(email=...).first.return_value = True (for email check)
            # This simpler side_effect list for first() assumes User.query.filter_by() is called twice,
            # once for username validation, once for email validation, in that order.
            mock_query.filter_by.return_value.first.side_effect = [None, True] # username available, email taken

            form = RegistrationForm(
                username='newuser',
                email='existing@example.com',
                password='password123',
                confirm_password='password123'
            )
            self.assertFalse(form.validate())
            self.assertIn('email', form.errors)
            self.assertIn('That email is already registered. Please choose a different one.', form.errors['email'])

if __name__ == '__main__':
    unittest.main()
