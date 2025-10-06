"""
Authentication and Authorization logic for the CRM application.
Includes password hashing, checking, and permission verification.
(COMPLETE ROLLBACK TO PURE BCRYPT FOR STABILITY)
"""
import os
import bcrypt 

# --- Password Hashing and Checking ---

def hash_password(password: str) -> str:
    """
    Hashes a plain text password using bcrypt.
    Returns the hash as a string (decoded from bytes).
    """
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """
    Checks a plain text password against a hashed password using bcrypt.
    
    Note: The hashed password in the database must be in bcrypt format (e.g., '$2b$').
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


# --- Permission Logic ---

# Define a map of permissions for each department (Keys must be in French as per user request)
PERMISSIONS_MAP = {
    "Gestion": [
        "create_employee", "list_employees", "update_employee", "delete_employee",
        "create_client", "list_clients", "update_client", "delete_client",
        "create_contract", "list_contracts", "update_contract", "delete_contract",
        "create_event", "list_events", "update_event", "delete_event",
        "assign_support_contact" 
    ],
    "Commercial": [
        "create_client", "list_clients", "update_client_own",
        "list_contracts", "update_contract_own",
        "create_event", "list_events",
    ],
    "Support": [
        "list_clients", "list_contracts", "list_events", 
        "list_events_own",
        "update_event_own",
    ]
}

def check_permission(employee, action: str) -> bool:
    """
    Checks if an employee has the permission to perform a specific action.
    """
    if employee.department not in PERMISSIONS_MAP:
        return False
    
    return action in PERMISSIONS_MAP[employee.department]
