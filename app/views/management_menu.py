"""
Management menu interface (View layer).
Handles routing for Employee CRUD operations and includes JWT expiration check.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy.orm import Session
from app.models import Employee # Pour le type hinting

# IMPORT CRITIQUE
from app.authentication import get_employee_from_token 

from .employee_views import (
    create_employee_cli,
    list_employees_cli,
    update_employee_cli,
    delete_employee_cli,
)

console = Console()

def display_management_menu(employee: Employee):
    """
    Displays the menu options for the Management department.
    """
    department_name = employee.department 

    # Style demandé par l'utilisateur
    console.print("\n" + "="*50, style="bold magenta")
    console.print(f"[bold magenta]MANAGEMENT DASHBOARD[/bold magenta] | User: [cyan]{employee.full_name}[/cyan] (ID: {employee.id}, Dept: [yellow]{department_name}[/yellow])")
    console.print("="*50, style="bold magenta")
    
    console.print("1. [green]Create[/green] a new employee")
    console.print("2. [blue]List[/blue] all employees")
    console.print("3. [yellow]Update[/yellow] an existing employee")
    console.print("4. [red]Delete[/red] an employee")
    
    console.print("---------------------------------------")
    
    console.print("5. [bold]Return[/bold] to Main Menu (Logout)")
    console.print("6. [bold red]Quit[/bold red] Application")
    
    console.print("--------------------------------------------------")

def management_menu(session: Session, employee: Employee, token: str) -> tuple[str, str | None]:
    """
    Main loop for the Management dashboard.
    Returns the next action ('stay', 'logout') and the token.
    """
    action = 'stay' # Default action
    
    while action == 'stay':
        # Assurez-vous que l'objet employee est bien dans la session
        employee_is_valid = session.merge(employee)
        employee = employee_is_valid
        
        display_management_menu(employee)
        
        choice = Prompt.ask("Select an option [1/2/3/4/5/6]", choices=['1', '2', '3', '4', '5', '6'])
        
        # --- VÉRIFICATION DE SÉCURITÉ JUSTE AVANT L'EXÉCUTION DU CHOIX ---
        # Si le token a expiré, l'utilisateur est déconnecté.
        if get_employee_from_token(token, session) is None:
            console.print("\n[bold red]Session Expired.[/bold red] You have been logged out.")
            return 'logout', token
        # ----------------------------------------------------------------------------------------

        if choice == '1':
            create_employee_cli(session, employee)
        elif choice == '2':
            list_employees_cli(session, employee)
        elif choice == '3':
            update_employee_cli(session, employee)
        elif choice == '4':
            delete_employee_cli(session, employee)
        elif choice == '5':
            console.print("[bold green]Logging out...[/bold green]")
            # Retourne l'action et le token
            return 'logout', token 
        elif choice == '6':
            console.print("[bold red]Quitting application...[/bold red]")
            sys.exit(0)
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
            
    return 'stay', token