"""
Handles user authentication, password hashing, and JWT token management.
Centralizes the logic for creating, decoding, and validating tokens.
"""
import bcrypt
import jwt
import os
import datetime
import time
from dotenv import load_dotenv
from typing import Union 
from rich.console import Console 

# Charger les variables d'environnement (pour la clé secrète JWT)
load_dotenv()

# Clé secrète utilisée pour signer le JWT. 
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_strong_fallback_secret_key_if_env_is_missing_change_me!")
ALGORITHM = "HS256"
# CORRECTION CRITIQUE 1: Rétablissement de la durée à 3 minutes
ACCESS_TOKEN_EXPIRE_MINUTES = 3 


# --- Hashing et Vérification des Mots de Passe ---

def hash_password(password: str) -> str:
    """
    Hashes a plain password using bcrypt.
    """
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

# --- JWT Token Management ---

# MODIFICATION CRITIQUE 2: La fonction retourne le token ET l'information sur l'expiration
def create_access_token(employee_id: int, employee_email: str, employee_department: str) -> tuple[str, str]:
    """
    Creates a JWT access token and returns it along with the expiration display string.
    """
    # L'expiration est calculée en secondes
    expire_delta = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.datetime.now(datetime.timezone.utc) + expire_delta
    
    # CRITIQUE: Convertit employee_id en chaîne de caractères pour le champ 'sub'
    employee_id_str = str(employee_id) 

    to_encode = {
        "sub": employee_id_str,
        "email": employee_email,            
        "department": employee_department,  
        "exp": expire                       
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # NOUVEAU: Formatage du temps d'expiration pour l'affichage dans main.py
    expire_display = f"{ACCESS_TOKEN_EXPIRE_MINUTES}m"
    if ACCESS_TOKEN_EXPIRE_MINUTES >= 60 * 24:
        expire_display = f"{ACCESS_TOKEN_EXPIRE_MINUTES // (60 * 24)}d"
    elif ACCESS_TOKEN_EXPIRE_MINUTES >= 60:
        expire_display = f"{ACCESS_TOKEN_EXPIRE_MINUTES // 60}h"

    return encoded_jwt, expire_display


# AJOUTÉ: Fonction pour décoder le token et vérifier l'expiration/signature
def decode_access_token(token: str) -> dict:
    """
    Decodes and validates a JWT access token (expiration, signature).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # S'assurer que le 'sub' (ID) est un entier après décodage pour les requêtes DB
        if payload and 'sub' in payload:
            try:
                # Reconvertit en entier pour l'utilisation dans les requêtes DB
                payload['sub'] = int(payload['sub']) 
            except ValueError:
                raise jwt.InvalidTokenError("Subject (sub) in token is not a valid integer.")
                
        return payload
    except Exception as e:
        # Laisse l'exception remonter pour être gérée par get_employee_from_token
        raise e


# AJOUTÉ: Fonction pour valider le token et récupérer l'employé
def get_employee_from_token(token: str, session) -> Union['Employee', None]:
    """
    Validates the token, checks expiration, and retrieves the corresponding Employee object.
    """
    # Import local de Employee pour briser la dépendance circulaire
    try:
        from app.models import Employee 
    except ImportError:
        return None
        
    try:
        console = Console()
        # Le décodage vérifie l'expiration et la signature
        payload = decode_access_token(token)
        
        employee_id = payload.get("sub")
        
        employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
        
        if not employee:
            console.print("[bold red]Token validation error:[/bold red] Employee linked to token not found.", style="dim")
            return None
            
        return employee
        
    except Exception as e:
        # Capture ExpiredSignatureError, InvalidSignatureError, etc.
        Console().print(f"[bold red]Token validation error (logout):[/bold red] {e}", style="dim")
        return None


# --- Permission System ---

PERMISSIONS = {
    'Gestion': {
        'create_employee': True, 'view_employees': True, 'update_employee': True, 'delete_employee': True,
        'create_client': True, 'view_clients': True, 'update_client': True, 
        'create_contract': True, 'view_contracts': True, 'update_contract': True, 
        'create_event': True, 'view_events': True, 'update_event': True,
    },
    'Commercial': {
        'create_employee': False, 'view_employees': True, 'update_employee': False, 'delete_employee': False,
        'create_client': True, 'view_clients': True, 'update_client': True, 
        'create_contract': True, 'view_contracts': True, 'update_contract': True, 
        'create_event': False, 'view_events': True, 'update_event': False, 
    },
    'Support': {
        'create_employee': False, 'view_employees': True, 'update_employee': False, 'delete_employee': False,
        'create_client': False, 'view_clients': True, 'update_client': False,
        'create_contract': False, 'view_contracts': True, 'update_contract': False,
        'create_event': False, 'view_events': True, 'update_event': True, 
    }
}

def check_permission(employee, action: str) -> bool:
    """
    Checks if an employee has permission to perform a specific action.
    """
    role_name = employee.department 
    return PERMISSIONS.get(role_name, {}).get(action, False)