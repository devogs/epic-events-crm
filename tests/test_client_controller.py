# tests/test_client_controller.py
import pytest
from app.controllers.client_controller import create_client, list_clients, update_client
from app.controllers.employee_controller import create_employee
from app.models import Client

def test_create_client_happy_sales(sales_employee, clean_session):
    client = create_client(clean_session, sales_employee, 'Client One', 'client1@e.com', '0192837465', 'Company')
    assert client is not None
    assert client.full_name == 'Client One'

def test_create_client_happy_admin(admin_employee, clean_session, sales_employee):
    client = create_client(clean_session, admin_employee, 'Client Two', 'client2@e.com', '0192837465', 'Company')
    assert client is not None
    assert client.sales_contact_id == admin_employee.id

def test_create_client_sad_permission(support_employee, clean_session):
    with pytest.raises(PermissionError):
        create_client(clean_session, support_employee, 'Client', 'client3@e.com', '0192837465', 'Comp')

def test_create_client_sad_invalid_data(sales_employee, clean_session):
    result = create_client(clean_session, sales_employee, '', 'client4@e.com', '0192837465', 'Comp')
    assert result is None

def test_create_client_sad_invalid_email(admin_employee, clean_session):
    result = create_client(clean_session, admin_employee, 'Client', 'invalid', '0192837465', 'Comp')
    assert result is None

def test_list_clients_happy_sales(sales_employee, clean_session):
    create_client(clean_session, sales_employee, 'Client', 'client5@e.com', '0192837465', 'Comp')
    clients = list_clients(clean_session, sales_employee)
    assert len(clients) == 1

def test_list_clients_happy_admin(admin_employee, clean_session, sales_employee):
    create_client(clean_session, sales_employee, 'Client', 'client6@e.com', '0192837465', 'Comp')
    clients = list_clients(clean_session, admin_employee, filter_by_sales_id=sales_employee.id)
    assert len(clients) == 1

def test_list_clients_sad_permission(support_employee, clean_session):
    result = list_clients(clean_session, support_employee)
    assert result == []  # Expect empty list for unauthorized access

def test_update_client_happy_sales(sales_employee, clean_session):
    client = create_client(clean_session, sales_employee, 'Client', 'client7@e.com', '0192837465', 'Comp')
    updated = update_client(clean_session, sales_employee, client.id, full_name='Updated Client')
    assert updated.full_name == 'Updated Client'

def test_update_client_sad_wrong_sales(sales_employee, clean_session, admin_employee):
    sales2 = create_employee(clean_session, admin_employee, 'Sales2', 'sales2@e.com', '4567890123', 'Commercial', 'pass')
    client = create_client(clean_session, sales2, 'Client', 'client8@e.com', '0192837465', 'Comp')
    result = update_client(clean_session, sales_employee, client.id, full_name='Fail')
    assert result is None  # Expect None for unauthorized update

def test_update_client_sad_invalid(admin_employee, clean_session, sales_employee):
    client = create_client(clean_session, sales_employee, 'Client', 'client9@e.com', '0192837465', 'Comp')
    result = update_client(clean_session, admin_employee, client.id, email='invalid')
    assert result is None  # Expect None for invalid email