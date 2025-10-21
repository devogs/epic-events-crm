"""
Handles user authentication, password hashing, and JWT token management.
Centralizes the logic for creating, decoding, and validating tokens.
"""

import os
import datetime
from typing import Union

import bcrypt
import jwt
from dotenv import load_dotenv
from rich.console import Console
from sqlalchemy.orm import Session

from app.models import Employee

console = Console()
load_dotenv()

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "your_strong_fallback_secret_key_if_env_is_missing_change_me!"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3


def hash_password(password: str) -> str:
    """Hashes a plain password using bcrypt."""
    hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")


def check_password(password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# --- JWT Token Management ---


def create_access_token(employee_id: int, employee_department: str) -> tuple[str, str]:
    """
    Creates a JWT access token for the given employee ID and department.
    """
    to_encode = {"sub": str(employee_id), "department": employee_department}

    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    expiration_display = f"{ACCESS_TOKEN_EXPIRE_MINUTES} minutes"

    return encoded_jwt, expiration_display


def decode_access_token(token: str) -> Union[dict, None]:
    """
    Decode and validate JWT token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        console.print(
            "[bold red]Token validation error:[/bold red] Token expired.", style="dim"
        )
        return None
    except jwt.InvalidTokenError as e:
        console.print(
            f"[bold red]Token validation error (logout):[/bold red] {e}", style="dim"
        )
        return None


def get_employee_from_token(token: str, session: Session) -> Employee | None:
    """
    Decode the token, valide is user exist in the DB, and manage refresh.
    """
    payload = decode_access_token(token)

    if payload is None:
        return None

    employee_id = payload.get("sub")

    if employee_id is None:
        console.print(
            "[bold red]Token validation error:[/bold red] Missing employee ID in payload.",
            style="dim",
        )
        return None

    employee = session.query(Employee).filter_by(id=int(employee_id)).one_or_none()

    if employee is None:
        console.print(
            f"[bold red]Token validation error:[/bold red] Employee ID {employee_id} not found.",
            style="dim",
        )
        return None

    if payload.get("department") != employee.department:
        console.print(
            "[bold red]Security Warning:[/bold red] " \
            "Department mismatch between token and DB. Token rejected.",
            style="dim",
        )
        return None

    return employee


# --- Permission System ---
PERMISSIONS = {
    "Gestion": {
        "create_employee": True,
        "view_employees": True,
        "update_employee": True,
        "delete_employee": True,
        "create_client": True,
        "view_clients": True,
        "update_client": True,
        "create_contract": True,
        "view_contracts": True,
        "update_contract": True,
        "create_event": True,
        "view_events": True,
        "update_event": True,
    },
    "Commercial": {
        "create_employee": False,
        "view_employees": True,
        "update_employee": False,
        "delete_employee": False,
        "create_client": True,
        "view_clients": True,
        "update_client": True,
        "create_contract": True,
        "view_contracts": True,
        "update_contract": True,
        "create_event": True,
        "view_events": True,
        "update_event": False,
    },
    "Support": {
        "create_employee": False,
        "view_employees": True,
        "update_employee": False,
        "delete_employee": False,
        "create_client": False,
        "view_clients": True,
        "update_client": False,
        "create_contract": False,
        "view_contracts": True,
        "update_contract": False,
        "create_event": False,
        "view_events": True,
        "update_event": True,
    },
}


def check_permission(employee, action: str) -> bool:
    """
    Checks if the employee has permission to perform the given action.
    """
    department = employee.department
    return PERMISSIONS.get(department, {}).get(action, False)
