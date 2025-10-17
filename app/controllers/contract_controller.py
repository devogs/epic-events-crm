from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console
from sqlalchemy.orm import joinedload

from app.models import Client, Contract, Employee
from app.authentication import check_permission

console = Console()

def create_contract(session: Session, current_user: Employee, client_id: int, total_amount: Decimal, remaining_amount: Decimal, status_signed: bool) -> Contract | None:
    """
    Creates a new Contract.
    Permissions: Gestion only.
    """
    if not check_permission(current_user, 'create_contract'):
        raise PermissionError("Permission denied. Only 'Gestion' can create contracts.")

    if total_amount <= 0 or remaining_amount < 0 or remaining_amount > total_amount:
        console.print("[bold red]ERROR:[/bold red] Invalid amounts.")
        return None

    client = session.query(Client).filter_by(id=client_id).one_or_none()
    if not client:
        console.print(f"[bold red]ERROR:[/bold red] Client with ID {client_id} not found.")
        return None

    if not client.sales_contact_id:
        console.print("[bold red]ERROR:[/bold red] The client must have an assigned sales contact before creating a contract.")
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
    except IntegrityError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] Database integrity error during contract creation: {e}")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR during contract creation:[/bold red] {e}")
        return None


def list_contracts(session: Session, current_user: Employee, filter_by_sales_id: int | None = None, filter_by_signed_status: bool | None = None) -> list[Contract]:
    """Lists contracts, optionally filtered by sales contact or signed status."""
    query = session.query(Contract).options(joinedload(Contract.client), joinedload(Contract.sales_contact))

    if current_user.department == 'Commercial' and filter_by_sales_id is None:
        query = query.filter(Contract.sales_contact_id == current_user.id)
    elif filter_by_sales_id:
        query = query.filter(Contract.sales_contact_id == filter_by_sales_id)

    if filter_by_signed_status is not None:
        query = query.filter(Contract.status_signed == filter_by_signed_status)

    return query.all()


def update_contract(session: Session, current_user: Employee, contract_id: int, **kwargs) -> Contract | None:
    """
    Updates an existing contract.
    Permissions: Gestion for all fields. Commercial for status_signed (their assigned contracts only).
    """
    contract = session.query(Contract).filter_by(id=contract_id).one_or_none()

    if not contract:
        console.print(f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found.")
        return None

    is_gestion = current_user.department == 'Gestion'
    is_sales_contact = contract.sales_contact_id == current_user.id

    # Permission check for Commercial staff
    if current_user.department == 'Commercial':
        # Commercial staff can only update status_signed on their own contracts.
        allowed_keys = ['status_signed']
        for key in kwargs:
            if key not in allowed_keys:
                raise PermissionError(f"Commercial staff can only modify {', '.join(allowed_keys)}.")
        if not is_sales_contact:
            raise PermissionError("Commercial staff can only update contracts they are assigned to.")

    # Permission check for Support staff
    elif current_user.department == 'Support':
        raise PermissionError("Support staff cannot update contracts.")

    updates_made = False
    try:
        # Financial fields (Gestion only)
        if 'total_amount' in kwargs:
            if not is_gestion:
                raise PermissionError("Only 'Gestion' can update the total amount.")
            new_total = Decimal(kwargs['total_amount'])
            if new_total <= 0:
                raise ValueError("Total amount must be greater than 0.")
            if new_total < contract.remaining_amount:
                raise ValueError("Total amount cannot be less than the remaining amount.")
            contract.total_amount = new_total
            updates_made = True

        if 'remaining_amount' in kwargs:
            if not is_gestion:
                raise PermissionError("Only 'Gestion' can update the remaining amount.")
            new_remaining = Decimal(kwargs['remaining_amount'])
            if new_remaining < 0 or new_remaining > contract.total_amount:
                raise ValueError("Remaining amount must be between 0 and the total amount.")
            contract.remaining_amount = new_remaining
            updates_made = True

        # Status Signed (Commercial/Gestion)
        if 'status_signed' in kwargs:
            # Commercial permission check is handled above.
            contract.status_signed = bool(kwargs['status_signed'])
            updates_made = True

        # --- Relational fields (Gestion only) ---

        if 'client_id' in kwargs:
            if not is_gestion:
                raise PermissionError("Only 'Gestion' can reassign the client ID.")

            new_client_id = kwargs['client_id']
            new_client = session.query(Client).filter_by(id=new_client_id).one_or_none()
            if not new_client:
                raise ValueError(f"Client ID {new_client_id} not found.")

            contract.client_id = new_client_id
            updates_made = True

        if 'sales_contact_id' in kwargs:
            if not is_gestion:
                raise PermissionError("Only 'Gestion' can reassign the sales contact.")

            new_sales_id = kwargs['sales_contact_id']
            new_sales_contact = session.query(Employee).filter_by(id=new_sales_id).one_or_none()
            if not new_sales_contact or new_sales_contact.department != 'Commercial':
                 raise ValueError(f"Sales Contact ID {new_sales_id} not found or is not a Commercial employee.")

            contract.sales_contact_id = new_sales_id
            updates_made = True

        if updates_made:
            session.commit()
            return contract
        return contract

    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR during contract update:[/bold red] {e}")
        return None