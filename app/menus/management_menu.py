"""
Management menu interface.
Handles routing for Employee CRUD operations.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt
from app.controllers.employee_controller import (
    create_employee_cli,
    list_employees_cli,
    update_employee_cli,
    delete_employee_cli,
)

console = Console()

def display_management_menu(employee):
    """
    Displays the menu options for the Management department using the required design.
    """
    console.print("\n" + "="*50, style="bold magenta")
    console.print(f"[bold magenta]MANAGEMENT DASHBOARD[/bold magenta] | User: [cyan]{employee.full_name}[/cyan] (ID: {employee.id})")
    console.print("="*50, style="bold magenta")
    
    console.print("1. [green]Create[/green] a new employee")
    console.print("2. [blue]List[/blue] all employees")
    console.print("3. [yellow]Update[/yellow] an existing employee")
    console.print("4. [red]Delete[/red] an employee")
    
    console.print("---------------------------------------")
    
    console.print("5. [bold]Return[/bold] to Main Menu (Logout)")
    console.print("6. [bold red]Quit[/bold red] Application")
    
    console.print("---------------------------------------")


def management_menu(employee, session):
    """
    Main loop for the Management menu.

    Args:
        employee (Employee): The currently logged-in Employee object.
        session (Session): The SQLAlchemy database session.
    
    Returns:
        bool: True if the user chooses to quit the application (option 6),
              False if the user returns to the main menu (option 5).
    """
    while True:
        display_management_menu(employee)
        
        choice = Prompt.ask("Select an option", choices=['1', '2', '3', '4', '5', '6'])
        
        if choice == '1':
            create_employee_cli(session)
        elif choice == '2':
            list_employees_cli(session)
        elif choice == '3':
            update_employee_cli(session)
        elif choice == '4':
            delete_employee_cli(session)
        elif choice == '5':
            return False 
        elif choice == '6':
            console.print("[bold red]Quitting application...[/bold red]")
            sys.exit(0)
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
