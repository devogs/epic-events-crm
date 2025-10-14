"""
This is the main script for the Epic Events CRM command-line interface.
It handles user authentication using JWT and routes to different functionalities based on user permissions.
"""

from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy.orm import sessionmaker
import os
import sys

# Configuration pour les imports relatifs
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)


# Imports des Modèles et des outils DB
from app.models import (
    Employee, 
    DATABASE_URL, 
    Base, 
    engine, 
    initialize_roles # Import critique pour l'initialisation de la base
)
# Imports de l'Authentification (NOTE: create_access_token retourne maintenant token et expiration display)
from app.authentication import check_password, create_access_token, get_employee_from_token
# Imports des Vues (Menus)
from app.views.management_menu import management_menu 
# Les autres menus seront importés ici si/quand implémentés
# from app.views.sales_menu import sales_menu 
# from app.views.support_menu import support_menu 

console = Console()

# --- Global State Simulation ---
# Stocke le jeton JWT pour la session actuelle.
GLOBAL_JWT_TOKEN: str | None = None

def get_session():
    """
    Crée et retourne une nouvelle session SQLAlchemy.
    """
    try:
        # Utilise l'engine importé de models.py
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        console.print(f"[bold red]Erreur de connexion à la base de données:[/bold red] {e}")
        sys.exit(1)

def login() -> str | None:
    """
    Gère le processus de connexion de l'utilisateur et retourne un jeton JWT en cas de succès.
    """
    console.print("\n" + "="*50)
    console.print("[bold cyan]EPIC EVENTS CRM LOGIN[/bold cyan]")
    console.print("="*50)

    email = Prompt.ask("Enter your email").strip().lower()
    password = Prompt.ask("Enter your password", password=True)
    
    session = get_session()
    
    try:
        # 1. Récupérer l'employé par email
        employee = session.query(Employee).filter_by(email=email).one_or_none()
        
        if employee and employee.verify_password(password):
            # 2. Créer le jeton JWT (retourne le token ET l'affichage de l'expiration)
            token, expire_display = create_access_token(
                employee_id=employee.id,
                employee_email=employee.email,
                employee_department=employee.department
            )
            console.print(f"\n[bold green]Login successful![/bold green] Welcome, {employee.full_name}.")
            
            # CORRECTION COULEUR: Changement de [bold dim] en [bold yellow dim]
            console.print(f"[bold yellow dim]JWT Token generated (Expires in {expire_display}):[/bold yellow dim] [dim]{token[:50]}...[/dim]")
            
            return token
        else:
            console.print("\n[bold red]Login failed.[/bold red] Invalid email or password.")
            return None
    except Exception as e:
        console.print(f"[bold red]An error occurred during login:[/bold red] {e}")
        return None
    finally:
        session.close()

# --- MENU ROUTER ---

def main_menu_router(logged_in_employee, session, token: str) -> str:
    """
    Aiguille l'employé vers le menu approprié en fonction de son département.
    """
    department_name = logged_in_employee.department 

    if department_name == 'Gestion':
        return management_menu(logged_in_employee, session, token) 
    # elif department_name == 'Commercial':
    #     return sales_menu(logged_in_employee, session, token)
    # elif department_name == 'Support':
    #     return support_menu(logged_in_employee, session, token)
    elif department_name in ('Commercial', 'Support'):
        # Espace réservé pour les menus non implémentés
        console.print(f"\n[bold yellow]Menu for {department_name} is not yet implemented.[/yellow]")
        return 'logout'
    else:
        console.print("[bold red]Error: Unknown department or no menu implemented.[/bold red]")
        return 'logout'


def main():
    """
    Fonction principale de l'application CLI, gérant la boucle de connexion et l'état (JWT).
    """
    global GLOBAL_JWT_TOKEN
    
    # --- INITIALISATION DE LA BASE DE DONNÉES ---
    session = get_session()
    try:
        console.print("\n--- Initializing Database Structure ---", style="bold")
        # Créer toutes les tables si elles n'existent pas
        Base.metadata.create_all(engine)
        console.print("All tables created/verified.", style="green")

        # Initialiser les rôles par défaut et l'admin par défaut
        initialize_roles(session)
        
        # Le commit est essentiel pour que initialize_roles soit permanent
        session.commit() 
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]FATAL ERROR during DB initialization:[/bold red] {e}")
        sys.exit(1)
    finally:
        session.close()
    
    # --- BOUCLE PRINCIPALE ---
    while True:
        # 1. La tentative de connexion retourne un jeton JWT
        token = login()

        if token:
            GLOBAL_JWT_TOKEN = token
            
            session = get_session() 
            
            try:
                # 2. Utiliser le jeton pour charger et valider l'employé (vérification initiale)
                logged_in_employee = get_employee_from_token(GLOBAL_JWT_TOKEN, session)
                
                if logged_in_employee:
                    # 3. Aiguiller vers le menu approprié
                    action = main_menu_router(logged_in_employee, session, GLOBAL_JWT_TOKEN)
                else:
                    # Jeton invalide ou employé supprimé (déjà logué dans get_employee_from_token)
                    action = 'logout'
            except Exception as e:
                console.print(f"[bold red]An unexpected error occurred in the main loop:[/bold red] {e}")
                action = 'logout'
            finally:
                session.close() # Fermeture de la session
            
            # 4. Gérer l'action de sortie du menu
            if action == 'quit':
                console.print("\n[bold yellow]Exiting the application.[/bold yellow]")
                break
            elif action == 'logout':
                GLOBAL_JWT_TOKEN = None # Effacer le jeton à la déconnexion
                console.print("\n[bold blue]You have been logged out. Returning to login screen.[/bold blue]")
        else:
            # Si la connexion a échoué, attendre l'entrée utilisateur pour réessayer
            Prompt.ask("Press Enter to try logging in again...")

if __name__ == "__main__":
    main()