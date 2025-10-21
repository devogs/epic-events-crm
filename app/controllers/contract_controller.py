"""
Contract Controller: Handles all business logic and CRUD operations related to the Contract model.
This module enforces permission checks for contract creation, updating, 
and filtering based on the user's role.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console
from sqlalchemy.orm import joinedload

from app.models import Client, Contract, Employee
from app.authentication import check_permission

import sentry_sdk

console = Console()

# =============================================================================
# --- CONTRACTS CRUD ---
# =============================================================================


def create_contract(
    session: Session,
    current_user: Employee,
    client_id: int,
    total_amount: Decimal,
    remaining_amount: Decimal,
    status_signed: bool,
) -> Contract | None:
    """
    Creates a new Contract.
    Permissions: Gestion only.
    """
    if not check_permission(current_user, "create_contract"):
        raise PermissionError("Permission denied. Only 'Gestion' can create contracts.")

    if total_amount <= 0 or remaining_amount < 0 or remaining_amount > total_amount:
        console.print("[bold red]ERROR:[/bold red] Invalid amounts.")
        return None

    client = session.query(Client).filter_by(id=client_id).one_or_none()
    if not client:
        console.print(
            f"[bold red]ERROR:[/bold red] Client with ID {client_id} not found."
        )
        return None

    if not client.sales_contact_id:
        console.print(
            "[bold red]ERROR:[/bold red] The client must have an " \
            "assigned sales contact before creating a contract."
        )
        return None

    try:
        new_contract = Contract(
            client_id=client_id,
            sales_contact_id=client.sales_contact_id,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            status_signed=status_signed,
        )
        session.add(new_contract)
        session.commit()
        return new_contract
    except IntegrityError:
        session.rollback()
        console.print(
            "[bold red]ERROR:[/bold red] Database integrity error " \
            "(e.g., non-existent client/sales contact)."
        )
        return None
    except Exception as e:
        session.rollback()
        sentry_sdk.capture_exception(e)
        console.print(
            f"[bold red]FATAL ERROR:[/bold red] An unexpected " \
            f"error occurred during contract creation: {e}"
        )
        return None


def list_contracts(
    session: Session, current_user: Employee, filter_signed: bool | None = None
) -> list[Contract]:
    """
    Lists all Contracts based on user permissions and optional filters.
    """
    query = session.query(Contract).options(joinedload(Contract.client))

    if current_user.department == "Commercial":
        query = query.join(Client).filter(Client.sales_contact_id == current_user.id)
    elif current_user.department == "Support":
        query = query.filter(Contract.status_signed == True)

    if filter_signed is not None:
        query = query.filter(Contract.status_signed == filter_signed)

    return query.all()


def update_contract(
    session: Session, current_user: Employee, contract_id: int, **kwargs
) -> Contract | None:
    """
    Updates a Contract record. Handles permissions and business rules.
    """
    is_gestion = current_user.department == "Gestion"

    try:
        contract = (
            session.query(Contract)
            .options(joinedload(Contract.client))
            .filter_by(id=contract_id)
            .one_or_none()
        )

        if not contract:
            console.print(
                f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found."
            )
            return None

        is_sales_contact = contract.sales_contact_id == current_user.id

        if not is_gestion and not is_sales_contact:
            raise PermissionError(
                "Permission denied. Only 'Gestion' or the assigned " \
                "'Commercial' contact can modify this contract."
            )

        updates_made = False

        if "total_amount" in kwargs:
            if not is_gestion:
                raise PermissionError(
                    "Only 'Gestion' can modify the total contract amount."
                )

            new_total = Decimal(kwargs["total_amount"])
            if new_total <= 0:
                raise ValueError("Total amount must be positive.")

            if new_total < contract.remaining_amount:
                contract.remaining_amount = (
                    new_total
                )

            contract.total_amount = new_total
            updates_made = True

        if "remaining_amount" in kwargs:
            new_remaining = Decimal(kwargs["remaining_amount"])
            if new_remaining < 0 or new_remaining > contract.total_amount:
                raise ValueError(
                    "Remaining amount must be between 0 and the total amount."
                )

            if not is_gestion and new_remaining > contract.remaining_amount:
                raise PermissionError(
                    "Only 'Gestion' can increase the remaining amount (cancel a payment)."
                )

            contract.remaining_amount = new_remaining
            updates_made = True

        if "status_signed" in kwargs:
            new_signed_status = bool(kwargs["status_signed"])

            if current_user.department == "Commercial" and not is_sales_contact:
                raise PermissionError(
                    "Commercial staff can only change the signed " \
                    "status for their own clients' contracts."
                )

            if not contract.status_signed and new_signed_status:

                message = (
                    f"Contract Signed: Contract ID {contract.id} ({contract.client.full_name}) "
                    f"by {current_user.full_name} ({current_user.department}). "
                    f"Total Amount: {contract.total_amount}."
                )
                sentry_sdk.capture_message(message, level="info")
                console.print(
                    f"[bold green]LOG INFO:[/bold green] Signature du " \
                    f"contrat enregistrée dans Sentry."
                )

            contract.status_signed = new_signed_status
            updates_made = True

        if "client_id" in kwargs:
            if not is_gestion:
                raise PermissionError("Only 'Gestion' can reassign the client ID.")

            new_client_id = kwargs["client_id"]
            new_client = session.query(Client).filter_by(id=new_client_id).one_or_none()
            if not new_client:
                raise ValueError(f"Client ID {new_client_id} not found.")

            contract.client_id = new_client_id
            updates_made = True

        if "sales_contact_id" in kwargs:
            if not is_gestion:
                raise PermissionError("Only 'Gestion' can reassign the sales contact.")

            new_sales_id = kwargs["sales_contact_id"]
            new_sales_contact = (
                session.query(Employee).filter_by(id=new_sales_id).one_or_none()
            )
            if not new_sales_contact or new_sales_contact.department != "Commercial":
                raise ValueError(
                    f"Sales Contact ID {new_sales_id} not found or is not a Commercial employee."
                )

            contract.sales_contact_id = new_sales_id
            updates_made = True

        if updates_made:
            session.commit()
            return contract
        return contract

    except Exception as e:
        session.rollback()
        sentry_sdk.capture_exception(e)
        console.print(f"[bold red]ERROR during contract update:[/bold red] {e}")
        return None
