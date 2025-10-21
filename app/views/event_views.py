"""
Event Views: Fonctions CLI pour la gestion des événements.
"""

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List

from app.models import Employee, Event, Contract
from app.controllers.event_controller import (
    create_event,
    list_events,
    update_event,
)
from app.controllers.employee_controller import (
    list_employees,
)  # Pour l'assignation de support

console = Console()


def display_event_table(events: List[Event], title: str):
    """Utility function to display events in a Rich Table."""
    if not events:
        console.print(
            f"[bold yellow]INFO:[/bold yellow] No events found for the '{title}' display."
        )
        return

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Name", style="bold green", min_width=20)
    table.add_column("Contract ID", style="cyan", min_width=10, justify="center")
    table.add_column("Client Name", min_width=20)
    table.add_column("Support Contact (ID)", style="yellow", min_width=20)
    table.add_column("Start Date", style="magenta", min_width=20)
    table.add_column("Location", min_width=15)
    table.add_column("Attendees", justify="right")
    table.add_column("Notes", style="dim", max_width=30)  # <-- NOUVELLE COLONNE AJOUTÉE

    for event in events:
        client_name = (
            event.contract.client.full_name
            if event.contract and event.contract.client
            else "N/A"
        )
        support_info = (
            f"{event.support_contact.full_name} ({event.support_contact_id})"
            if event.support_contact
            else "[bold red]UNASSIGNED[/bold red]"
        )

        # Pour les notes, on affiche le contenu ou "N/A" s'il est vide
        notes_content = event.notes if event.notes else "N/A"

        table.add_row(
            str(event.id),
            event.name,
            str(event.contract_id),
            client_name,
            support_info,
            (
                event.event_start.strftime("%Y-%m-%d %H:%M")
                if event.event_start
                else "N/A"
            ),
            event.location,
            str(event.attendees),
            notes_content,  # <-- AFFICHAGE DU CONTENU
        )
    console.print(table)


def create_event_cli(session: Session, current_employee: Employee):
    """CLI function to create a new event."""
    console.print("\n[bold green]--- CREATE NEW EVENT ---[/bold green]")
    try:
        contract_id = int(Prompt.ask("Enter Contract ID to link the event").strip())
    except ValueError:
        console.print("[bold red]ERROR:[/bold red] Contract ID must be a number.")
        return

    name = Prompt.ask("Enter Event Name").strip()

    try:
        attendees = int(Prompt.ask("Enter Number of Attendees").strip())
        if attendees <= 0:
            raise ValueError
    except ValueError:
        console.print("[bold red]ERROR:[/bold red] Invalid number of attendees.")
        return

    # Date/Time input
    while True:
        try:
            start_date_str = Prompt.ask("Enter Start Date (YYYY-MM-DD HH:MM)").strip()
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M")
            break
        except ValueError:
            console.print(
                "[bold red]ERROR:[/bold red] Invalid date/time format. Use YYYY-MM-DD HH:MM."
            )

    while True:
        try:
            end_date_str = Prompt.ask("Enter End Date (YYYY-MM-DD HH:MM)").strip()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M")
            if end_date <= start_date:
                console.print(
                    "[bold red]ERROR:[/bold red] End date must be after start date."
                )
                continue
            break
        except ValueError:
            console.print(
                "[bold red]ERROR:[/bold red] Invalid date/time format. Use YYYY-MM-DD HH:MM."
            )

    location = Prompt.ask("Enter Event Location").strip()
    notes = Prompt.ask("Enter Notes (Optional)").strip()

    new_event = create_event(
        session,
        current_employee,
        contract_id,
        name,
        attendees,
        start_date,
        end_date,
        location,
        notes,
    )

    if new_event:
        console.print(
            f"\n[bold green]SUCCESS:[/bold green] Event created (ID: {new_event.id}) for Contract {new_event.contract_id}."
        )


def list_events_cli(session: Session, current_employee: Employee):
    """CLI function to list events with filters based on department."""
    console.print("\n[bold blue]--- EVENT LIST ---[/bold blue]")

    filter_scope = None
    filter_by_support_id = None

    if current_employee.department == "Support":
        choice = Prompt.ask(
            "Filter Events? (1: Mine, 2: Unassigned, 3: All, Leave empty for Mine + Unassigned)",
            choices=["1", "2", "3", ""],
            default="",
        ).strip()

        if choice == "1":
            filter_scope = "mine"
            title_suffix = " (Assigned to Me)"
        elif choice == "2":
            filter_scope = "unassigned"
            title_suffix = " (Unassigned)"
        elif choice == "3":
            filter_scope = "all_db"
            title_suffix = " (All Events)"
        else:  # Default: Mine + Unassigned
            filter_scope = "default"
            title_suffix = " (Mine + Unassigned)"

    elif current_employee.department == "Gestion":
        choice = Prompt.ask(
            "Filter Events? (1: Assigned to Support ID, 2: All, Leave empty for All)",
            choices=["1", "2", ""],
            default="2",
        ).strip()

        if choice == "1":
            try:
                filter_by_support_id = int(
                    Prompt.ask("Enter Support Employee ID").strip()
                )
                title_suffix = f" (Filtered by Support ID {filter_by_support_id})"
            except ValueError:
                console.print(
                    "[bold red]ERROR:[/bold red] Invalid Support ID. Showing all events."
                )
                title_suffix = " (All Events)"
        else:
            title_suffix = " (All Events)"

    elif current_employee.department == "Commercial":
        # Commercial only sees events for their contracts (no further filter prompt needed)
        title_suffix = f" (Linked to My Contracts)"

    else:
        title_suffix = (
            " (All Events)"  # Should only be for Gestion if no filter is applied
        )

    try:
        events = list_events(
            session,
            current_employee,
            filter_by_support_id=filter_by_support_id,
            support_filter_scope=filter_scope,
        )
        display_event_table(events, f"Events{title_suffix}")
    except PermissionError as e:
        console.print(f"[bold red]PERMISSION ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]ERROR:[/bold red] Could not fetch events: {e}")


