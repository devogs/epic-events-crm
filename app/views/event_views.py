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
    """Prompts and validates a date in YYYY-MM-DD HH:MM format."""
    while True:
        date_str = Prompt.ask(f"{prompt_text} (YYYY-MM-DD HH:MM or 'q' to cancel)").strip()
        if date_str.lower() == 'q' or not date_str:
            return None
        try:
            # Try to parse the full format
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
    table.add_column("Event Name", style="bold", min_width=20)
    table.add_column("Contract ID", style="bold green", min_width=10, justify="center")
    table.add_column("Support Contact (ID)", style="yellow", min_width=25)
    table.add_column("Attendees", style="dim", min_width=10, justify="right")
    table.add_column("Location", min_width=20)
    table.add_column("Start Date", style="magenta", min_width=15)
    
    for event in events:
        support_info = f"{event.support_contact.full_name} ({event.support_contact_id})" if event.support_contact else "UNASSIGNED"
        
        display_date = event.event_start.strftime("%Y-%m-%d %H:%M") if hasattr(event, 'event_start') else "N/A"
        
        table.add_row(
            str(event.id),
            event.name,
            str(event.contract_id),
            support_info,
            str(event.attendees),
            event.location,
            display_date 
        )
    console.print(table)


# --- CLI Functions ---

def create_event_cli(session, current_employee: Employee):
    """CLI to create an event (Reserved for Sales for a signed contract)."""
    console.print("\n[bold green]-- CREATE NEW EVENT --[/bold green]")
    
    # 1. Get Contract ID
    while True:
        contract_id_str = Prompt.ask("Enter Contract ID (must be signed)").strip()
        try:
            contract_id = int(contract_id_str)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] ID must be a number.")

    # 2. Collect details
    name = Prompt.ask("Event Name").strip()
    location = Prompt.ask("Event Location").strip()
    notes = Prompt.ask("Event Notes (description)").strip()
    
    while True:
        try:
            attendees = int(Prompt.ask("Estimated number of Attendees").strip())
            if attendees >= 0: break
            console.print("[bold red]Error:[/bold red] Number of attendees cannot be negative.")
        except ValueError:
            console.print("[bold red]Error:[/bold red] Must be an integer.")

    # 3. Get and validate dates
    while True:
        start_date = get_valid_date("Start Date and Time")
        if start_date is None: return 
        end_date = get_valid_date("End Date and Time")
        if end_date is None: return 
        
        if validate_dates_order(start_date, end_date):
            break

    # 4. Call controller
    try:
        new_event = create_event(
            session,
            current_employee,
            contract_id,
            name,
            attendees,
            start_date,
            end_date,
            location,
            notes
            # support_contact_id left as None by default
        )
        if new_event:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Event '{new_event.name}' created with ID [cyan]{new_event.id}[/cyan]. Support will be assigned by Management.")

    except Exception as e:
         console.print(f"\n[bold red]EVENT CREATION FAILED:[/bold red] {e}")


def list_events_cli(session, current_employee: Employee):
    """CLI to list events with filtering options."""
    console.print("\n[bold blue]-- LIST EVENTS --[/bold blue]")

    # Initialize filters
    filter_support_id = None
    
    # 1. Filter for unassigned events
    filter_unassigned = Confirm.ask("Do you want to display ONLY unassigned events? [y/n]")
    
    # 2. Filter by Support contact
    
    if current_employee.department == 'Support':
        # SUPPORT LOGIC: "Filter only events assigned to me"
        if Confirm.ask("Do you want to display ONLY events assigned to you? [y/n]"):
            # If 'yes', filter by the current employee's ID
            filter_support_id = current_employee.id 
            
    elif current_employee.department == 'Gestion':
        # MANAGEMENT LOGIC: Option to filter by any Support ID
        if Confirm.ask("Do you want to filter by a specific support contact? [y/n]"):
            support_id_input = Prompt.ask("Enter Support Contact ID").strip()
            try:
                filter_support_id = int(support_id_input)
            except ValueError:
                console.print("[bold red]Invalid Support ID, filter ignored.[/bold red]")


    # 3. Call controller with filters
    try:
        events = list_events(
            session, 
            current_employee,
            filter_by_support_id=filter_support_id,
            filter_unassigned=filter_unassigned 
        )
        display_event_table(events, "FILTERED EVENTS")
        
    except PermissionError as e:
        console.print(f"[bold red]PERMISSION DENIED:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]UNKNOWN ERROR:[/bold red] {e}")


def update_event_cli(session, current_employee: Employee):
    """CLI to update an event (Reserved for Management for assignment and Support for details)."""
    console.print("\n[bold yellow]-- UPDATE EVENT --[/bold yellow]")

    while True:
        event_id_input = Prompt.ask("Enter Event ID to update").strip()
        try:
            event_id = int(event_id_input)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] ID must be a number.")

    updates = {}
    console.print("\n[dim]Leave empty to keep current values.[/dim]")

    # 1. Update content fields (Name, Location, Attendees, Dates, Notes)
    if current_employee.department in ['Gestion', 'Support']:
        
        # Name
        name = Prompt.ask("New Event Name").strip()
        if name:
            updates['name'] = name
            
        # Location
        location = Prompt.ask("New Event Location").strip()
        if location:
            updates['location'] = location
        
        # Notes
        notes = Prompt.ask("New Event Notes").strip()
        if notes:
            updates['notes'] = notes

        # Attendees
        attendees_str = Prompt.ask("New Estimated Number of Attendees").strip()
        if attendees_str:
            try:
                updates['attendees'] = int(attendees_str)
                if updates['attendees'] < 0:
                    console.print("[bold red]Error:[/bold red] Number of attendees cannot be negative. Ignored.")
                    del updates['attendees']
            except ValueError:
                console.print("[bold red]Error:[/bold red] Must be an integer. Ignored.")
                
        # Dates (must be handled with a separate call)
        if Confirm.ask("Do you want to modify dates and times? [y/n]"):
            start_date = get_valid_date("New Start Date and Time")
            end_date = get_valid_date("New End Date and Time")
            
            if start_date and end_date:
                # IMPORTANT: Keys must match model field names
                updates['event_start'] = start_date 
                updates['event_end'] = end_date     
            elif start_date or end_date:
                 console.print("[bold red]Date modification cancelled:[/bold red] You must provide both start and end dates.")

    # 2. Change Support contact : Reserved for 'Gestion'
    if current_employee.department == 'Gestion':
        if Confirm.ask("Do you want to assign/reassign the Support Contact? [y/n]"):
            
            # Display available support staff (Support and Management)
            support_employees = [e for e in list_employees(session) if e.department in ['Support', 'Gestion']]
            console.print("\n[bold yellow]Available Support Contacts (ID | Name):[/bold yellow]")
            for emp in support_employees:
                 console.print(f"  [cyan]{emp.id}[/cyan]: {emp.full_name}")

            new_contact_id_input = Prompt.ask("Enter New Support ID (or '0' to unassign)").strip()
            try:
                new_contact_id = int(new_contact_id_input)
                updates['support_contact_id'] = new_contact_id if new_contact_id != 0 else None
            except ValueError:
                console.print("[bold red]Error:[/bold red] Support ID must be a number. Entry cancelled.")
                
    if not updates:
        console.print("[bold yellow]INFO:[/bold yellow] No valid data provided for update.")
        return

    # 3. Call controller (it checks permissions)
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