from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from decimal import Decimal
from sqlalchemy.orm import Session
from typing import List

from app.models import Employee, Client, Contract
from app.controllers.contract_controller import (
    create_contract,
    list_contracts,
    update_contract,
)
from app.controllers.employee_controller import list_employees

console = Console()


def display_contract_table(contracts: List[Contract], title: str):
    """Utility function to display contracts in a Rich Table."""
    if not contracts:
        console.print(f"[bold yellow]INFO:[/bold yellow] No contracts found for the '{title}' display.")
        return

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Client (ID)", style="bold green", min_width=20)
    table.add_column("Sales Contact (ID)", style="yellow", min_width=20)
    table.add_column("Total (€)", justify="right", style="magenta", min_width=15)
    table.add_column("Remaining (€)", justify="right", style="red", min_width=15)
    table.add_column("Signed", min_width=10, justify="center")

    for contract in contracts:
        client_info = f"{contract.client.full_name} ({contract.client_id})" if contract.client else "N/A"
        sales_info = f"{contract.sales_contact.full_name} ({contract.sales_contact_id})" if contract.sales_contact else "N/A"
        signed_status = "[bold green]YES[/bold green]" if contract.status_signed else "[bold red]NO[/bold red]"

        table.add_row(
            str(contract.id),
            client_info,
            sales_info,
            f"{contract.total_amount}",
            f"{contract.remaining_amount}",
            signed_status,
        )
    console.print(table)


def create_contract_cli(session: Session, current_employee: Employee):
    """CLI function to create a new contract."""
    console.print("\n[bold green]--- CREATE NEW CONTRACT ---[/bold green]")
    try:
        client_id = int(Prompt.ask("Enter Client ID").strip())
    except ValueError:
        console.print("[bold red]ERROR:[/bold red] Client ID must be a number.")
        return

    try:
        total_amount = Decimal(Prompt.ask("Enter Total Amount (€)").strip())
    except Exception:
        console.print("[bold red]ERROR:[/bold red] Invalid total amount format.")
        return

    try:
        remaining_amount = Decimal(Prompt.ask("Enter Remaining Amount (€)").strip())
    except Exception:
        console.print("[bold red]ERROR:[/bold red] Invalid remaining amount format.")
        return

    status_signed_choice = Prompt.ask("Is the contract signed? (Y/N)", choices=['y', 'n']).lower()
    status_signed = status_signed_choice == 'y'

    new_contract = create_contract(
        session,
        current_employee,
        client_id,
        total_amount,
        remaining_amount,
        status_signed,
    )

    if new_contract:
        console.print(f"\n[bold green]SUCCESS:[/bold green] Contract created (ID: {new_contract.id}) for Client {new_contract.client_id}.")


def list_contracts_cli(session: Session, current_employee: Employee):
    """CLI function to list contracts with filters."""
    console.print("\n[bold blue]--- CONTRACT LIST ---[/bold blue]")

    filter_choice = Prompt.ask(
        "Filter contracts? (1: Assigned to me, 2: Signed, 3: Unsigned, 4: All, Leave empty for All)",
        choices=['1', '2', '3', '4', ''],
        default='4'
    ).strip()

    if filter_choice == '1':
        contracts = list_contracts(session, current_employee, filter_by_sales_id=current_employee.id)
        display_contract_table(contracts, f"Contracts Assigned to {current_employee.full_name}")
    elif filter_choice == '2':
        contracts = list_contracts(session, current_employee, filter_by_signed_status=True)
        display_contract_table(contracts, "Signed Contracts")
    elif filter_choice == '3':
        contracts = list_contracts(session, current_employee, filter_by_signed_status=False)
        display_contract_table(contracts, "Unsigned Contracts")
    else:
        contracts = list_contracts(session, current_employee)
        display_contract_table(contracts, "All Contracts")


def update_contract_cli(session: Session, current_employee: Employee):
    """CLI function to update an existing contract."""
    console.print("\n[bold yellow]--- UPDATE CONTRACT ---[/bold yellow]")
    contract_id_str = Prompt.ask("Enter Contract ID to update").strip()

    try:
        contract_id = int(contract_id_str)
    except ValueError:
        console.print("[bold red]ERROR:[/bold red] Contract ID must be a number.")
        return

    updates = {}

    # Total Amount
    total_amount_str = Prompt.ask("Enter New Total Amount (€) (Leave empty to skip)").strip()
    if total_amount_str:
        try:
            updates['total_amount'] = Decimal(total_amount_str)
        except Exception:
            console.print("[bold red]ERROR:[/bold red] Invalid total amount format. Skipping total amount update.")

    # Remaining Amount
    remaining_amount_str = Prompt.ask("Enter New Remaining Amount (€) (Leave empty to skip)").strip()
    if remaining_amount_str:
        try:
            updates['remaining_amount'] = Decimal(remaining_amount_str)
        except Exception:
            console.print("[bold red]ERROR:[/bold red] Invalid remaining amount format. Skipping remaining amount update.")

    # Signed Status
    is_signed_choice = Prompt.ask("New Signed Status? (Y: Yes, N: No, Leave empty)", choices=['y', 'n', ''], default='').lower()
    if is_signed_choice == 'y':
        updates['status_signed'] = True
    elif is_signed_choice == 'n':
        updates['status_signed'] = False

    # Gestion-only fields
    if current_employee.department == 'Gestion':
        # Client ID (Le champ manquant)
        new_client_id_input = Prompt.ask("Enter New Client ID (Leave empty to skip)").strip()
        if new_client_id_input:
            try:
                updates['client_id'] = int(new_client_id_input)
            except ValueError:
                console.print("[bold red]ERROR:[/bold red] Client ID must be a number. Entry cancelled.")

        # Sales Contact ID
        if Confirm.ask("Do you want to reassign the Sales Contact? [y/n]"):
            new_contact_id_input = Prompt.ask("Enter New Sales Contact ID").strip()
            if new_contact_id_input:
                try:
                    updates['sales_contact_id'] = int(new_contact_id_input)
                except ValueError:
                    console.print("[bold red]ERROR:[/bold red] Sales ID must be a number. Entry cancelled.")

    if not updates:
        console.print("[bold yellow]INFO:[/bold yellow] No valid data provided for update.")
        return

    try:
        updated_contract = update_contract(
            session,
            current_employee,
            contract_id,
            **updates
        )

        if updated_contract:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Contract ID {updated_contract.id} updated.")
    except Exception as e:
        console.print(f"\n[bold red]ERROR:[/bold red] An unexpected error occurred: {e}")