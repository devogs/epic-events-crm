"""
Client Views: Fonctions CLI pour la gestion des clients par l'équipe salese.
"""
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
import re # Ajouté pour les helpers de validation si nécessaire
from datetime import datetime

# Import local de check_permission pour respecter le principe de dépendance minimale
from app.models import Employee 
from app.controllers.client_controller import list_clients, create_client, update_client
from app.controllers.utils import is_valid_email, is_valid_phone

from app.controllers.employee_controller import list_employees # Pour afficher la liste des commerciaux lors de la réassignation

console = Console()


# --- Display Functions ---

def display_client_table(clients: list, title: str):
    """Utility function to display clients in a Rich Table."""
    if not clients:
        console.print(f"[bold yellow]INFO:[/bold yellow] Aucun client trouvé pour l'affichage de '{title}'.")
        return

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Full Name", style="bold", min_width=20)
    table.add_column("Company", min_width=20)
    table.add_column("Email", min_width=30)
    table.add_column("sales Contact (ID)", style="yellow", min_width=20)
    table.add_column("Last Update", style="dim", min_width=15)
    
    for client in clients:
        sales_name = client.sales_contact.full_name if client.sales_contact else "N/A"
        
        table.add_row(
            str(client.id),
            client.full_name,
            client.company_name or "N/A",
            client.email,
            f"{sales_name} ({client.sales_contact_id})",
            client.last_update.strftime("%Y-%m-%d %H:%M") if client.last_update else "N/A"
        )
    console.print(table)


# --- CLI Functions ---

def create_client_cli(session, current_employee: Employee) -> None:
    """
    CLI interface to gather data and call the pure controller function to create a new Client.
    Requires 'Commercial' or 'Gestion' permission.
    """
    # ... (Vérification de permission, inchangée)

    # CORRECTION DES TITRES ET DES PROMPTS EN ANGLAIS
    console.print("\n[bold green]-- CREATE NEW CLIENT --[/bold green]")

    while True:
        # 1. Gather data
        full_name = Prompt.ask("Client Full Name").strip()
        company_name = Prompt.ask("Company Name").strip()
        email = Prompt.ask("Client Email").strip()
        phone = Prompt.ask("Phone Number").strip()

        # 2. Call controller
        try:
            new_client = create_client(
                session,
                current_employee,
                full_name=full_name,
                email=email,
                phone=phone,
                company_name=company_name
            )

            if new_client:
                # CORRECTION DU MESSAGE DE SUCCÈS
                console.print(f"\n[bold green]SUCCESS:[/bold green] Client '{new_client.full_name}' created with ID {new_client.id} and assigned to you.")
                break
            # Le contrôleur gère les erreurs et affiche un message ERROR, donc pas de 'else' ici
            
        except PermissionError as e:
            # Afficher l'erreur de permission générée par le contrôleur
            console.print(f"\n[bold red]ERROR:[/bold red] {e}")
            break
        except Exception as e:
            # Gérer les autres exceptions non capturées par le contrôleur
            console.print(f"\n[bold red]FATAL ERROR:[/bold red] An unexpected error occurred: {e}")
            break


def list_clients_cli(session, current_employee: Employee):
    """CLI pour lister les clients (avec option de filtrage pour 'Mes Clients')."""
    console.print("\n[bold blue]-- LISTE DES CLIENTS --[/bold blue]")

    # Option de filtrage
    choice = Prompt.ask("Filtrer les clients? [1: Tous | 2: Mes Clients]", choices=['1', '2'], default='1')

    filter_id = None
    title = "TOUS LES CLIENTS (Lecture Seule)"
    
    if choice == '2':
        filter_id = current_employee.id
        title = f"MES CLIENTS (sales ID: {current_employee.id})"
        
    clients = list_clients(session, current_employee, filter_by_sales_id=filter_id)

    if clients is not None:
        display_client_table(clients, title)


def update_client_cli(session, current_employee: Employee):
    """CLI pour mettre à jour un client existant."""
    console.print("\n[bold yellow]-- MODIFIER UN CLIENT --[/bold yellow]")
    
    # 1. Saisie de l'ID
    while True:
        client_id_str = Prompt.ask("Entrez l'ID du client à modifier (ou 'q' pour annuler)").strip()
        if client_id_str.lower() == 'q':
            return
        try:
            client_id = int(client_id_str)
            break
        except ValueError:
            console.print("[bold red]Erreur:[/bold red] L'ID doit être un nombre.")
            
    # 2. Collecte des données à mettre à jour
    updates = {}
    
    console.print("[dim]Laissez les champs vides pour conserver les valeurs actuelles.[/dim]")
    
    new_name = Prompt.ask("Nouveau nom complet").strip()
    if new_name: updates['full_name'] = new_name
        
    new_company = Prompt.ask("Nouveau nom de compagnie").strip()
    if new_company: updates['company_name'] = new_company
        
    while True:
        new_email = Prompt.ask("Nouvel email").strip()
        if not new_email: break
        if is_valid_email(new_email):
            updates['email'] = new_email
            break
        console.print("[bold red]Erreur:[/bold red] Format d'email invalide.")
        
    while True:
        new_phone = Prompt.ask("Nouveau téléphone").strip()
        if not new_phone: break
        if is_valid_phone(new_phone):
            updates['phone'] = new_phone
            break
        console.print("[bold red]Erreur:[/bold red] Format de téléphone invalide.")
        
    # Changement du sales : Réservé à l'équipe 'Gestion' (le contrôleur vérifie)
    if current_employee.department == 'Gestion':
        if Confirm.ask("Voulez-vous réassigner le Contact sales ?"):
            sales_employees = [e for e in list_employees(session, filter_by_department='sales') if e.department == 'sales']
            
            console.print("\n[bold yellow]Contacts Commerciaux disponibles:[/bold yellow]")
            for emp in sales_employees:
                 console.print(f"  [cyan]{emp.id}[/cyan]: {emp.full_name}")

            new_sales_id_str = Prompt.ask("Entrez Nouvel ID sales").strip()
            if new_sales_id_str:
                try:
                    # L'argument pour le contrôleur est 'sales_id'
                    updates['sales_id'] = int(new_sales_id_str) 
                except ValueError:
                    console.print("[bold red]Erreur:[/bold red] L'ID du sales doit être un nombre. Annulation de l'entrée.")
        
    if not updates:
        console.print("[bold yellow]INFO:[/bold yellow] Aucune donnée valide fournie pour la mise à jour.")
        return

    # 3. Appel au contrôleur
    updated_client = update_client(
        session,
        current_employee,
        client_id,
        **updates
    )
    
    # 4. Affichage du résultat
    if updated_client:
        console.print(f"\n[bold green]SUCCÈS:[/bold green] Client ID [cyan]{updated_client.id}[/cyan] mis à jour.")