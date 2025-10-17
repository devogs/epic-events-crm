# tests/test_contract_controller_unit.py
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.controllers.contract_controller import create_contract, list_contracts, update_contract
from app.models import Client, Contract, Employee

@pytest.fixture
def mock_session():
    return Mock(spec=Session)

@pytest.fixture
def mock_employee():
    return Mock(spec=Employee, id=1, department='Gestion', full_name='Admin User')

@pytest.fixture
def mock_client():
    return Mock(spec=Client, id=1, sales_contact_id=1, full_name='Client')

@pytest.fixture
def mock_contract():
    return Mock(spec=Contract, id=1, client_id=1, sales_contact_id=1, total_amount=Decimal('1000'), 
                remaining_amount=Decimal('500'), status_signed=False, client=Mock(full_name='Client'))

def test_create_contract_gestion_success(mock_session, mock_employee, mock_client):
    with patch('app.controllers.contract_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
        mock_session.commit.return_value = None
        contract = create_contract(mock_session, mock_employee, 1, Decimal('1000'), Decimal('500'), True)
        assert contract is not None
        assert contract.client_id == 1
        assert contract.total_amount == Decimal('1000')
        assert contract.remaining_amount == Decimal('500')
        assert contract.status_signed is True

def test_create_contract_permission_denied(mock_session, mock_employee):
    with patch('app.controllers.contract_controller.check_permission', return_value=False):
        with pytest.raises(PermissionError, match="Permission denied. Only 'Gestion' can create contracts."):
            create_contract(mock_session, mock_employee, 1, Decimal('1000'), Decimal('500'), True)

def test_create_contract_invalid_amounts(mock_session, mock_employee, mock_client):
    with patch('app.controllers.contract_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
        result = create_contract(mock_session, mock_employee, 1, Decimal('0'), Decimal('500'), True)
        assert result is None
        result = create_contract(mock_session, mock_employee, 1, Decimal('1000'), Decimal('-1'), True)
        assert result is None
        result = create_contract(mock_session, mock_employee, 1, Decimal('1000'), Decimal('1500'), True)
        assert result is None

def test_create_contract_client_not_found(mock_session, mock_employee):
    with patch('app.controllers.contract_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
        result = create_contract(mock_session, mock_employee, 1, Decimal('1000'), Decimal('500'), True)
        assert result is None

def test_create_contract_no_sales_contact(mock_session, mock_employee):
    with patch('app.controllers.contract_controller.check_permission', return_value=True):
        mock_client = Mock(spec=Client, id=1, sales_contact_id=None)
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
        result = create_contract(mock_session, mock_employee, 1, Decimal('1000'), Decimal('500'), True)
        assert result is None

def test_create_contract_integrity_error(mock_session, mock_employee, mock_client):
    with patch('app.controllers.contract_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_client
        mock_session.commit.side_effect = IntegrityError("mock error", {}, None)
        result = create_contract(mock_session, mock_employee, 1, Decimal('1000'), Decimal('500'), True)
        assert result is None
        assert mock_session.rollback.called

def test_list_contracts_gestion(mock_session, mock_employee):
    mock_contract = Mock(spec=Contract, id=1, client_id=1, total_amount=Decimal('1000'), status_signed=True)
    mock_session.query.return_value.options.return_value.all.return_value = [mock_contract]
    contracts = list_contracts(mock_session, mock_employee)
    assert len(contracts) == 1
    assert contracts[0] == mock_contract

def test_list_contracts_commercial(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Commercial')
    mock_contract = Mock(spec=Contract, id=1, client_id=1, sales_contact_id=1, status_signed=True)
    mock_session.query.return_value.options.return_value.join.return_value.filter.return_value.all.return_value = [mock_contract]
    contracts = list_contracts(mock_session, mock_employee)
    assert len(contracts) == 1
    assert contracts[0] == mock_contract

def test_list_contracts_filter_signed(mock_session, mock_employee):
    mock_contract = Mock(spec=Contract, id=1, client_id=1, status_signed=False)
    mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_contract]
    contracts = list_contracts(mock_session, mock_employee, filter_signed=False)
    assert len(contracts) == 1
    assert contracts[0] == mock_contract

def test_update_contract_gestion_all_fields(mock_session, mock_employee, mock_contract):
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    mock_session.query.return_value.filter_by.return_value.one_or_none.side_effect = [Mock(id=2), Mock(id=2, department='Commercial')]
    mock_session.commit.return_value = None
    updated = update_contract(mock_session, mock_employee, 1, 
                             total_amount=Decimal('2000'), 
                             remaining_amount=Decimal('1000'), 
                             status_signed=True, 
                             client_id=2, 
                             sales_contact_id=2)
    assert updated is not None
    assert updated.total_amount == Decimal('2000')
    assert updated.remaining_amount == Decimal('1000')
    assert updated.status_signed is True
    assert updated.client_id == 2
    assert updated.sales_contact_id == 2

def test_update_contract_commercial_status_signed(mock_session, mock_contract):
    mock_employee = Mock(spec=Employee, id=1, department='Commercial')
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    updated = update_contract(mock_session, mock_employee, 1, status_signed=True)
    assert updated is not None
    assert updated.status_signed is True

def test_update_contract_commercial_wrong_field(mock_session, mock_contract):
    mock_employee = Mock(spec=Employee, id=1, department='Commercial')
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    result = update_contract(mock_session, mock_employee, 1, total_amount=Decimal('2000'))
    assert result is None

def test_update_contract_commercial_wrong_sales_contact(mock_session, mock_contract):
    mock_employee = Mock(spec=Employee, id=2, department='Commercial')
    mock_contract.sales_contact_id = 1
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    result = update_contract(mock_session, mock_employee, 1, status_signed=True)
    assert result is None

def test_update_contract_support_denied(mock_session, mock_contract):
    mock_employee = Mock(spec=Employee, id=2, department='Support')
    mock_contract.sales_contact_id = 1  # Ensure sales_contact_id differs
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    result = update_contract(mock_session, mock_employee, 1, status_signed=True)
    assert result is None

def test_update_contract_invalid_total_amount(mock_session, mock_employee, mock_contract):
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    result = update_contract(mock_session, mock_employee, 1, total_amount=Decimal('0'))
    assert result is None

def test_update_contract_invalid_remaining_amount(mock_session, mock_employee, mock_contract):
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    result = update_contract(mock_session, mock_employee, 1, remaining_amount=Decimal('1500'))
    assert result is None

def test_update_contract_commercial_increase_remaining(mock_session, mock_contract):
    mock_employee = Mock(spec=Employee, id=1, department='Commercial')
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    result = update_contract(mock_session, mock_employee, 1, remaining_amount=Decimal('600'))
    assert result is None

def test_update_contract_invalid_client_id(mock_session, mock_employee, mock_contract):
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    result = update_contract(mock_session, mock_employee, 1, client_id=2)
    assert result is None

def test_update_contract_invalid_sales_contact_id(mock_session, mock_employee, mock_contract):
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    result = update_contract(mock_session, mock_employee, 1, sales_contact_id=2)
    assert result is None

def test_update_contract_no_updates(mock_session, mock_employee, mock_contract):
    mock_session.query.return_value.options.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
    updated = update_contract(mock_session, mock_employee, 1)
    assert updated is mock_contract
    assert not mock_session.commit.called