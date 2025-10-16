"""
Event Views: Handles all user interface (CLI) interactions for Event CRUD operations.
It calls the pure business logic functions from the crm_controller layer.
"""
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
import datetime

# Import local de check_permission pour respecter le principe de dépendance minimale
from app.models import Employee, Contract, Event 
from app.controllers.event_controller import (
    create_event,
    list_events,
    update_event,
)
from app.controllers.employee_controller import list_employees # Pour afficher la liste des supports lors de l'assignation

console = Console()


# --- Helpers de Validation des Dates ---

def get_valid_date(prompt_text: str) -> datetime.datetime | None:
    """Demande et valide une date au format YYYY-MM-DD HH:MM."""
    while True:
        date_str = Prompt.ask(f"{prompt_text} (YYYY-MM-DD HH:MM ou 'q' pour annuler)").strip()
        if date_str.lower() == 'q' or not date_str:
            return None
        try:
            # Essayer de parser le format complet
            return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            console.print("[bold red]Erreur:[/bold red] Format de date/heure invalide. Utilisez YYYY-MM-DD HH:MM.")

def validate_dates_order(start: datetime.datetime, end: datetime.datetime) -> bool:
    """Vérifie que la date de début est antérieure à la date de fin."""
    if start >= end:
        console.print("[bold red]Erreur:[/bold red] La date de début doit être antérieure à la date de fin.")
        return False
    return True


# --- Display Functions ---

def display_event_table(events: list, title: str):
    """Utility function to display events in a Rich Table."""
    if not events:
        console.print(f"[bold yellow]INFO:[/bold yellow] Aucun événement trouvé pour l'affichage de '{title}'.")
        return

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Event Name", style="bold", min_width=20)
    table.add_column("Contract ID", style="bold green", min_width=10, justify="center")
    table.add_column("Support Contact (ID)", style="yellow", min_width=25)
    table.add_column("Attendees", style="dim", min_width=10, justify="right")
    table.add_column("Location", min_width=20)
    table.add_column("Start Date", style="magenta", min_width=15)
    
    for event in events:
        support_info = f"{event.support_contact.full_name} ({event.support_contact_id})" if event.support_contact else "NON ASSIGNÉ"
        
        table.add_row(
            str(event.id),
            event.name,
            str(event.contract_id),
            support_info,
            str(event.attendees),
            event.location,
            event.start_date.strftime("%Y-%m-%d %H:%M")
        )
    console.print(table)


# --- CLI Functions ---

def create_event_cli(session, current_employee: Employee):
    """CLI pour créer un événement (Réservé au Commercial pour un contrat signé)."""
    console.print("\n[bold green]-- CRÉER UN NOUVEL ÉVÉNEMENT --[/bold green]")
    
    # 1. Saisie de l'ID Contrat
    while True:
        contract_id_str = Prompt.ask("Entrez l'ID du Contrat (doit être signé)").strip()
        try:
            contract_id = int(contract_id_str)
            break
        except ValueError:
            console.print("[bold red]Erreur:[/bold red] L'ID doit être un nombre.")

    # 2. Collecte des détails
    name = Prompt.ask("Nom de l'événement").strip()
    location = Prompt.ask("Lieu de l'événement").strip()
    
    while True:
        try:
            attendees = int(Prompt.ask("Nombre de participants estimés").strip())
            if attendees >= 0: break
            console.print("[bold red]Erreur:[/bold red] Le nombre de participants ne peut être négatif.")
        except ValueError:
            console.print("[bold red]Erreur:[/bold red] Doit être un nombre entier.")

    # 3. Saisie et validation des dates
    while True:
        start_date = get_valid_date("Date et heure de début")
        if start_date is None: return # Annulation
        end_date = get_valid_date("Date et heure de fin")
        if end_date is None: return # Annulation
        
        if validate_dates_order(start_date, end_date):
            break

    # 4. Appel au contrôleur (il vérifie la permission et la signature du contrat)
    new_event = create_event(
        session,
        current_employee,
        contract_id,
        name,
        start_date,
        end_date,
        location,
        attendees
    )

    if new_event:
        console.print(f"\n[bold green]SUCCÈS:[/bold green] Événement '{new_event.name}' créé avec l'ID [cyan]{new_event.id}[/cyan]. Le support sera assigné par la Gestion.")


