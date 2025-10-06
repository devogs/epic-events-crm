"""
Script to manually create a new employee in the database for testing purposes.
This is a utility script and not part of the main application.
"""
import os
import sys
from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# --- CORRECTION DE L'ERREUR D'IMPORTATION ---
# Ajoute le répertoire parent (la racine du projet) au sys.path.
# Ceci permet d'importer les modules du dossier 'app'.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
# ---------------------------------------------

# L'importation fonctionne maintenant car la racine du projet est dans le chemin.
from app.models import Employee, DATABASE_URL

console = Console()

def create_employee_cli_utility():
    """
    Interactively gathers data and creates a new Employee for testing.
    """
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    console.print("\n[bold green]----- CRÉATION D'UN EMPLOYÉ DE TEST ----- [/bold green]")
    console.print("[yellow]Veuillez fournir les informations pour le nouvel employé (Gestion, Commercial, Support).[/yellow]")

    full_name = Prompt.ask("Nom Complet de l'employé").strip()
    email = Prompt.ask("Email (Doit être unique)").strip()
    
    # Validation basique de l'email
    if '@' not in email:
        console.print("[bold red]Erreur: Format d'email invalide.[/bold red]")
        session.close()
        return

    password = Prompt.ask("Mot de passe par défaut", password=True)
    phone = Prompt.ask("Numéro de téléphone").strip()

    # Sélection du département
    DEPARTMENT_OPTIONS = {'1': 'Gestion', '2': 'Commercial', '3': 'Support'}
    while True:
        console.print("\n[bold yellow]Sélectionnez le Département:[/bold yellow]")
        for key, value in DEPARTMENT_OPTIONS.items():
            console.print(f"  {key}: {value}")
        
        choice = Prompt.ask("Entrez le numéro", choices=DEPARTMENT_OPTIONS.keys())
        department = DEPARTMENT_OPTIONS[choice]
        break

    try:
        # Check if email exists
        if session.query(Employee).filter_by(email=email).one_or_none():
             console.print("[bold red]Erreur: Cet email existe déjà. Opération annulée.[/bold red]")
             return

        # Create the new Employee object
        new_employee = Employee(
            full_name=full_name,
            email=email,
            phone=phone,
            department=department
        )
        # Le setter du modèle hash le mot de passe automatiquement
        new_employee.password = password 

        session.add(new_employee)
        session.commit()
        console.print(f"\n[bold green]SUCCÈS:[/bold green] Employé '{full_name}' ({department}) créé avec ID: {new_employee.id}.")

    except IntegrityError as e:
        session.rollback()
        console.print(f"\n[bold red]ERREUR:[/bold red] Échec de la création. Détails de l'intégrité de la base de données: {e}")
    except Exception as e:
        session.rollback()
        console.print(f"\n[bold red]ERREUR INCONNUE:[/bold red] {e}")
    finally:
        session.close()

if __name__ == "__main__":
    create_employee_cli_utility()
