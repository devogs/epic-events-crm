"""
Contract Views: Handles all user interface (CLI) interactions for Contract CRUD operations.
It calls the pure business logic functions from the crm_controller layer.
"""
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from decimal import Decimal
import sys

# Import local dependencies
from app.models import Employee, Client
from app.controllers.contract_controller import (
    create_contract,
    list_contracts,
    update_contract,
)
from app.controllers.employee_controller import list_employees 

console = Console()


# --- Display Functions ---

def display_contract_table(contracts: list, title: str):
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
        client_info = f"{contract.client.full_name} ({contract.client.id})" if contract.client else "N/A"
        sales_info = f"{contract.sales_contact.full_name} ({contract.sales_contact_id})" if contract.sales_contact else "N/A"
        signed_status = "[bold green]YES[/bold green]" if contract.status_signed else "[bold red]NO[/bold red]"
        
        table.add_row(
            str(contract.id),
            client_info,
            sales_info,
            f"{contract.total_amount:.2f}",
            f"{contract.remaining_amount:.2f}",
            signed_status
        )
    console.print(table)


# --- CLI Functions ---

def create_contract_cli(session, current_employee: Employee):
    """CLI to create a new contract."""
    console.print("\n[bold green]-- CREATE NEW CONTRACT --[/bold green]")
    
    while True:
        client_id_str = Prompt.ask("Client ID for the contract (or 'q' to cancel)").strip()
        if client_id_str.lower() == 'q': return
        try:
            client_id = int(client_id_str)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] Client ID must be a number.")

    while True:
        total_amount_str = Prompt.ask("Total Amount (€)").strip()
        try:
            total_amount = Decimal(total_amount_str)
            break
        except Exception:
            console.print("[bold red]Error:[/bold red] Invalid amount format.")
            
    while True:
        remaining_amount_str = Prompt.ask("Remaining Amount (€)").strip()
        try:
            remaining_amount = Decimal(remaining_amount_str)
            break
        except Exception:
            console.print("[bold red]Error:[/bold red] Invalid amount format.")
    
    status_signed = Confirm.ask("Is the contract signed?", default=False) 
    
    # 2. Call controller
    try:
        new_contract = create_contract(
            session,
            current_employee,
            client_id=client_id,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            status_signed=status_signed
        )
        
        if new_contract:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Contract created with ID {new_contract.id}.") 
    
    except PermissionError as e:
        console.print(f"\n[bold red]ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")


def list_contracts_cli(session, current_employee: Employee):
    """
    CLI interface to list contracts with filtering options 
    for Management (All/By Sales ID) and Commercial (My Contracts).
    """
    console.print("\n[bold blue]-- LIST CONTRACTS --[/bold blue]")

    filter_id = None
    title = "ALL CONTRACTS"

    if current_employee.department == 'Gestion':
        # Filtering option for Management
        choice = Prompt.ask("Filter contracts? [1: All Contracts | 2: By Sales ID]", choices=['1', '2'], default='1')

        if choice == '2':
            # Filter by Sales ID
            while True:
                sales_id_str = Prompt.ask("Enter the Sales ID to filter (or 'q' to cancel)").strip()
                if sales_id_str.lower() == 'q':
                    return
                try:
                    filter_id = int(sales_id_str)
                    title = f"CONTRACTS BY SALES (ID: {filter_id})" 
                    break
                except ValueError:
                    console.print("[bold red]Error:[/bold red] ID must be a number.")

    elif current_employee.department == 'Commercial':
        # Commercial only sees their own contracts (filter_id is set to their ID)
        filter_id = current_employee.id
        title = f"MY CONTRACTS (Commercial ID: {current_employee.id})"

    elif current_employee.department == 'Support':
        # Support sees all contracts by default (filter_id remains None)
        filter_id = None
        title = "ALL CONTRACTS (Support)"
        
    # Call controller
    try:
        contracts = list_contracts(session, current_employee, filter_by_sales_id=filter_id)

        if contracts is not None:
            display_contract_table(contracts, title)
            
    except PermissionError as e:
        console.print(f"\n[bold red]ERROR:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]FATAL ERROR when listing contracts:[/bold red] {e}")


def update_contract_cli(session, current_employee: Employee):
    """CLI to update an existing contract."""
    console.print("\n[bold yellow]-- MODIFY A CONTRACT --[/bold yellow]")
    
    # 1. ID Input
    while True:
        contract_id_str = Prompt.ask("Enter the ID of the contract to modify (or 'q' to cancel)").strip() 
        if contract_id_str.lower() == 'q': return
        try:
            contract_id = int(contract_id_str)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] ID must be a number.")

    # 2. Collect data to update
    updates = {}
    
    console.print("[dim]Leave fields empty to keep current values.[/dim]")
    
    new_remaining_amount = Prompt.ask("New Remaining Amount (€)").strip() 
    if new_remaining_amount: updates['remaining_amount'] = new_remaining_amount
        
    new_total_amount = Prompt.ask("New Total Amount (€) (Management only)").strip() 
    if new_total_amount: updates['total_amount'] = new_total_amount
        
    is_signed_choice = Prompt.ask("New Signed Status? (Y: Yes, N: No, Leave empty)", choices=['y', 'n', ''], default='').lower()
    if is_signed_choice == 'y':
        updates['status_signed'] = True
    elif is_signed_choice == 'n':
        updates['status_signed'] = False
            
    # 4. Sales Contact (Management only)
    if current_employee.department == 'Gestion':
        if Confirm.ask("Do you want to reassign the Sales Contact? [y/n]"):
            
            # NOTE: We assume list_employees is available to fetch sales contacts if needed for display.
            new_contact_id_input = Prompt.ask("Enter New Sales Contact ID").strip()
            try:
                updates['sales_contact_id'] = int(new_contact_id_input)
            except ValueError:
                console.print("[bold red]Error:[/bold red] Sales ID must be a number. Entry cancelled.")
                
    if not updates:
        console.print("[bold yellow]INFO:[/bold yellow] No valid data provided for update.")
        return

    # 5. Call controller (it verifies permissions)
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