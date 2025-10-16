"""
Management menu interface (View layer).
Handles routing for Employee, Contract, and Event operations for the Management department (Gestion).
"""
import sys
from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy.orm import Session
from app.models import Employee 

# IMPORT CRITIQUE: Authentification
from app.authentication import get_employee_from_token 

# Imports des vues spécifiques aux employés (existantes)
from .employee_views import (
    create_employee_cli,
    list_employees_cli,
    update_employee_cli,
    delete_employee_cli,
)

# Imports des vues de Contrats (NOUVEAU)
from .contract_views import (
    create_contract_cli, 
    update_contract_cli,
)

# Imports des vues d'Événements (NOUVEAU)
from .event_views import (
    list_events_cli,
    update_event_cli, 
)

console = Console()

def display_management_menu(employee: Employee):
    """
    Displays the menu options for the Management department (Gestion).
    Mis à jour pour inclure la gestion des contrats et des événements.
    """
    department_name = employee.department 

    # Style inchangé
    console.print("\n" + "="*50, style="bold magenta")
    console.print(f"[bold magenta]MANAGEMENT DASHBOARD[/bold magenta] | User: [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: [yellow]{department_name}[/yellow])")
    console.print("="*50, style="bold magenta")
    
    # --- EMPLOYEE MANAGEMENT (Choix 1 à 4) ---
    console.print("[bold underline]EMPLOYEE MANAGEMENT[/bold underline]")
    console.print("1. [green]Create[/green] a new employee")
    console.print("2. [blue]List[/blue] all employees")
    console.print("3. [yellow]Update[/yellow] an existing employee")
    console.print("4. [red]Delete[/red] an employee")
    
    # --- NOUVEAU: CONTRACT MANAGEMENT (Choix 5 et 6) ---
    console.print("\n[bold underline]CONTRACT MANAGEMENT[/bold underline]")
    console.print("5. [green]Create[/green] a new Contract (All clients)")
    console.print("6. [yellow]Update[/yellow] a Contract (All contracts)")

    # --- NOUVEAU: EVENT MANAGEMENT (Choix 7 et 8) ---
    console.print("\n[bold underline]EVENT MANAGEMENT[/bold underline]")
    console.print("7. [blue]List[/blue] Events (with filters)")
    console.print("8. [yellow]Update[/yellow] an Event (Assign Support)") 
    
    console.print("---------------------------------------")
    
    # --- SORTIE (Choix 9 et 10) ---
    console.print("9. [bold]Return[/bold] to Main Menu (Logout)")
    console.print("10. [bold red]Quit[/bold red] Application")     
    
    console.print("="*50, style="bold magenta")

def management_menu(session: Session, employee: Employee, token: str) -> tuple[str, str | None]:
    """
    Main loop and router for the Management department menu.
    Mis à jour pour gérer les choix 1 à 10.
    """
    while True:
        # 1. Vérification de l'expiration du jeton (sécurité)
        if get_employee_from_token(token, session) is None:
            console.print("\n[bold red]Session Expired.[/bold red] You have been logged out.")
            return 'logout', None

        # 2. Afficher le menu
        display_management_menu(employee)
        
        # 3. Récupérer le choix (plage 1-10)
        choice = Prompt.ask("Select an option [1-10]", choices=[str(i) for i in range(1, 11)]).strip()

        # 4. ROUTAGE MIS À JOUR (1-10)
        
        # --- EMPLOYEE MANAGEMENT (1-4) ---
        if choice == '1':
            create_employee_cli(session, employee)
        elif choice == '2':
            list_employees_cli(session, employee)
        elif choice == '3':
            update_employee_cli(session, employee)
        elif choice == '4':
            delete_employee_cli(session, employee)
        
        # --- CONTRACT MANAGEMENT (5-6) ---
        elif choice == '5':
            create_contract_cli(session, employee)
        elif choice == '6':
            update_contract_cli(session, employee)

        # --- EVENT MANAGEMENT (7-8) ---
        elif choice == '7':
            list_events_cli(session, employee)
        elif choice == '8':
            update_event_cli(session, employee)

        # --- SORTIE (9-10) ---
        elif choice == '9':
            console.print("[bold green]Logging out...[/bold green]")
            return 'logout', None 
        elif choice == '10': 
            console.print("[bold red]Quitting application...[/bold red]")
            sys.exit(0)
        
        # Gestion de l'erreur
        else:
             console.print("[bold red]Invalid choice. Please select an option from 1 to 10.[/bold red]")

        # Le routeur retourne 'stay' pour que main.py rafraîchisse le jeton
        return 'stay', token