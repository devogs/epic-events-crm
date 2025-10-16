"""
CRM Controller: Handles all CRUD operations related to Client, Contract, and Event models.
Implements the core business logic and data validation.
"""
import re
import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func, or_
from rich.console import Console

# Import des Modèles et de l'outil de permission
from app.models import Client, Contract, Event, Employee
# Note: check_permission est importé de app.authentication
from app.authentication import check_permission 

console = Console()


# --- Helper Functions ---

def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    return re.fullmatch(regex, email)

def is_valid_phone(phone: str) -> bool:
    """Basic phone number validation (accepts digits, spaces, hyphens)."""
    # Accepte 5 à 20 chiffres, espaces ou tirets
    return bool(re.fullmatch(r'^[\d\s-]{5,20}$', phone))


# =============================================================================
# --- CLIENTS CRUD ---\
# =============================================================================

def create_client(session: Session, current_user: Employee, full_name: str, email: str, phone: str, company_name: str) -> Client | None:
    """
    Creates a new Client record and automatically assigns the creator as the sales contact.
    Permissions: Commercial (creates their own clients) or Gestion (creates any client).
    """
    if not check_permission(current_user, 'create_client'):
        raise PermissionError("Permission denied to create a client.")

    # 1. Validation des données
    if not full_name or not email or not phone:
        console.print("[bold red]ERROR:[/bold red] Missing required field(s).")
        return None

    if not is_valid_email(email):
        console.print("[bold red]ERROR:[/bold red] Invalid email format.")
        return None
    
    if not is_valid_phone(phone):
        console.print("[bold red]ERROR:[/bold red] Invalid phone number format.")
        return None

    # L'ID du contact commercial est celui de l'utilisateur actuel
    sales_contact_id = current_user.id

    try:
        new_client = Client(
            full_name=full_name,
            email=email,
            phone=phone,
            company_name=company_name,
            sales_contact_id=sales_contact_id
        )

        session.add(new_client)
        session.commit()
        return new_client

    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERROR:[/bold red] A client with this email already exists.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]FATAL ERROR:[/bold red] An unexpected error occurred during client creation: {e}")
        return None

# --- CORRECTION APPLIQUÉE ICI ---
def list_clients(session: Session, current_user: Employee, filter_by_commercial_id: int | None = None) -> list[Client]:
    """
    Retrieves a list of clients, optionally filtered by the sales contact ID.
    Permissions: All departments can view clients, but Commercial only sees their own by default.
    """
    # CRITIQUE: L'objet Employee (current_user) doit être le premier argument.
    if not check_permission(current_user, 'view_clients'):
        raise PermissionError("Permission denied to view clients.")

    query = session.query(Client)

    # Logique de filtrage pour les commerciaux
    if current_user.department == 'Commercial':
        # Si le Commercial demande "Tous", il voit quand même seulement ses clients
        query = query.filter(Client.sales_contact_id == current_user.id)
    elif current_user.department == 'Support' or current_user.department == 'Gestion':
        # Si un filtre est demandé (ex: pour Gestion/Support pour voir les clients d'un Commercial spécifique)
        if filter_by_commercial_id is not None:
            query = query.filter(Client.sales_contact_id == filter_by_commercial_id)
        # Sinon, Gestion et Support voient tous les clients (pas de filtre supplémentaire)
        pass 
    
    return query.all()
# -------------------------------

