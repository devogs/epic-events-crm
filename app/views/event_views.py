"""
Event Views: Handles all user interface (CLI) interactions for Event CRUD operations.
It calls the pure business logic functions from the crm_controller layer.
"""
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
import datetime

# Import local dependencies
from app.models import Employee, Contract, Event 
from app.controllers.event_controller import (
    create_event,
    list_events,
    update_event,
)
from app.controllers.employee_controller import list_employees 

console = Console()


# --- Date Validation Helpers ---

def get_valid_date(prompt_text: str) -> datetime.datetime | None:
    """Prompts for and validates a date in YYYY-MM-DD HH:MM format."""
    while True:
        date_str = Prompt.ask(f"{prompt_text} (YYYY-MM-DD HH:MM or 'q' to cancel)").strip()
        if date_str.lower() == 'q' or not date_str:
            return None
        try:
            # Attempt to parse the full format
            return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            console.print("[bold red]Error:[/bold red] Invalid date/time format. Use YYYY-MM-DD HH:MM.")

def validate_dates_order(start: datetime.datetime, end: datetime.datetime) -> bool:
    """Checks that the start date is before the end date."""
    if start >= end:
        console.print("[bold red]Error:[/bold red] Start date must be before end date.")
        return False
    return True


# --- Display Functions ---

def display_event_table(events: list, title: str):
    """Utility function to display events in a Rich Table."""
    if not events:
        console.print(f"[bold yellow]INFO:[/bold yellow] No events found for the '{title}' display.")
        return

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Contract ID", min_width=10)
    table.add_column("Name", style="bold", min_width=20)
    table.add_column("Sales Contact (ID)", style="yellow", min_width=20)
    table.add_column("Support Contact (ID)", style="magenta", min_width=20)
    table.add_column("Start Date", style="dim", min_width=15)
    table.add_column("End Date", style="dim", min_width=15)
    
    for event in events:
        sales_name = event.contract.sales_contact.full_name if event.contract and event.contract.sales_contact else "N/A"
        support_name = event.support_contact.full_name if event.support_contact else "[bold red]UNASSIGNED[/bold red]"
        support_id = event.support_contact_id if event.support_contact_id else "N/A"
        
        table.add_row(
            str(event.id),
            str(event.contract_id),
            event.name,
            f"{sales_name} ({event.contract.sales_contact_id})" if event.contract else "N/A",
            f"{support_name} ({support_id})",
            event.event_start.strftime("%Y-%m-%d %H:%M"),
            event.event_end.strftime("%Y-%m-%d %H:%M")
        )
    console.print(table)


# --- CLI Functions ---

def create_event_cli(session, current_employee: Employee):
    """CLI to create a new event."""
    console.print("\n[bold green]-- CREATE NEW EVENT --[/bold green]")
    
    # 1. Gather data
    while True:
        contract_id_str = Prompt.ask("Contract ID for the event (must be signed)").strip()
        try:
            contract_id = int(contract_id_str)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] Contract ID must be a number.")
            
    name = Prompt.ask("Event Name").strip()
    
    while True:
        attendees_str = Prompt.ask("Number of Attendees").strip()
        try:
            attendees = int(attendees_str)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] Attendees must be a number.")
            
    # Date/Time Input
    start_date = get_valid_date("Event Start Date/Time")
    if start_date is None: return
    
    end_date = get_valid_date("Event End Date/Time")
    if end_date is None: return
    
    if not validate_dates_order(start_date, end_date): return
    
    location = Prompt.ask("Location").strip()
    notes = Prompt.ask("Notes (Optional)").strip()
    
    # 2. Call controller
    try:
        new_event = create_event(
            session,
            current_employee,
            contract_id=contract_id,
            name=name,
            attendees=attendees,
            start_date=start_date,
            end_date=end_date,
            location=location,
            notes=notes
        )
        
        if new_event:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Event created with ID {new_event.id}.") 
            
    except PermissionError as e:
        console.print(f"\n[bold red]ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")


def list_events_cli(session, current_employee: Employee):
    """CLI to list events with specific filtering options for each department."""
    console.print("\n[bold blue]-- LIST EVENTS --[/bold blue]")

    filter_id = None
    support_scope = None
    title = "ALL EVENTS"

    if current_employee.department == 'Commercial':
        # Commercial only sees events related to their contracts. The controller handles this implicitly.
        title = f"EVENTS FOR MY CLIENTS (Sales ID: {current_employee.id})"
        
    elif current_employee.department == 'Support':
        # NEW FILTERING LOGIC FOR SUPPORT
        choice = Prompt.ask(
            "Filter events? [1: My Assigned Events | 2: Unassigned Events | 3: My Assigned & Unassigned (Default) | 4: All CRM Events]",
            choices=['1', '2', '3', '4'], 
            default='3'
        ).strip()
        
        if choice == '1':
            support_scope = 'mine'
            title = f"MY ASSIGNED EVENTS (Support ID: {current_employee.id})"
        elif choice == '2':
            support_scope = 'unassigned'
            title = "UNASSIGNED EVENTS"
        elif choice == '3':
            support_scope = 'default'
            title = f"MY ASSIGNED & UNASSIGNED EVENTS (Support ID: {current_employee.id})"
        elif choice == '4':
            support_scope = 'all_db'
            title = "ALL CRM EVENTS (All Assigned / Unassigned)"

    elif current_employee.department == 'Gestion':
        # Management options: All (default) or filter by Support ID
        choice = Prompt.ask("Filter events? [1: All Events | 2: By Support ID]", choices=['1', '2'], default='1')

        if choice == '2':
            while True:
                support_id_str = Prompt.ask("Enter the Support ID to filter (or 'q' to cancel)").strip()
                if support_id_str.lower() == 'q': return
                try:
                    filter_id = int(support_id_str)
                    title = f"EVENTS BY SUPPORT (ID: {filter_id})"
                    break
                except ValueError:
                    console.print("[bold red]Error:[/bold red] ID must be a number.")
        
    # Call controller
    try:
        events = list_events(
            session, 
            current_employee, 
            filter_by_support_id=filter_id, 
            support_filter_scope=support_scope
        )

        if events is not None:
            display_event_table(events, title)
            
    except PermissionError as e:
        console.print(f"\n[bold red]ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR when listing events:[/bold red] {e}")


