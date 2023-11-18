from enum import Enum
from datetime import datetime
from dataclasses import dataclass


@dataclass
class DatabaseConnectionSettings:
    """Database connection settings."""

    instance_hostname: str
    instance_port: int

    credentials_username: str
    credentials_password: str

    database_name: str

    pool_minimum_size: int
    pool_maximum_size: int


@dataclass
class StorageConnectionSettings:
    """Storage connection settings."""

    instance_url: str
    instance_region_name: str

    credentials_access_key: str
    credentials_secret_access_key: str

    bucket_name: str

    public_url_base: str | None


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


@dataclass
class Content:
    """Content information from the database."""

    content_id: int
    content_submission_urn: str
    content_source_urn: str
    content_origin_urn: str
    content_media_url: str
    content_thumbnail_url: str | None
    content_tags: str | list[str]
    content_submitted_at: datetime


class ContentViewResult(ViewResult):
    """View result with contents."""

    results: list[Content]


class ImageType(Enum):
    """Image type."""

    MEDIA = 0
    THUMBNAIL = 1
    AVATAR = 2
