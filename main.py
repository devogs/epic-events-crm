"""
This is the main script for the Epic Events CRM command-line interface.
It handles user authentication and routes to different functionalities based on user permissions.
"""

from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

from app.models import Employee, DATABASE_URL
from app.authentication import check_password, get_employee_permissions
from app.menus.management_menu import management_menu 

console = Console()

def get_session():
    """
    Creates and returns a new SQLAlchemy session.
    """
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        console.print(f"[bold red]Database connection error:[/bold red] {e}")
        console.print("[bold red]Please ensure your database container is running and .env is correct.[/bold red]")
        sys.exit(1)

def login():
    """
    Handles the user login process.
    """
    session = get_session()
    
    console.print("\n" + "="*50, style="bold green")
    console.print("[bold green]EPIC EVENTS CRM LOGIN[/bold green]")
    console.print("="*50, style="bold green")
    
    email = Prompt.ask("Enter your email")
    password = Prompt.ask("Enter your password", password=True)

    employee = session.query(Employee).filter_by(email=email).one_or_none()

    if employee and check_password(password, employee._password_hash):
        console.print(f"\n[bold green]Login successful! Welcome, {employee.full_name}.[/bold green]")
        return employee
    else:
        console.print("\n[bold red]Login failed. Please check your credentials.[/bold red]")
        return None

def main_menu_router(employee, session):
    """
    Routes the logged-in employee to the appropriate main menu based on their department.
    
    Args:
        employee (Employee): The currently logged-in Employee object.
        session (Session): The SQLAlchemy database session.
        
    Returns:
        bool: True if the user chooses to quit the application (from a submenu), False otherwise.
    """
    if employee.department == 'Gestion':
        return management_menu(employee, session)
    elif employee.department == 'Commercial':
        # TODO: Implement sales_menu
        console.print(f"\n[bold blue]Welcome to the Sales Dashboard, {employee.full_name}.[/bold blue]")
        console.print("[yellow]Sales menu is not yet implemented.[/yellow]")
        return False # Go back to login
    elif employee.department == 'Support':
        # TODO: Implement support_menu
        console.print(f"\n[bold blue]Welcome to the Support Dashboard, {employee.full_name}.[/bold blue]")
        console.print("[yellow]Support menu is not yet implemented.[/yellow]")
        return False 
    else:
        console.print("[bold red]Error: Unknown department or no menu implemented.[/bold red]")
        return False

def main():
    """
    Main function of the CLI application, handling the login loop.
    """
    while True:
        logged_in_employee = login()

        if logged_in_employee:
            with get_session() as session:
                should_quit = main_menu_router(logged_in_employee, session)
            
            if should_quit:
                console.print("\n[bold yellow]Exiting the application.[/bold yellow]")
                break
            else:
                console.print("\n[bold blue]You have been logged out. Returning to login screen.[/bold blue]")
        else:
            Prompt.ask("Press Enter to try logging in again...")

if __name__ == "__main__":
    main()
