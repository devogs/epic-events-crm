# tests/test_employee_controller.py
import pytest
from app.controllers.employee_controller import create_employee, list_employees, update_employee, delete_employee
from app.models import Employee

def test_create_employee_happy(admin_employee, clean_session):
    new_emp = create_employee(clean_session, admin_employee, 'Test User', '', '123', 'Commercial', 'pass')
    assert new_emp is not None
    assert new_emp.full_name == 'Test User'
    assert new_emp.email == 'test.user@epicevents.com'  # Match actual email generation

def test_create_employee_sad_permission(sales_employee, clean_session):
    result = create_employee(clean_session, sales_employee, 'Test', 'test@e.com', '123', 'Commercial', 'pass')
    assert result is None

def test_create_employee_sad_invalid_data(admin_employee, clean_session):
    result = create_employee(clean_session, admin_employee, '', 'test@e.com', '123', 'Commercial', 'pass')
    assert result is None

def test_create_employee_sad_invalid_dept(admin_employee, clean_session):
    result = create_employee(clean_session, admin_employee, 'Test', 'test@e.com', '123', 'Invalid', 'pass')
    assert result is None

def test_list_employees_happy(clean_session, admin_employee):
    assert len(list_employees(clean_session)) == 1

def test_update_employee_happy(admin_employee, clean_session):
    updated = update_employee(clean_session, admin_employee, admin_employee.id, full_name='Updated Admin')
    assert updated.full_name == 'Updated Admin'

def test_update_employee_sad_permission(sales_employee, clean_session, admin_employee):
    result = update_employee(clean_session, sales_employee, admin_employee.id, full_name='Fail')
    assert result is None  # Keep this, but we'll check controller logic

def test_update_employee_sad_invalid(admin_employee, clean_session):
    result = update_employee(clean_session, admin_employee, 999, full_name='No')
    assert result is None

def test_delete_employee_happy(admin_employee, clean_session):
    create_employee(clean_session, admin_employee, 'Admin2', 'admin2@e.com', '123', 'Gestion', 'pass')
    assert delete_employee(clean_session, admin_employee.id) is True
    assert clean_session.query(Employee).filter_by(id=admin_employee.id).one_or_none() is None

def test_delete_employee_sad_last_admin(admin_employee, clean_session):
    assert delete_employee(clean_session, admin_employee.id) is False

def test_delete_employee_sad_not_found(clean_session):
    assert delete_employee(clean_session, 999) is False