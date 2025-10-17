"""
This is the main script for the Epic Events CRM command-line interface.
It handles user authentication using JWT and routes to different functionalities based on user permissions.
"""

from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy.orm import sessionmaker
import os
import sys

# --- NOUVEAUX IMPORTS POUR SENTRY ET ENV ---
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
# ------------------------------------------

# Configuration pour les imports relatifs (assure que les modules sont trouvables)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)


# Imports des Modèles et des outils DB
from app.models import (
    Employee, 
    Base, 
    engine, 
    initialize_roles
)
# Imports de l'Authentification 
from app.authentication import check_password, create_access_token, get_employee_from_token

# Imports des Vues (Menus) - Assurez-vous que ces fichiers existent
from app.views.management_menu import management_menu 
from app.views.sales_menu import sales_menu 
from app.views.support_menu import support_menu 

console = Console()

# --- Global State Simulation ---
# Stocke le jeton JWT pour la session actuelle.
GLOBAL_JWT_TOKEN: str | None = None


# --- NOUVELLE FONCTION: INITIALISATION SENTRY ---
def init_sentry():
    """Initializes Sentry SDK using DSN from environment variable (SENTRY_DSN)."""
    sentry_dsn = os.environ.get("SENTRY_DSN")
    
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=1.0,
            environment="cli-prod",
            integrations=[
                SqlalchemyIntegration(),
            ],
            send_default_pii=False,
        )
        console.print("[bold green]Sentry Initialized (DSN found).[/bold green]")
    else:
        console.print("[bold yellow]Sentry DSN not found. Running without error logging. Check SENTRY_DSN environment variable.[/bold yellow]")
# ------------------------------------------------


def get_session():
    """
    Crée et retourne une nouvelle session SQLAlchemy.
    Chaque opération (login ou cycle de menu) doit utiliser une nouvelle session.
    """
    try:
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        # Tentative de capture si Sentry est initialisé
        if sentry_sdk.HUB.get_global_scope().client:
             sentry_sdk.capture_exception(e)
        console.print(f"[bold red]ERREUR FATALE lors de la création de la session:[/bold red] {e}")
        sys.exit(1)


def login_cli(session) -> Employee | None:
    """
    Gère l'interface de connexion, valide les identifiants et génère un token JWT.
    """
    global GLOBAL_JWT_TOKEN

    console.print("\n" + "="*50, style="bold blue")
    console.print("[bold blue]EPIC EVENTS CRM LOGIN[/bold blue]")
    console.print("="*50, style="bold blue")

    email = Prompt.ask("Enter your Email").strip()
    password = Prompt.ask("Enter your Password", password=True).strip()

    employee = session.query(Employee).filter_by(email=email).one_or_none()

    # LOGIQUE DE CONNEXION RESTAURÉE DE main_trusted.py
    if employee and employee._password and check_password(password, employee._password):
        # Authentification réussie
        token, expiration_display = create_access_token(employee.id, employee.department)
        GLOBAL_JWT_TOKEN = token
        
        console.print(f"\n[bold green]Welcome {employee.full_name} ({employee.department})![/bold green]")
        console.print(f"[bold dim]Session expires in: {expiration_display}[/bold dim]")
        return employee
    else:
        # Échec de l'authentification
        console.print("[bold red]ERROR:[/bold red] Invalid email or password.")
        return None


def main_menu_router(employee: Employee, session, token: str) -> tuple[str, str | None]:
    """
    Aiguille l'utilisateur vers le menu approprié en fonction de son département.

    Returns: 
        tuple[str, str | None]: (action: 'stay' | 'logout' | 'quit', new_token: str | None)
    """
    
    department = employee.department
    
    if department == 'Gestion':
        return management_menu(session, employee, token) 
    elif department == 'Commercial':
        return sales_menu(session, employee, token) 
    elif department == 'Support':
        return support_menu(session, employee, token) 
    else:
        console.print(f"[bold red]ERROR:[/bold red] Unknown department '{department}'. Logging out.")
        return 'logout', None


