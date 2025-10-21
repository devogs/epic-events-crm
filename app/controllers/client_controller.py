"""
Client Controller: Handles all CRUD operations related to the Client model.
Implements core business logic and data validation for clients.
"""

import re
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console

from app.models import Client, Employee, Role
from app.authentication import check_permission
from app.controllers.utils import is_valid_email, is_valid_phone

console = Console()

# =============================================================================
# --- CLIENTS CRUD ---
# =============================================================================


def create_client(
    session: Session,
    current_user: Employee,
    full_name: str,
    email: str,
    phone: str,
    company_name: str,
) -> Client | None:
    """
    Creates a new Client record and automatically assigns the creator as the sales contact.
    Permissions: Commercial (creates their own clients) or Gestion.
    """
    if not check_permission(current_user, "create_client"):
        raise PermissionError("Permission denied to create a client.")

    if not full_name or not email or not phone:
        console.print("[bold red]ERROR:[/bold red] Missing required field(s).")
        return None

    if not is_valid_email(email):
        console.print("[bold red]ERROR:[/bold red] Invalid email format.")
        return None

    if not is_valid_phone(phone):
        console.print("[bold red]ERROR:[/bold red] Invalid phone number format.")
        return None

    sales_contact_id = current_user.id

    try:
        new_client = Client(
            full_name=full_name,
            email=email,
            phone=phone,
            company_name=company_name,
            sales_contact_id=sales_contact_id,
        )

        session.add(new_client)
        session.commit()
        return new_client

    except IntegrityError:
        session.rollback()
        console.print(
            "[bold red]ERROR:[/bold red] A client with this email already exists."
        )
        return None
    except Exception as e:
        session.rollback()
        console.print(
            f"[bold red]FATAL ERROR:[/bold red] An unexpected error occurred during client creation: {e}"
        )
        return None


def list_clients(
    session: Session, current_user: Employee, filter_by_sales_id: int | None = None
) -> list[Client]:
    """
    Retrieves a list of clients, respecting filtering and permissions.
    """
    if not check_permission(current_user, "view_clients"):
        raise PermissionError("Permission denied to view clients.")

    query = session.query(Client)

    if current_user.department == "Commercial":
        if filter_by_sales_id is not None:
            query = query.filter(Client.sales_contact_id == filter_by_sales_id)

    elif (
        current_user.department in ["Gestion", "Support"]
        and filter_by_sales_id is not None
    ):
        query = query.filter(Client.sales_contact_id == filter_by_sales_id)

    return query.all()


def update_client(
    session: Session, current_user: Employee, client_id: int, **kwargs
) -> Client | None:
    """
    Updates an existing Client record.
    Permissions: Gestion can update any client. Commercial can only update clients assigned to them.
    """
    client = session.query(Client).filter_by(id=client_id).one_or_none()

    if not client:
        console.print(
            f"[bold red]ERROR:[/bold red] Client with ID {client_id} not found."
        )
        return None

    if not check_permission(current_user, "update_client"):
        raise PermissionError("Permission denied to update clients.")

    if (
        current_user.department == "Commercial"
        and client.sales_contact_id != current_user.id
    ):
        console.print(
            "[bold red]ERROR:[/bold red] You can only update clients assigned to you."
        )
        return None

    try:
        updates_made = False

        if "full_name" in kwargs and kwargs["full_name"]:
            client.full_name = kwargs["full_name"]
            updates_made = True

        if "email" in kwargs and kwargs["email"]:
            if not is_valid_email(kwargs["email"]):
                raise ValueError("Invalid email format.")
            client.email = kwargs["email"]
            updates_made = True

        if "phone" in kwargs and kwargs["phone"]:
            if not is_valid_phone(kwargs["phone"]):
                raise ValueError("Invalid phone number format.")
            client.phone = kwargs["phone"]
            updates_made = True

        if "company_name" in kwargs and kwargs["company_name"]:
            client.company_name = kwargs["company_name"]
            updates_made = True

        if "sales_contact_id" in kwargs and kwargs["sales_contact_id"]:
            if current_user.department != "Gestion":
                raise PermissionError("Only 'Gestion' can reassign the sales contact.")

            new_sales_id = kwargs["sales_contact_id"]
            new_sales_contact = (
                session.query(Employee)
                .filter(
                    Employee.id == new_sales_id,
                    Employee.role.has(Role.name == "Commercial"),
                )
                .one_or_none()
            )

            if not new_sales_contact:
                raise ValueError(
                    f"Sales contact ID {new_sales_id} must be a Commercial employee."
                )

            client.sales_contact_id = new_sales_id
            updates_made = True

        if updates_made:
            session.commit()
            return client
        else:
            return client

    except Exception as e:
        session.rollback()
        console.print(
            f"[bold red]ERREUR lors de la modification du client:[/bold red] {e}"
        )
        return None
