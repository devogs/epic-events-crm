"""
This is the main script for the Epic Events CRM command-line interface.
It handles user authentication using JWT and routes to different functionalities based on user permissions.
"""

from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
import os
import sys

# Configuration for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)


# MODIFIÉ : Import de Role
from app.models import Employee, Role, DATABASE_URL, Base, engine
from app.authentication import check_password, create_access_token, decode_access_token
# CORRECTED IMPORT PATH: Importing from app.views as per the project structure
from app.views.management_menu import management_menu 
# The Sales and Support menus will be implemented in subsequent steps
# from app.views.sales_menu import sales_menu 
# from app.views.support_menu import support_menu 

console = Console()

# --- Global State Simulation ---
# Stores the JWT token for the current session.
GLOBAL_JWT_TOKEN: str | None = None

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
        # In a real app, you might want to stop execution here
        sys.exit(1)


# NOUVELLE FONCTION : Initialise les rôles
def initialize_roles(session):
    """ Ensures that the core roles exist in the database. """
    roles_to_ensure = ['Gestion', 'Commercial', 'Support']
    
    for role_name in roles_to_ensure:
        if not session.query(Role).filter_by(name=role_name).one_or_none():
            new_role = Role(name=role_name)
            session.add(new_role)
    
    session.commit()
    console.print("[bold green]Roles initialized in database.[/bold green]")


def get_employee_from_token(token: str, session) -> Employee | None:
    """
    Decodes the JWT token and fetches the corresponding Employee object from the database.
    
    Args:
        token: The JWT access token string.
        session: The SQLAlchemy database session.
        
    Returns:
        The Employee object if valid and found, None otherwise.
    """
    try:
        # Decode the token payload
        payload = decode_access_token(token)
        
        # 'sub' contains the employee ID
        employee_id = payload.get("sub")
        
        if not employee_id:
            console.print("[bold red]Token validation failed:[/bold red] Employee ID not found in token.")
            return None
            
        # Fetch the employee from the DB to ensure they still exist and department is up-to-date
        # La jointure implicite par la relation 'role' assure que le département est chargé
        employee = session.query(Employee).filter_by(id=employee_id).one_or_none()
        
        if not employee:
            console.print(f"[bold red]Token validation failed:[/bold red] Employee with ID {employee_id} no longer exists.")
            return None
            
        return employee
        
    except NoResultFound:
        # Should be caught by .one_or_none() but kept for robustness
        console.print("[bold red]Error:[/bold red] Employee not found in database.")
        return None
    except Exception as e:
        # This catches ExpiredSignatureError, DecodeError, etc., from decode_access_token
        console.print(f"[bold red]Token validation error:[/bold red] {e}")
        return None


def login() -> str | None:
    """
    Handles the user login process by verifying credentials and issuing a JWT token.

    Returns:
        The JWT token string if login is successful, None otherwise.
    """
    # Use a separate session for login attempt
    session = get_session()
    
    console.print("\n" + "="*50, style="bold green")
    console.print("[bold green]EPIC EVENTS CRM LOGIN[/bold green]")
    console.print("="*50, style="bold green")
    
    email = Prompt.ask("Enter your email")
    password = Prompt.ask("Enter your password", password=True)

    employee = session.query(Employee).filter_by(email=email).one_or_none()
    
    # Correction critique de connexion
    if employee and check_password(password, employee._password_hash): 
        # Utilise la propriété @department du modèle (qui renvoie employee.role.name)
        token = create_access_token(employee.id, employee.email, employee.department)
        console.print("\n[bold green]Authentication successful![/bold green]")
        console.print(f"[bold yellow]JWT Token generated (Expires in 24h):[/bold yellow] {token[:50]}...")
        session.close()
        return token
    else:
        console.print("\n[bold red]Authentication failed. Invalid email or password.[/bold red]")
        session.close()
        return None

def main_menu_router(employee: Employee, session) -> str:
    """
    Routes the logged-in user to the appropriate department-specific menu.
    """
    # Utilise la propriété @department du modèle
    department = employee.department 
    
    if department == 'Gestion':
        # The menu function returns 'logout' or 'quit'
        return management_menu(employee, session)
    elif department == 'Commercial':
        console.print(f"\n[bold yellow]Welcome, {employee.full_name} ({department})![/bold yellow] Sales menu is not yet implemented.")
        # return sales_menu(employee, session)
        return 'logout'
    elif department == 'Support':
        console.print(f"\n[bold yellow]Welcome, {employee.full_name} ({department})![/bold yellow] Support menu is not yet implemented.")
        # return support_menu(employee, session)
        return 'logout'
    else:
        console.print("[bold red]Error: Unknown department or no menu implemented.[/bold red]")
        return 'logout'

def main():
    """
    Main function of the CLI application, handling the login loop and state management (JWT).
    """
    global GLOBAL_JWT_TOKEN
    
    # 0. NOUVEAU: Création des tables et initialisation des rôles au démarrage
    try:
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(engine)
        with get_session() as init_session:
            initialize_roles(init_session)
    except Exception as e:
        console.print(f"[bold red]FATAL ERROR during DB initialization:[/bold red] {e}")
        sys.exit(1)

    # TEMPORAIRE : À AJOUTER DANS main.py APRÈS initialize_roles()
    # admin_email = "admin@epicevents.com"
    # if not init_session.query(Employee).filter_by(email=admin_email).one_or_none():
    #     console.print("\n[bold yellow]Creating initial 'Gestion' account...[/bold yellow]")
        
    #     # Récupérer l'ID du rôle 'Gestion'
    #     gestion_role_id = init_session.query(Role).filter_by(name='Gestion').one().id
        
    #     admin_user = Employee(
    #         full_name="Admin Principal",
    #         email=admin_email,
    #         phone="0000000000",
    #         role_id=gestion_role_id # Utilisation du role_id
    #     )
    #     admin_user.password = "admin1234" # CHANGEZ CE MOT DE PASSE IMMEDIATEMENT APRES
    #     init_session.add(admin_user)
    #     init_session.commit()
    #     console.print(f"[bold green]Admin account created:[/bold green] {admin_email} (Password: admin1234)")
    # TEMPORAIRE : À RETIRER UNE FOIS L'ADMIN CRÉÉ

    while True:
        # 1. Login attempt returns a JWT Token
        token = login()

        if token:
            GLOBAL_JWT_TOKEN = token
            
            # Utilise get_session() sans 'with' pour éviter le blocage du rollback implicite
            session = get_session()
            
            # 2. Use the token to load and validate the employee
            logged_in_employee = get_employee_from_token(GLOBAL_JWT_TOKEN, session)
            
            if logged_in_employee:
                # 3. Route to the appropriate menu
                action = main_menu_router(logged_in_employee, session)
            else:
                # Invalid token or deleted employee
                action = 'logout'
            
            # Fermeture de la session
            session.close()

            # 4. Handle menu exit action
            if action == 'quit':
                console.print("\n[bold yellow]Exiting the application.[/bold yellow]")
                break
            elif action == 'logout':
                GLOBAL_JWT_TOKEN = None # Clear token on logout
                console.print("\n[bold blue]You have been logged out. Returning to login screen.[/bold blue]")
        else:
            Prompt.ask("Press Enter to try logging in again...")

if __name__ == "__main__":
    main()