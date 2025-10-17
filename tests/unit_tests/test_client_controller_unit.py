# tests/test_client_controller_unit.py
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.controllers.client_controller import create_client, list_clients, update_client
from app.models import Client, Employee, Role

@pytest.fixture
def mock_session():
    return Mock(spec=Session)

@pytest.fixture
def mock_employee():
    return Mock(spec=Employee, id=1, department='Commercial')

@pytest.fixture
def mock_client():
    return Mock(spec=Client, id=1, full_name='John Doe', email='john@e.com', phone='1234567890', 
                company_name='Company', sales_contact_id=1)

def test_create_client_commercial_success(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_email', return_value=True):
            with patch('app.controllers.client_controller.is_valid_phone', return_value=True):
                mock_session.commit.return_value = None
                client = create_client(mock_session, mock_employee, 'John Doe', 'john@e.com', '1234567890', 'Company')
                assert client is not None
                assert client.full_name == 'John Doe'
                assert client.email == 'john@e.com'
                assert client.phone == '1234567890'
                assert client.company_name == 'Company'
                assert client.sales_contact_id == mock_employee.id

def test_create_client_permission_denied(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=False):
        with pytest.raises(PermissionError, match="Permission denied to create a client."):
            create_client(mock_session, mock_employee, 'John Doe', 'john@e.com', '1234567890', 'Company')

def test_create_client_missing_fields(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        result = create_client(mock_session, mock_employee, '', 'john@e.com', '1234567890', 'Company')
        assert result is None
        result = create_client(mock_session, mock_employee, 'John Doe', '', '1234567890', 'Company')
        assert result is None
        result = create_client(mock_session, mock_employee, 'John Doe', 'john@e.com', '', 'Company')
        assert result is None

def test_create_client_invalid_email(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_email', return_value=False):
            result = create_client(mock_session, mock_employee, 'John Doe', 'invalid_email', '1234567890', 'Company')
            assert result is None

def test_create_client_invalid_phone(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_email', return_value=True):
            with patch('app.controllers.client_controller.is_valid_phone', return_value=False):
                result = create_client(mock_session, mock_employee, 'John Doe', 'john@e.com', 'invalid_phone', 'Company')
                assert result is None

def test_create_client_integrity_error(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_email', return_value=True):
            with patch('app.controllers.client_controller.is_valid_phone', return_value=True):
                mock_session.commit.side_effect = IntegrityError("mock error", {}, None)
                result = create_client(mock_session, mock_employee, 'John Doe', 'john@e.com', '1234567890', 'Company')
                assert result is None
                assert mock_session.rollback.called

def test_create_client_unexpected_error(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_email', return_value=True):
            with patch('app.controllers.client_controller.is_valid_phone', return_value=True):
                mock_session.commit.side_effect = Exception("unexpected error")
                result = create_client(mock_session, mock_employee, 'John Doe', 'john@e.com', '1234567890', 'Company')
                assert result is None
                assert mock_session.rollback.called

def test_list_clients_commercial_with_filter(mock_session, mock_employee):
    mock_client = Mock(spec=Client, id=1, sales_contact_id=1)
    mock_session.query.return_value.filter.return_value.all.return_value = [mock_client]
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        clients = list_clients(mock_session, mock_employee, filter_by_sales_id=1)
        assert len(clients) == 1
        assert clients[0] == mock_client

def test_list_clients_gestion_with_filter(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Gestion')
    mock_client = Mock(spec=Client, id=1, sales_contact_id=2)
    mock_session.query.return_value.filter.return_value.all.return_value = [mock_client]
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        clients = list_clients(mock_session, mock_employee, filter_by_sales_id=2)
        assert len(clients) == 1
        assert clients[0] == mock_client

def test_list_clients_support_with_filter(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_client = Mock(spec=Client, id=1, sales_contact_id=2)
    mock_session.query.return_value.filter.return_value.all.return_value = [mock_client]
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        clients = list_clients(mock_session, mock_employee, filter_by_sales_id=2)
        assert len(clients) == 1
        assert clients[0] == mock_client

def test_list_clients_permission_denied(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=False):
        with pytest.raises(PermissionError, match="Permission denied to view clients."):
            list_clients(mock_session, mock_employee)

def test_update_client_gestion_success(mock_session, mock_employee):
    mock_employee.department = 'Gestion'
    mock_client = Mock(spec=Client, id=1, sales_contact_id=2)
    mock_sales_contact = Mock(spec=Employee, id=3, role=Mock(name='Commercial'))
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_client)))),
        Mock(filter=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_sales_contact))))
    ]
    mock_session.commit.return_value = None
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_email', return_value=True):
            with patch('app.controllers.client_controller.is_valid_phone', return_value=True):
                updated = update_client(mock_session, mock_employee, 1, 
                                       full_name='Jane Doe', email='jane@e.com', 
                                       phone='0987654321', company_name='NewCo', 
                                       sales_contact_id=3)
                assert updated is not None
                assert updated.full_name == 'Jane Doe'
                assert updated.email == 'jane@e.com'
                assert updated.phone == '0987654321'
                assert updated.company_name == 'NewCo'
                assert updated.sales_contact_id == 3

def test_update_client_commercial_success(mock_session, mock_employee, mock_client):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_email', return_value=True):
            with patch('app.controllers.client_controller.is_valid_phone', return_value=True):
                updated = update_client(mock_session, mock_employee, 1, 
                                       full_name='Jane Doe', email='jane@e.com', 
                                       phone='0987654321', company_name='NewCo')
                assert updated is not None
                assert updated.full_name == 'Jane Doe'
                assert updated.email == 'jane@e.com'
                assert updated.phone == '0987654321'
                assert updated.company_name == 'NewCo'

def test_update_client_commercial_unassigned(mock_session, mock_employee):
    mock_client = Mock(spec=Client, id=1, sales_contact_id=2)
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        result = update_client(mock_session, mock_employee, 1, full_name='Jane Doe')
        assert result is None

def test_update_client_permission_denied(mock_session, mock_employee):
    with patch('app.controllers.client_controller.check_permission', return_value=False):
        with pytest.raises(PermissionError, match="Permission denied to update clients."):
            update_client(mock_session, mock_employee, 1, full_name='Jane Doe')

def test_update_client_not_found(mock_session, mock_employee):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        result = update_client(mock_session, mock_employee, 1, full_name='Jane Doe')
        assert result is None

def test_update_client_invalid_email(mock_session, mock_employee, mock_client):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_email', return_value=False):
            result = update_client(mock_session, mock_employee, 1, email='invalid_email')
            assert result is None

def test_update_client_invalid_phone(mock_session, mock_employee, mock_client):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        with patch('app.controllers.client_controller.is_valid_phone', return_value=False):
            result = update_client(mock_session, mock_employee, 1, phone='invalid_phone')
            assert result is None

def test_update_client_commercial_sales_contact_denied(mock_session, mock_employee, mock_client):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        result = update_client(mock_session, mock_employee, 1, sales_contact_id=2)
        assert result is None

def test_update_client_invalid_sales_contact(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Gestion')
    mock_client = Mock(spec=Client, id=1, sales_contact_id=1)
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_client)))),
        Mock(filter=Mock(return_value=Mock(one_or_none=Mock(return_value=None))))
    ]
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        result = update_client(mock_session, mock_employee, 1, sales_contact_id=2)
        assert result is None

def test_update_client_no_updates(mock_session, mock_employee, mock_client):
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
    with patch('app.controllers.client_controller.check_permission', return_value=True):
        updated = update_client(mock_session, mock_employee, 1)
        assert updated is mock_client
        assert not mock_session.commit.called