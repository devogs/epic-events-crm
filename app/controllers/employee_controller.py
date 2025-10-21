"""
Employee Controller: Handles all CRUD operations related to the Employee model.
These functions are called by the department menus (like Management Menu).
"""

import re
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from rich.console import Console
from rich.table import Table

from app.models import Employee, Role
from app.authentication import hash_password, check_permission

import sentry_sdk


console = Console()

DEPARTMENT_OPTIONS = {"1": "Gestion", "2": "Commercial", "3": "Support"}

# --- Utility Functions ---


def get_role_id_by_name(session: Session, role_name: str) -> int | None:
    """Retrieves the Role ID from the Role name."""
    role = session.query(Role).filter_by(name=role_name).one_or_none()
    return role.id if role else None


def format_email(full_name: str, session: Session) -> str:
    """
    Generates a unique email address based on the employee's full name.
    Format: firstname.lastname[N]@epicevents.com
    """
    base_name = re.sub(r"[^a-zA-Z\s]", "", full_name).lower().strip()
    parts = base_name.split()

    if len(parts) > 1:
        base_email_prefix = f"{parts[0]}.{parts[-1]}"
    elif parts:
        base_email_prefix = parts[0]
    else:
        base_email_prefix = "unknown"

    base_email = f"{base_email_prefix}@epicevents.com"
    email = base_email

    # Check for existing email and add a number if necessary
    counter = 1
    while session.query(Employee).filter_by(email=email).first():
        email = f"{base_email_prefix}{counter}@epicevents.com"
        counter += 1

    return email


# =============================================================================
# --- EMPLOYEES CRUD ---
# =============================================================================


def create_employee(
    session: Session,
    current_user: Employee,
    full_name: str,
    email: str,
    phone: str,
    department: str,
    password: str,
) -> Employee | None:
    """
    Creates a new employee (Management only).
    """
    if current_user.department != "Gestion":
        console.print(
            "[bold red]Permission denied.[/bold red] Only the 'Gestion' " \
            "department can create employees."
        )
        return None

    if not full_name or not phone or not department or not password:
        console.print("[bold red]ERROR:[/bold red] Missing required field(s).")
        return None

    if not email:
        email = format_email(full_name, session)
        console.print(f"[bold yellow]INFO:[/bold yellow] Email generated: {email}")
    elif not re.fullmatch(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}$", email):
        console.print("[bold red]ERROR:[/bold red] Invalid email format.")
        return None

    role_id = get_role_id_by_name(session, department)

    if role_id is None:
        console.print(
            f"[bold red]ERROR:[/bold red] Department '{department}' " \
            "is invalid or role not found in DB."
        )
        return None

    try:
        new_employee = Employee(
            full_name=full_name,
            email=email,
            phone=phone,
            role_id=role_id,
            password=password,
        )

        session.add(new_employee)
        session.commit()

        sentry_sdk.capture_message(
            f"Employee CREATED: {new_employee.full_name} "
            f"(ID: {new_employee.id}) in "
            f"{new_employee.department} by User ID {current_user.id}",
            level="info",
        )

        return new_employee

    except IntegrityError:
        session.rollback()
        sentry_sdk.capture_exception()
        console.print(
            "[bold red]ERROR:[/bold red] Database integrity error." \
            "Check if the provided email/phone is already in use."
        )
        return None
    except Exception as e:
        session.rollback()
        sentry_sdk.capture_exception(e)
        console.print(
            f"[bold red]FATAL ERROR:[/bold red] "
            f"An unexpected error occurred during employee creation: {e}"
        )
        return None


def list_employees(session: Session) -> list[Employee]:
    """
    Retrieves a list of all employees.
    """
    return session.query(Employee).all()


def update_employee(
    session: Session, current_user: Employee, employee_id: int, **kwargs
) -> Employee | None:
    """
    Updates an existing employee record. Only 'Gestion' can perform this action.
    """
    if not check_permission(current_user, "update_employee"):
        console.print(
            "[bold red]Permission denied.[/bold red] Only the " \
            "'Gestion' department can update employees."
        )
        return None

    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()

    if not employee:
        console.print(
            f"[bold red]ERROR:[/bold red] Employee with ID {employee_id} not found."
        )
        return None

    try:
        updates_made = False

        if "full_name" in kwargs and kwargs["full_name"]:
            employee.full_name = kwargs["full_name"]
            updates_made = True

        if "email" in kwargs and kwargs["email"]:
            if not re.fullmatch(
                r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}$", kwargs["email"]
            ):
                raise ValueError("Invalid email format.")
            employee.email = kwargs["email"]
            updates_made = True

        if "phone" in kwargs and kwargs["phone"]:
            employee.phone = kwargs["phone"]
            updates_made = True

        if "password" in kwargs and kwargs["password"]:
            employee.password = kwargs["password"]
            updates_made = True

        if (
            "department" in kwargs
            and kwargs["department"]
            and kwargs["department"] != employee.department
        ):
            new_role_name = kwargs["department"]
            new_role_id = get_role_id_by_name(session, new_role_name)

            if new_role_id is None:
                raise ValueError(
                    f"Department '{new_role_name}' is invalid or role not found."
                )

            employee.role_id = new_role_id
            updates_made = True

        if updates_made:
            session.commit()

            sentry_sdk.set_context(
                "employee_update",
                {
                    "employee_id": employee.id,
                    "updated_by": current_user.id,
                    "updates": kwargs,
                },
            )
            sentry_sdk.capture_message(
                f"Employee UPDATED: {employee.full_name} "
                f"(ID: {employee.id}). "
                f"Fields modified: {list(kwargs.keys())}.",
                level="info",
            )
            sentry_sdk.set_context("employee_update", {})

            return employee
        else:
            return employee

    except ValueError as e:
        session.rollback()
        sentry_sdk.capture_exception(e)
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        return None
    except IntegrityError:
        session.rollback()
        sentry_sdk.capture_exception()
        console.print(
            "[bold red]ERROR:[/bold red] Database integrity error." \
            "Check if the provided email/phone is already in use."
        )
        return None
    except Exception as e:
        session.rollback()
        sentry_sdk.capture_exception(e)
        console.print(
            f"[bold red]FATAL ERROR:[/bold red] An unexpected "
            f"error occurred during employee update: {e}"
        )
        return None


def delete_employee(session: Session, employee_id: int) -> bool:
    """
    Deletes an Employee record.
    """
    employee = session.query(Employee).filter_by(id=employee_id).one_or_none()

    if not employee:
        return False

    try:
        if employee.department == "Gestion":
            gestion_count = (
                session.query(Employee)
                .join(Role)
                .filter(Role.name == "Gestion")
                .count()
            )
            if gestion_count <= 1:
                raise ValueError(
                    "Cannot delete the last remaining employee from the 'Gestion' department."
                )

        session.delete(employee)
        session.commit()
        return True

    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] {e}")
        return False
    except SQLAlchemyError as e:
        session.rollback()
        sentry_sdk.capture_exception(e)
        console.print(
            f"[bold red]ERROR:[/bold red] Failed to delete employee. Details: {e}"
        )
        return False
