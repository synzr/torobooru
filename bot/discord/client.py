from core.managers import (
    ContentManager,
    MediaProcessingManager,
    ExternalDataManager
)
from core.models import (
    DatabaseConnectionSettings,
    StorageConnectionSettings
)
from discord import Client, Intents, User
import logging


class TorobooruClient(Client):
    """Torobooru's discord bot implementation."""

    def __init__(self,
                 database_connection_settings: DatabaseConnectionSettings,
                 storage_connection_settings: StorageConnectionSettings) -> None:
        """Class constructor.

        Args:
            database_connection_settings (DatabaseConnectionSettings): Database connection settings.
            storage_connection_settings (StorageConnectionSettings): Storage connection settings.
        """

        intents = Intents.default()
        intents.message_content = True

        self.__media_processing_manager = MediaProcessingManager(storage_connection_settings)
        self.__content_manager = ContentManager(database_connection_settings,
                                                storage_connection_settings,
                                                self.__media_processing_manager)
        self.__external_data_manager = ExternalDataManager(database_connection_settings)
        self.__logger = logging.getLogger("bot.discord")

        super().__init__(intents=intents)

    async def on_ready(self) -> None:
        self.__logger.info(f"on_ready(): Bot ({self.user}) is ready!")
