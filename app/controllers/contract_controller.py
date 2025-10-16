"""
Contract Controller: Handles all CRUD operations related to the Contract model.
Implements core business logic and data validation for contracts.
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console

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
            status_signed=(remaining_amount == Decimal('0.00')), 
        )

        session.add(new_contract)
        session.commit()
        return new_contract

    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR FATALE lors de la création du contrat:[/bold red] {e}")
        return None

def list_contracts(
    session: Session, 
    current_user: Employee, 
    # CRITIQUE: Changer filter_signed par filter_by_status pour correspondre à la vue
    filter_by_status: bool | None = None,    
    filter_by_unpaid: bool = False,
    filter_by_commercial_id: int | None = None
) -> list[Contract]:
    """
    Retrieves a list of contracts, filtered by permissions, status, unpaid, or commercial.
    """
    if not check_permission(current_user, 'view_contracts'):
        raise PermissionError("Permission denied to view contracts.")

    query = session.query(Contract)

    # 1. LOGIQUE DE PERMISSION ET FILTRAGE PAR COMMERCIAL
    if current_user.department == 'Commercial':
        # Commercial : Seulement les contrats de leurs clients
        query = query.filter(Contract.sales_contact_id == current_user.id)
        
    elif current_user.department == 'Support':
        # Support : Seulement les contrats SIGNÉS
        query = query.filter(Contract.status_signed == True)
        
    elif current_user.department == 'Gestion' and filter_by_commercial_id is not None:
        # Gestion : Filtre optionnel par commercial
        query = query.filter(Contract.sales_contact_id == filter_by_commercial_id)


    # 2. LOGIQUE DE FILTRE D'ÉTAT (demandée par la vue)
    # filter_by_status gère les options "Tous" (None), "Signés" (True), "Non signés" (False)
    if filter_by_status is not None:
        query = query.filter(Contract.status_signed == filter_by_status)

    # filter_by_unpaid gère l'option "Non entièrement payés"
    if filter_by_unpaid:
        query = query.filter(Contract.remaining_amount > Decimal('0.00'))
        
    return query.all()

def update_contract(session: Session, current_user: Employee, contract_id: int, **kwargs) -> Contract | None:
    """
    Updates an existing Contract record.
    Permissions: Gestion can update all. Commercial can only update amounts/status for their clients' contracts.
    """
    contract = session.query(Contract).filter_by(id=contract_id).one_or_none()
    
    if not contract:
        console.print(f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found.")
        return None

    if not check_permission(current_user, 'update_contract'):
        raise PermissionError("Permission denied to update contracts.")
        
    if current_user.department == 'Commercial' and contract.sales_contact_id != current_user.id:
        console.print("[bold red]ERROR:[/bold red] You can only update contracts assigned to your clients.")
        return None

    try:
        updates_made = False

        if 'remaining_amount' in kwargs:
            new_remaining = Decimal(str(kwargs['remaining_amount']))
            if new_remaining < 0 or new_remaining > contract.total_amount:
                raise ValueError("Remaining amount is invalid.")

            contract.remaining_amount = new_remaining
            contract.status_signed = (new_remaining == Decimal('0.00'))
            updates_made = True
            
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

        if updates_made:
            session.commit()
            return contract
        else:
            return contract
            
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR lors de la modification du contrat:[/bold red] {e}")
        return None