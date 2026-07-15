from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"


class ListingStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PropertyType(str, Enum):
    HOUSE = "house"
    PLOT = "plot"
    APARTMENT = "apartment"
    COMMERCIAL = "commercial"
    OTHER = "other"


class SearchMode(str, Enum):
    CONTAINS = "contains"
    REGEX = "regex"
    FUZZY = "fuzzy"


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Tell SQLAlchemy to persist enum values instead of Python member names."""
    return [item.value for item in enum_class]
