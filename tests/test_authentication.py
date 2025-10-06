"""
Unit tests for the authentication module (app/authentication.py).
Tests password hashing and checking functionalities.
"""
import pytest
import sys
import os

# Add the project's root directory to the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.authentication import hash_password, check_password, get_employee_permissions

# --- Test Password Hashing and Checking ---

def test_password_hashing_and_checking():
    """
    Tests that a password can be correctly hashed and verified.
    """
    plain_password = "MySecurePassword123"
    
    # 1. Test Hashing
    hashed_password = hash_password(plain_password)
    
    # Check that the hashed password is not the same as the plain text
    assert hashed_password != plain_password
    # Check that the hash is a valid bcrypt hash format (usually starts with $2b$ or $2a$)
    assert hashed_password.startswith('$2b$') or hashed_password.startswith('$2a$') 

    # 2. Test Checking (Success)
    # Check that the original password verifies against the hash
    assert check_password(plain_password, hashed_password) is True

    # 3. Test Checking (Failure)
    # Check that a wrong password does NOT verify against the hash
    wrong_password = "WrongPassword456"
    assert check_password(wrong_password, hashed_password) is False

def test_different_hashes_for_same_password():
    """
    Tests that two calls to hash_password with the same input yield different results 
    due to salting (essential feature of bcrypt).
    """
    password = "TestingSalting"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    
    # The two hashes should be different because of the random salt
    assert hash1 != hash2
    # But both should still verify correctly against the original password
    assert check_password(password, hash1) is True
    assert check_password(password, hash2) is True

# --- Test Permissions Mapping ---

def test_get_employee_permissions_management():
    """
    Tests permissions mapping for the 'Management' department.
    """
    permissions = get_employee_permissions('Gestion')
    expected_permissions = ['view_clients', 'view_contracts', 'view_events', 'create_employee', 'update_employee']
    
    # Case-insensitive comparison is important here, ensure the logic is robust
    assert sorted(permissions) == sorted(expected_permissions)

def test_get_employee_permissions_commercial():
    """
    Tests permissions mapping for the 'Commercial' department.
    """
    permissions = get_employee_permissions('Commercial')
    expected_permissions = ['view_clients', 'create_client', 'update_client', 'view_contracts', 'create_contract', 'update_contract']
    assert sorted(permissions) == sorted(expected_permissions)

def test_get_employee_permissions_support():
    """
    Tests permissions mapping for the 'Support' department.
    """
    permissions = get_employee_permissions('Support')
    expected_permissions = ['view_events', 'update_event']
    assert sorted(permissions) == sorted(expected_permissions)

def test_get_employee_permissions_unknown():
    """
    Tests permissions mapping for an unknown department.
    """
    permissions = get_employee_permissions('Finance')
    assert permissions == []
