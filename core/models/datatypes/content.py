from dataclasses import dataclass
from datetime import datetime
from ..settings.view import ViewResult


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
