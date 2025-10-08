"""
Pytest tests for the employee_controller.py module.
These tests use mock objects to simulate the database session and Employee model.
"""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.controllers.employee_controller import create_employee, list_employees, update_employee, delete_employee
from app.models import Employee # Used for mock object structure

# --- Mock Fixtures ---

class MockEmployee:
    """A minimal mock class to simulate the SQLAlchemy Employee model object."""
    def __init__(self, id, full_name, email, department, phone=None, _password_hash='hashed_password'):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.department = department
        self.phone = phone
        self._password_hash = _password_hash

    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.full_name}')>"

@pytest.fixture
def mock_employee():
    """Returns a mock Employee object."""
    return MockEmployee(
        id=99,
        full_name='Test User',
        email='test.user@epicevents.com',
        department='Commercial',
        phone='0123456789'
    )

@pytest.fixture
def mock_gestion_employee():
    """Returns a mock Employee object belonging to Gestion department."""
    return MockEmployee(
        id=1,
        full_name='Admin User',
        email='admin.user@epicevents.com',
        department='Gestion'
    )

@pytest.fixture
def mock_session():
    """
    Returns a mock SQLAlchemy session.
    The query chain is mocked for filtering and fetching data.
    """
    session = MagicMock()
    session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    session.query.return_value.filter.return_value.first.return_value = None
    return session

# --- Utility Setup Functions ---

def setup_update_mocks(mock_session, mock_employee):
    """
    Configures the mock session to return a specific employee for an update/delete operation.
    It simulates session.query(Employee).filter_by(id=employee_id).one_or_none() finding the employee.
    """
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_employee
    return mock_employee


# --- Test Cases for CREATE ---

@patch('app.controllers.employee_controller.hash_password', return_value='new_hashed_password')
@patch('app.controllers.employee_controller.format_email', return_value='new.employee@epicevents.com') 
def test_create_employee_success(mock_format_email, mock_hash_password, mock_session):
    """Test successful employee creation."""
    employee = create_employee(mock_session, 'New Employee', '000', 'Commercial', 'pass')

    assert employee is not None
    assert employee.full_name == 'New Employee'
    assert employee.email == 'new.employee@epicevents.com'
    assert employee._password_hash == 'new_hashed_password'
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()

@patch('app.controllers.employee_controller.hash_password')
@patch('app.controllers.employee_controller.format_email', return_value='safe.email@epicevents.com')
def test_create_employee_integrity_error(mock_format_email, mock_hash_password, mock_session):
    """Test failure when DB raises IntegrityError (e.g., duplicate phone/email constraint failure)."""
    mock_session.commit.side_effect = IntegrityError("msg", "params", "orig")
    
    employee = create_employee(mock_session, 'Duplicate User', '111', 'Support', 'pass')

    assert employee is None
    mock_session.rollback.assert_called_once()


# --- Test Cases for LIST ---

def test_list_employees_success(mock_session, mock_employee):
    """Test successful listing of employees."""
    mock_session.query.return_value.all.return_value = [mock_employee]

    employees = list_employees(mock_session)

    assert len(employees) == 1
    assert employees[0].full_name == 'Test User'


# --- Test Cases for UPDATE ---

@patch('app.controllers.employee_controller.hash_password', return_value='new_hashed_pass')
def test_update_employee_success(mock_hash_password, mock_session, mock_employee):
    """Test successful update of multiple fields (phone, department, name, email)."""
    
    employee = setup_update_mocks(mock_session, mock_employee)
    
    mock_session.query.return_value.filter.return_value.first.return_value = None 
    
    updates = {
        'full_name': 'New Full Name',
        'email': 'new.email.manual@epicevents.com',
        'phone': '9876543210', 
        'department': 'Support', 
        'plain_password': 'new_pass'
    }

    updated_employee = update_employee(mock_session, 99, updates)

    assert updated_employee is not None
    assert updated_employee.full_name == 'New Full Name'
    assert updated_employee.email == 'new.email.manual@epicevents.com'
    assert updated_employee.phone == '9876543210'
    assert updated_employee.department == 'Support'
    assert updated_employee._password_hash == 'new_hashed_pass'
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()

