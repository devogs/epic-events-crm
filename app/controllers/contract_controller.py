"""
Contract Controller: Handles all CRUD operations related to the Contract model.
Implements core business logic and data validation for contracts.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console
from sqlalchemy.orm import joinedload 

from app.models import Client, Contract, Employee
from app.authentication import check_permission

console = Console()

# =============================================================================
# --- CONTRACTS CRUD ---
# =============================================================================

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

    try:
        new_contract = Contract(
            client_id=client_id,
            sales_contact_id=client.sales_contact_id, 
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            status_signed=status_signed # <-- NEW: Explicit signed status
        )
        session.add(new_contract)
        session.commit()
        return new_contract
    
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR during contract creation:[/bold red] {e}")
        return None


def list_contracts(session: Session, current_user: Employee, filter_by_sales_id: int | None = None, filter_signed: bool | None = None, filter_unpaid: bool = False, filter_unsigned: bool | None = None) -> list[Contract]:
    """
    Retrieves a list of contracts.
    Permissions: Gestion sees all. Commercial sees contracts for their clients. Support sees all.
    (Function kept consistent with existing logic)
    """
    if not check_permission(current_user, 'view_contracts'):
        raise PermissionError("Permission denied to view contracts.")

    # Eager load the client and sales contact for display in the view
    query = session.query(Contract).options(
        joinedload(Contract.client),
        joinedload(Contract.sales_contact)
    )

    # Authorization Filters
    if current_user.department == 'Commercial':
        # Commercial only sees contracts for their clients
        query = query.join(Client).filter(Client.sales_contact_id == current_user.id)
    
    # CLI Filters
    if filter_by_sales_id is not None:
        query = query.filter(Contract.sales_contact_id == filter_by_sales_id)
        
    if filter_signed is True:
        query = query.filter(Contract.status_signed == True)
    elif filter_unsigned is True:
        query = query.filter(Contract.status_signed == False)
        
    if filter_unpaid:
        query = query.filter(Contract.remaining_amount > Decimal('0.00'))
        
    return query.all()


def update_contract(session: Session, current_user: Employee, contract_id: int, **kwargs) -> Contract | None:
    """
    Updates an existing Contract record.
    Permissions: Gestion can update all. Commercial can update their clients' contracts (excluding total amount).
    """
    contract = session.query(Contract).filter_by(id=contract_id).one_or_none()
    
    if not contract:
        console.print(f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found.")
        return None
        
    if not check_permission(current_user, 'update_contract'):
        raise PermissionError("Permission denied to update contracts.")
        
    # Secondary Authorization Check for Commercial
    is_sales_contact = contract.sales_contact_id == current_user.id
    if current_user.department == 'Commercial' and not is_sales_contact:
        console.print("[bold red]ERROR:[/bold red] You can only update contracts assigned to your clients.")
        return None

    try:
        updates_made = False

        # --- Remaining Amount ---
        if 'remaining_amount' in kwargs:
            new_remaining = Decimal(str(kwargs['remaining_amount']))
            if new_remaining < 0 or new_remaining > contract.total_amount:
                raise ValueError("Remaining amount is invalid.")

            contract.remaining_amount = new_remaining
            # REMOVED: Implicit signed status update
            updates_made = True
            
        # --- Total Amount ---
        if 'total_amount' in kwargs:
            if current_user.department != 'Gestion':
                raise PermissionError("Only 'Gestion' can change the total contract amount.")
            
            new_total = Decimal(str(kwargs['total_amount']))
            if new_total <= 0:
                raise ValueError("Total amount must be positive.")
            
            if new_total < contract.remaining_amount:
                 raise ValueError("Total amount cannot be less than the remaining amount.")
            
            contract.total_amount = new_total
            updates_made = True

        # --- Signed Status (NEW ISOLATED PARAMETER) ---
        if 'status_signed' in kwargs:
            if current_user.department == 'Commercial' and not is_sales_contact:
                 raise PermissionError("Commercial staff can only change the signed status for their own clients' contracts.")
            
            contract.status_signed = bool(kwargs['status_signed'])
            updates_made = True
            
        # --- Sales Contact (Reassignment logic, reserved for Gestion) ---
        if 'sales_contact_id' in kwargs:
            if current_user.department != 'Gestion':
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
        else:
            return contract
            
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR during contract update:[/bold red] {e}")
        return None