def update_client(session: Session, current_user: Employee, client_id: int, **kwargs) -> Client | None:
    """
    Updates an existing Client record.
    Permissions: Gestion can update any client. Commercial can only update clients assigned to them.
    """
    client = session.query(Client).filter_by(id=client_id).one_or_none()
    
    if not client:
        console.print(f"[bold red]ERROR:[/bold red] Client with ID {client_id} not found.")
        return None
    
    # Permission 1: Peut-on mettre à jour?
    if not check_permission(current_user, 'update_client'):
        raise PermissionError("Permission denied to update clients.")

    # Permission 2: Le commercial peut-il modifier CE client?
    if current_user.department == 'Commercial' and client.sales_contact_id != current_user.id:
        console.print("[bold red]ERROR:[/bold red] You can only update clients assigned to you.")
        return None

    try:
        updates_made = False
        
        # Validation et application des champs mis à jour
        if 'full_name' in kwargs and kwargs['full_name']:
            client.full_name = kwargs['full_name']
            updates_made = True
            
        if 'email' in kwargs and kwargs['email']:
            if not is_valid_email(kwargs['email']):
                raise ValueError("Invalid email format.")
            client.email = kwargs['email']
            updates_made = True
            
        if 'phone' in kwargs and kwargs['phone']:
            if not is_valid_phone(kwargs['phone']):
                raise ValueError("Invalid phone number format.")
            client.phone = kwargs['phone']
            updates_made = True
            
        if 'company_name' in kwargs and kwargs['company_name']:
            client.company_name = kwargs['company_name']
            updates_made = True
            
        # Changement du contact commercial (Gestion uniquement)
        if 'sales_contact_id' in kwargs and kwargs['sales_contact_id']:
            if current_user.department != 'Gestion':
                raise PermissionError("Only 'Gestion' can reassign the sales contact.")
                
            new_sales_id = kwargs['sales_contact_id']
            new_sales_contact = session.query(Employee).filter_by(id=new_sales_id).one_or_none()
            
            if not new_sales_contact or new_sales_contact.department != 'Commercial':
                raise ValueError(f"Sales contact ID {new_sales_id} must be a Commercial employee.")

            client.sales_contact_id = new_sales_id
            updates_made = True
            
        if updates_made:
            session.commit()
            return client
        else:
            return client
            
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]ERREUR de validation:[/bold red] {e}")
        return None
    except PermissionError as e:
        session.rollback()
        console.print(f"[bold red]ERREUR de permission:[/bold red] {e}")
        return None
    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERREUR DB:[/bold red] Erreur d'intégrité (l'email est peut-être déjà utilisé).")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR FATALE:[/bold red] Une erreur inattendue est survenue lors de la modification du client: {e}")
        return None
    

# =============================================================================
# --- CONTRACTS CRUD ---\
# =============================================================================

def create_contract(session: Session, current_user: Employee, client_id: int, total_amount: Decimal, remaining_amount: Decimal) -> Contract | None:
    """
    Creates a new Contract.
    Permissions: Gestion only.
    """
    if not check_permission(current_user, 'create_contract'):
        raise PermissionError("Permission denied. Only 'Gestion' can create contracts.")

    # 1. Validation des montants
    if total_amount <= 0 or remaining_amount < 0 or remaining_amount > total_amount:
        console.print("[bold red]ERROR:[/bold red] Invalid amounts.")
        return None

    # 2. Validation du client
    client = session.query(Client).filter_by(id=client_id).one_or_none()
    if not client:
        console.print(f"[bold red]ERROR:[/bold red] Client with ID {client_id} not found.")
        return None

    try:
        new_contract = Contract(
            client_id=client_id,
            sales_contact_id=client.sales_contact_id, # Assigne le commercial du client
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            status_signed=(remaining_amount == Decimal('0.00')), # Si reste=0, il est signé
        )

        session.add(new_contract)
        session.commit()
        return new_contract

    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERREUR DB:[/bold red] Erreur d'intégrité lors de la création du contrat.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR FATALE:[/bold red] Une erreur inattendue est survenue lors de la création du contrat: {e}")
        return None

def list_contracts(session: Session, current_user: Employee, filter_signed: bool | None = None) -> list[Contract]:
    """
    Retrieves a list of contracts, optionally filtered by status (signed/not signed).
    Permissions: Gestion sees all. Commercial sees only their clients' contracts. Support sees signed contracts only.
    """
    if not check_permission(current_user, 'view_contracts'):
        raise PermissionError("Permission denied to view contracts.")

    query = session.query(Contract)

    if current_user.department == 'Commercial':
        # Commercial : Seulement les contrats de leurs clients
        query = query.filter(Contract.sales_contact_id == current_user.id)
        
    elif current_user.department == 'Support':
        # Support : Seulement les contrats SIGNÉS (qui peuvent avoir un événement)
        query = query.filter(Contract.status_signed == True)

    # Filtrage additionnel par statut si demandé
    if filter_signed is not None:
        query = query.filter(Contract.status_signed == filter_signed)
        
    return query.all()

