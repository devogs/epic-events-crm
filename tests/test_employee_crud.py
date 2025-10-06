"""
Integration tests for the employee_controller module.
These tests verify CRUD operations (Create, List, Update, Delete) 
and permission checks for employees in the 'Gestion' department 
using an in-memory SQLite database.
"""
import sys
import os

# FIX: Add the project root directory (one level up from 'tests') to the Python path
# This allows 'app' package imports to be resolved correctly during pytest execution.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Employee
from app.controllers.employee_controller import (
    create_employee, 
    list_employees, 
    update_employee, 
    delete_employee,
    check_permission
)
from app.authentication import check_password # Required for password update check

# --- Fixtures for Testing Environment ---

@pytest.fixture(scope="module")
def db_engine():
    """
    Creates an in-memory SQLite engine for the entire module test session.
    """
    # Using ':memory:' ensures a temporary and clean database.
    engine = create_engine('sqlite:///:memory:', connect_args={"check_same_thread": False})
    # Creates all tables defined in Base
    Base.metadata.create_all(engine)
    yield engine
    # Cleans up metadata after tests
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def session(db_engine):
    """
    Creates a new database session for each test function.
    Uses a rollback at the end to isolate each test.
    """
    connection = db_engine.connect()
    # Starts a transaction that will be rolled back after the test
    transaction = connection.begin()
    
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def management_employee(session: Session) -> Employee:
    """
    Fixture for a 'Gestion' department employee who executes the actions.
    """
    emp = Employee(
        full_name="Manager John", 
        email="manager@epic.com", 
        phone="111-222-3333", 
        department="Gestion"
    )
    # The model hashes the password automatically
    emp.password = "passGesti0n" 
    session.add(emp)
    session.commit()
    return emp

# --- CRUD Tests for the 'Gestion' department ---

def test_01_management_can_create_employee(session: Session, management_employee: Employee):
    """
    Verifies that a 'Gestion' user can create a new employee.
    (Permission: 'create_employee')
    """
    # 1. Permission Check
    assert check_permission(management_employee, 'create_employee') is True

    # 2. Data for the new Commercial employee
    data = {
        'full_name': "Commercial Jane",
        'email': "jane.com@epic.com",
        'phone': "222-333-4444",
        'department': "Commercial",
        'password': "passCom"
    }
    
    # 3. Execution of Creation
    new_employee = create_employee(session, data)

    # 4. Verification
    assert new_employee is not None
    assert new_employee.department == "Commercial"
    
    # Verifies there are now 2 employees (Management + Commercial)
    assert len(list_employees(session)) == 2

def test_02_management_can_list_all_employees(session: Session, management_employee: Employee):
    """
    Verifies that a 'Gestion' user can list all employees.
    """
    # Creates two additional employees
    create_employee(session, {'full_name': "Com User", 'email': "com@epic.com", 'phone': "333", 'department': "Commercial", 'password': "pass"})
    create_employee(session, {'full_name': "Sup User", 'email': "sup@epic.com", 'phone': "444", 'department': "Support", 'password': "pass"})
    
    employees = list_employees(session)
    
    # Should find 3 employees: Manager John (fixture) + Com User + Sup User
    assert len(employees) == 3
    
    # Verifies that departments are correctly stored
    departments = {emp.department for emp in employees}
    assert 'Gestion' in departments
    assert 'Commercial' in departments
    assert 'Support' in departments

def test_03_management_can_update_another_employee(session: Session, management_employee: Employee):
    """
    Verifies that a 'Gestion' user can update another employee.
    (Permission: 'update_employee')
    """
    # 1. Create the target employee to update
    target_data = {'full_name': "Old Name", 'email': "old@epic.com", 'phone': "555", 'department': "Support", 'password': "passOld"}
    target_employee = create_employee(session, target_data)
    
    # 2. Define the updates (change name and department)
    update_data = {
        'full_name': "New Name Updated",
        'department': "Commercial",
        'password': "newpass"
    }
    
    # 3. Execution of the Update
    updated_employee = update_employee(session, target_employee.id, update_data)
    
    # 4. Verification of the Update
    assert updated_employee is not None
    assert updated_employee.full_name == "New Name Updated"
    assert updated_employee.department == "Commercial"
    
    # Verifies that the password is correctly updated (check the hash)
    db_employee = session.query(Employee).filter_by(id=target_employee.id).one()
    # We must use the check_password function from authentication.py
    assert check_password("newpass", db_employee._password_hash) is True
    assert check_password("passOld", db_employee._password_hash) is False # Old password should no longer work

def test_04_management_can_delete_another_employee(session: Session, management_employee: Employee):
    """
    Verifies that a 'Gestion' user can delete another employee.
    (Permission: 'delete_employee')
    """
    # 1. Create the target employee to delete
    target_data = {'full_name': "User To Delete", 'email': "delete@epic.com", 'phone': "666", 'department': "Support", 'password': "passDelete"}
    target_employee = create_employee(session, target_data)
    
    initial_count = len(list_employees(session))
    
    # 2. Execution of the Deletion
    was_deleted = delete_employee(session, target_employee.id)
    
    # 3. Verification of the Deletion
    assert was_deleted is True
    final_count = len(list_employees(session))
    
    # The number of employees must have decreased by 1 (Manager John is still there)
    assert final_count == initial_count - 1 
    
    # Verifies that the employee is truly gone from the database
    deleted_employee_check = session.query(Employee).filter_by(id=target_employee.id).one_or_none()
    assert deleted_employee_check is None

def test_05_update_employee_duplicate_email_fails(session: Session, management_employee: Employee):
    """
    Verifies that updating an employee to an existing email fails.
    """
    # 1. Create two employees
    emp1_data = {'full_name': "Emp1", 'email': "emp1@epic.com", 'phone': "111", 'department': "Commercial", 'password': "p1"}
    emp2_data = {'full_name': "Emp2", 'email': "emp2@epic.com", 'phone': "222", 'department': "Support", 'password': "p2"}
    emp1 = create_employee(session, emp1_data)
    emp2 = create_employee(session, emp2_data) # Target ID for the update
    
    # 2. Attempt to update Emp2 with Emp1's email
    update_data = {'email': "emp1@epic.com"}
    
    # Must raise a ValueError (handled from IntegrityError)
    with pytest.raises(ValueError) as excinfo:
        update_employee(session, emp2.id, update_data)
    
    # This assertion must match the French error message produced by your controller
    assert "L'e-mail existe déjà" in str(excinfo.value)
