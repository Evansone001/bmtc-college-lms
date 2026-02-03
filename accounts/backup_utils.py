import random
import re
import logging
import threading

from datetime import datetime
from time import sleep
from functools import wraps
from uuid import uuid4
from typing import Tuple, Optional, Dict, Any, List

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction, IntegrityError, DatabaseError
from django.core.cache import cache

from accounts.models import FailedEmail
from core.utils import send_html_email  

# set up logging
logger = logging.getLogger(__name__)

# ########################################################
# Utility Functions
# ########################################################

def retry_on_failure(max_attempts: int = 3, delay_seconds: int = 1, jitter_factor: float = 0.1):
    """Decorator to retry a function on failure withe exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from time import sleep
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (IntegrityError, DatabaseError) as e:
                    attempts +=1
                    if attempts == max_attempts:
                        logger.error(f"Failed to execute {func.__name__} after {max_attempts} attempts: {e}")
                        raise
                # calculate base delay with exponential backoff
                base_wait_time = delay_seconds * (2 ** (attempts-1 ))  

                # add some jitter to the wait time
                jitter = random.uniform(-jitter_factor, jitter_factor) * base_wait_time
                wait_time = base_wait_time + jitter
                logger.warning(f"Retrr {attempts}/{max_attempts} for {func.__name__} in {wait_time} seconds")
                sleep(wait_time)
        return wrapper
    return decorator


def generate_password(length: int = 12) -> str:
    """Generate a random password for the user.
    """
    return get_user_model().objects.make_random_password(length=length)

def get_lock_key(prefix: str, namespace: Optional[str] = None) -> str:
    """

    Generate a unique lock key for distributed locking systems.
    
    Args:
        prefix: A descriptive identifier for the lock purpose
        namespace: Optional namespace to prevent collisions between systems
        
    Returns:
        A unique string formatted as "lock:{namespace}:{sanitized_prefix}:{uuid}"
        
    Raises:
        ValueError: If prefix contains invalid characters
        
    Example:
        >>> get_lock_key("test_lock", namespace="system_a")
        "lock:system_a:test_lock:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    """
    if not re.match(r'^[a-zA-Z0-9_.-]+$', prefix):
        raise ValueError(f"Invalid prefix: {prefix}. Only alphanumeric characters, underscores, and hyphens are allowed.")
    
    # Generate components of the lock key
    unique_id = uuid4().hex
    namespace_part = f"{namespace}:" if namespace else ""

    return f"lock:{namespace_part}{prefix}:{unique_id}"


@retry_on_failure()
@transaction.atomic
def generate_student_id():
    """ 
    Generate a unique student ID with proper locking to avoid race conditions.
    Uses atomic transaction and a distributed lock via cache.
    Returns:
       str: Returns a unique student ID in the format "PREFIX-YEAR-XXXX"
    Raises:
        IntegrityError: If the lock cannot be acquired or if the ID already exists.
    """

    registered_year: str = datetime.now().strftime("%Y")
    # Add timestamp to lock key for debugging
    lock_key: str = get_lock_key(f"student_id_gen_{registered_year}",
                                  namespace="bmtc_system_1")

    #Try acquire a distributed lock
    if not cache.add(lock_key, "locked", timeout=30) :       # lock expires in 30 seconds FOR SAFETY
        logger.warning("Failed to acquire lock for student ID generation.")
        raise IntegrityError("Could not acquire lock for student ID generation.")
    

    try:
        # Get settings with defaults values 
        prefix: str = getattr(settings, 'STUDENT_ID_PREFIX', 'STU')
        padding = getattr(settings, 'STUDENT_ID_PADDING', 4)

        User = get_user_model()

        #  find the highest existing ID for this year
        latest_student = (
            User.objects
            .select_for_update()
            .filter(student_id__startswith=f"{prefix}-{registered_year}-")
            .order_by('-student_id')
            .first()
        )

        if latest_student and latest_student.student_id:
            try:
                # Extract the numeric part and increment it
                current_number: int = int(latest_student.student_id.split('-')[2])
                next_number: int = current_number + 1
            except (IndexError, ValueError):
                # Fallback if parsing fails
                logger.warning("Failed to parse student ID, falling back to count method.Oops! check format of student id")
                next_number = (
                    User.objects
                    .filter(is_student=True)
                    .count() + 1
                )
        else:
            # No existing students with this year prefix, start from 1
            next_number = 1

        # Generate ID with padding for future growth
        student_id = f"{prefix}-{registered_year}-{next_number:0{padding}d}"

        # verify id uniqueness
        if User.objects.filter(student_id=student_id).exists():
            logger.warning(f"Generated ID {student_id} already exists, attempting to resolve...")
            raise IntegrityError("Generated student ID already exists.")

        logger.info(f"Successfully generated student ID: {student_id}")
        
        return student_id
        
    
    except IntegrityError as e:
        logger.error(f"IntegrityError occurred while generating student ID: {str(e)}")
        raise

    finally:
        # Release the lock
        try:
            cache.delete(lock_key)
            logger.info(f"Lock {lock_key} released.")
        except Exception as e:
            logger.error(f"Failed to release lock {lock_key}: {str(e)}")
            # Optionally, you can raise an exception or log it as needed
            raise IntegrityError(f"Failed to release lock {lock_key}: {str(e)}")
              

