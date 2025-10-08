"""
Employee Controller: Handles all CRUD operations related to the Employee model.
These functions are called by the department menus (like Management Menu).
"""
import re
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from rich.console import Console
from rich.table import Table

# Note: We assume the application structure includes these imports
from app.models import Employee
from app.authentication import hash_password

console = Console()

# Department options shared with views
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
    # 1. Standardize the name
    # Replace any non-alphabetic characters (except spaces) with nothing,
    # convert to lowercase, and replace spaces with dots.
    base_name = re.sub(r'[^a-zA-Z\s]', '', full_name).lower().strip()
    parts = base_name.split()

    # If the name is composed of multiple words, use first.last
    if len(parts) > 1:
        base_email_prefix = f"{parts[0]}.{parts[-1]}"
    elif parts:
        # If only one name is provided
        base_email_prefix = parts[0]
    else:
        # Fallback if name is empty after cleanup
        base_email_prefix = "unknown"

    # 2. Check for uniqueness and append counter if necessary
    email_suffix = "@epicevents.com"
    email_prefix = base_email_prefix
    counter = 0

    while True:
        proposed_email = f"{email_prefix}{email_suffix}"
        
        # Check if the proposed email already exists in the database
        if session.query(Employee).filter_by(email=proposed_email).one_or_none() is None:
            return proposed_email
        
        # If it exists, increment counter and try again
        counter += 1
        email_prefix = f"{base_email_prefix}{counter}"


# --- CRUD Controller Functions ---

def create_employee(session, full_name: str, phone: str, department: str, plain_password: str) -> Employee | None:
    """
    Creates a new Employee record in the database.

    Args:
        session: SQLAlchemy session.
        full_name: Employee's full name.
        phone: Employee's phone number.
        department: Employee's department ('Gestion', 'Commercial', or 'Support').
        plain_password: The unhashed password.

    Returns:
        The created Employee object, or None if creation failed.
    """
    try:
        # The email is automatically generated and checked for uniqueness
        email = format_email(full_name, session)

        new_employee = Employee(
            full_name=full_name,
            email=email,
            phone=phone,
            department=department
        )
        # The model's setter handles hashing the password
        new_employee.password = plain_password

        session.add(new_employee)
        session.commit()
        return new_employee
    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERROR:[/bold red] Database integrity error. Check if the generated email is somehow duplicated.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] An unexpected error occurred during employee creation: {e}")
        return None


def list_employees(session) -> list[Employee]:
    """
    Retrieves all Employee records and displays them in a Rich table.

    Args:
        session: SQLAlchemy session.

    Returns:
        A list of all Employee objects.
    """
    employees = session.query(Employee).all()
    
    table = Table(title="Epic Events Employees")
    table.add_column("ID", style="cyan", justify="center")
    table.add_column("Full Name", style="magenta")
    table.add_column("Email", style="green")
    table.add_column("Phone")
    table.add_column("Department", style="yellow")

    for emp in employees:
        table.add_row(
            str(emp.id),
            emp.full_name,
            emp.email,
            emp.phone or "N/A",
            emp.department
        )

    console.print(table)
    return employees


def update_employee(session, employee_id: int, full_name: str | None = None, email: str | None = None, phone: str | None = None, department: str | None = None, plain_password: str | None = None) -> Employee | None:
    """
    Updates an existing Employee record based on provided fields.

    Args:
        session: SQLAlchemy session.
        employee_id: ID of the employee to update.
        full_name, email, phone, department, plain_password: Optional fields to update.

    Returns:
        The updated Employee object, or None if the update fails.
    """
    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
    
    if not employee:
        console.print(f"[bold red]ERROR:[/bold red] Employee with ID {employee_id} not found.")
        return None
        
    try:
        # 1. Update fields if provided
        if full_name is not None:
            employee.full_name = full_name
            # NOTE: If the email was auto-generated, changing full_name here will NOT
            # automatically update the email. If the email is now mandatory, the
            # view must provide it or the controller must generate it.
            
        if email is not None:
            # NOUVEAU : Ajouter la gestion de l'email
            employee.email = email
            
        if phone is not None:
            employee.phone = phone
            
        if department is not None:
            # Check if attempting to change the last 'Gestion' member's department
            if employee.department == 'Gestion' and department != 'Gestion':
                gestion_count = session.query(Employee).filter_by(department='Gestion').count()
                if gestion_count <= 1:
                    raise ValueError("Cannot change the department of the last remaining 'Gestion' employee.")
            
            employee.department = department
            
        if plain_password is not None:
            # Assumes the Employee model has a setter for password (employee.password = value)
            # which handles the hashing and storage.
            employee.password = plain_password 

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
        # Check if the employee is the last 'Gestion' member
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
