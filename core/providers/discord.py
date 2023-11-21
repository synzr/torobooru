from core.models import DiscordMessage, DiscordUser, URN
from discord import Client
import asyncio
import logging


class DiscordProvider:
    """Discord data provider."""

    def __init__(self, bot_token: str | None = None, client: Client | None = None) -> None:
        """Class constructor.

        Args:
            bot_token (str): Discord bot token.
            client (Client, optional): Previously configured Discord API client.
        """

        self.__logger = logging.getLogger("core.providers.discord")

        if client: self.__client = client
        else:
            self.__client = Client()

            asyncio.get_event_loop().run_until_complete(
                self.__client.login(bot_token))

    async def __fetch_message(self,
                              channel_id: int,
                              message_id: int) -> DiscordMessage | None:
        try:
            channel = await self.__client.fetch_channel(channel_id)
            message = await channel.fetch_message(message_id)
        except:
            return None

        message_id = message.id
        message_user_id = message.author.id
        message_full_url = message.jump_url
        message_content = message.clean_content
        message_image_attachements = []

        for attachement in message.attachments:
            if not attachement.content_type.startswith("image"):
                continue

            message_image_attachements.append(attachement.proxy_url)

        self.__logger.info(f"__fetch_message(channel_id={channel_id}, message_id={message_id}): Received message \"{message_content}\" ({message_full_url})")

        return DiscordMessage(
            message_id=message_id,
            message_user_id=message_user_id,
            message_full_url=message_full_url,
            message_content=message_content,
            message_image_attachements=message_image_attachements
        )

    async def __fetch_user(self, user_id: int) -> DiscordUser | None:
        try: user = await self.__client.fetch_user(user_id)
        except: return None

        user_id = user.id
        user_name = user.name
        user_display_name = user.display_name
        user_legacy_discriminator = user.discriminator
        user_avatar_url = user.avatar.with_size(512).with_static_format("png").url
        user_banner_url = user.banner.with_size(512).with_static_format("png").url

        self.__logger.info(f"__fetch_user(user_id={user_id}): Received user {user_display_name} ({user_name}#{user_legacy_discriminator})")

        return DiscordUser(
            user_id=user_id,
            user_name=user_name,
            user_display_name=user_display_name,
            user_legacy_discriminator=user_legacy_discriminator,
            user_avatar_url=user_avatar_url,
            user_banner_url=user_banner_url
        )

    async def fetch(self, urn: URN) -> DiscordUser | DiscordMessage | None:
        """Fetch the object using an identifier.

        Args:
            urn (URN): URN.

        Returns:
            DiscordUser: Discord user information.
            DiscordMessage: Discord message information.
            None: Nothing.
        """

        if urn.urn_object == "message":
            channel_id = int(urn.urn_extra_fields["channel_id"], 10)
            message_id = int(urn.urn_identifier, 10)

            return await self.__fetch_message(channel_id, message_id)

        if urn.urn_object == "user":
            user_id = int(urn.urn_identifier, 10)
            return await self.__fetch_user(user_id)

        self.__logger.error(f"fetch(urn={urn}): Can't receive this object")
        return None
