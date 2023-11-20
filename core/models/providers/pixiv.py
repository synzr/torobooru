from dataclasses import dataclass


@dataclass
class PivixArtwork:
    """Pivix artwork information."""

    artwork_id: int | str
    artwork_full_url: str
    artwork_title: str
    artwork_comment: str
    artwork_hq_image_url: str
    artwork_author_id: int | str
    artwork_author_full_url: str


@dataclass
class PivixUser:
    """Pivix user information."""

    user_id: int | str
    user_full_url: str
    user_name: str
    user_hq_avatar_url: str
    user_following_count: int
    user_twitter_account_url: str | None
