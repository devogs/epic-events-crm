"""
Employee Controller: Handles all PURE BUSINESS LOGIC (CRUD operations) related to the Employee model.
These functions are named for their purpose (e.g., create_employee) and DO NOT contain any CLI logic.
"""
import re
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Employee


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

    email_suffix = "@epicevents.com"
    final_email_prefix = base_email_prefix
    
    counter = 1
    while True:
        email = f"{final_email_prefix}{email_suffix}"
        
        exists = session.query(Employee).filter_by(email=email).one_or_none()
        
        if not exists:
            return email
        
        counter += 1
        final_email_prefix = f"{base_email_prefix}{counter}"


# --- PURE CRUD Operations (No CLI/Rich objects here) ---

def create_employee(session, full_name: str, phone: str, password: str, department: str) -> Employee:
    """
    Creates a new Employee record in the database.
    This is the pure business logic function.
    """
    try:
        email = format_email(full_name, session)
        
        new_employee = Employee(
            full_name=full_name,
            email=email,
            phone=phone,
            department=department
        )
        new_employee.password = password

        session.add(new_employee)
        session.commit()
        return new_employee

    except IntegrityError:
        session.rollback()
        raise ValueError("Database integrity error, possibly a duplicate email (should be prevented by format_email).")
    except SQLAlchemyError as e:
        session.rollback()
        raise Exception(f"Database error during creation: {e}")


def list_employees(session) -> list[Employee]:
    """
    Retrieves all employees from the database.
    """
    return session.query(Employee).all()


def update_employee(session, employee_id: int, update_data: dict) -> Employee:
    """
    Updates an existing Employee's data based on the provided dictionary.
    Raises ValueError if the employee is not found.
    """
    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()

    if not employee:
        raise ValueError(f"Employee with ID {employee_id} not found.")

    for key, value in update_data.items():
        if hasattr(employee, key):
            setattr(employee, key, value)
    
    try:
        session.commit()
        return employee
    except SQLAlchemyError as e:
        session.rollback()
        raise Exception(f"Database error during update: {e}")


def delete_employee(session, employee_id: int) -> None:
    """
    Deletes an Employee record from the database.
    Raises ValueError if the employee is not found.
    """
    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()

    if not employee:
        raise ValueError(f"Employee with ID {employee_id} not found.")
        
    try:
        session.delete(employee)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise Exception(f"Database error during deletion: {e}")
