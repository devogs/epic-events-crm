"""
Sales menu interface (View layer).
Handles routing for Client, Contract, and Event operations specific to Commercial staff,
and includes JWT expiration check.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy.orm import Session
from app.models import Employee # Pour le type hinting

# Import des fonctions d'authentification
# NOTE: Suppression de create_access_token car le refresh doit être géré par main.py
from app.authentication import get_employee_from_token

# Import des vues spécifiques
from .client_views import (
    create_client_cli,
    list_clients_cli,
    update_client_cli,
)
from .contract_views import (
    list_contracts_cli,
    update_contract_cli,
)
from .event_views import (
    create_event_cli,
    list_events_cli,
)

console = Console()

def display_sales_menu(employee: Employee):
    """
    Displays the menu options for the Commercial department based on user's new structure.
    """
    department_name = employee.department 

    # Style demandé par l'utilisateur (Intact)
    console.print("\n" + "="*50, style="bold yellow")
    console.print(f"[bold yellow]SALES DASHBOARD[/bold yellow] | User: [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: [yellow]{department_name}[/yellow])")
    console.print("="*50, style="bold yellow")
    
    console.print("[bold underline]CLIENTS[/bold underline]")
    console.print("1. [green]Create[/green] a new Client")
    console.print("2. [blue]List[/blue] all Clients")
    console.print("3. [yellow]Update[/yellow] a Client")
    
    console.print("\n[bold underline]CONTRACTS[/bold underline]")
    console.print("4. [blue]List[/blue] Contracts")
    console.print("5. [yellow]Update[/yellow] a Contract (Your clients only)")
    
    console.print("\n[bold underline]EVENTS[/bold underline]")
    console.print("6. [green]Create[/green] an Event (For a signed contract of your client)")
    console.print("7. [blue]List[/blue] Events")
    
    console.print("--------------------------------------")
    
    console.print("8. [bold]Logout[/bold] (Return to Login)")
    console.print("9. [bold red]Quit[/bold red] Application")
    
    console.print("="*50, style="bold yellow")

# Signature de fonction correcte pour main.py
def sales_menu(session: Session, employee: Employee, token: str) -> tuple[str, str | None]:
    """
    Main loop and router for the Sales department menu.
    """
    while True:
        
        # 1. Afficher le menu
        display_sales_menu(employee)
        
        # 2. Récupérer le choix (plage 1-9)
        choice = Prompt.ask("Select an option [1-9]").strip()
        
        # FIX HOMOGÉNÉITÉ (JWT): Vérification APRES le choix (comme Support/Gestion)
        if get_employee_from_token(token, session) is None:
            console.print("\n[bold red]Session Expired.[/bold red] You have been logged out.")
            # Retourne None pour le token car il est expiré
            return 'logout', None 

        # 3. ROUTAGE MIS À JOUR (1-9)
        
        # --- CLIENTS ---
        if choice == '1':
            create_client_cli(session, employee)
        elif choice == '2':
            list_clients_cli(session, employee)
        elif choice == '3':
            update_client_cli(session, employee)

        # --- CONTRACTS ---
        elif choice == '4':
            list_contracts_cli(session, employee)
        elif choice == '5':
            update_contract_cli(session, employee)

        # --- EVENTS ---
        elif choice == '6':
            create_event_cli(session, employee)
        elif choice == '7':
            list_events_cli(session, employee)

        # --- SORTIE ---
        elif choice == '8':
            console.print("[bold green]Logging out...[/bold green]")
            # Retourne None car le jeton doit être effacé lors de la déconnexion
            return 'logout', None 
        elif choice == '9':
            console.print("[bold red]Quitting application...[/bold red]")
            sys.exit(0)
        
        # Gestion de l'erreur
        else:
             console.print("[bold red]Invalid choice. Please select an option from 1 to 9.[/bold red]")

        # FIX RETOUR: Suppression de la logique de rafraîchissement explicite.
        # La boucle principale de main.py est responsable de rafraîchir le jeton
        # après l'exécution d'une action réussie ou échouée.
        pass # La boucle continue, main.py s'occupe du refresh