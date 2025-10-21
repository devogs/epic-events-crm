"""
Client Views: CLI functions for client management by the sales team.
"""

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from app.models import Employee
from app.controllers.client_controller import list_clients, create_client, update_client
from app.controllers.utils import is_valid_email, is_valid_phone

from app.controllers.employee_controller import list_employees

console = Console()


# --- Display Functions ---


def display_client_table(clients: list, title: str):
    """Utility function to display clients in a Rich Table."""
    if not clients:
        # Translated: No client found for the 'title' display.
        console.print(
            f"[bold yellow]INFO:[/bold yellow] No client found for the '{title}' display."
        )
        return

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Full Name", style="bold", min_width=20)
    table.add_column("Company", min_width=20)
    table.add_column("Email", min_width=30)
    table.add_column("sales Contact (ID)", style="yellow", min_width=20)
    table.add_column("Last Update", style="dim", min_width=15)

    for client in clients:
        sales_name = client.sales_contact.full_name if client.sales_contact else "N/A"

        table.add_row(
            str(client.id),
            client.full_name,
            client.company_name or "N/A",
            client.email,
            f"{sales_name} ({client.sales_contact_id})",
            (
                client.last_update.strftime("%Y-%m-%d %H:%M")
                if client.last_update
                else "N/A"
            ),
        )
    console.print(table)


# --- CLI Functions ---


def create_client_cli(session, current_employee: Employee) -> None:
    """
    CLI interface to gather data and call the pure controller function to create a new Client.
    Requires 'Commercial' or 'Gestion' permission.
    """
    # ... (Permission check, unchanged)

    # Translated: -- CREATE NEW CLIENT --
    console.print("\n[bold green]-- CREATE NEW CLIENT --[/bold green]")

    while True:
        # 1. Gather data
        full_name = Prompt.ask("Client Full Name").strip()
        company_name = Prompt.ask("Company Name").strip()
        email = Prompt.ask("Client Email").strip()
        phone = Prompt.ask("Phone Number").strip()

        # 2. Call controller
        try:
            new_client = create_client(
                session,
                current_employee,
                full_name=full_name,
                email=email,
                phone=phone,
                company_name=company_name,
            )

            if new_client:
                console.print(
                    f"\n[bold green]SUCCESS:[/bold green] Client" \
                    "'{new_client.full_name}' created with ID {new_client.id} and assigned to you."
                )
                break

        except PermissionError as e:
            console.print(f"\n[bold red]ERROR:[/bold red] {e}")
            break
        except Exception as e:
            console.print(
                f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}"
            )
            break


def list_clients_cli(session, current_employee: Employee):
    """CLI to list clients (with filtering option for 'All Clients' or 'My Clients')."""
    console.print("\n[bold blue]-- LIST CLIENTS --[/bold blue]")

    choice = Prompt.ask(
        "Filter clients? [1: All Clients | 2: My Clients]",
        choices=["1", "2"],
        default="1",
    )

    filter_id = None
    title = "ALL CLIENTS (Read Only)"

    if choice == "2":
        # Choice 2: My Clients
        filter_id = current_employee.id
        title = f"MY CLIENTS (Sales ID: {current_employee.id})"
    elif choice == "1":
        # Choice 1: All Clients
        filter_id = None
        title = "ALL CLIENTS (Read Only)"

    clients = list_clients(session, current_employee, filter_by_sales_id=filter_id)

    if clients is not None:
        display_client_table(clients, title)


def update_client_cli(session, current_employee: Employee):
    """CLI to update an existing client."""
    console.print("\n[bold yellow]-- MODIFY A CLIENT --[/bold yellow]")

    # 1. ID Input
    while True:
        client_id_str = Prompt.ask(
            "Enter the ID of the client to modify (or 'q' to cancel)"
        ).strip()
        if client_id_str.lower() == "q":
            return
        try:
            client_id = int(client_id_str)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] ID must be a number.")

    # 2. Collect data to update
    updates = {}

    console.print("[dim]Leave fields empty to keep current values.[/dim]")

    new_name = Prompt.ask("New full name").strip()
    if new_name:
        updates["full_name"] = new_name

    new_company = Prompt.ask("New company name").strip()
    if new_company:
        updates["company_name"] = new_company

    while True:
        new_email = Prompt.ask("New email").strip()
        if not new_email:
            break
        if is_valid_email(new_email):
            updates["email"] = new_email
            break
        console.print("[bold red]Error:[/bold red] Invalid email format.")

    while True:
        new_phone = Prompt.ask("New phone").strip()
        if not new_phone:
            break
        if is_valid_phone(new_phone):
            updates["phone"] = new_phone
            break
        console.print("[bold red]Error:[/bold red] Invalid phone format.")

    # Change sales contact: Reserved for 'Gestion' team (controller checks permission)
    if current_employee.department == "Gestion":
        if Confirm.ask("Do you want to reassign the Sales Contact?"):
            sales_employees = [
                e
                for e in list_employees(session, filter_by_department="sales")
                if e.department == "sales"
            ]

            console.print("\n[bold yellow]Available Sales Contacts:[/bold yellow]")
            for emp in sales_employees:
                console.print(f"  [cyan]{emp.id}[/cyan]: {emp.full_name}")

            new_sales_id_str = Prompt.ask("Enter New sales ID").strip()
            if new_sales_id_str:
                try:
                    # The argument for the controller is 'sales_id'
                    updates["sales_id"] = int(new_sales_id_str)
                except ValueError:
                    console.print(
                        "[bold red]Error:[/bold red] Sales ID must be a number. Entry cancelled."
                    )

    if not updates:
        console.print(
            "[bold yellow]INFO:[/bold yellow] No valid data provided for update."
        )
        return

    # 3. Controller call
    updated_client = update_client(session, current_employee, client_id, **updates)

    # 4. Display result
    if updated_client:
        console.print(
            f"\n[bold green]SUCCESS:[/bold green]" \
            f"Client ID [cyan]{updated_client.id}[/cyan] updated."
        )
