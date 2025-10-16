"""
Event Controller: Handles all CRUD operations related to the Event model.
Implements core business logic and data validation for events.
"""
import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console
from sqlalchemy.orm import joinedload 
from sqlalchemy import or_, func 

from app.models import Contract, Event, Employee
from app.authentication import check_permission

console = Console()

# =============================================================================
# --- EVENTS CRUD ---
# =============================================================================

def create_event(session: Session, current_user: Employee, contract_id: int, name: str, attendees: int, start_date: datetime.datetime, end_date: datetime.datetime, location: str, notes: str) -> Event | None:
    # ... (fonction inchangée)
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
        console.print(f"[bold red]FATAL ERROR during event creation:[/bold red] {e}")
        return None


def list_events(
    session: Session, 
    current_user: Employee, 
    filter_by_support_id: int | None = None, 
    filter_unassigned: bool = False,
) -> list[Event]:    
    # ... (fonction inchangée)
    if not check_permission(current_user, 'view_events'):
        raise PermissionError("Permission denied to view events.")

    query = session.query(Event).options(
        joinedload(Event.contract),
        joinedload(Event.support_contact)
    )

    if current_user.department == 'Commercial':
        query = query.join(Contract).filter(Contract.sales_contact_id == current_user.id)
    elif current_user.department == 'Support':
        if filter_by_support_id is None and not filter_unassigned:
             query = query.filter(Event.support_contact_id == current_user.id)
        
    if filter_by_support_id is not None:
        query = query.filter(Event.support_contact_id == filter_by_support_id)
        
    if filter_unassigned:
        query = query.filter(Event.support_contact_id.is_(None))
        
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

    if current_user.department == 'Commercial':
        is_sales_contact = event.contract.sales_contact_id == current_user.id
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
        # Handle support contact assignment/reassignment
        updates_made = False

        if 'support_contact_id' in kwargs:
             new_support_id = kwargs['support_contact_id']
             
             if current_user.department == 'Support':
                 if new_support_id is not None and new_support_id != current_user.id:
                     raise PermissionError("Support staff can only assign themselves or unassign.")
             
             if new_support_id is not None:
                 # FIX CRITIQUE: Vérifier l'employé par ID, puis VÉRIFIER LE DÉPARTEMENT EN PYTHON.
                 # Cela contourne les problèmes de type/propriété de la base de données.
                 new_support_contact = session.query(Employee).filter(
                     Employee.id == new_support_id
                 ).one_or_none()
                 
                 # Vérification en Python après le chargement
                 if not new_support_contact or new_support_contact.department.strip() not in ['Support', 'Gestion']:
                     raise ValueError(f"ID {new_support_id} for new support contact not found or is not Support/Gestion.")
                     
             # Appliquer le changement
             event.support_contact_id = new_support_id
             del kwargs['support_contact_id'] 
             updates_made = True


        for key, value in kwargs.items():
            if hasattr(event, key) and key not in ['id', 'contract_id']: 
                setattr(event, key, value)
                updates_made = True

        if ('event_start' in kwargs or 'event_end' in kwargs) and event.event_start >= event.event_end:
             raise ValueError("Start date must be before end date.")


        if updates_made: 
            session.commit()
            return event
        else:
            # Si aucune mise à jour n'a eu lieu
            return event

    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR during event update:[/bold red] {e}")
        return None