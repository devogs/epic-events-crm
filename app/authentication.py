"""
Handles user authentication, password hashing, and JWT token management.
"""
import bcrypt
import jwt
import os
import datetime
import time
from dotenv import load_dotenv

# Charger les variables d'environnement (pour la clé secrète JWT)
load_dotenv()

# Clé secrète utilisée pour signer le JWT. 
# IMPORTANT: Elle doit être définie dans un fichier .env et être très complexe.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_strong_fallback_secret_key_if_env_is_missing_change_me!")
ALGORITHM = "HS256"
# Durée de vie du token (par exemple, 24 heures)
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
    # bcrypt.gensalt() génère un nouveau sel à chaque fois
    # Le sel est intégré au hachage pour des raisons de sécurité
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.

    Args:
        password: The plain string password.
        hashed_password: The hashed password from the database.

    Returns:
        True if the passwords match, False otherwise.
    """
    try:
        # bcrypt.checkpw gère automatiquement l'encodage/décodage nécessaire
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # Peut arriver si le hash est mal formé ou non-bcrypt
        return False

# --- JWT Token Management ---

def create_access_token(employee_id: int, employee_email: str, department: str) -> str:
    """
    Creates a JSON Web Token (JWT) for the authenticated employee.

    Args:
        employee_id: The ID of the employee (subject of the token).
        employee_email: The email of the employee.
        department: The department of the employee (for permissions).

    Returns:
        The encoded JWT string.
    """
    # Définition de l'expiration du token
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Le payload contient les données de l'employé et l'heure d'expiration
    to_encode = {
        "exp": expire,
        "iat": datetime.datetime.now(datetime.timezone.utc),
        "sub": str(employee_id),
        "email": employee_email,
        "department": department
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """
    Decodes and validates a JWT access token.

    Args:
        token: The encoded JWT string.

    Returns:
        The payload dictionary if valid, or None if validation fails.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Le token a expiré
        print("ERROR: Token has expired.")
        return None
    except jwt.InvalidTokenError:
        # Le token est invalide (signature incorrecte, etc.)
        print("ERROR: Invalid token.")
        return None

# --- Permission Management ---

# Définition des permissions par département
PERMISSIONS = {
    'Gestion': {
        'create_employee': True, 'view_employees': True, 'update_employee': True, 'delete_employee': True,
        'create_client': True, 'view_clients': True, 'update_client': True, 
        'create_contract': True, 'view_contracts': True, 'update_contract': True, 
        'create_event': True, 'view_events': True, 'update_event': True,
    },
    'Commercial': {
        'create_employee': False, 'view_employees': True, 'update_employee': False, 'delete_employee': False,
        'create_client': True, 'view_clients': True, 'update_client': True, # Peut voir tous les clients, mais gérer seulement les siens
        'create_contract': True, 'view_contracts': True, 'update_contract': True,
        'create_event': False, 'view_events': True, 'update_event': False,
    },
    'Support': {
        'create_employee': False, 'view_employees': True, 'update_employee': False, 'delete_employee': False,
        'create_client': False, 'view_clients': True, 'update_client': False,
        'create_contract': False, 'view_contracts': True, 'update_contract': False,
        'create_event': False, 'view_events': True, 'update_event': True, # Peut mettre à jour les événements qui lui sont assignés
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
    department = employee.department
    return PERMISSIONS.get(department, {}).get(action, False)
