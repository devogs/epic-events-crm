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
    Permissions: Management only.
    """
    if not check_permission(current_user, 'create_contract'):
        raise PermissionError("Permission denied. Only 'Management' can create contracts.")

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
            client=client,
            sales_contact_id=client.sales_contact_id, # Contract inherits the client's Sales Contact
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            status_signed=status_signed
        )
        session.add(new_contract)
        session.commit()
        return new_contract
    except IntegrityError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] Integrity constraint failed (e.g., client_id not found or duplicate key): {e}")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR during contract creation:[/bold red] {e}")
        return None


def list_contracts(session: Session, current_user: Employee, filter_by_sales_id: int | None = None) -> list[Contract]:
    """
    Retrieves a list of contracts, filtered by sales contact if requested.
    Permissions: 
    - Management/Support: Can view all or filter by Sales ID.
    - Commercial: Only views their own contracts.
    """
    if not check_permission(current_user, 'view_contracts'):
        raise PermissionError("Permission denied to view contracts.")

    # Eager loading related entities for display optimization
    query = session.query(Contract).options(joinedload(Contract.client), joinedload(Contract.sales_contact)) 

    # 1. Commercial Role: Always restricted to their own contracts.
    if current_user.department == 'Commercial':
        query = query.filter(Contract.sales_contact_id == current_user.id)
        
    # 2. Management/Support Roles: Can see all (filter_by_sales_id is None) 
    # or filter by a specific Sales ID.
    elif filter_by_sales_id is not None:
         query = query.filter(Contract.sales_contact_id == filter_by_sales_id)
         
    # If it's Management or Support and filter_by_sales_id is None, no filter is added, and all contracts are returned.

    return query.all()


def update_contract(session: Session, current_user: Employee, contract_id: int, **kwargs) -> Contract | None:
    """
    Updates an existing Contract.
    Permissions:
    - Commercial: Update remaining amount and signed status for their own contracts.
    - Management: Update all fields including sales contact reassignment.
    """
    try:
        contract = session.query(Contract).filter_by(id=contract_id).one_or_none()
        if not contract:
            console.print(f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found.")
            return None
        
        # Check if the current user is the Sales Contact for the contract
        is_sales_contact = (contract.sales_contact_id == current_user.id)

        # Permission check: Commercial staff can update the remaining amount and signed status for their own clients' contracts.
        if current_user.department == 'Commercial' and not is_sales_contact:
            raise PermissionError("Commercial staff can only update the remaining amount and signed status for their own contracts.")

        updates_made = False

        # --- Remaining Amount (REMAINING) ---
        if 'remaining_amount' in kwargs:
            try:
                new_remaining = Decimal(kwargs['remaining_amount'])
            except:
                raise ValueError("Remaining amount must be a valid number.")
                
            if new_remaining < 0 or new_remaining > contract.total_amount:
                raise ValueError(f"Remaining amount must be between 0 and total amount ({contract.total_amount}).") 
            
            contract.remaining_amount = new_remaining
            updates_made = True

        # --- Total Amount (TOTAL) ---
        if 'total_amount' in kwargs:
            if current_user.department not in ['Gestion']:
                raise PermissionError("Only 'Management' can modify the total amount.")
                
            try:
                new_total = Decimal(kwargs['total_amount'])
            except:
                raise ValueError("Total amount must be a valid number.")
                
            if new_total <= 0:
                raise ValueError("Total amount must be greater than 0.")
                
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
            
        # --- Sales Contact (Reassignment logic, reserved for Management) ---
        if 'sales_contact_id' in kwargs:
            if current_user.department != 'Gestion':
                raise PermissionError("Only 'Management' can reassign the sales contact.")
            
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