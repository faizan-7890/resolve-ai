"""
Input validators for ResolveAI schemas.
Provides Pydantic field validators for common validation patterns.
"""

from pydantic import field_validator, ValidationInfo
from typing import Any
import re


class CommonValidators:
    """Common validation methods used across schemas"""

    @staticmethod
    def validate_non_empty_string(value: str, field_name: str, min_length: int = 1, max_length: int = 5000) -> str:
        """Validate that a string is not empty and within length constraints"""
        if not value or not isinstance(value, str):
            raise ValueError(f"{field_name} must be a non-empty string")
        
        value = value.strip()
        
        if len(value) < min_length:
            raise ValueError(f"{field_name} must be at least {min_length} characters long")
        
        if len(value) > max_length:
            raise ValueError(f"{field_name} cannot exceed {max_length} characters")
        
        return value

    @staticmethod
    def validate_password(password: str) -> str:
        """
        Validate password strength:
        - At least 8 characters
        - At least one digit
        """
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one number")

        return password

    @staticmethod
    def validate_name(name: str, min_length: int = 2, max_length: int = 100) -> str:
        """Validate user/display names"""
        name = name.strip()
        
        if len(name) < min_length:
            raise ValueError(f"Name must be at least {min_length} characters long")
        
        if len(name) > max_length:
            raise ValueError(f"Name cannot exceed {max_length} characters")
        
        # Allow letters, numbers, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z0-9\s\-']+$", name):
            raise ValueError("Name can only contain letters, numbers, spaces, hyphens, and apostrophes")
        
        return name

    @staticmethod
    def validate_enum_field(value: str, allowed_values: list[str]) -> str:
        """Validate that value is in allowed list"""
        if value not in allowed_values:
            raise ValueError(f"Value must be one of: {', '.join(allowed_values)}")
        return value

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Remove potentially harmful content and extra whitespace"""
        # Remove leading/trailing whitespace
        text = text.strip()
        # Replace multiple spaces/newlines with single space/newline
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n\n+", "\n\n", text)
        return text
