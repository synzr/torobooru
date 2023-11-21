from core.managers import (
    ContentManager,
    MediaProcessingManager,
    ExternalDataManager
)
from core.models import (
    DatabaseConnectionSettings,
    StorageConnectionSettings
)
from discord import Client, Intents, Message
import logging


class TorobooruClient(Client):
    """Torobooru's discord bot implementation."""

    MESSAGE_SPECIAL_WORD = "+torobooru"
    MESSAGE_SPACE_SYMBOL = " "

    def __init__(self,
                 database_connection_settings: DatabaseConnectionSettings,
                 storage_connection_settings: StorageConnectionSettings,
                 text_channels: list[int]) -> None:
        """Class constructor.

        Args:
            database_connection_settings (DatabaseConnectionSettings): Database connection settings.
            storage_connection_settings (StorageConnectionSettings): Storage connection settings.
            text_channels (list[int]): Text channels.
        """

        intents = Intents.default()
        intents.message_content = True

        self.__media_processing_manager = MediaProcessingManager(storage_connection_settings)
        self.__content_manager = ContentManager(database_connection_settings,
                                                storage_connection_settings,
                                                self.__media_processing_manager)
        self.__external_data_manager = ExternalDataManager(database_connection_settings)

        self.__text_channels = text_channels
        self.__logger = logging.getLogger("bot.discord")

        super().__init__(intents=intents)

    async def on_ready(self) -> None:
        self.__logger.info(f"on_ready(): Bot ({self.user}) is ready!")

    async def __get_urns_from_message(self, message: Message) -> list[str]:
        words = message.clean_content.split(self.MESSAGE_SPACE_SYMBOL)

        urls = list(filter(lambda url: url.startswith("http://") or url.startswith("https://"), words))
        urns = filter(lambda urn: urn != None,
                      [await self.__external_data_manager.get_urn_from_url(url) for url in urls])

        return list(urns)

    def __get_hashtags_from_message(self, message: Message) -> list[str]:
        words = message.clean_content.split(self.MESSAGE_SPACE_SYMBOL)

        hashtags = filter(lambda word: word.startswith("~"), words)
        hashtags = map(lambda hashtag: hashtag[1:], hashtags)

        return list(hashtags)

    async def on_message(self, message: Message) -> None:
        is_special_word_not_in_message_content = self.MESSAGE_SPECIAL_WORD not in message.clean_content
        is_not_in_allowed_text_channels = message.channel.id not in self.__text_channels
        is_message_from_torobooru = message.author.id == self.user.id

        if message.author.bot or \
            is_not_in_allowed_text_channels or \
                is_message_from_torobooru or \
                    is_special_word_not_in_message_content:
            return

        urns = await self.__get_urns_from_message(message)
        hashtags = self.__get_hashtags_from_message(message)

        self.__logger.info(f"on_message(message={message}): {urns}, {hashtags}")
