"""
Handles user authentication, password hashing, and JWT token management.
"""
import bcrypt
import jwt
import os
import datetime
import time
from dotenv import load_dotenv

load_dotenv()


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_strong_fallback_secret_key_if_env_is_missing_change_me!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 

# --- Hashing et Vérification des Mots de Passe ---

def hash_password(password: str) -> str:
    """
    Hashes a plain password using bcrypt.

    Args:
        password: The plain string password.

    Returns:
        The hashed password as a UTF-8 string.
    """

    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.

    Args:
        password: The plain string password.
        hashed_password: The hashed password from the database.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

# --- JWT Token Management ---

def create_access_token(employee_id: int, employee_email: str, employee_department: str) -> str:
    """
    Creates a JWT access token containing employee information and expiration time.

    Args:
        employee_id: The ID of the employee ('sub').
        employee_email: The employee's email.
        employee_department: The employee's department/role name.

    Returns:
        The encoded JWT token string.
    """
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    employee_id_str = str(employee_id) 
    
    to_encode = {
        "sub": employee_id_str,             # Subject (Employee ID)
        "email": employee_email,            # Employee Email
        "department": employee_department,  # Employee Role Name
        "exp": expire                       # Expiration Time
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """
    Decodes and validates a JWT access token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload and 'sub' in payload:
            try:
                payload['sub'] = int(payload['sub'])
            except ValueError:
                raise jwt.InvalidTokenError("Subject (sub) in token is not a valid integer.")
                
        return payload
    except Exception as e:
        raise e

# --- Permissions (Basé sur le nom du Rôle) ---

PERMISSIONS = {
    'Gestion': {
        'create_employee': True, 'view_employees': True, 'update_employee': True, 'delete_employee': True,
        'create_client': True, 'view_clients': True, 'update_client': True, 'delete_client': True,
        'create_contract': True, 'view_contracts': True, 'update_contract': True, 'delete_contract': True,
        'create_event': True, 'view_events': True, 'update_event': True, 'delete_event': True,
    },
    'Commercial': {
        'create_employee': False, 'view_employees': True, 'update_employee': False, 'delete_employee': False,
        'create_client': True, 'view_clients': True, 'update_client': True, 
        'create_contract': True, 'view_contracts': True, 'update_contract': True, 'delete_contract': False,
        'create_event': True, 'view_events': True, 'update_event': False, 'delete_event': False,
    },
    'Support': {
        'create_employee': False, 'view_employees': True, 'update_employee': False, 'delete_employee': False,
        'create_client': False, 'view_clients': True, 'update_client': False, 'delete_client': False,
        'create_contract': False, 'view_contracts': True, 'update_contract': False, 'delete_contract': False,
        'create_event': False, 'view_events': True, 'update_event': True, 'delete_event': False, 
    }
}

def check_permission(employee, action: str) -> bool:
    """
    Checks if an employee has permission to perform a specific action.

    Args:
        employee (Employee): The Employee object.
        action: The string representing the action (e.g., 'create_employee').

    Returns:
        True if the employee has permission, False otherwise.
    """
    department_name = employee.department 
    
    return PERMISSIONS.get(department_name, {}).get(action, False)