def update_event_cli(session, current_employee: Employee):
    """CLI to update an existing event (Support and Management permissions)."""
    console.print("\n[bold yellow]-- MODIFY AN EVENT --[/bold yellow]")
    
    # 1. ID Input
    while True:
        event_id_str = Prompt.ask("Enter the ID of the event to modify (or 'q' to cancel)").strip()
        if event_id_str.lower() == 'q': return
        try:
            event_id = int(event_id_str)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] ID must be a number.")

    # 2. Collect data to update
    updates = {}
    
    console.print("[dim]Leave fields empty to keep current values. Enter 'None' to clear a field.[/dim]")
    
    new_name = Prompt.ask("New Event Name").strip()
    if new_name: updates['name'] = new_name
        
    new_location = Prompt.ask("New Location").strip()
    if new_location: updates['location'] = new_location

    new_notes = Prompt.ask("New Notes").strip()
    if new_notes: updates['notes'] = new_notes
        
    new_attendees = Prompt.ask("New Estimated Number of Attendees").strip()
    if new_attendees: 
        try:
            updates['attendees'] = int(new_attendees)
        except ValueError:
            console.print("[bold red]Error:[/bold red] Attendees must be a number. Ignoring update.")
            new_attendees = None # Reset the value to ignore it
    
    # Date/Time updates
    if Confirm.ask("Do you want to modify dates and times?"):
        new_start_str = Prompt.ask("New Start Date/Time (YYYY-MM-DD HH:MM)").strip()
        if new_start_str.lower() == 'none': updates['event_start'] = None
        elif new_start_str: updates['event_start'] = datetime.datetime.strptime(new_start_str, "%Y-%m-%d %H:%M") 
            
        new_end_str = Prompt.ask("New End Date/Time (YYYY-MM-DD HH:MM)").strip()
        if new_end_str.lower() == 'none': updates['event_end'] = None
        elif new_end_str: updates['event_end'] = datetime.datetime.strptime(new_end_str, "%Y-%m-%d %H:%M") 

    # Support Contact Update: Reserved for Management AND Support (to self-assign/unassign)
    if current_employee.department in ['Gestion', 'Support']:
        
        if Confirm.ask("Do you want to assign/reassign the Support Contact?"):
            
            # --- Management (Gestion) ---
            if current_employee.department == 'Gestion':
                # Get employees whose department is 'Support'
                support_employees = [e for e in list_employees(session) if e.department == 'Support']
                
                console.print("\n[bold yellow]Available Support Contacts (ID | Name):[/bold yellow]")
                if not support_employees:
                    console.print("[dim]No Support employees available.[/dim]")
                    return # Exit update process if no support staff found
                    
                for emp in support_employees:
                     console.print(f"  [cyan]{emp.id}[/cyan]: {emp.full_name}")

                new_contact_id_input = Prompt.ask("Enter New Support ID (or '0' to unassign)").strip()
                try:
                    new_contact_id = int(new_contact_id_input)
                    updates['support_contact_id'] = new_contact_id if new_contact_id != 0 else None
                except ValueError:
                    console.print("[bold red]Error:[/bold red] Support ID must be a number. Entry cancelled.")
        
            # --- Support ---
            elif current_employee.department == 'Support':
                 assign_choice = Prompt.ask("Assign to yourself (A) or Unassign (U)?", choices=['a', 'u']).lower()
                 if assign_choice == 'a':
                     updates['support_contact_id'] = current_employee.id
                 elif assign_choice == 'u':
                     updates['support_contact_id'] = None
                
    if not updates:
        console.print("[bold yellow]INFO:[/bold yellow] No valid data provided for update.")
        return

    # 3. Call controller (it verifies permissions)
    try:
        updated_event = update_event(
            session,
            current_employee,
            event_id,
            **updates
        )

        if updated_event:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Event ID {updated_event.id} updated.")
    except Exception as e:
        console.print(f"\n[bold red]ERROR:[/bold red] An unexpected error occurred: {e}")