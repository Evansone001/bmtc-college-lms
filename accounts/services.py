from django.db import transaction
from .utils import (
    send_new_account_email,
    create_user_with_credentials,
)

class UserService:
    @classmethod
    @transaction.atomic
    def create_student(cls, email: str, first_name: str, last_name: str, **kwargs):
        """
        Create a student account with the given email, first name, last name, and other optional parameters.
        """
        user = create_user_with_credentials(
            email=email, 
            first_name=first_name, 
            last_name=last_name, 
            is_student=True,
            send_email=True,
            **kwargs
            )
        
        return user

    @classmethod
    @transaction.atomic
    def create_lecturer(cls, email: str, first_name: str, last_name: str, **kwargs):
        """
        Create a lecturer account with the given email, first name, last name, and other optional parameters.
        """
        user = create_user_with_credentials(
            email=email, 
            first_name=first_name, 
            last_name=last_name, 
            is_lecturer=True, 
            send_email=True,
            **kwargs
            )
        
        return user