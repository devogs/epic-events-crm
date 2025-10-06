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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from app.models import Employee, DATABASE_URL
from app.authentication import check_password 
from app.views.management_menu import management_menu 

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
    Returns the logged-in Employee object or None.
    """
    session = get_session()
    logged_in_employee = None

    try:
        console.print("\n" + "="*50, style="bold green")
        console.print("[bold green]EPIC EVENTS CRM LOGIN[/bold green]")
        console.print("="*50, style="bold green")
        
        email = Prompt.ask("Enter your email")
        password = Prompt.ask("Enter your password", password=True)

        employee = session.query(Employee).filter_by(email=email).one_or_none()

        if employee and check_password(password, employee._password_hash):
            console.print(f"\n[bold green]✅ Success:[/bold green] Welcome, [cyan]{employee.full_name}[/cyan] ({employee.department})!")
            logged_in_employee = employee
        else:
            console.print("\n[bold red]❌ Login Failed:[/bold red] Invalid email or password.")
            logged_in_employee = None

        return logged_in_employee

    finally:
        if session:
            session.close()

def main_menu_router(employee: Employee, session) -> str:
    """
    Routes the user to their respective department menu based on their role.
    
    Args:
        employee (Employee): The currently logged-in Employee object.
        session (Session): The active SQLAlchemy database session.

    Returns:
        str: 'logout' if the user chooses to return to the login, 
             or 'quit' if the user exits the application.
    """
    if employee.department == 'Gestion':
        return management_menu(employee, session)
    elif employee.department == 'Commercial':
        # TODO: Implémenter sales_menu
        console.print(f"\n[bold blue]Welcome to the Sales Dashboard, {employee.full_name}.[/bold blue]")
        console.print("[yellow]Sales menu is not yet implemented. Logging out...[/yellow]")
        return 'logout'
    elif employee.department == 'Support':
        # TODO: Implémenter support_menu
        console.print(f"\n[bold blue]Welcome to the Support Dashboard, {employee.full_name}.[/bold blue]")
        console.print("[yellow]Support menu is not yet implemented. Logging out...[/yellow]")
        return 'logout'
    else:
        console.print("[bold red]Error: Unknown department or no menu implemented. Logging out.[/bold red]")
        return 'logout'

def main():
    """
    Main function of the CLI application, handling the login loop.
    """
    while True:
        logged_in_employee = login()

        if logged_in_employee:
            session = get_session()
            try:
                result = main_menu_router(logged_in_employee, session)
                
                if result == 'quit':
                    console.print("\n[bold yellow]Exiting the application.[/bold yellow]")
                    break
                else:
                    console.print("\n[bold blue]You have been logged out. Returning to login screen.[/bold blue]")
            finally:
                session.close()
        else:
            Prompt.ask("Press Enter to try logging in again...")
            

if __name__ == "__main__":
    main()
