from dataclasses import dataclass


@dataclass
class DiscordUser:
    """Discord user information."""

    user_id: int
    user_name: str
    user_display_name: str
    user_legacy_discriminator: str | int
    user_avatar_url: str | None
    user_banner_url: str | None


@dataclass
class DiscordMessage:
    """Discord message information."""

    message_id: int
    message_user_id: int
    message_full_url: str
    message_content: str
    message_image_attachements: list[str]
