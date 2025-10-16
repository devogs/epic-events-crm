"""
Support menu interface (View layer).
Handles routing for read and specific update operations for the Support department.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy.orm import Session # Import de Session pour le type hinting

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
    console.print("4. [yellow]Update[/yellow] an Event (Assigned Events only)")
    
    console.print("---------------------------------------")
    
    console.print("5. [bold]Logout[/bold] (Return to Login)")
    console.print("6. [bold red]Quit[/bold red] Application")


# CORRECTION CRITIQUE: L'ordre des arguments est inversé pour correspondre à main.py
def support_menu(session: Session, employee: Employee, token: str) -> tuple[str, str | None]:
    """
    Main loop for the Support menu.
    """
    while True:
        # 1. Affichage du menu
        display_support_menu(employee)
        
        # 2. Récupération du choix
        choice = Prompt.ask("Select an option [1-6]", choices=[str(i) for i in range(1, 7)])
        action_performed = False 
        
        # --- VÉRIFICATION DE SÉCURITÉ JWT ---
        if get_employee_from_token(token, session) is None:
            console.print("\n[bold red]Session Expired.[/bold red] You have been logged out.")
            return 'logout', None # Retourne None pour le token car il est expiré
        
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
            console.print("[bold yellow]Logging out...[/bold yellow]")
            return 'logout', None # Retourne None pour le token
        elif choice == '6':
            console.print("[bold red]Quitting application...[/bold red]")
            sys.exit(0)
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
        
        # 3. Logique de renouvellement du token (si une action a été effectuée ou simplement pour la cohérence)
        if action_performed:
            # Assurez-vous d'avoir importé create_access_token si cette logique est là.
            # Pour l'instant, je m'en tiens à la vérification sans rafraîchissement explicite
            # car la logique de rafraîchissement est habituellement dans main.py.
            pass