import os
import django

import unittest
from unittest.mock import patch, MagicMock
from accounts.utils import send_new_account_email, EmailThread
from django.contrib.auth.models import User

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")  # Replace 'config.settings' with your settings module path
django.setup()

class TestSendNewAccountEmail(unittest.TestCase):
    @patch("accounts.utils.EmailThread.start")
    def test_send_new_account_email_student(self, mock_thread_start):
        # Mock user object
        user = MagicMock()
        user.is_student = True
        user.email = "student@example.com"

        # Call the function
        send_new_account_email(user, "securepassword")

        # Assert that EmailThread was started
        mock_thread_start.assert_called_once()

    @patch("accounts.utils.EmailThread.start")
    def test_send_new_account_email_lecturer(self, mock_thread_start):
        # Mock user object
        user = MagicMock()
        user.is_student = False
        user.email = "lecturer@example.com"

        # Call the function
        send_new_account_email(user, "securepassword")

        # Assert that EmailThread was started
        mock_thread_start.assert_called_once()

    @patch("accounts.utils.send_html_email")
    def test_email_thread_run(self, mock_send_html_email):
        # Mock email data
        email_data = {
            "subject": "Test Subject",
            "recipient_list": ["test@example.com"],
            "template_name": "test_template.html",
            "context": {"key": "value"},
        }

        # Create an EmailThread instance
        email_thread = EmailThread(**email_data)

        # Run the thread's run method
        email_thread.run()

        # Assert that send_html_email was called with the correct arguments
        mock_send_html_email.assert_called_once_with(
            subject="Test Subject",
            recipient_list=["test@example.com"],
            template="test_template.html",
            context={"key": "value"},
        )


if __name__ == "__main__":
    unittest.main()