def update_event_cli(session: Session, current_employee: Employee):
    """CLI function to update an existing event."""
    console.print("\n[bold yellow]--- UPDATE EVENT ---[/bold yellow]")
    event_id_str = Prompt.ask("Enter Event ID to update").strip()

    try:
        event_id = int(event_id_str)
    except ValueError:
        console.print("[bold red]ERROR:[/bold red] Event ID must be a number.")
        return

    updates = {}

    # --- Standard fields (modifiable by Support and Gestion) ---
    name = Prompt.ask("Enter New Event Name (Leave empty to skip)").strip()
    if name:
        updates["name"] = name

    attendees_str = Prompt.ask(
        "Enter New Number of Attendees (Leave empty to skip)"
    ).strip()
    if attendees_str:
        try:
            updates["attendees"] = int(attendees_str)
        except ValueError:
            console.print(
                "[bold red]ERROR:[/bold red] Attendees must be a number. Skipping."
            )

    location = Prompt.ask("Enter New Location (Leave empty to skip)").strip()
    if location:
        updates["location"] = location

    notes = Prompt.ask("Enter New Notes (Leave empty to skip)").strip()
    if notes:
        updates["notes"] = notes

    # Date fields
    start_date_str = Prompt.ask(
        "Enter New Start Date (YYYY-MM-DD HH:MM) (Leave empty to skip)"
    ).strip()
    if start_date_str:
        try:
            updates["event_start"] = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            console.print(
                "[bold red]ERROR:[/bold red] Invalid start date format (use YYYY-MM-DD HH:MM). Skipping."
            )

    end_date_str = Prompt.ask(
        "Enter New End Date (YYYY-MM-DD HH:MM) (Leave empty to skip)"
    ).strip()
    if end_date_str:
        try:
            updates["event_end"] = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            console.print(
                "[bold red]ERROR:[/bold red] Invalid end date format (use YYYY-MM-DD HH:MM). Skipping."
            )

    # --- Relational/Gestion-only fields ---

    # Contract ID (Gestion only)
    if current_employee.department == "Gestion":
        new_contract_id_input = Prompt.ask(
            "Enter New Contract ID (Gestion only, Leave empty to skip)"
        ).strip()
        if new_contract_id_input:
            try:
                updates["contract_id"] = int(new_contract_id_input)
            except ValueError:
                console.print(
                    "[bold red]ERROR:[/bold red] Contract ID must be a number. Entry cancelled."
                )

    # Support Contact ID (Support/Gestion only)
    if (
        current_employee.department == "Gestion"
        or current_employee.department == "Support"
    ):
        if Confirm.ask("Do you want to reassign the Support Contact? [y/n]"):
            # Inform the user that 'Support' can only assign to themselves or unassign.
            prompt_text = "Enter New Support Contact ID (0 or empty to unassign)"
            if current_employee.department == "Support":
                prompt_text += " (Only self-assignment or unassign is permitted)"

            new_contact_id_input = Prompt.ask(prompt_text).strip()

            if new_contact_id_input:
                try:
                    # The controller will validate permissions (Support can only assign self or unassign)
                    updates["support_contact_id"] = int(new_contact_id_input)
                except ValueError:
                    console.print(
                        "[bold red]ERROR:[/bold red] Support ID must be a number. Entry cancelled."
                    )
            else:
                updates["support_contact_id"] = None  # Explicitly pass None to unassign

    if not updates:
        console.print(
            "[bold yellow]INFO:[/bold yellow] No valid data provided for update."
        )
        return

    try:
        updated_event = update_event(session, current_employee, event_id, **updates)

        if updated_event:
            console.print(
                f"\n[bold green]SUCCESS:[/bold green] Event ID {updated_event.id} updated."
            )
    except Exception as e:
        console.print(
            f"\n[bold red]ERROR:[/bold red] An unexpected error occurred: {e}"
        )
