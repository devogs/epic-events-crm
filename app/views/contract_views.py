"""
Contract Views: Handles all user interface (CLI) interactions for Contract CRUD operations.
It calls the pure business logic functions from the crm_controller layer.
"""
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from decimal import Decimal
import sys

# Import local de check_permission pour respecter le principe de dépendance minimale
from app.models import Employee, Client
from app.controllers.contract_controller import (
    create_contract,
    list_contracts,
    update_contract,
)
# Pour les listes d'employés utiles (Gestion)
from app.controllers.employee_controller import list_employees 

console = Console()


# --- Display Functions ---

def display_contract_table(contracts: list, title: str):
    """Utility function to display contracts in a Rich Table."""
    if not contracts:
        console.print(f"[bold yellow]INFO:[/bold yellow] Aucun contrat trouvé pour l'affichage de '{title}'.")
        return
        
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Client (ID)", style="bold green", min_width=20)
    table.add_column("Commercial (ID)", style="yellow", min_width=20)
    table.add_column("Total (€)", justify="right", style="magenta", min_width=15)
    table.add_column("Restant (€)", justify="right", style="red", min_width=15)
    table.add_column("Signé", justify="center", style="bold", min_width=10)
    table.add_column("Création", style="dim", min_width=15)
    
    for contract in contracts:
        client_info = f"{contract.client.full_name} ({contract.client_id})" if contract.client else f"ID: {contract.client_id}"
        commercial_info = f"{contract.commercial_contact.full_name} ({contract.commercial_contact_id})" if contract.commercial_contact else f"ID: {contract.commercial_contact_id}"
        
        remaining = contract.total_amount - contract.amount_paid
        
        table.add_row(
            str(contract.id),
            client_info,
            commercial_info,
            f"{contract.total_amount:,.2f}",
            f"{remaining:,.2f}",
            "[bold green]OUI[/bold green]" if contract.status else "[bold red]NON[/bold red]",
            contract.creation_date.strftime("%Y-%m-%d")
        )
    console.print(table)


# --- CLI Functions ---

def create_contract_cli(session, current_employee: Employee):
    """CLI pour créer un contrat. Normalement réservé à Gestion."""
    console.print("\n[bold green]-- CRÉER UN NOUVEAU CONTRAT --[/bold green]")
    
    if current_employee.department != 'Gestion':
        console.print("[bold red]PERMISSION DENIED:[/bold red] Seul le département 'Gestion' peut créer un contrat.")
        return

    # 1. Saisie de l'ID Client
    while True:
        client_id_str = Prompt.ask("Entrez l'ID du Client concerné").strip()
        try:
            client_id = int(client_id_str)
            # Vérification simple de l'existence du client
            client = session.query(Client).filter_by(id=client_id).one_or_none()
            if client:
                console.print(f"[bold dim]Client trouvé:[/bold dim] {client.full_name}")
                break
            else:
                console.print(f"[bold red]Erreur:[/bold red] Client ID {client_id} non trouvé.")
        except ValueError:
            console.print("[bold red]Erreur:[/bold red] L'ID doit être un nombre.")

    # 2. Saisie des montants
    while True:
        try:
            total_amount = Decimal(Prompt.ask("Montant Total du Contrat (€)").replace(',', '.').strip())
            amount_paid = Decimal(Prompt.ask("Montant Payé (Acompte) (€)").replace(',', '.').strip())
            if total_amount > 0 and amount_paid >= 0 and amount_paid <= total_amount:
                break
            console.print("[bold red]Erreur:[/bold red] Vérifiez que le montant total > 0 et que l'acompte est valide.")
        except Exception:
            console.print("[bold red]Erreur:[/bold red] Montant saisi invalide.")
            
    # 3. Saisie du statut (facultatif, le contrôleur peut le déduire)
    status_str = Prompt.ask("Le contrat est-il déjà signé/payé ? [y/N]", choices=['y', 'n'], default='n').lower()
    status = status_str == 'y'

    # 4. Appel au contrôleur
    new_contract = create_contract(
        session,
        current_employee,
        client_id,
        total_amount,
        amount_paid,
        status
    )
    
    if new_contract:
        console.print(f"\n[bold green]SUCCÈS:[/bold green] Contrat ID [cyan]{new_contract.id}[/cyan] créé pour le client ID {client_id}.")


