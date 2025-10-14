"""
Employee Controller: Handles all CRUD operations related to the Employee model.
These functions are called by the department menus (like Management Menu).
"""
import re
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from rich.console import Console
from rich.table import Table

from app.models import Employee, Role
from app.authentication import hash_password

console = Console()

DEPARTMENT_OPTIONS = {
    '1': 'Gestion',
    '2': 'Commercial',
    '3': 'Support'
}


# --- Utility Functions (AJOUT D'UNE UTILITAIRE) ---

def get_role_id_by_name(session, role_name: str) -> int | None:
    """ Retrieves the Role ID from the Role name. """
    role = session.query(Role).filter_by(name=role_name).one_or_none()
    return role.id if role else None


def format_email(full_name: str, session) -> str:
    """
    Generates a unique email address based on the employee's full name.
    Format: firstname.lastname[N]@epicevents.com

    Args:
        full_name: The full name of the employee (e.g., "Billy Bob").
        session: SQLAlchemy session for checking email uniqueness.

    Returns:
        A unique email address string.
    """

    base_name = re.sub(r'[^a-zA-Z\s]', '', full_name).lower().strip()
    parts = base_name.split()

    if len(parts) > 1:
        base_email_prefix = f"{parts[0]}.{parts[-1]}"
    elif parts:
        base_email_prefix = parts[0]
    else:
        base_email_prefix = "unknown"

    base_email = f"{base_email_prefix}@epicevents.com"
    email = base_email
    counter = 1

    while session.query(Employee).filter_by(email=email).one_or_none():
        email = f"{base_email_prefix}{counter}@epicevents.com"
        counter += 1
        
    return email


# --- CRUD Functions ---

def create_employee(session, full_name: str, phone: str, department_name: str, plain_password: str) -> Employee | None:
    """
    Creates a new Employee record.
    """
    try:
        role_id = get_role_id_by_name(session, department_name)
        if role_id is None:
             raise ValueError(f"Role '{department_name}' not found in the database.")
             
        email = format_email(full_name, session)

        new_employee = Employee(
            full_name=full_name,
            email=email,
            phone=phone,
            role_id=role_id, 
        )
        new_employee.password = plain_password 

        session.add(new_employee)
        session.commit()
        return new_employee
    
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        return None
    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERROR:[/bold red] Database integrity error. Check if the provided email/phone is already in use.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]FATAL ERROR:[/bold red] An unexpected error occurred during employee creation: {e}")
        return None


def list_employees(session) -> list[Employee]:
    """ Lists all employees. """
    return session.query(Employee).all()


def update_employee(session, employee_id: int, full_name: str | None = None, email: str | None = None, phone: str | None = None, department: str | None = None, plain_password: str | None = None) -> Employee | None:
    """
    Updates an existing Employee record based on provided fields.
    """
    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    
    if not employee:
        console.print(f"[bold red]ERROR:[/bold red] Employee with ID {employee_id} not found.")
        return None
        
    try:
        if full_name is not None:
            employee.full_name = full_name
            
        if email is not None:
            employee.email = email
            
        if phone is not None:
            employee.phone = phone
            
        if plain_password is not None:
            employee.password = plain_password 

        if department is not None:
            new_role_id = get_role_id_by_name(session, department)
            if new_role_id is None:
                raise ValueError(f"Role '{department}' not found in the database.")
                
            if employee.department == 'Gestion' and department != 'Gestion':
                gestion_count = session.query(Employee).join(Role).filter(Role.name == 'Gestion').count()
                if gestion_count <= 1:
                    raise ValueError("Cannot change the role of the last remaining 'Gestion' employee.")
            
            employee.role_id = new_role_id
            
        session.commit()
        return employee
        
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        return None
    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERROR:[/bold red] Database integrity error. Check if the provided email/phone is already in use.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]FATAL ERROR:[/bold red] An unexpected error occurred during employee update: {e}")
        return None


def delete_employee(session, employee_id: int) -> bool:
    """
    Deletes an Employee record.
    """
    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    
    if not employee:
        return False
        
    try:
        if employee.department == 'Gestion': 
            gestion_count = session.query(Employee).join(Role).filter(Role.name == 'Gestion').count()
            if gestion_count <= 1:
                raise ValueError("Cannot delete the last remaining employee from the 'Gestion' department.")
                
        session.delete(employee)
        session.commit()
        return True
    
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        return False
    except SQLAlchemyError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] Failed to delete employee. Details: {e}")
        return False
