"""
Support menu interface (View layer).
Handles routing for read and specific update operations for the Support department.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt
from app.authentication import get_employee_from_token # Pour la vérification de token
from app.models import Employee # Pour le type hinting

# Import des vues CRUD (Note: Support n'a que la lecture sur Clients/Contrats)
from .client_views import list_clients_cli
from .contract_views import list_contracts_cli
from .event_views import list_events_cli, update_event_cli

console = Console()

def display_support_menu(employee: Employee):
    """
    Displays the menu options for the Support department.
    """
    department_name = employee.department 

    console.print("\n" + "="*50, style="bold blue")
    console.print(f"[bold blue]SUPPORT DASHBOARD[/bold blue] | User: [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: [yellow]{department_name}[/yellow])")
    console.print("="*50, style="bold blue")
    
    console.print("[bold underline]READ ACCESS (All Entities)[/bold underline]")
    console.print("1. [blue]List[/blue] all Clients")
    console.print("2. [blue]List[/blue] all Contracts")
    
    console.print("\n[bold underline]EVENTS MANAGEMENT[/bold underline]")
    console.print("3. [blue]List[/blue] Events (with filters)")
    console.print("4. [yellow]Update[/yellow] an Event (manage event details)")
    
    console.print("---------------------------------------")
    
    console.print("5. [bold]Return[/bold] to Main Menu (Logout)")
    console.print("6. [bold red]Quit[/bold red] Application")


def support_menu(employee: Employee, session, token: str) -> tuple[str, str]:
    """
    Main loop for the Support menu.
    """
    while True:
        display_support_menu(employee)
        
        choice = Prompt.ask("Select an option [1-6]", choices=[str(i) for i in range(1, 7)])
        action_performed = False # Par défaut, car Support a beaucoup de lecture
        
        # --- VÉRIFICATION DE SÉCURITÉ JWT ---
        if get_employee_from_token(token, session) is None:
            console.print("\n[bold red]Session Expired.[/bold red] You have been logged out.")
            return 'logout', token
        
        # --- ROUTEUR ---
        if choice == '1':
            list_clients_cli(session, employee)
        elif choice == '2':
            list_contracts_cli(session, employee)
        elif choice == '3':
            list_events_cli(session, employee)
        elif choice == '4':
            update_event_cli(session, employee)
            action_performed = True # Mise à jour de la DB
        elif choice == '5':
            console.print("[bold yellow]Returning to Login...[/bold yellow]")
            return 'logout', token
        elif choice == '6':
            console.print("[bold red]Quitting application...[/bold red]")
            sys.exit(0)
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
        
        # Logique de renouvellement du token (à copier si elle existe)

    return 'stay', token
