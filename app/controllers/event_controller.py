"""
Event Controller: Handles all CRUD operations related to the Event model.
Implements core business logic and data validation for events.
"""
import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console

from app.models import Contract, Event, Employee
from app.authentication import check_permission

console = Console()

# =============================================================================
# --- EVENTS CRUD ---
# =============================================================================

def create_event(session: Session, current_user: Employee, contract_id: int, name: str, attendees: int, start_date: datetime.datetime, end_date: datetime.datetime, location: str, notes: str) -> Event | None:
    """
    Creates a new Event for a signed contract.
    Permissions: Commercial only, for their signed contracts.
    """
    if not check_permission(current_user, 'create_event'):
        raise PermissionError("Permission denied to create events.")

    contract = session.query(Contract).filter_by(id=contract_id).one_or_none()
    if not contract:
        console.print(f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found.")
        return None
        
    if not contract.status_signed:
        console.print("[bold red]ERROR:[/bold red] Cannot create an event for an unsigned contract.")
        return None

    if contract.sales_contact_id != current_user.id:
        console.print("[bold red]ERROR:[/bold red] You can only create events for your clients' contracts.")
        return None
        
    if start_date >= end_date:
        console.print("[bold red]ERROR:[/bold red] Start date must be before end date.")
        return None

    try:
        new_event = Event(
            contract_id=contract_id,
            name=name,
            attendees=attendees,
            event_start=start_date,
            event_end=end_date,
            location=location,
            notes=notes,
            support_contact_id=None 
        )

        session.add(new_event)
        session.commit()
        return new_event

    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR FATALE lors de la création de l'événement:[/bold red] {e}")
        return None


def list_events(
    session: Session, 
    current_user: Employee, 
    filter_by_support_id: int | None = None, 
    # CRITIQUE: Ajout de ces deux arguments pour correspondre à la vue
    filter_by_unassigned: bool = False,       
    filter_by_commercial_id: int | None = None 
) -> list[Event]:    
    """
    Retrieves a list of events.
    Permissions: Gestion sees all. Commercial sees events for their contracts. Support sees events assigned to them.
    """
    if not check_permission(current_user, 'view_events'):
        raise PermissionError("Permission denied to view events.")

    query = session.query(Event)

    if current_user.department == 'Commercial':
        query = query.join(Contract).filter(Contract.sales_contact_id == current_user.id)
    elif current_user.department == 'Support':
        query = query.filter(Event.support_contact_id == current_user.id)
        
    if filter_by_support_id is not None:
        query = query.filter(Event.support_contact_id == filter_by_support_id)
        
    return query.all()

def update_event(session: Session, current_user: Employee, event_id: int, **kwargs) -> Event | None:
    """
    Updates an existing Event record.
    Permissions: Gestion can update all. Commercial can update non-assigned events. Support can update their assigned events.
    """
    event = session.query(Event).filter_by(id=event_id).one_or_none()
    
    if not event:
        console.print(f"[bold red]ERROR:[/bold red] Event with ID {event_id} not found.")
        return None
        
    if not check_permission(current_user, 'update_event'):
        raise PermissionError("Permission denied to update events.")

    is_assigned_to_support = event.support_contact_id == current_user.id
    is_sales_contact = event.contract.sales_contact_id == current_user.id

    if current_user.department == 'Commercial':
        if not is_sales_contact:
            console.print("[bold red]ERROR:[/bold red] You can only update events for your clients' contracts.")
            return None
        if event.support_contact_id is not None:
            console.print("[bold red]ERROR:[/bold red] Event is assigned to Support. Only Support or Gestion can update it now.")
            return None
            
    elif current_user.department == 'Support' and not is_assigned_to_support:
        console.print("[bold red]ERROR:[/bold red] You can only update events assigned to you.")
        return None

    try:
        # Gestion du changement de contact support
        if 'support_contact_id' in kwargs:
             new_support_id = kwargs['support_contact_id']
             
             if current_user.department == 'Support':
                 if new_support_id is not None and new_support_id != current_user.id:
                     raise PermissionError("Support staff can only assign themselves or unassign.")
             elif current_user.department != 'Gestion':
                 raise PermissionError("Only Gestion or Support can change the support contact.")

             if new_support_id is not None:
                 new_support_contact = session.query(Employee).filter(Employee.id==new_support_id, Employee.role.has(Role.name.in_(['Support', 'Gestion']))).one_or_none()
                 if not new_support_contact:
                     raise ValueError(f"ID {new_support_id} du nouveau contact support non trouvé ou n'est pas Support/Gestion.")
                     
             event.support_contact_id = new_support_id
             del kwargs['support_contact_id'] 

        updates_made = False
        for key, value in kwargs.items():
            if hasattr(event, key) and key not in ['id', 'contract_id']: 
                setattr(event, key, value)
                updates_made = True

        if event.event_start >= event.event_end:
             raise ValueError("La date de début doit être antérieure à la date de fin.")


        if updates_made:
            session.commit()
            return event
        else:
            return event
        
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR lors de la modification de l'événement:[/bold red] {e}")
        return None