def test_update_employee_regenerates_email_on_name_change(mock_session, mock_employee):
    """Test that email is automatically regenerated if name changes but email is not provided."""
    employee = setup_update_mocks(mock_session, mock_employee)
    
    updates = {
        'full_name': 'Regenerate Email User',
        'phone': '111222333'
    }

    with patch('app.controllers.employee_controller.format_email', return_value='regenerate.email@epicevents.com') as mock_format_email:
        updated_employee = update_employee(mock_session, 99, updates)

    assert updated_employee is not None
    assert updated_employee.full_name == 'Regenerate Email User'
    assert updated_employee.email == 'regenerate.email@epicevents.com'
    mock_format_email.assert_called_once()
    mock_session.commit.assert_called_once()

def test_update_employee_not_found(mock_session):
    """Test update failure when the employee ID does not exist."""
    
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    
    updates = {'phone': '123'}
    updated_employee = update_employee(mock_session, 99, updates)
    
    assert updated_employee is None
    mock_session.rollback.assert_not_called()

@patch('app.controllers.employee_controller.format_email', return_value='safe.email@epicevents.com') 
def test_update_employee_invalid_department(mock_format_email, mock_session, mock_employee):
    """Test update failure when an update causes an IntegrityError (e.g., invalid department in real DB)."""
    employee = setup_update_mocks(mock_session, mock_employee)
    
    updates = {'department': 'Invalid Department', 'full_name': 'New Name'}
    
    mock_session.commit.side_effect = IntegrityError("msg", "params", "orig")
    
    updated_employee = update_employee(mock_session, 99, updates)
    
    assert updated_employee is None
    mock_session.rollback.assert_called_once()


def test_update_employee_duplicate_email(mock_session, mock_employee):
    """Test update failure when the new email already belongs to another employee."""
    employee = setup_update_mocks(mock_session, mock_employee)
    
    updates = {'email': 'existing.user@epicevents.com'}

    mock_session.query.return_value.filter.return_value.first.return_value = MockEmployee(
        id=100, full_name='Existing User', email='existing.user@epicevents.com', department='Commercial'
    )
    
    updated_employee = update_employee(mock_session, 99, updates)
    
    assert updated_employee is None
    mock_session.rollback.assert_called_once()


# --- Test Cases for DELETE ---

def test_delete_employee_success(mock_session, mock_employee):
    """Test successful employee deletion (non-Gestion employee)."""
    setup_update_mocks(mock_session, mock_employee)
    
    result = delete_employee(mock_session, 99)
    
    assert result is True
    mock_session.delete.assert_called_once_with(mock_employee)
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()

def test_delete_employee_not_found(mock_session):
    """Test deletion failure when the employee ID does not exist."""
    
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    
    result = delete_employee(mock_session, 999)
    
    assert result is False
    mock_session.delete.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()

def test_delete_employee_last_gestion(mock_session, mock_gestion_employee):
    """Test deletion failure when trying to delete the last 'Gestion' employee."""
    setup_update_mocks(mock_session, mock_gestion_employee)
    
    mock_session.query.return_value.filter_by.return_value.count.return_value = 1 
    
    result = delete_employee(mock_session, 1)
    
    assert result is False
    mock_session.delete.assert_not_called()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_called_once()

def test_delete_employee_multiple_gestion(mock_session, mock_gestion_employee):
    """Test successful deletion when there are multiple 'Gestion' employees."""
    setup_update_mocks(mock_session, mock_gestion_employee)
    
    mock_session.query.return_value.filter_by.return_value.count.return_value = 2
    
    result = delete_employee(mock_session, 1)
    
    assert result is True
    mock_session.delete.assert_called_once_with(mock_gestion_employee)
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()