@retry_on_failure()
@transaction.atomic
def generate_lecturer_id():
    """
    Generate a unique lecturer ID with proper locking to avoid race conditions.
    Uses atomic transaction and a distributed lock via cache.
    Returns:
        str: Returns a unique lecturer ID in the format "PREFIX-YEAR-XXXX"
    Raises:
        IntegrityError: If the lock cannot be acquired or if the ID already exists.
    """

    registered_year: str = datetime.now().strftime("%Y")
    # Add timestamp to lock key for debugging
    lock_key: str = get_lock_key(f"lecturer_id_gen_{registered_year}",
                                  namespace="bmtc_system_1")

    #Try acquire a distributed lock
    if not cache.add(lock_key, "locked", timeout=30) :       # lock expires in 30 seconds FOR SAFETY
        logger.warning("Failed to acquire lock for lecturer ID generation.")
        raise IntegrityError("Could not acquire lock for lecturer ID generation.")


    try:
        # Get settings with defaults values 
        prefix: str = getattr(settings, 'LECTURER_ID_PREFIX', 'LEC')
        padding = getattr(settings, 'LECTURER_ID_PADDING', 4)

        User = get_user_model()

        #  find the highest existing ID for this year
        latest_lecturer = (
            User.objects
            .select_for_update()
            .filter(lecturer_id__startswith=f"{prefix}-{registered_year}-")
            .order_by('-lecturer_id')
            .first()
        )

        if latest_lecturer and latest_lecturer.lecturer_id:
            try:
                # Extract the numeric part and increment it
                current_number: int = int(latest_lecturer.lecturer_id.split('-')[2])
                next_number: int = current_number + 1
            except (IndexError, ValueError):
                # Fallback if parsing fails
                logger.warning("Failed to parse lecturer ID, falling back to count method.Oops! check format of lecturer id")
                next_number = (
                    User.objects
                    .filter(is_lecturer=True)
                    .count() + 1
                )
        else:
            # No existing lecturers with this year prefix, start from 1
            next_number = 1

        # Generate ID with padding for future growth
        lecturer_id = f"{prefix}-{registered_year}-{next_number:0{padding}d}"

        # verify id uniqueness
        if User.objects.filter(lecturer_id=lecturer_id).exists():
            logger.warning(f"Generated ID {lecturer_id} already exists, attempting to resolve...")
            raise IntegrityError("Generated lecturer ID already exists.")

        logger.info(f"Successfully generated lecturer ID: {lecturer_id}")
        
        return lecturer_id
        
    
    except IntegrityError as e:
        logger.error(f"IntegrityError occurred while generating lecturer ID: {str(e)}")
        raise

    finally:
        # Release the lock
        try:
            cache.delete(lock_key)
            logger.info(f"Lock {lock_key} released.")
        except Exception as e:
            logger.error(f"Failed to release lock {lock_key}: {str(e)}")
          
            raise IntegrityError(f"Failed to release lock {lock_key}: {str(e)}")

def generate_student_credentials() -> Tuple[str, str]:
    """
    Generate a unique student ID and password for the user.
    """
    return generate_student_id(), generate_password()


def generate_lecturer_credentials() -> Tuple[str, str]:
    """
    Generate a unique lecturer ID and password for the user.
    """
    return generate_lecturer_id(), generate_password()