def update_contract(session: Session, current_user: Employee, contract_id: int, **kwargs) -> Contract | None:
    """
    Updates an existing Contract record.
    Permissions: Gestion can update all. Commercial can only update amounts/status for their clients' contracts.
    """
    contract = session.query(Contract).filter_by(id=contract_id).one_or_none()
    
    if not contract:
        console.print(f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found.")
        return None

    if not check_permission(current_user, 'update_contract'):
        raise PermissionError("Permission denied to update contracts.")
        
    # Permission 2: Vérification de la propriété du contrat pour le Commercial
    if current_user.department == 'Commercial' and contract.sales_contact_id != current_user.id:
        console.print("[bold red]ERROR:[/bold red] You can only update contracts assigned to your clients.")
        return None

    try:
        updates_made = False

        if 'remaining_amount' in kwargs:
            new_remaining = Decimal(str(kwargs['remaining_amount']))
            if new_remaining < 0 or new_remaining > contract.total_amount:
                raise ValueError("Remaining amount is invalid.")

            contract.remaining_amount = new_remaining
            # Mise à jour automatique du statut
            contract.status_signed = (new_remaining == Decimal('0.00'))
            updates_made = True
            
        if 'total_amount' in kwargs:
            # Gestion uniquement pour le montant total
            if current_user.department != 'Gestion':
                raise PermissionError("Only 'Gestion' can change the total contract amount.")
            
            new_total = Decimal(str(kwargs['total_amount']))
            if new_total <= 0:
                raise ValueError("Total amount must be positive.")
            
            # Ne pas laisser le total devenir inférieur au montant restant
            if new_total < contract.remaining_amount:
                 raise ValueError("Total amount cannot be less than the remaining amount.")
            
            contract.total_amount = new_total
            updates_made = True

        if updates_made:
            session.commit()
            return contract
        else:
            return contract
            
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]ERREUR de validation:[/bold red] {e}")
        return None
    except PermissionError as e:
        session.rollback()
        console.print(f"[bold red]ERREUR de permission:[/bold red] {e}")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR FATALE:[/bold red] Une erreur inattendue est survenue lors de la modification du contrat: {e}")
        return None


# =============================================================================
# --- EVENTS CRUD ---\
# =============================================================================

def create_event(session: Session, current_user: Employee, contract_id: int, name: str, attendees: int, start_date: datetime.datetime, end_date: datetime.datetime, location: str, notes: str) -> Event | None:
    """
    Creates a new Event for a signed contract.
    Permissions: Commercial only, for their signed contracts.
    """
    if not check_permission(current_user, 'create_event'):
        raise PermissionError("Permission denied to create events.")

    # 1. Validation du Contrat
    contract = session.query(Contract).filter_by(id=contract_id).one_or_none()
    if not contract:
        console.print(f"[bold red]ERROR:[/bold red] Contract with ID {contract_id} not found.")
        return None
        
    if not contract.status_signed:
        console.print("[bold red]ERROR:[/bold red] Cannot create an event for an unsigned contract.")
        return None

    # 2. Vérification de la propriété du contrat (Commercial seulement)
    if contract.sales_contact_id != current_user.id:
        console.print("[bold red]ERROR:[/bold red] You can only create events for your clients' contracts.")
        return None
        
    # 3. Validation des dates
    if start_date >= end_date:
        console.print("[bold red]ERROR:[/bold red] Start date must be before end date.")
        return None

    try:
        new_event = Event(
            contract_id=contract_id,
            name=name,
            attendees=attendees,
            event_start=start_date,
            event_end=end_date,
            location=location,
            notes=notes,
            # Le contact support est laissé à NULL initialement
            support_contact_id=None 
        )

        session.add(new_event)
        session.commit()
        return new_event

    except IntegrityError:
        session.rollback()
        console.print("[bold red]ERREUR DB:[/bold red] Erreur d'intégrité lors de la création de l'événement.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR FATALE:[/bold red] Une erreur inattendue est survenue lors de la création de l'événement: {e}")
        return None


def list_events(session: Session, current_user: Employee, filter_by_support_id: int | None = None) -> list[Event]:
    """
    Retrieves a list of events.
    Permissions: Gestion sees all. Commercial sees events for their contracts. Support sees events assigned to them.
    """
    if not check_permission(current_user, 'view_events'):
        raise PermissionError("Permission denied to view events.")

    query = session.query(Event)

    if current_user.department == 'Commercial':
        # Commercial : Événements liés à leurs contrats
        query = query.join(Contract).filter(Contract.sales_contact_id == current_user.id)
    elif current_user.department == 'Support':
        # Support : Événements qui leur sont assignés
        query = query.filter(Event.support_contact_id == current_user.id)
        
    # Filtrage additionnel par ID support (utile pour Gestion et Commercial/Support s'ils veulent filtrer)
    if filter_by_support_id is not None:
        query = query.filter(Event.support_contact_id == filter_by_support_id)
        
    return query.all()

