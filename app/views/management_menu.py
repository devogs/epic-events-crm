"""
Management menu interface (View layer).
Handles routing for Employee CRUD operations and includes JWT expiration check.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt

# IMPORT CRITIQUE
from app.authentication import get_employee_from_token 

from .employee_views import (
    create_employee_cli,
    list_employees_cli,
    update_employee_cli,
    delete_employee_cli,
)

console = Console()

def display_management_menu(employee):
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
    
    console.print("---------------------------------------")


# MODIFICATION CRITIQUE : Ajout de la vérification de l'expiration avant l'exécution du choix
def management_menu(employee, session, token: str) -> str:
    """
    Main loop for the Management menu, including immediate JWT expiration check.
    """
    while True:
        # --- 1. VÉRIFICATION DU TOKEN À CHAQUE ITÉRATION (BLOQUE L'AFFICHAGE DU MENU) ---
        employee_is_valid = get_employee_from_token(token, session)
        
        if employee_is_valid is None:
            # Déconnexion forcée AVANT toute interaction.
            console.print("\n[bold red]Session Expired.[/bold red] You have been logged out.")
            return 'logout' 
        
        employee = employee_is_valid
        # --------------------------------------------------------------------------------

        display_management_menu(employee)
        
        choice = Prompt.ask("Select an option [1/2/3/4/5/6]", choices=['1', '2', '3', '4', '5', '6'])
        
        # --- 2. VÉRIFICATION DE SÉCURITÉ JUSTE AVANT L'EXÉCUTION DU CHOIX (CORRECTION DU FLUX) ---
        # Si le token a expiré entre l'affichage du menu et le choix, on bloque.
        if get_employee_from_token(token, session) is None:
            # On réaffiche le message d'expiration ici pour la clarté de l'utilisateur
            console.print("\n[bold red]Session Expired.[/bold red] You have been logged out.")
            return 'logout' 
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
            return 'logout'
        elif choice == '6':
            console.print("[bold red]Quitting application...[/bold red]")
            sys.exit(0)
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")