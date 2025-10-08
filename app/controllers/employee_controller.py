"""
Employee Controller: Handles all CRUD operations related to the Employee model.
These functions are called by the department menus (like Management Menu).
"""
import re
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from app.models import Employee
from app.authentication import hash_password


console = Console()

DEPARTMENT_OPTIONS = {
    '1': 'Gestion',
    '2': 'Commercial',
    '3': 'Support'
}


# --- Utility Functions ---

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
    else:
        base_email_prefix = parts[0]
        
    base_email = f"{base_email_prefix}@epicevents.com"
    
    email_to_check = base_email
    counter = 0
    
    while session.query(Employee).filter_by(email=email_to_check).first() is not None:
        counter += 1
        email_to_check = f"{base_email_prefix}{counter}@epicevents.com"
        
    return email_to_check

# --- CRUD Functions ---

def create_employee(session, full_name: str, phone: str, department: str, plain_password: str) -> Employee | None:
    """
    Creates a new Employee record in the database.

    Args:
        session: SQLAlchemy session.
        full_name: Employee's full name.
        phone: Employee's phone number.
        department: Employee's department (Gestion, Commercial, Support).
        plain_password: The unhashed password.

    Returns:
        The created Employee object, or None if creation failed.
    """
    try:
        email = format_email(full_name, session)
        
        hashed_password = hash_password(plain_password)
        
        new_employee = Employee(
            full_name=full_name,
            email=email,
            phone=phone,
            department=department,
            _password_hash=hashed_password
        )
        
        session.add(new_employee)
        session.commit()
        return new_employee
        
    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERROR:[/bold red] Database integrity error. Employee creation failed.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] An error occurred during employee creation: {e}")
        return None


def list_employees(session) -> list[Employee]:
    """
    Retrieves all Employee records.

    Args:
        session: SQLAlchemy session.

    Returns:
        A list of Employee objects.
    """
    try:
        employees = session.query(Employee).all()
        return employees
    except Exception as e:
        console.print(f"[bold red]ERROR:[/bold red] An error occurred while listing employees: {e}")
        return []


def update_employee(session, employee_id: int, updates: dict) -> Employee | None:
    """
    Updates an existing Employee record based on the provided dictionary of updates.

    Args:
        session: SQLAlchemy session.
        employee_id: ID of the employee to update.
        updates: Dictionary of fields to update (e.g., {'phone': '12345', 'department': 'Commercial', 'plain_password': 'new'}).

    Returns:
        The updated Employee object, or None if not found or update failed.
    """
    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    if not employee:
        return None

    try:
        if 'plain_password' in updates:
            employee._password_hash = hash_password(updates.pop('plain_password'))
        
        if 'full_name' in updates and updates['full_name'] != employee.full_name:
            employee.full_name = updates['full_name']
            
            if 'email' not in updates:
                new_email = format_email(employee.full_name, session)
                employee.email = new_email
            
        if 'email' in updates and updates['email'] != employee.email:
            new_email = updates['email']
            if session.query(Employee).filter(Employee.email == new_email, Employee.id != employee_id).first():
                raise ValueError(f"Email '{new_email}' already exists for another employee.")
            employee.email = new_email
        
        for key, value in updates.items():
            if hasattr(employee, key):
                setattr(employee, key, value)
        
        session.commit()
        return employee
        
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] Validation failed: {e}")
        return None
    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERROR:[/bold red] Database integrity error. Check if the provided email/phone is already in use.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] An unexpected error occurred during employee update: {e}")
        return None


def delete_employee(session, employee_id: int) -> bool:
    """
    Deletes an Employee record.

    Args:
        session: SQLAlchemy session.
        employee_id: ID of the employee to delete.

    Returns:
        True if deletion was successful, False otherwise.
    """
    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    
    if not employee:
        return False
        
    try:
        if employee.department == 'Gestion':
            gestion_count = session.query(Employee).filter_by(department='Gestion').count()
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