def update_event(session: Session, current_user: Employee, event_id: int, **kwargs) -> Event | None:
    """
    Updates an existing Event record.
    Permissions: Gestion can update all. Commercial can update non-assigned events. Support can update their assigned events.
    """
    event = session.query(Event).filter_by(id=event_id).one_or_none()
    
    if not event:
        console.print(f"[bold red]ERROR:[/bold red] Event with ID {event_id} not found.")
        return None
        
    if not check_permission(current_user, 'update_event'):
        raise PermissionError("Permission denied to update events.")

    # Vérification des autorisations spécifiques
    is_assigned_to_support = event.support_contact_id == current_user.id
    is_sales_contact = event.contract.sales_contact_id == current_user.id

    if current_user.department == 'Commercial':
        # Un commercial ne peut modifier que s'il est le commercial en charge (et que l'événement n'est pas assigné)
        if not is_sales_contact:
            console.print("[bold red]ERROR:[/bold red] You can only update events for your clients' contracts.")
            return None
        # Le commercial ne peut pas modifier un événement qui a déjà un contact support assigné
        if event.support_contact_id is not None:
            console.print("[bold red]ERROR:[/bold red] Event is assigned to Support. Only Support or Gestion can update it now.")
            return None
            
    elif current_user.department == 'Support' and not is_assigned_to_support:
        # Un support ne peut modifier que ses propres événements
        console.print("[bold red]ERROR:[/bold red] You can only update events assigned to you.")
        return None

    try:
        # Gestion du changement de contact support (Gestion uniquement ou Support pour lui-même)
        if 'support_contact_id' in kwargs:
             # Gestion peut assigner/désassigner
             if current_user.department == 'Gestion':
                 new_support_id = kwargs['support_contact_id']
             # Support ne peut s'assigner que lui-même (s'il n'est pas déjà assigné) ou se désassigner
             elif current_user.department == 'Support':
                 new_support_id = kwargs['support_contact_id']
                 if new_support_id is not None and new_support_id != current_user.id:
                     raise PermissionError("Support staff can only assign themselves or unassign.")
             else: # Commercial ou autre
                 raise PermissionError("Only Gestion or Support can change the support contact.")

             
             if new_support_id is not None:
                 new_support_contact = session.query(Employee).filter_by(id=new_support_id).one_or_none()
                 if new_support_contact is None:
                     raise ValueError(f"ID {new_support_id} du nouveau contact support non trouvé.")
                 
                 if new_support_contact.department not in ['Support', 'Gestion']:
                     raise ValueError("Le contact support doit être du département 'Support' ou 'Gestion'.")
                     
             # Appliquer le changement
             event.support_contact_id = new_support_id
             del kwargs['support_contact_id'] 

        # Apply updates (pour les autres champs comme name, attendees, dates, etc.)
        for key, value in kwargs.items():
            if hasattr(event, key) and key not in ['id', 'contract_id']: 
                
                if key in ['event_start', 'event_end']:
                    # Validation des dates (si les deux dates sont dans kwargs, elles seront validées par la boucle)
                    pass 
                
                setattr(event, key, value)

        # Vérification finale des dates après application des mises à jour
        if event.event_start >= event.event_end:
             raise ValueError("La date de début doit être antérieure à la date de fin.")


        session.commit()
        return event
        
    except ValueError as e:
        session.rollback()
        console.print(f"[bold red]ERREUR de validation:[/bold red] {e}")
        return None
    except PermissionError as e:
        session.rollback()
        console.print(f"[bold red]ERREUR de permission:[/bold red] {e}")
        return None
    except IntegrityError as e:
        session.rollback()
        console.print(f"[bold red]ERREUR DB:[/bold red] Erreur d'intégrité.")
        return None
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]ERREUR FATALE:[/bold red] Une erreur inattendue est survenue lors de la modification de l'événement: {e}")
        return None