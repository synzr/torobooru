from enum import Enum
from dataclasses import dataclass


class ViewTagType(Enum):
    """Tag type for an view settings."""

    NESSECARY = 1
    BLOCKED = 2


class ViewOrderType(Enum):
    """Order type for an view settings."""

    ASCENDING_ORDER = 1
    DESCENDING_ORDER = -1


@dataclass
class ViewSettings:
    """View settings."""

    page_index: int
    page_size: int

    tags: dict[str, ViewTagType]
    order_by: ViewOrderType


@dataclass
class ViewResult:
    """View result."""

    results: list
    has_more: bool
