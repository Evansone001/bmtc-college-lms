from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test

def admin_required(
    function=None,
    redirect_to="/",
):
    """
    Decorator for views that checks that the logged-in user is a superuser,
    redirects to the specified URL if necessary.
    """

    # Define the test function: checks if the user is active and a superuser
    def test_func(user):
        return user.is_authenticated and user.is_active and user.is_superuser

    # Use djangos built-in user_passes_test decorator to check if the user passes the test
    decorator = user_passes_test(test_func, login_url=redirect_to)

    # Apply decorator immediately if function is provided
    if function:
        return decorator(function)
    
    # Otherwise, return the decorator function itself
    return decorator


def lecturer_required(
    function=None,
    redirect_to="/",
):
    """
    Decorator for views that checks that the logged-in user is a lecturer,
    redirects to the specified URL if necessary.
    """

    def test_func(user):
        return user.is_authenticated and user.is_active and user.is_lecturer or user.is_superuser
    
    decorator = user_passes_test(test_func, login_url=redirect_to)

    if function:
        return decorator(function)

    return decorator
    

def student_required(
    function=None,
    redirect_to="/",
):
    """
    Decorator for views that checks that the logged-in user is a student,
    redirects to the specified URL if necessary.
    """

    def test_func(user):
        return user.is_authenticated and user.is_active and user.is_student or user.is_superuser

    decorator = user_passes_test(test_func, login_url=redirect_to)

    if function:
        return decorator(function)
   
    return decorator
  
