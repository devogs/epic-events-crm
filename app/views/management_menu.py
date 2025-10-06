"""
Management menu interface (View layer).
Handles routing for Employee CRUD operations.
"""
import sys
from rich.console import Console
from rich.prompt import Prompt

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
    All display text is in English, except for the department name.
    """
    
    department_name = employee.department 

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


def management_menu(employee, session):
    """
    Main loop for the Management menu.

    Args:
        employee (Employee): The currently logged-in Employee object.
        session (Session): The SQLAlchemy database session.
    
    Returns:
        str: 'logout' if the user chooses to return to the main login menu,
             or calls sys.exit(0) if the user quits the application.
    """
    while True:
        display_management_menu(employee)
        
        choice = Prompt.ask("Select an option [1/2/3/4/5/6]", choices=['1', '2', '3', '4', '5', '6'])
        
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
