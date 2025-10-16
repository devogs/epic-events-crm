from __future__ import annotations 

import os
import datetime
import re
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    Numeric,
    Boolean,
    ForeignKey,
    Text,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base, Session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from rich.console import Console 

console = Console()

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'database', '.env'))

POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_ADDRESS = os.environ.get("POSTGRES_ADDRESS")

if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_ADDRESS]):
    raise ValueError(
        "Database environment variables are not set. "
        "Please check your .env file in the 'database' folder."
    )

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_ADDRESS}:5432/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL)
Base = declarative_base()


# --- RÔLES ---
class Role(Base):
    # CORRECTION CRITIQUE: Pluriel
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False) 
    employees = relationship("Employee", back_populates="role")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"

# --- EMPLOYÉ ---
class Employee(Base):
    # CORRECTION CRITIQUE: Pluriel
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    # CORRECTION CRITIQUE: Référence de FK au pluriel
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    _password = Column('password_hash', String(128), nullable=False)
    
    # Relationships
    role = relationship("Role", back_populates="employees")
    # CORRECTION CRITIQUE: Référence de FK au pluriel
    clients_assigned = relationship("Client", back_populates="sales_contact")
    contracts_assigned = relationship("Contract", back_populates="sales_contact")
    events_support = relationship("Event", back_populates="support_contact")
    
    @property
    def department(self):
        """Helper to get department name (Role name)."""
        return self.role.name if self.role else None

    @property
    def password(self):
        return None 

    @password.setter
    def password(self, password_str: str):
        """
        Hashes le mot de passe. Import local pour éviter la boucle circulaire.
        """
        # Hachage conservé (utilise l'importation locale)
        from app.authentication import hash_password 
        self._password = hash_password(password_str)
        
    def check_password(self, password_str: str) -> bool:
        """
        Vérifie si le mot de passe fourni correspond au hash stocké.
        Import local pour éviter la boucle circulaire.
        """
        # Vérification conservée (utilise l'importation locale)
        from app.authentication import check_password 
        return check_password(password_str, self._password)

    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.full_name}', department='{self.department}')>"


# --- CLIENT ---
class Client(Base):
    # CORRECTION CRITIQUE: Pluriel
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    company_name = Column(String(100))
    creation_date = Column(TIMESTAMP, default=datetime.datetime.now)
    last_update = Column(TIMESTAMP, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    # CORRECTION CRITIQUE: Référence de FK au pluriel
    sales_contact_id = Column(Integer, ForeignKey('employees.id'), nullable=False)

    # Relationships
    sales_contact = relationship("Employee", back_populates="clients_assigned")
    contracts = relationship("Contract", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}', sales_id={self.sales_contact_id})>"

# --- CONTRAT ---
class Contract(Base):
    # CORRECTION CRITIQUE: Pluriel
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True)
    # CORRECTION CRITIQUE: Référence de FK au pluriel
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    # CORRECTION CRITIQUE: Référence de FK au pluriel
    sales_contact_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    remaining_amount = Column(Numeric(10, 2), nullable=False)
    creation_date = Column(TIMESTAMP, default=datetime.datetime.now)
    status_signed = Column(Boolean, default=False)

    # Relationships
    client = relationship("Client", back_populates="contracts")
    sales_contact = relationship("Employee", back_populates="contracts_assigned", foreign_keys=[sales_contact_id])
    events = relationship("Event", back_populates="contract")

    def __repr__(self):
        return f"<Contract(id={self.id}, client_id={self.client_id}, signed={self.status_signed})>"

# --- ÉVÉNEMENT ---
class Event(Base):
    # CORRECTION CRITIQUE: Pluriel
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    # CORRECTION CRITIQUE: Référence de FK au pluriel
    contract_id = Column(Integer, ForeignKey('contracts.id'), nullable=False)
    name = Column(String(100), nullable=False)
    attendees = Column(Integer)
    event_start = Column(TIMESTAMP, nullable=False)
    event_end = Column(TIMESTAMP, nullable=False)
    location = Column(String(100))
    notes = Column(Text)
    # CORRECTION CRITIQUE: Référence de FK au pluriel
    support_contact_id = Column(Integer, ForeignKey('employees.id'), nullable=True) # Peut être NULL

    # Relationships
    contract = relationship("Contract", back_populates="events")
    support_contact = relationship("Employee", back_populates="events_support")

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}', support_id={self.support_contact_id})>"


# --- Initialisation de la base de données ---
def initialize_roles(session: Session, engine_instance) -> None:
    """Crée la structure de la DB et s'assure que les rôles et l'Admin existent."""
    # 1. Création des tables (si elles n'existent pas)
    Base.metadata.create_all(engine_instance)

    # 2. Vérification et création des rôles
    roles_to_create = ['Gestion', 'Commercial', 'Support']
    roles_created = 0
    for role_name in roles_to_create:
        if not session.query(Role).filter_by(name=role_name).first():
            new_role = Role(name=role_name)
            session.add(new_role)
            roles_created += 1

    if roles_created > 0:
        console.print(f"[bold green]Roles created in database: {', '.join(roles_to_create)}.[/bold green]")
    else:
        console.print("[bold green]Roles verified in database.[/bold green]")

    # 3. Assurez-vous qu'un utilisateur administrateur existe
    try:
        session.commit() # S'assurer que les rôles sont là
        
        if not session.query(Employee).filter_by(email="admin@epicevents.com").first():
            gestion_role = session.query(Role).filter_by(name="Gestion").one()
            
            admin = Employee(
                full_name="Super Admin",
                email="admin@epicevents.com",
                phone="0000000000",
                role_id=gestion_role.id,
                password="admin" # La propriété .password utilise la fonction de hachage
            )
            session.add(admin)
            session.commit()
            console.print("[bold green]Default Admin User (admin@epicevents.com/admin) created.[/bold green]")
        else:
            session.rollback()
            
    except NoResultFound:
        session.rollback()
        console.print("[bold red]Admin user could not be created: 'Gestion' role not found.[/bold red]")
        pass 
    except IntegrityError:
        session.rollback()
        console.print("[bold red]Admin user could not be created: Integrity Error (user already exists or duplicate role).[/bold red]")
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]FATAL ERROR during initialization:[/bold red] {e}")