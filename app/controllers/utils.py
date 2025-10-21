"""
Utility functions used across multiple controllers for validation and helpers.
"""

import re


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    regex = r"^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    return re.fullmatch(regex, email)


def is_valid_phone(phone: str) -> bool:
    """Basic phone number validation (accepts digits, spaces, hyphens)."""
    # Accepte 5 à 20 chiffres, espaces ou tirets
    return bool(re.fullmatch(r"^[\d\s-]{5,20}$", phone))
