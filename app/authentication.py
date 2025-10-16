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
from sqlalchemy.orm import Session
# Import local nécessaire pour la validation du token
from app.models import Employee 

console = Console()
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_strong_fallback_secret_key_if_env_is_missing_change_me!")
ALGORITHM = "HS256"
# Durée du token (à ajuster selon vos besoins)
ACCESS_TOKEN_EXPIRE_MINUTES = 3 

# --- Hashing et Vérification des Mots de Passe ---
# ... (hash_password et check_password, inchangés mais nécessaires)
def hash_password(password: str) -> str:
    """Hashes a plain password using bcrypt."""
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

# --- JWT Token Management ---

# CORRECTION CRITIQUE: Ajout du paramètre 'employee_department'
def create_access_token(employee_id: int, employee_department: str) -> tuple[str, str]:
    """
    Crée un jeton d'accès JWT avec l'ID de l'employé et son département.
    Retourne le token et une chaîne d'information sur l'expiration.
    """
    to_encode = {"sub": str(employee_id), "department": employee_department}
    
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    expiration_display = f"{ACCESS_TOKEN_EXPIRE_MINUTES} minutes"
    
    return encoded_jwt, expiration_display


def decode_access_token(token: str) -> Union[dict, None]:
    """
    Décode et valide le token JWT.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        console.print("[bold red]Token validation error:[/bold red] Token expired.", style="dim")
        return None
    except jwt.InvalidTokenError as e:
        console.print(f"[bold red]Token validation error (logout):[/bold red] {e}", style="dim")
        return None


def get_employee_from_token(token: str, session: Session) -> Employee | None:
    """
    Décode le token, valide l'existence de l'utilisateur dans la DB, et gère le rafraîchissement si nécessaire.
    """
    payload = decode_access_token(token)
    
    if payload is None:
        return None # Token invalide ou expiré
        
    employee_id = payload.get("sub")
    
    if employee_id is None:
        console.print("[bold red]Token validation error:[/bold red] Missing employee ID in payload.", style="dim")
        return None
        
    employee = session.query(Employee).filter_by(id=int(employee_id)).one_or_none()
    
    if employee is None:
        console.print(f"[bold red]Token validation error:[/bold red] Employee ID {employee_id} not found in DB.", style="dim")
        return None

    # Vérification que le département dans le token correspond au département dans la DB
    if payload.get("department") != employee.department:
        console.print("[bold red]Security Warning:[/bold red] Department mismatch between token and DB. Token rejected.", style="dim")
        return None
        
    return employee


# --- Permission System ---
# ... (check_permission et PERMISSIONS, non modifiés mais nécessaires)
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
        'create_event': True, 'view_events': True, 'update_event': False, 
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
    Vérifie si l'employé a la permission d'effectuer l'action donnée.
    """
    department = employee.department
    return PERMISSIONS.get(department, {}).get(action, False)