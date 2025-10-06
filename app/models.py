"""
This module defines the database models for the Epic Events CRM application.
It uses SQLAlchemy to map Python classes to database tables.
"""
import os
import datetime
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


class Employee(Base):
    """Model for the 'employees' table."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(255))
    _password_hash = Column('password', String(255), nullable=False)
    department = Column(String(255), nullable=False)

    @property
    def password(self):
        """ Getter for the password property. """
        raise AttributeError('Password is not a readable attribute.')

    @password.setter
    def password(self, plain_password):
        """ Setter for the password property to hash the password. """
        self._password_hash = hash_password(plain_password)

    clients = relationship("Client", back_populates="sales_contact")
    contracts = relationship("Contract", back_populates="sales_contact")
    events_support = relationship("Event", back_populates="support_contact")

    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.full_name}')>"


class Client(Base):
    """Model for the 'clients' table."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(255))
    company_name = Column(String(255))
    creation_date = Column(Date, default=datetime.date.today, nullable=False)
    last_updated = Column(
        Date,
        default=datetime.date.today,
        onupdate=datetime.date.today,
        nullable=False,
    )
    sales_contact_id = Column(Integer, ForeignKey("employees.id"))

    sales_contact = relationship("Employee", back_populates="clients")
    contracts = relationship("Contract", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}')>"


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
    sales_contact = relationship("Employee", back_populates="contracts")
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
    support_contact = relationship("Employee", back_populates="events_support")

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}')>"


# Base.metadata.create_all(engine)
