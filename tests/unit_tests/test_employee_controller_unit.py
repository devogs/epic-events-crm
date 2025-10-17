# tests/test_employee_controller_unit.py
import pytest
import re
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.controllers.employee_controller import create_employee, list_employees, update_employee, delete_employee, format_email, get_role_id_by_name
from app.models import Employee, Role

@pytest.fixture
def mock_session():
    return Mock(spec=Session)

@pytest.fixture
def mock_employee():
    return Mock(spec=Employee, id=1, department='Gestion', full_name='Admin User', role_id=1)

@pytest.fixture
def mock_role():
    return Mock(spec=Role, id=1, name='Gestion')

def test_get_role_id_by_name_success(mock_session, mock_role):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_role
    role_id = get_role_id_by_name(mock_session, 'Gestion')
    assert role_id == 1

def test_get_role_id_by_name_not_found(mock_session):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    role_id = get_role_id_by_name(mock_session, 'Invalid')
    assert role_id is None

def test_format_email_unique(mock_session):
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    email = format_email('John Doe', mock_session)
    assert email == 'john.doe@epicevents.com'

def test_format_email_with_counter(mock_session):
    mock_session.query.return_value.filter_by.return_value.first.side_effect = [Mock(), None]
    email = format_email('John Doe', mock_session)
    assert email == 'john.doe1@epicevents.com'

def test_format_email_single_name(mock_session):
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    email = format_email('John', mock_session)
    assert email == 'john@epicevents.com'

def test_format_email_no_name(mock_session):
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    email = format_email('', mock_session)
    assert email == 'unknown@epicevents.com'

def test_create_employee_gestion_success(mock_session, mock_employee, mock_role):
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(first=Mock(return_value=None)))),  # Email check
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_role))))  # Role check
    ]
    mock_session.commit.return_value = None
    employee = create_employee(mock_session, mock_employee, 'John Doe', '', '1234567890', 'Gestion', 'password')
    assert employee is not None
    assert employee.full_name == 'John Doe'
    assert employee.email == 'john.doe@epicevents.com'
    assert employee.phone == '1234567890'
    assert employee.role_id == 1

def test_create_employee_non_gestion_denied(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Commercial')
    employee = create_employee(mock_session, mock_employee, 'John Doe', 'john@e.com', '1234567890', 'Gestion', 'password')
    assert employee is None

def test_create_employee_missing_fields(mock_session, mock_employee):
    employee = create_employee(mock_session, mock_employee, '', 'john@e.com', '1234567890', 'Gestion', 'password')
    assert employee is None

def test_create_employee_invalid_email(mock_session, mock_employee):
    employee = create_employee(mock_session, mock_employee, 'John Doe', 'invalid_email', '1234567890', 'Gestion', 'password')
    assert employee is None

def test_create_employee_integrity_error(mock_session, mock_employee, mock_role):
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(first=Mock(return_value=None)))),  # Email check
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_role))))  # Role check
    ]
    mock_session.commit.side_effect = IntegrityError("mock error", {}, None)
    with patch('app.controllers.employee_controller.sentry_sdk.capture_exception') as mock_sentry:
        employee = create_employee(mock_session, mock_employee, 'John Doe', 'john@e.com', '1234567890', 'Gestion', 'password')
        assert employee is None
        assert mock_session.rollback.called
        assert mock_sentry.called

def test_create_employee_unexpected_error(mock_session, mock_employee, mock_role):
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(first=Mock(return_value=None)))),  # Email check
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_role))))  # Role check
    ]
    mock_session.commit.side_effect = Exception("unexpected error")
    with patch('app.controllers.employee_controller.sentry_sdk.capture_exception') as mock_sentry:
        employee = create_employee(mock_session, mock_employee, 'John Doe', 'john@e.com', '1234567890', 'Gestion', 'password')
        assert employee is None
        assert mock_session.rollback.called
        assert mock_sentry.called

def test_list_employees(mock_session):
    mock_employee = Mock(spec=Employee, id=1, full_name='John Doe')
    mock_session.query.return_value.all.return_value = [mock_employee]
    employees = list_employees(mock_session)
    assert len(employees) == 1
    assert employees[0] == mock_employee

