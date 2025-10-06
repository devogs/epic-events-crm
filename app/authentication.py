"""
This module handles authentication and password hashing.
"""
import bcrypt

def hash_password(password: str) -> str:
    """
    Hashes the user's password.

    Args:
        password: The plain-text password.

    Returns:
        The salted and hashed password.
    """
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """
    Checks if a plain-text password matches its hashed version.

    Args:
        password: The plain-text password.
        hashed_password: The salted and hashed password stored in the database.

    Returns:
        True if the passwords match, False otherwise.
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_employee_permissions(department: str) -> list[str]:
    """
    Defines an employee's permissions based on their department.

    Args:
        department: The employee's department.

    Returns:
        A list of permissions.
    """
    permissions = []
    if department == 'commercial':
        permissions = ['view_clients', 'create_client', 'update_client', 'view_contracts', 'create_contract', 'update_contract']
    elif department == 'support':
        permissions = ['view_events', 'update_event']
    elif department == 'management':
        permissions = ['view_clients', 'view_contracts', 'view_events', 'create_employee', 'update_employee']
    return permissions
