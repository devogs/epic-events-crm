"""
This module defines the database models for the Epic Events CRM application.
It uses SQLAlchemy to map Python classes to database tables.
"""
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
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from .authentication import hash_password, check_password

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


# --- Define the classes (models) ---

class Role(Base):
    """MODÈLE DE RÔLE : Model for the 'roles' table."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False) 
    
    employees = relationship("Employee", back_populates="role")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class Employee(Base):
    """MODIFIÉ : Model for the 'employees' table."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False) 
    
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), unique=False, nullable=False)
    _password_hash = Column("password", String(100), nullable=False)

    role = relationship("Role", back_populates="employees") 

    contracts = relationship("Contract", foreign_keys='Contract.sales_contact_id', back_populates="sales_contact")
    events_supported = relationship("Event", foreign_keys='Event.support_contact_id', back_populates="support_contact")
    
    @property
    def password(self):
        """ Getter for the password property. """
        raise AttributeError('Password is not a readable attribute.')

    @password.setter
    def password(self, plain_password):
        """ Setter to hash the password before storing. """
        self._password_hash = hash_password(plain_password)
        
    @property
    def department(self):
        """ Allows accessing the role name via 'employee.department' for backward compatibility. """
        return self.role.name if self.role else None

    def __repr__(self):
        return f"<Employee(id={self.id}, full_name='{self.full_name}', role='{self.role.name if self.role else 'N/A'}')>"


class Client(Base):
    """Model for the 'clients' table."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    company_name = Column(String(100), nullable=False)
    creation_date = Column(Date, default=datetime.date.today, nullable=False)
    last_contact = Column(Date, default=datetime.date.today, nullable=False)
    sales_contact_id = Column(Integer, ForeignKey("employees.id"))

    sales_contact = relationship("Employee", foreign_keys=[sales_contact_id])
    contracts = relationship("Contract", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, full_name='{self.full_name}', company='{self.company_name}')>"


class Contract(Base):
    """Model for the 'contracts' table."""

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    sales_contact_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    total_amount = Column(Numeric(10, 2))
    amount_remaining = Column(Numeric(10, 2))
    creation_date = Column(Date, default=datetime.date.today, nullable=False)
    status_signed = Column(Boolean, nullable=False, default=False)

    client = relationship("Client", back_populates="contracts")
    sales_contact = relationship("Employee", foreign_keys=[sales_contact_id], back_populates="contracts")
    events = relationship("Event", back_populates="contract")

    def __repr__(self):
        return f"<Contract(id={self.id}, total_amount={self.total_amount})>"


class Event(Base):
    """Model for the 'events' table."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    name = Column(String(255))
    support_contact_id = Column(Integer, ForeignKey("employees.id"))
    start_date = Column(TIMESTAMP, nullable=False)
    end_date = Column(TIMESTAMP, nullable=False)
    location = Column(String(255))
    attendees = Column(Integer)
    notes = Column(Text)

    contract = relationship("Contract", back_populates="events")
    support_contact = relationship("Employee", foreign_keys=[support_contact_id], back_populates="events_supported")

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}', location='{self.location}')>"
