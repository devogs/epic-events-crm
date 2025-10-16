"""
Contract Controller: Handles all CRUD operations related to the Contract model.
Implements core business logic and data validation for contracts.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console
from sqlalchemy.orm import joinedload # Added import for optimization

from app.models import Client, Contract, Employee
from app.authentication import check_permission

console = Console()

# =============================================================================
# --- CONTRACTS CRUD ---
# =============================================================================

def create_contract(session: Session, current_user: Employee, client_id: int, total_amount: Decimal, remaining_amount: Decimal) -> Contract | None:
    """
    Creates a new Contract.
    Permissions: Gestion only.
    """
    if not check_permission(current_user, 'create_contract'):
        raise PermissionError("Permission denied. Only 'Gestion' can create contracts.")

    # Validation: Basic amount check
    if total_amount <= 0 or remaining_amount < 0 or remaining_amount > total_amount:
        console.print("[bold red]ERROR:[/bold red] Invalid amounts.")
        return None

    # Check if client exists
    client = session.query(Client).filter_by(id=client_id).one_or_none()
    if not client:
        console.print(f"[bold red]ERROR:[/bold red] Client with ID {client_id} not found.")
        return None

    try:
        # Sales contact is automatically inherited from the client
        new_contract = Contract(
            client_id=client_id,
            sales_contact_id=client.sales_contact_id, 
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            status_signed=(remaining_amount == total_amount) # Initial state
        )
        session.add(new_contract)
        session.commit()
        return new_contract
    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERROR:[/bold red] Database integrity error (e.g., non-existent foreign key).")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]FATAL ERROR:[/bold red] An unexpected error occurred during contract creation: {e}")
        return None


def list_contracts(
    session: Session, 
    current_user: Employee, 
    filter_by_sales_id: int | None = None, 
    filter_signed: bool | None = None,
    filter_unpaid: bool = False,
    filter_unsigned: bool = False
) -> list[Contract]:
    """
    Retrieves a list of contracts based on user department and applied filters.
    Permissions: Gestion sees all. Commercial sees their own. Support sees all.
    """
    try:
        if not check_permission(current_user, 'view_contracts'):
            # Only Gestion, Commercial, and Support should have this permission
            raise PermissionError("Permission denied to view contracts.")

        # 1. Base Query with optimization (eager loading client and sales contact)
        query = session.query(Contract).options(
            joinedload(Contract.client),
            joinedload(Contract.sales_contact)
        )

        # 2. Authorization Filters (Department restrictions)
        if current_user.department == 'Commercial':
            # Commercial only sees contracts where they are the sales contact
            query = query.filter(Contract.sales_contact_id == current_user.id)
            
        # FIX: Support sees all contracts to check details for events. No filter applied here.

        # 3. CLI Filters (Applied across the board)
        
        # Filter by specific Sales Contact ID (Used primarily by Gestion)
        if filter_by_sales_id is not None:
            query = query.filter(Contract.sales_contact_id == filter_by_sales_id)
            
        # Filter by explicit signed status (True/False)
        if filter_signed is not None:
            query = query.filter(Contract.status_signed == filter_signed)
            
        # Filter for unsigned contracts (convenience filter, overrides filter_signed=True)
        if filter_unsigned:
            query = query.filter(Contract.status_signed == False)

        # Filter for not fully paid contracts
        if filter_unpaid:
            # Check where remaining_amount > 0
            query = query.filter(Contract.remaining_amount > Decimal('0.00'))
            
        return query.all()

    except PermissionError as e:
        console.print(f"[bold red]PERMISSION ERROR:[/bold red] {e}")
        return []
    except Exception as e:
        console.print(f"[bold red]FATAL ERROR during contract listing:[/bold red] An unexpected error occurred: {e}")
        return []


def update_contract(session: Session, current_user: Employee, contract_id: int, **kwargs) -> Contract | None:
    """
    Updates a Contract record.
    Permissions: Gestion can update anything. Commercial can update remaining_amount.
    """
    if not check_permission(current_user, 'update_contract'):
        raise PermissionError("Permission denied to update contracts.")
        
    contract = session.query(Contract).filter_by(id=contract_id).one_or_none()
    
    if not contract:
        console.print(f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found.")
        return None

    # Secondary Authorization Check: Commercial can only update their own contracts
    if current_user.department == 'Commercial' and contract.sales_contact_id != current_user.id:
        console.print("[bold red]ERROR:[/bold red] You can only update contracts assigned to your clients.")
        return None

    try:
        updates_made = False

        if 'remaining_amount' in kwargs:
            # Commercial and Gestion can update remaining_amount
            new_remaining = Decimal(str(kwargs['remaining_amount']))
            
            # Validation
            if new_remaining < 0 or new_remaining > contract.total_amount:
                raise ValueError("Remaining amount is invalid (must be between 0 and total amount).")

            contract.remaining_amount = new_remaining
            
            # CRITICAL: Automatically sign/unsign based on remaining amount
            contract.status_signed = (new_remaining == Decimal('0.00'))
            updates_made = True
            
        if 'total_amount' in kwargs:
            # Only Gestion can change the total contract amount
            if current_user.department != 'Gestion':
                raise PermissionError("Only 'Gestion' can change the total contract amount.")
            
            new_total = Decimal(str(kwargs['total_amount']))
            
            # Validation
            if new_total <= 0:
                raise ValueError("Total amount must be positive.")
            if new_total < contract.remaining_amount:
                 raise ValueError("Total amount cannot be less than the remaining amount.")
            
            contract.total_amount = new_total
            updates_made = True
            
        if 'sales_contact_id' in kwargs:
            # Only Gestion can reassign the Sales contact
            if current_user.department != 'Gestion':
                raise PermissionError("Only 'Gestion' can reassign the sales contact.")
                
            new_sales_id = kwargs['sales_contact_id']
            new_sales_contact = session.query(Employee).filter_by(id=new_sales_id).one_or_none()
            
            if not new_sales_contact or new_sales_contact.department != 'Commercial':
                raise ValueError(f"Sales ID {new_sales_id} not found or is not a 'Commercial' employee.")
            
            contract.sales_contact_id = new_sales_contact.id
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