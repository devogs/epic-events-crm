# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Employee, Role, Client, Contract, Event  # Added Event
from app.authentication import hash_password

@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="module")
def test_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture(scope="function")
def clean_session(test_session):
    test_session.query(Employee).delete()
    test_session.query(Client).delete()
    test_session.query(Contract).delete()
    test_session.query(Event).delete()  # Added Event table cleanup
    test_session.commit()
    yield test_session
    test_session.rollback()

@pytest.fixture(scope="module")
def create_roles(test_session):
    roles_to_create = ['Gestion', 'Commercial', 'Support']
    for role_name in roles_to_create:
        if not test_session.query(Role).filter_by(name=role_name).first():
            new_role = Role(name=role_name)
            test_session.add(new_role)
    test_session.commit()
    roles = {role.name: role for role in test_session.query(Role).all()}
    yield roles
    test_session.query(Role).delete()
    test_session.commit()

@pytest.fixture
def admin_employee(clean_session, create_roles):
    admin = Employee(
        full_name='Admin User',
        email='admin@epicevents.com',
        phone='1234567890',
        role_id=create_roles['Gestion'].id,
        _password=hash_password('adminpass')
    )
    clean_session.add(admin)
    clean_session.commit()
    yield admin
    clean_session.query(Employee).filter_by(id=admin.id).delete()
    clean_session.commit()

@pytest.fixture
def sales_employee(clean_session, create_roles):
    sales = Employee(
        full_name='Sales User',
        email='sales@epicevents.com',
        phone='9876543210',
        role_id=create_roles['Commercial'].id,
        _password=hash_password('salespass')
    )
    clean_session.add(sales)
    clean_session.commit()
    yield sales
    clean_session.query(Employee).filter_by(id=sales.id).delete()
    clean_session.commit()

@pytest.fixture
def support_employee(clean_session, create_roles):
    support = Employee(
        full_name='Support User',
        email='support@epicevents.com',
        phone='5555555555',
        role_id=create_roles['Support'].id,
        _password=hash_password('supportpass')
    )
    clean_session.add(support)
    clean_session.commit()
    yield support
    clean_session.query(Employee).filter_by(id=support.id).delete()
    clean_session.commit()