def test_update_employee_gestion_success(mock_session, mock_employee, mock_role):
    with patch('app.controllers.employee_controller.check_permission', return_value=True):
        mock_session.query.side_effect = [
            Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_employee)))),
            Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_role))))
        ]
        mock_session.commit.return_value = None
        with patch('app.controllers.employee_controller.sentry_sdk') as mock_sentry:
            updated = update_employee(mock_session, mock_employee, 1, full_name='Jane Doe', email='jane@e.com', phone='0987654321', department='Commercial', password='newpass')
            assert updated is not None
            assert updated.full_name == 'Jane Doe'
            assert updated.email == 'jane@e.com'
            assert updated.phone == '0987654321'
            assert updated.role_id == 1
            assert mock_sentry.capture_message.called

def test_update_employee_permission_denied(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Commercial')
    with patch('app.controllers.employee_controller.check_permission', return_value=False):
        result = update_employee(mock_session, mock_employee, 1, full_name='Jane Doe')
        assert result is None

def test_update_employee_not_found(mock_session, mock_employee):
    with patch('app.controllers.employee_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
        result = update_employee(mock_session, mock_employee, 1, full_name='Jane Doe')
        assert result is None

def test_update_employee_invalid_email(mock_session, mock_employee):
    with patch('app.controllers.employee_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_employee
        with patch('app.controllers.employee_controller.sentry_sdk.capture_exception') as mock_sentry:
            result = update_employee(mock_session, mock_employee, 1, email='invalid_email')
            assert result is None
            assert mock_sentry.called

def test_update_employee_invalid_department(mock_session, mock_employee):
    with patch('app.controllers.employee_controller.check_permission', return_value=True):
        mock_session.query.side_effect = [
            Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_employee)))),
            Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=None))))
        ]
        with patch('app.controllers.employee_controller.sentry_sdk.capture_exception') as mock_sentry:
            result = update_employee(mock_session, mock_employee, 1, department='Invalid')
            assert result is None
            assert mock_sentry.called

def test_update_employee_integrity_error(mock_session, mock_employee, mock_role):
    with patch('app.controllers.employee_controller.check_permission', return_value=True):
        mock_session.query.side_effect = [
            Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_employee)))),
            Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_role))))
        ]
        mock_session.commit.side_effect = IntegrityError("mock error", {}, None)
        with patch('app.controllers.employee_controller.sentry_sdk.capture_exception') as mock_sentry:
            result = update_employee(mock_session, mock_employee, 1, email='jane@e.com')
            assert result is None
            assert mock_session.rollback.called
            assert mock_sentry.called

def test_update_employee_no_updates(mock_session, mock_employee):
    with patch('app.controllers.employee_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_employee
        updated = update_employee(mock_session, mock_employee, 1)
        assert updated is mock_employee
        assert not mock_session.commit.called

def test_delete_employee_success(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Commercial')
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_employee)))),
        Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(count=Mock(return_value=2))))))
    ]
    mock_session.commit.return_value = None
    result = delete_employee(mock_session, 1)
    assert result is True
    assert mock_session.delete.called
    assert mock_session.commit.called

def test_delete_employee_not_found(mock_session):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    result = delete_employee(mock_session, 1)
    assert result is False

def test_delete_employee_last_gestion(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Gestion')
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_employee)))),
        Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(count=Mock(return_value=1))))))
    ]
    result = delete_employee(mock_session, 1)
    assert result is False

def test_delete_employee_sqlalchemy_error(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Commercial')
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_employee)))),
        Mock(join=Mock(return_value=Mock(filter=Mock(return_value=Mock(count=Mock(return_value=2))))))
    ]
    mock_session.commit.side_effect = SQLAlchemyError("mock error")
    with patch('app.controllers.employee_controller.sentry_sdk.capture_exception') as mock_sentry:
        result = delete_employee(mock_session, 1)
        assert result is False
        assert mock_session.rollback.called
        assert mock_sentry.called