class EmailThread(threading.Thread):
    def __init__(self, email_data: dict, max_retries: int = 3):
        super().__init__()  # Remove daemon=True
        self.email_data = email_data
        self.max_retries = max_retries
        self.message_id = uuid4().hex

    def run(self):
        try:
            attempts: int = 0
            while attempts < self.max_retries:
                try:
                    logger.info(f"Sending email {self.message_id}")
                    send_html_email(**self.email_data)
                    logger.info(f"Email {self.message_id} sent successfully.")
                    return
                except Exception as e:
                    attempts += 1
                    error: str = str(e)
                    logger.error(f"Failed email {self.message_id} (attempt {attempts}): {error}")
                    
                    if attempts == self.max_retries:
                        logger.critical(f"Permanently failed email {self.message_id}")
                        store_failed_email(self.email_data, error)
                        raise  # Propagate error for better visibility
        finally:
            logger.debug(f"Email thread {self.message_id} exiting")
            
def send_new_account_email(user, password: str, is_async: bool = True) -> Optional[bool]:
    """
    Send an email with account credentials.
    
    Args:
        user: The user object
        password: The generated password
        is_async: Whether to send the email asynchronously
        
    Returns:
        None if async, True if successful sync send, False if sync send failed
    """

    # Create a serializable context for the email
    context = {
        
            "username": user.username,
            "password": password,
            "login_url": getattr(settings, 'LOGIN_URL', '/login/'),
            "site_name": getattr(settings, 'SITE_NAME', 'BMTC'),
            "site_url": getattr(settings, 'SITE_URL', 'https://bmtc.ac.ke'),
            "support_email": getattr(settings, 'SUPPORT_EMAIL', 'support@bmtc.ac.ke'),
            "expiration_time": getattr(settings, 'PASSWORD_EXPIRE_DAYS', 3),  # in hours
            }

    if user.is_student:
        template_name = "accounts/email/new_student_account_confirmation.html"
    elif user.is_lecturer:
        template_name = "accounts/email/new_lecturer_account_confirmation.html"
    else:
        template_name = "accounts/email/new_account_confirmation.html"

    email_data= {
        "subject": "Your BMTC account confirmation and credentials",
        "recipient_list": [user.email],
        "template_name": template_name,
        "context": context,  
    }

    try:
        if is_async:
            # Send email in a separate thread
            EmailThread(email_data).start()
            return None
        else:
            try:
                # Send email synchronously for when immediate feedback is needed
                send_html_email(**{k: v for k, v in email_data.items() if k != 'max_retries'})  
                return True
            except Exception as e:
                store_failed_email(email_data, str(e))
                return False
        
    except Exception as e:
        logger.error(f"faild to initilaize email sending: {str(e)}")
        if not is_async:
            # If sync send failed, return False
            return False
        return None
    
@transaction.atomic
def create_user_with_credentials(
    email: str, 
    first_name: str, 
    last_name: str, 
    is_student: bool = False, 
    is_lecturer: bool = False,
    send_email: bool = True,
    **extra_fields
) -> Tuple[Any, str]:
    """
    Create a new user with generated credentials in an atomic transaction.
    
    Args:
        email: User's email
        first_name: User's first name
        last_name: User's last name
        is_student: Whether user is a student
        is_lecturer: Whether user is a lecturer
        send_email: Whether to send welcome email
        **extra_fields: Additional user model fields
        
    Returns:
        Tuple of (user, password)
    """
    User = get_user_model()

    # Validate role assignment
    if sum([is_student, is_lecturer]) > 1:
        raise ValueError("User cannot be both a student and a lecturer.")
    
    # Generate credentials based on user type
    if is_student:
        username, password = generate_student_credentials()
        extra_fields['is_student'] = True
    elif is_lecturer:
        username, password = generate_lecturer_credentials()
        extra_fields['is_lecturer'] = True
    else:
        # Handle other user types
        username = f"user-{uuid4().hex[:8]}"
        password = generate_password()
    
    try:
        # Create the user in a transaction
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_student=is_student,
            is_lecturer=is_lecturer,
            **extra_fields
        )
        
        # Send email if requested
        if send_email:
            send_new_account_email(user, password)
            
        return user, password
    
    except IntegrityError as e:
        logger.error(f"Failed to create user: {str(e)}")
        raise

def store_failed_email(email_data: dict, error: str):
    try:
        # Sanitize context for JSON serialization
        safe_context = {
            k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v 
            for k, v in email_data.get('context', {}).items()
        }

        # Store the failed email in the database or a file
        FailedEmail.objects.create(
            subject=email_data.get('subject', ''),
            recipient_list=email_data.get('recipient_list', []),
            template_name=email_data.get('template_name', ''),
            context=safe_context,
            error_message=error,
            message_id=email_data.get('message_id', uuid4().hex),
        )

    except Exception as e:
        logger.error(f"Failed to store failed email: {str(e)}")
        
    finally:
        # Clean up any resources --implement this later
        pass