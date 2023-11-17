from core.models import (
    DatabaseConnectionSettings,
    StorageConnectionSettings
)

import aiomysql
import aiobotocore.session

import asyncio


class ContentManager:
    """Content manager implementation."""

    def __init__(self,
                 database_connection_settings: DatabaseConnectionSettings,
                 storage_connection_settings: StorageConnectionSettings) -> None:
        """Class constructor that connects the database.

        Args:
            database_connection_settings (DatabaseConnectionSettings): Database connection settings.
            storage_connection_settings (StorageConnectionSettings): Storage connection settings.
        """

        self.__storage = {
            "session": aiobotocore.session.get_session({
                "AWS_ACCESS_KEY_ID": storage_connection_settings.credentials_access_key,
                "AWS_SECRET_ACCESS_KEY": storage_connection_settings.credentials_secret_access_key,
                "AWS_DEFAULT_REGION": storage_connection_settings.instance_region_name
            }),
            "instance_url": storage_connection_settings.instance_url,
            "bucket_name": storage_connection_settings.bucket_name
        }

        asyncio.get_event_loop().run_until_complete(
            self.__instantiate_pool(database_connection_settings))

    async def __instantiate_pool(self,
                                 database_connection_settings: DatabaseConnectionSettings) -> None:
        """Instantiate the database pool.

        Args:
            database_connection_settings (DatabaseConnectionSettings): Database connection settings.
        """

        self.__database_pool = aiomysql.create_pool(database_connection_settings.pool_minimum_size,
                                                    database_connection_settings.pool_maximum_size,
                                                    host=database_connection_settings.instance_hostname,
                                                    port=database_connection_settings.instance_port,
                                                    user=database_connection_settings.credentials_username,
                                                    password=database_connection_settings.credentials_password,
                                                    db=database_connection_settings.database_name,
                                                    cursorclass=aiomysql.DictCursor)