def list_events_cli(session, current_employee: Employee):
    """CLI pour lister les événements avec options de filtrage (Exigence Commerciale)."""
    console.print("\n[bold blue]-- LISTE DES ÉVÉNEMENTS --[/bold blue]")

    # Logique de filtrage Commerciale (seulement ceux dont le client est responsable)
    # L'exigence commerciale était de créer un événement, pas de filtre particulier.
    # On ajoute la logique standard de filtres pour la cohésion de l'app.
    
    choices = ['1', '2', '3']
    
    if current_employee.department == 'Gestion':
         choice = Prompt.ask("Filtrer? [1: Tous | 2: Non assignés au support]", choices=choices[:-1], default='1')
    elif current_employee.department == 'Support':
         choice = Prompt.ask("Filtrer? [1: Tous | 2: Ceux qui me sont attribués]", choices=['1', '2'], default='1')
    else: # Commercial
        choice = Prompt.ask("Filtrer? [1: Tous | 2: Mes événements clients]", choices=['1', '2'], default='1')


    filter_by_support_id = None
    filter_by_unassigned = None
    filter_by_commercial_id = None
    title = "TOUS LES ÉVÉNEMENTS"

    if current_employee.department == 'Gestion' and choice == '2':
        filter_by_unassigned = True
        title = "ÉVÉNEMENTS NON ASSIGNÉS AU SUPPORT"
    elif current_employee.department == 'Support' and choice == '2':
        filter_by_support_id = current_employee.id
        title = f"MES ÉVÉNEMENTS (Support ID: {current_employee.id})"
    elif current_employee.department == 'Commercial' and choice == '2':
        # Le contrôleur doit supporter le filtre par commercial (via le contrat)
        filter_by_commercial_id = current_employee.id
        title = f"ÉVÉNEMENTS DE MES CLIENTS (Commercial ID: {current_employee.id})"
        
    events = list_events(session, current_employee, filter_by_support_id=filter_by_support_id, filter_by_unassigned=filter_by_unassigned, filter_by_commercial_id=filter_by_commercial_id)

    if events is not None:
        display_event_table(events, title)


def update_event_cli(session, current_employee: Employee):
    """CLI pour mettre à jour un événement existant."""
    console.print("\n[bold yellow]-- MODIFIER UN ÉVÉNEMENT --[/bold yellow]")
    
    # 1. Saisie de l'ID
    while True:
        event_id_str = Prompt.ask("Entrez l'ID de l'événement à modifier (ou 'q' pour annuler)").strip()
        if event_id_str.lower() == 'q':
            return
        try:
            event_id = int(event_id_str)
            break
        except ValueError:
            console.print("[bold red]Erreur:[/bold red] L'ID doit être un nombre.")
            
    # 2. Collecte des données à mettre à jour
    updates = {}
    
    console.print("[dim]Laissez les champs vides/inchangés pour conserver les valeurs actuelles.[/dim]")
    
    # Le Support peut mettre à jour ces champs. La Gestion aussi.
    if current_employee.department != 'Commercial':
        new_name = Prompt.ask("Nouveau nom de l'événement").strip()
        if new_name: updates['name'] = new_name
            
        new_location = Prompt.ask("Nouveau lieu").strip()
        if new_location: updates['location'] = new_location
            
        attendees_str = Prompt.ask("Nouveau nombre de participants estimés").strip()
        if attendees_str:
            try:
                updates['attendees'] = int(attendees_str)
            except ValueError:
                console.print("[bold red]Erreur:[/bold red] Le nombre de participants doit être un nombre. Annulation de l'entrée.")
                return

        new_start_date = get_valid_date("Nouvelle date et heure de début")
        if new_start_date is not None: updates['start_date'] = new_start_date

        new_end_date = get_valid_date("Nouvelle date et heure de fin")
        if new_end_date is not None: updates['end_date'] = new_end_date
            
        # NOTE: Le contrôleur vérifiera que start_date < end_date si les deux sont fournies.

    # 3. Changement du contact Support : Réservé à l'équipe 'Gestion'
    if current_employee.department == 'Gestion':
        if Confirm.ask("Voulez-vous assigner/réassigner le Contact Support ?"):
            support_employees = [e for e in list_employees(session) if e.department == 'Support']
            
            console.print("\n[bold yellow]Contacts Support disponibles:[/bold yellow]")
            for emp in support_employees:
                 console.print(f"  [cyan]{emp.id}[/cyan]: {emp.full_name}")

            new_contact_id_input = Prompt.ask("Entrez Nouvel ID Support (ou '0' pour désassigner)").strip()
            try:
                new_contact_id = int(new_contact_id_input)
                # L'argument pour le contrôleur est 'support_contact_id'
                updates['support_contact_id'] = new_contact_id if new_contact_id != 0 else None
            except ValueError:
                console.print("[bold red]Erreur:[/bold red] L'ID du support doit être un nombre. Annulation de l'entrée.")
                
    if not updates:
        console.print("[bold yellow]INFO:[/bold yellow] Aucune donnée valide fournie pour la mise à jour.")
        return

    # 4. Appel au contrôleur (il vérifie les permissions)
    updated_event = update_event(
        session,
        current_employee,
        event_id,
        **updates
    )

    if updated_event:
        console.print(f"\n[bold green]SUCCÈS:[/bold green] Événement ID [cyan]{updated_event.id}[/cyan] mis à jour.")