def main():
    """
    Point d'entrée principal de l'application.
    """
    global GLOBAL_JWT_TOKEN 

    # --- CHARGEMENT DU .ENV (NOUVEAU) ---
    base_dir = os.path.dirname(os.path.abspath(__file__)) 
    dotenv_path = os.path.join(base_dir, 'database', '.env') 

    try:
        is_loaded = load_dotenv(dotenv_path)
        
        if not is_loaded:
             console.print(f"[bold yellow]WARNING:[/bold yellow] Failed to load .env file from {dotenv_path}. Check file existence and path.")
        else:
             console.print(f"[bold green]INFO:[/bold green] .env loaded successfully from {dotenv_path}.")
             
    except Exception as e:
         console.print(f"[bold red]FATAL WARNING:[/bold red] Error during .env load: {e}")
    # -----------------------------------

    # 1. Préparation de la base de données
    console.print("[bold cyan]--- Initializing Database Structure & Roles ---[/bold cyan]")
    
    # CRITIQUE: Crée les tables avant d'initialiser les rôles
    Base.metadata.create_all(engine) 
    
    init_session = get_session() 
    
    try:
        initialize_roles(init_session, engine) 
    except Exception as e:
        # Sentry peut être initialisé ici si le .env a fonctionné
        if sentry_sdk.HUB.get_global_scope().client:
            sentry_sdk.capture_exception(e)
            sentry_sdk.flush(timeout=1.0)
        console.print(f"[bold red]ERREUR FATALE lors de l'initialisation de la DB:[/bold red] {e}")
        sys.exit(1)
    finally:
        init_session.close() 

    # --- INITIALISATION SENTRY (NOUVEAU) ---
    init_sentry() 
    # ---------------------------------------

    # Boucle principale de l'application (Login/Menu Loop)
    
    try:
        while True:
            if GLOBAL_JWT_TOKEN is None:
                # État déconnecté : Affichage de l'écran de connexion
                login_session = get_session() 
                logged_in_employee = login_cli(login_session)
                login_session.close() 
                
                if logged_in_employee is None:
                    Prompt.ask("Press Enter to try logging in again...")
            
            else:
                # État connecté : Gestion des menus
                session = get_session() 
                action = 'stay' 
                
                try:
                    # 2. Recharger l'employé à partir du token (Vérification de validité)
                    logged_in_employee = get_employee_from_token(GLOBAL_JWT_TOKEN, session)
                    
                    if logged_in_employee:
                        # 3. Aiguiller vers le menu approprié
                        action, new_token_from_menu = main_menu_router(logged_in_employee, session, GLOBAL_JWT_TOKEN)
                        
                        GLOBAL_JWT_TOKEN = new_token_from_menu 
                    else:
                        action = 'logout'
                except Exception as e:
                    # Capture des erreurs dans la boucle du menu
                    sentry_sdk.capture_exception(e)
                    console.print(f"[bold red]An unexpected error occurred in the main loop:[/bold red] {e}. Error logged to Sentry.")
                    action = 'logout'
                finally:
                    session.close() 
                
                # 4. Gérer l'action de sortie du menu
                if action == 'quit':
                    console.print("\n[bold yellow]Exiting the application.[/bold yellow]")
                    # Flush Sentry sur sortie propre
                    console.print("[bold yellow]Flushing Sentry events before exiting...[/bold yellow]")
                    sentry_sdk.flush(timeout=1.0)
                    
                    break
                elif action == 'logout':
                    GLOBAL_JWT_TOKEN = None 
                    console.print("\n[bold blue]You have been logged out. Returning to login screen.[/bold blue]")

    except Exception as e:
        # --- GESTION DU CRASH FATAL (NOUVEAU) ---
        sentry_sdk.capture_exception(e)
        console.print(f"[bold red]FATAL CRASH:[/bold red] Application encountered an unhandled error. Error logged to Sentry.")
        
        # Flush Sentry pour garantir l'envoi de l'événement
        console.print("[bold yellow]Flushing Sentry events after crash...[/bold yellow]")
        sentry_sdk.flush(timeout=2.0)
        
        # Quitte l'application
        sys.exit(1) 


if __name__ == "__main__":
    main()