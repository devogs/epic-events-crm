"""
Event Controller: Handles all CRUD operations related to the Event model.
Implements core business logic and data validation for events.
"""
import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from rich.console import Console
from sqlalchemy.orm import joinedload 

from app.models import Contract, Event, Employee, Role
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
        console.print(f"[bold red]ERROR:[/bold red] You are not the sales contact for Contract ID {contract_id}.")
        return None
        
    if start_date >= end_date:
         console.print("[bold red]ERROR:[/bold red] Start date must be before end date.")
         return None

    try:
        new_event = Event(
            contract_id=contract_id,
            support_contact_id=None, # Initially unassigned
            name=name,
            attendees=attendees,
            event_start=start_date,
            event_end=end_date,
            location=location,
            notes=notes
        )
        session.add(new_event)
        session.commit()
        return new_event
    except IntegrityError as e:
        session.rollback()
        console.print(f"[bold red]ERROR:[/bold red] Integrity constraint failed (e.g., contract_id not found): {e}")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR during event creation:[/bold red] {e}")
        return None


def list_events(session: Session, current_user: Employee, filter_by_support_id: int | None = None, support_filter_scope: str | None = None) -> list[Event]:
    """
    Retrieves a list of events.
    Permissions:
    - Commercial: Only events linked to their contracts.
    - Support: Events based on the chosen filter (assigned, unassigned, default, or all_db).
    - Management: All events or filtered by a specific Support ID.
    
    'support_filter_scope' is used ONLY for the 'Support' department:
    - 'mine': Only events assigned to current_user.
    - 'unassigned': Only events not assigned (support_contact_id IS NULL).
    - 'default': Both assigned to user and unassigned (the standard scope).
    - 'all_db': All events in the database (new option).
    """
    if not check_permission(current_user, 'view_events'):
        raise PermissionError("Permission denied to view events.")

    # Eager loading related entities for display
    query = session.query(Event).options(joinedload(Event.contract).joinedload(Contract.sales_contact), joinedload(Event.support_contact))

    if current_user.department == 'Commercial':
        # Commercial sees events linked to their contracts.
        query = query.join(Contract).filter(Contract.sales_contact_id == current_user.id)
    
    elif current_user.department == 'Support':
        # NEW LOGIC: Support filtering based on support_filter_scope
        if support_filter_scope == 'all_db':
             # No filter applied, returns all events in the database
             pass 
        elif support_filter_scope == 'mine':
            query = query.filter(Event.support_contact_id == current_user.id)
            
        elif support_filter_scope == 'unassigned':
            query = query.filter(Event.support_contact_id.is_(None))
            
        elif support_filter_scope == 'default' or support_filter_scope is None:
             # Default comprehensive view: assigned to me OR unassigned
             query = query.filter((Event.support_contact_id == current_user.id) | (Event.support_contact_id.is_(None)))

    elif filter_by_support_id is not None:
         # Management can filter by support ID
         query = query.filter(Event.support_contact_id == filter_by_support_id)

    # If Management and filter_by_support_id is None, no filter is added, and all events are returned.
    
    return query.all()


def update_event(session: Session, current_user: Employee, event_id: int, **kwargs) -> Event | None:
    """
    Updates an existing Event.
    Permissions:
    - Support: Update all fields (excluding sales contact) for assigned events.
    - Management: Update all fields including support contact reassignment.
    - Commercial: Read-only except for event creation.
    """
    try:
        event = session.query(Event).filter_by(id=event_id).one_or_none()
        if not event:
            console.print(f"[bold red]ERROR:[/bold red] Event with ID {event_id} not found.")
            return None
            
        # Permission Check for standard field updates (name, attendees, dates, location, notes)
        if current_user.department == 'Commercial':
             raise PermissionError("Commercial staff cannot modify events; they can only create them.")

        if current_user.department == 'Support' and event.support_contact_id != current_user.id:
             raise PermissionError("Support staff can only modify events assigned to them.")

        # --- Support Contact (Reassignment/Assignment logic) ---
        if 'support_contact_id' in kwargs:
             new_support_id = kwargs['support_contact_id'] # Can be int or None (for unassign)
             
             # Specific permission checks for the support assignment field
             if current_user.department == 'Support':
                 # Support can only assign themselves or unassign (set to None)
                 if new_support_id is not None and new_support_id != current_user.id:
                     raise PermissionError("Support staff can only assign themselves or unassign.")
             elif current_user.department != 'Gestion':
                 raise PermissionError("Only Management or Support can change the support contact.")

             if new_support_id is not None:
                 # Check if the new support contact is a valid Support or Management employee
                 new_support_contact = session.query(Employee).filter(Employee.id==new_support_id, Employee.department.in_(['Support', 'Gestion'])).one_or_none()
                 if not new_support_contact:
                     raise ValueError(f"Support Contact ID {new_support_id} not found or is not a Support/Management employee.")
                     
             event.support_contact_id = new_support_id
             del kwargs['support_contact_id'] 

        updates_made = False
        for key, value in kwargs.items():
            if hasattr(event, key) and key not in ['id', 'contract_id']: 
                setattr(event, key, value)
                updates_made = True

        if updates_made and event.event_start is not None and event.event_end is not None and event.event_start >= event.event_end:
             raise ValueError("Start date must be before end date.")


        if updates_made:
            session.commit()
            return event
        else:
            return event
        
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERROR during event modification:[/bold red] {e}")
        return None