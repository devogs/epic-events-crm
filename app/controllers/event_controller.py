"""
Event Controller: Handles all CRUD operations related to the Event model.
Implements core business logic and data validation for events.
"""
import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console
from sqlalchemy.orm import joinedload 
from sqlalchemy.sql.expression import and_ 

from app.models import Contract, Event, Employee, Role 
from app.authentication import check_permission

console = Console()

# =============================================================================
# --- EVENTS CRUD ---
# =============================================================================

def create_event(
    session: Session, 
    current_user: Employee, 
    contract_id: int, 
    name: str, 
    start_date: datetime.datetime,  
    end_date: datetime.datetime,    
    location: str, 
    attendees: int, 
    notes: str,
    support_contact_id: int | None = None
) -> Event | None:
    """
    Creates a new Event for a signed contract.
    Permissions: Commercial only, for their signed contracts.
    """
    try:
        if not check_permission(current_user, 'create_event'):
            raise PermissionError("Permission denied to create events.")

        contract = session.query(Contract).filter_by(id=contract_id).one_or_none()
        
        if not contract:
            raise ValueError(f"Contract with ID {contract_id} not found.")
            
        if not contract.status_signed:
            raise ValueError("Cannot create an event for an unsigned contract.")

        if current_user.department == 'Commercial' and contract.sales_contact_id != current_user.id:
            raise PermissionError("You can only create events for your clients' contracts.")
            
        if start_date >= end_date:
            raise ValueError("Start date must be before end date.")
            
        if attendees < 0:
            raise ValueError("Attendees count cannot be negative.")

        new_event = Event(
            contract_id=contract_id,
            name=name,
            attendees=attendees,
            event_start=start_date,
            event_end=end_date,
            location=location,
            notes=notes,
            support_contact_id=support_contact_id 
        )

        session.add(new_event)
        session.commit()
        return new_event

    except PermissionError as e:
        session.rollback()
        console.print(f"[bold red]PERMISSION ERROR:[/bold red] {e}")
        return None
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]VALIDATION ERROR:[/bold red] {e}")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]FATAL ERROR during event creation:[/bold red] An unexpected error occurred: {e}")
        return None


def list_events(
    session: Session, 
    current_user: Employee, 
    filter_by_support_id: int | None = None, 
    filter_unassigned: bool = False,       
) -> list[Event]:    
    """
    Retrieves a list of events.
    Permissions: Gestion sees all. Commercial sees events for their contracts. Support sees all, but applies filters.
    """
    try:
        if not check_permission(current_user, 'view_events'):
            raise PermissionError("Permission denied to view events.")

        # 1. Requête de base avec optimisation
        query = session.query(Event).options(
            joinedload(Event.contract),
            joinedload(Event.support_contact)
        )

        # 2. Filtres d'Autorisation (Restriction par département)
        if current_user.department == 'Commercial':
            # Restriction stricte: Le Commercial voit uniquement les événements de ses contrats
            query = query.join(Contract).filter(Contract.sales_contact_id == current_user.id)
            
        # NOUVELLE LOGIQUE POUR LE SUPPORT : PAS DE RESTRICTION PAR DÉFAUT.
        # Le Support a le droit de lire TOUS les événements.
        # Le filtre pour ses propres événements est appliqué via filter_by_support_id (voir point 3).
        # elif current_user.department == 'Support': 
        #    PAS DE FILTRE PAR DÉFAUT ICI pour répondre au besoin de voir TOUT.
        
        # 3. Filtres CLI (Appliqués à TOUS les utilisateurs sauf si contredit par le filtre d'autorisation)
        
        # Filtre par ID support explicite
        if filter_by_support_id is not None:
            query = query.filter(Event.support_contact_id == filter_by_support_id)
            
        # Filtre pour les non-assignés
        if filter_unassigned:
            query = query.filter(Event.support_contact_id.is_(None))
        
        return query.all()

    except PermissionError as e:
        console.print(f"[bold red]PERMISSION ERROR:[/bold red] {e}")
        return []
    except Exception as e:
        console.print(f"[bold red]FATAL ERROR during event listing:[/bold red] An unexpected error occurred: {e}")
        return []


def update_event(session: Session, current_user: Employee, event_id: int, **kwargs) -> Event | None:
    """
    Updates an existing Event record.
    Permissions: Gestion can update all. Commercial can update unassigned events for their contracts. 
    Support can update ONLY their assigned events.
    """
    event = session.query(Event).options(joinedload(Event.contract)).filter(Event.id == event_id).one_or_none()
    
    if not event:
        console.print(f"[bold red]ERROR:[/bold red] Event with ID {event_id} not found.")
        return None
        
    if not check_permission(current_user, 'update_event'):
        raise PermissionError("Permission denied to update events.")

    is_assigned_to_support = event.support_contact_id == current_user.id
    is_sales_contact = event.contract.sales_contact_id == current_user.id

    # LOGIQUE DE PERMISSION DE MODIFICATION
    if current_user.department == 'Commercial':
        if not is_sales_contact:
            console.print("[bold red]ERROR:[/bold red] You can only update events for your clients' contracts.")
            return None
        if event.support_contact_id is not None:
            console.print("[bold red]ERROR:[/bold red] Event is assigned to Support. Only Support or Gestion can update it now.")
            return None
            
    # LOGIQUE CRITIQUE DU SUPPORT: NE PEUT MODIFIER QUE SES ÉVÉNEMENTS
    elif current_user.department == 'Support':
        if not is_assigned_to_support:
             console.print("[bold red]ERROR:[/bold red] You can only update events assigned to you.")
             return None
        # Le support ne peut pas changer le contact support, car c'est la responsabilité de la Gestion
        if 'support_contact_id' in kwargs:
             console.print("[bold red]ERROR:[/bold red] Support staff cannot change the support contact ID. Only Gestion can do this.")
             del kwargs['support_contact_id']
             
    # GESTION peut tout modifier

    try:
        # Gestion du changement de contact support (Réservé à la GESTION)
        if 'support_contact_id' in kwargs and current_user.department == 'Gestion':
             new_support_id = kwargs['support_contact_id']
             
             if new_support_id is not None:
                 new_support_contact = session.query(Employee).filter(Employee.id==new_support_id).one_or_none()
                 
                 if new_support_contact and new_support_contact.department not in ['Support', 'Gestion']:
                     raise ValueError(f"ID {new_support_id} is not a valid Support/Gestion contact.")

             event.support_contact_id = new_support_id
             del kwargs['support_contact_id']
        elif 'support_contact_id' in kwargs:
             # Cette erreur est déjà gérée pour le Support ci-dessus, mais c'est une sécurité pour les autres départements
             raise PermissionError("Only Gestion can change the support contact assignment.")


        updates_made = False
        
        for key, value in kwargs.items():
            if hasattr(event, key) and key not in ['id', 'contract_id']: 
                setattr(event, key, value)
                updates_made = True

        if hasattr(event, 'event_start') and hasattr(event, 'event_end') and event.event_start >= event.event_end:
             raise ValueError("Start date must be before end date.")

        if updates_made:
            session.commit()
            return event
        else:
            return event
        
    except PermissionError as e:
        session.rollback()
        console.print(f"[bold red]PERMISSION ERROR:[/bold red] {e}")
        return None
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]VALIDATION ERROR:[/bold red] {e}")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]FATAL ERROR during event update:[/bold red] An unexpected error occurred: {e}")
        return None