def list_contracts_cli(session, current_employee: Employee):
    """CLI pour lister les contrats avec options de filtrage."""
    console.print("\n[bold blue]-- LISTE DES CONTRATS --[/bold blue]")

    # Logique de filtrage selon les besoins de l'équipe Commerciale (et la Gestion)
    
    choices = ['1', '2', '3', '4']
    
    if current_employee.department == 'Commercial':
         choice = Prompt.ask("Filtrer? [1: Tous | 2: Non signés | 3: Non entièrement payés]", choices=choices[:-1], default='1')
    else:
         choice = Prompt.ask("Filtrer? [1: Tous | 2: Non signés | 3: Non entièrement payés]", choices=choices, default='1')
         
    filter_by_status = None
    filter_by_unpaid = False
    filter_by_commercial = None
    title = "TOUS LES CONTRATS"

    if choice == '2':
        filter_by_status = False
        title = "CONTRATS NON SIGNÉS"
    elif choice == '3':
        filter_by_unpaid = True
        title = "CONTRATS NON ENTIÈREMENT PAYÉS"

    # Commercial ne voit que ses contrats (sauf si le cahier des charges dit le contraire - ici, on filtre par défaut pour le Commercial)
    if current_employee.department == 'Commercial':
        filter_by_commercial = current_employee.id
        title = f"{title} (Mes Clients - ID {current_employee.id})"

    contracts = list_contracts(session, current_employee, filter_by_status=filter_by_status, filter_by_unpaid=filter_by_unpaid, filter_by_commercial_id=filter_by_commercial)

    if contracts is not None:
        display_contract_table(contracts, title)


def update_contract_cli(session, current_employee: Employee):
    """CLI pour mettre à jour un contrat existant."""
    console.print("\n[bold yellow]-- MODIFIER UN CONTRAT --[/bold yellow]")
    
    # 1. Saisie de l'ID
    while True:
        contract_id_str = Prompt.ask("Entrez l'ID du contrat à modifier (ou 'q' pour annuler)").strip()
        if contract_id_str.lower() == 'q':
            return
        try:
            contract_id = int(contract_id_str)
            break
        except ValueError:
            console.print("[bold red]Erreur:[/bold red] L'ID doit être un nombre.")
            
    # 2. Collecte des données à mettre à jour
    updates = {}
    
    console.print("[dim]Laissez les champs vides/inchangés pour conserver les valeurs actuelles.[/dim]")
    
    # Montant total
    total_amount_str = Prompt.ask("Nouveau Montant Total du Contrat (€)").strip().replace(',', '.')
    try:
        if total_amount_str:
            updates['total_amount'] = Decimal(total_amount_str)
    except Exception:
        console.print("[bold red]Erreur:[/bold red] Montant total invalide.")
        return

    # Montant payé
    amount_paid_str = Prompt.ask("Nouveau Montant Payé (Acompte) (€)").strip().replace(',', '.')
    try:
        if amount_paid_str:
            updates['amount_paid'] = Decimal(amount_paid_str)
    except Exception:
        console.print("[bold red]Erreur:[/bold red] Montant payé invalide.")
        return
            
    # Statut
    status_str = Prompt.ask("Le contrat est-il signé/payé ? [y/N/Laisser vide]").strip().lower()
    if status_str in ('y', 'n'):
        updates['status'] = status_str == 'y'

    if not updates:
        console.print("[bold yellow]INFO:[/bold yellow] Aucune donnée valide fournie pour la mise à jour.")
        return

    # 3. Appel au contrôleur (le contrôleur vérifie les permissions)
    updated_contract = update_contract(
        session,
        current_employee,
        contract_id,
        **updates
    )

    if updated_contract:
        console.print(f"\n[bold green]SUCCÈS:[/bold green] Contrat ID [cyan]{updated_contract.id}[/cyan] mis à jour. Signé: {'[bold green]OUI[/bold green]' if updated_contract.status else '[bold red]NON[/bold red]'}")