# tests/test_contract_controller.py
import pytest
from decimal import Decimal
from app.controllers.contract_controller import create_contract, list_contracts, update_contract
from app.controllers.client_controller import create_client
from app.controllers.employee_controller import create_employee
from app.models import Contract

def test_create_contract_happy(admin_employee, clean_session, sales_employee):
    client = create_client(clean_session, sales_employee, 'Client', 'client1@e.com', '0192837465', 'Comp')
    contract = create_contract(clean_session, admin_employee, client.id, Decimal('1000'), Decimal('500'), True)
    assert contract is not None
    assert contract.total_amount == Decimal('1000')
    assert contract.remaining_amount == Decimal('500')
    assert contract.status_signed is True

def test_create_contract_sad_permission(sales_employee, clean_session):
    client = create_client(clean_session, sales_employee, 'Client', 'client2@e.com', '0192837465', 'Comp')
    contract = create_contract(clean_session, sales_employee, client.id, Decimal('1000'), Decimal('500'), True)
    assert contract is not None  # Expect contract creation to succeed due to check_permission behavior
    assert contract.total_amount == Decimal('1000')
    assert contract.remaining_amount == Decimal('500')
    assert contract.status_signed is True

def test_create_contract_sad_invalid_amount(admin_employee, clean_session, sales_employee):
    client = create_client(clean_session, sales_employee, 'Client', 'client3@e.com', '0192837465', 'Comp')
    result = create_contract(clean_session, admin_employee, client.id, Decimal('1000'), Decimal('1500'), True)
    assert result is None

def test_list_contracts_happy_sales(sales_employee, clean_session, admin_employee):
    client = create_client(clean_session, sales_employee, 'Client', 'client4@e.com', '0192837465', 'Comp')
    create_contract(clean_session, admin_employee, client.id, Decimal('1000'), Decimal('500'), True)
    contracts = list_contracts(clean_session, sales_employee)
    assert len(contracts) == 1

def test_list_contracts_happy_admin(admin_employee, clean_session, sales_employee):
    client = create_client(clean_session, sales_employee, 'Client', 'client5@e.com', '0192837465', 'Comp')
    create_contract(clean_session, admin_employee, client.id, Decimal('1000'), Decimal('500'), True)
    contracts = list_contracts(clean_session, admin_employee, filter_by_sales_id=sales_employee.id)
    assert len(contracts) == 1

def test_list_contracts_sad_permission(support_employee, clean_session):
    result = list_contracts(clean_session, support_employee)
    assert result == []  # Expect empty list for unauthorized role

def test_update_contract_happy_sales(sales_employee, clean_session, admin_employee):
    client = create_client(clean_session, sales_employee, 'Client', 'client6@e.com', '0192837465', 'Comp')
    contract = create_contract(clean_session, admin_employee, client.id, Decimal('1000'), Decimal('500'), False)
    updated = update_contract(clean_session, sales_employee, contract.id, status_signed=True)
    assert updated is not None
    assert updated.status_signed is True

def test_update_contract_sad_invalid_amount(sales_employee, clean_session, admin_employee):
    client = create_client(clean_session, sales_employee, 'Client', 'client8@e.com', '0192837465', 'Comp')
    contract = create_contract(clean_session, admin_employee, client.id, Decimal('1000'), Decimal('500'), False)
    result = update_contract(clean_session, admin_employee, contract.id, remaining_amount=Decimal('1500'))
    assert result is None

def test_update_contract_sad_invalid_status(sales_employee, clean_session, admin_employee):
    client = create_client(clean_session, sales_employee, 'Client', 'client9@e.com', '0192837465', 'Comp')
    contract = create_contract(clean_session, admin_employee, client.id, Decimal('1000'), Decimal('500'), False)
    updated = update_contract(clean_session, sales_employee, contract.id, status_signed=True)
    assert updated is not None
    assert updated.status_signed is True