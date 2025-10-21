"""
Management menu interface (View layer).
Handles routing for Employee, Contract, and Event operations for the Management department (Gestion).
"""

import sys
from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy.orm import Session
from app.models import Employee

# CRITICAL IMPORT: Authentication
from app.authentication import get_employee_from_token

# Imports for Employee views
from .employee_views import (
    create_employee_cli,
    list_employees_cli,
    update_employee_cli,
    delete_employee_cli,
)

# Imports for Contract views
from .contract_views import (
    list_contracts_cli,
    create_contract_cli,
    update_contract_cli,
)

# Imports for Event views
from .event_views import (
    list_events_cli,
    update_event_cli,
)

console = Console()


def display_management_menu(employee: Employee):
    """
    Displays the menu options for the Management department.
    Updated to include contract listing.
    """
    department_name = employee.department

    # Style unchanged
    console.print("\n" + "=" * 50, style="bold magenta")
    console.print(
        f"[bold magenta]MANAGEMENT DASHBOARD[/bold magenta] | User: [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: [yellow]{department_name}[/yellow])"
    )
    console.print("=" * 50, style="bold magenta")

    console.print("[bold underline]EMPLOYEE MANAGEMENT[/bold underline]")
    console.print("1. [green]Create[/green] a new Employee")
    console.print("2. [blue]List[/blue] all Employees")
    console.print("3. [yellow]Update[/yellow] an Employee")
    console.print("4. [red]Delete[/red] an Employee")

    # CONTRACT MANAGEMENT - New option 5 added, shifting others
    console.print("\n[bold underline]CONTRACT MANAGEMENT[/bold underline]")
    console.print("5. [blue]List[/blue] Contracts")
    console.print("6. [green]Create[/green] a new Contract")
    console.print("7. [yellow]Update[/yellow] a Contract")

    # EVENT MANAGEMENT
    console.print("\n[bold underline]EVENT MANAGEMENT[/bold underline]")
    console.print("8. [blue]List[/blue] Events (with filters)")
    console.print("9. [yellow]Update[/yellow] an Event")

    console.print("--------------------------------------")
    console.print("10. [bold]Logout[/bold] (Return to Login)")
    console.print("11. [bold red]Quit[/bold red] Application")

    console.print("=" * 50, style="bold magenta")


def management_menu(
    session: Session, employee: Employee, token: str
) -> tuple[str, str | None]:
    """
    Handles user input and routes to the appropriate CLI function.
    NOTE: Renamed from management_menu_router back to management_menu for main.py compatibility.
    """
    action_performed = False

    while True:
        # CRITICAL FIX: Display the menu BEFORE prompting for input
        display_management_menu(employee)

        # Get choice (range 1-11)
        choice = Prompt.ask(
            "Select an option [1-11]", choices=[str(i) for i in range(1, 12)]
        ).strip()

        # JWT Security Check
        if get_employee_from_token(token, session) is None:
            console.print(
                "\n[bold red]Session Expired.[/bold red] You have been logged out."
            )
            return "logout", None

        # --- ROUTING (1-11) ---

        # --- EMPLOYEE MANAGEMENT (1-4) ---
        if choice == "1":
            create_employee_cli(session, employee)
            action_performed = True
        elif choice == "2":
            list_employees_cli(session, employee)
        elif choice == "3":
            update_employee_cli(session, employee)
            action_performed = True
        elif choice == "4":
            delete_employee_cli(session, employee)
            action_performed = True

        # --- CONTRACT MANAGEMENT (5-7) ---
        elif choice == "5":  # List Contracts (NEW)
            list_contracts_cli(session, employee)
        elif choice == "6":
            create_contract_cli(session, employee)
            action_performed = True
        elif choice == "7":
            update_contract_cli(session, employee)
            action_performed = True

        # --- EVENT MANAGEMENT (8-9) ---
        elif choice == "8":
            list_events_cli(session, employee)
        elif choice == "9":
            update_event_cli(session, employee)
            action_performed = True

        # --- EXIT (10-11) ---
        elif choice == "10":
            console.print("[bold green]Logging out...[/bold green]")
            return "logout", None
        elif choice == "11":
            console.print("[bold red]Quitting application...[/bold red]")
            sys.exit(0)

        # Error handling
        else:
            console.print(
                "[bold red]Invalid choice. Please select an option from 1 to 11.[/bold red]"
            )

        return "stay", token
