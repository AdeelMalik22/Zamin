import re


PHONE_ALLOWED = re.compile(r"^\+?[0-9][0-9().\s-]*$")


def clean_required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be blank")
    return cleaned


def normalize_phone(value: str) -> str:
    cleaned = value.strip()
    if not PHONE_ALLOWED.fullmatch(cleaned):
        raise ValueError("phone number must contain only digits and common phone separators")
    digit_count = sum(character.isdigit() for character in cleaned)
    if not 7 <= digit_count <= 15:
        raise ValueError("phone number must contain between 7 and 15 digits")
    return cleaned


def validate_password(value: str) -> str:
    if not 8 <= len(value) <= 72:
        raise ValueError("password must be between 8 and 72 characters")
    if len(value.encode("utf-8")) > 72:
        raise ValueError("password must not exceed 72 UTF-8 bytes")
    return value
