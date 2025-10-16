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
        client_info = f"{contract.client.full_name} ({contract.client_id})" if contract.client else "N/A"
        sales_info = f"{contract.sales_contact.full_name} ({contract.sales_contact_id})" if contract.sales_contact else "N/A"
        
        remaining_style = "red bold" if contract.remaining_amount > 0 and contract.status_signed else "green"
        
        table.add_row(
            str(contract.id),
            client_info,
            sales_info,
            f"{contract.total_amount:.2f}",
            f"[{remaining_style}]{contract.remaining_amount:.2f}[/]",
            "✅" if contract.status_signed else "❌"
        )
    console.print(table)


# --- CLI Functions ---

def create_contract_cli(session, current_employee: Employee):
    """CLI to create a contract (Reserved for Management)."""
    console.print("\n[bold green]-- CREATE NEW CONTRACT --[/bold green]")
    
    # 1. Get Client ID
    while True:
        client_id_str = Prompt.ask("Enter Client ID (must be existing)").strip()
        try:
            client_id = int(client_id_str)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] ID must be a number.")

    # 2. Get Amounts
    while True:
        total_amount_str = Prompt.ask("Enter Total Contract Amount (€)").strip().replace(',', '.')
        remaining_amount_str = Prompt.ask("Enter Remaining Amount (Paid Deposit) (€)").strip().replace(',', '.')
        
        try:
            total_amount = Decimal(total_amount_str)
            remaining_amount = Decimal(remaining_amount_str)
            
            if total_amount <= 0:
                console.print("[bold red]Error:[/bold red] Total amount must be positive.")
            elif remaining_amount < 0:
                console.print("[bold red]Error:[/bold red] Remaining amount cannot be negative.")
            elif remaining_amount > total_amount:
                console.print("[bold red]Error:[/bold red] Remaining amount cannot exceed total amount.")
            else:
                break
        except Exception:
            console.print("[bold red]Error:[/bold red] Invalid amount format.")
            
    # 3. Get Signed Status (NEW ISOLATED PARAMETER)
    is_signed = Confirm.ask("Is the contract signed? [y/n]")
            
    # 4. Call controller
    try:
        new_contract = create_contract(
            session,
            current_employee,
            client_id,
            total_amount,
            remaining_amount,
            status_signed=is_signed # <-- PASS NEW PARAM
        )
        if new_contract:
            console.print(f"\n[bold green]SUCCESS:[/bold green] Contract created with ID [cyan]{new_contract.id}[/cyan] for Client ID {client_id}.")

    except PermissionError as e:
        console.print(f"\n[bold red]PERMISSION DENIED:[/bold red] {e}")
    except Exception as e:
         console.print("[bold red]CONTRACT CREATION FAILED:[/bold red]", str(e))


def list_contracts_cli(session, current_employee: Employee):
    """CLI to list contracts with filtering options."""
    console.print("\n[bold blue]-- LIST CONTRACTS --[/bold blue]")

    # Initialize filters
    filter_sales_id = None
    filter_signed = None
    filter_unpaid = False
    filter_unsigned = False

    # 1. Filter by Sales Contact ID (Management only)
    if current_employee.department == 'Gestion':
        if Confirm.ask("Do you want to filter by assigned Sales Contact? [y/n]"):
            sales_id_input = Prompt.ask("Enter Sales Contact ID").strip()
            try:
                filter_sales_id = int(sales_id_input)
            except ValueError:
                console.print("[bold red]Invalid Sales ID, filter ignored.[/bold red]")
                
    # 2. Filter by Status (Signed/Unsigned/Not fully Paid)
    
    # Filter for signed/unsigned (mutually exclusive high-level filters)
    filter_signed_choice = Prompt.ask("Filter by signature status? (S: Signed, U: Unsigned, A: All)", choices=['s', 'u', 'a', ''], default='a').lower()
    
    if filter_signed_choice == 's':
        filter_signed = True
    elif filter_signed_choice == 'u':
        filter_unsigned = True
    
    # Filter for not fully paid (can be combined with other filters)
    filter_unpaid = Confirm.ask("Do you want to display ONLY contracts not fully paid (Remaining > 0)? [y/n]")

    # 3. Call controller with filters
    try:
        contracts = list_contracts(
            session, 
            current_employee,
            filter_by_sales_id=filter_sales_id,
            filter_signed=filter_signed,
            filter_unpaid=filter_unpaid,
            filter_unsigned=filter_unsigned
        )
        display_contract_table(contracts, "FILTERED CONTRACTS")
        
    except PermissionError as e:
        console.print(f"[bold red]PERMISSION DENIED:[/bold red] {e}")
    except Exception as e:
        console.print("[bold red]UNKNOWN ERROR:[/bold red]", str(e))
        

def update_contract_cli(session, current_employee: Employee):
    """CLI to update a contract (Reserved for Management and Sales)."""
    console.print("\n[bold yellow]-- UPDATE CONTRACT --[/bold yellow]")

    while True:
        contract_id_input = Prompt.ask("Enter Contract ID to update").strip()
        try:
            contract_id = int(contract_id_input)
            break
        except ValueError:
            console.print("[bold red]Error:[/bold red] ID must be a number.")

    updates = {}
    console.print("\n[dim]Leave empty to keep current values.[/dim]")
    
    # 1. Total Amount (Management only)
    if current_employee.department == 'Gestion':
        total_amount_str = Prompt.ask("New Total Contract Amount (€)").strip().replace(',', '.')
        if total_amount_str:
            try:
                updates['total_amount'] = Decimal(total_amount_str)
            except Exception:
                console.print("[bold red]Error:[/bold red] Invalid total amount.")
                return

    # 2. Remaining Amount (Sales/Management)
    remaining_amount_str = Prompt.ask("New Remaining Amount (€)").strip().replace(',', '.')
    if remaining_amount_str:
        try:
            updates['remaining_amount'] = Decimal(remaining_amount_str)
        except Exception:
            console.print("[bold red]Error:[/bold red] Invalid remaining amount.")
            return
            
    # 3. Signed Status (NEW ISOLATED PARAMETER)
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