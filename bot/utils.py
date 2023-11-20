from core.models import (
    DatabaseConnectionSettings,
    StorageConnectionSettings
)
from argparse import ArgumentParser, Namespace
import os

ENVIRONMENT_VARIABLES_MAPPING = {
    "DISCORD_TOKEN": "discord_token",
    "DATABASE_INSTANCE_HOSTNAME": "database_instance_hostname",
    "DATABASE_INSTANCE_PORT": ["database_instance_port", int],
    "DATABASE_CREDENTIALS_USERNAME": "database_credentials_username",
    "DATABASE_CREDENTIALS_PASSWORD": "database_credentials_password",
    "DATABASE_NAME": "database_name",
    "STORAGE_INSTANCE_URL": "storage_instance_url",
    "STORAGE_INSTANCE_REGION_NAME": "storage_instance_region_name",
    "STORAGE_CREDENTIALS_ACCESS_KEY": "storage_credentials_access_key",
    "STORAGE_CREDENTIALS_SECRET_ACCESS_KEY": "storage_credentials_secret_access_key",
    "STORAGE_BUCKET_NAME": "storage_bucket_name",
    "STORAGE_PUBLIC_BASE_URL": "storage_public_base_url"
}


def build_argument_parser() -> ArgumentParser:
    """Create an argument parser for the bot.

    Returns:
        ArgumentParser: Argument parser.
    """

    argument_parser = ArgumentParser("toroboorubot",
                                     description="Torobooru's discord bot")

    argument_parser.add_argument("--discord-token", default=None)

    argument_parser.add_argument_group()

    # Database settings
    argument_parser.add_argument("--database-instance-hostname", default=None)
    argument_parser.add_argument("--database-instance-port", type=int, default=None)

    argument_parser.add_argument("--database-credentials-username", default=None)
    argument_parser.add_argument("--database-credentials-password", default=None)

    argument_parser.add_argument("--database-name", default=None)

    # Storage settings
    argument_parser.add_argument("--storage-instance-url", default=None)
    argument_parser.add_argument("--storage-instance-region-name", default=None)

    argument_parser.add_argument("--storage-credentials-access-key", default=None)
    argument_parser.add_argument("--storage-credentials-secret-access-key", default=None)

    argument_parser.add_argument("--storage-bucket-name", default=None)
    argument_parser.add_argument("--storage-public-base-url", default=None)

    return argument_parser


def parse_environment_variables_to_namespace(namespace: Namespace) -> Namespace:
    """Parse the current environment variables to namespace.

    Args:
        namespace (Namespace): Namespace.

    Returns:
        Namespace: Namespace with parsed environment variables.
    """

    for environment_variable_field, namespace_field in ENVIRONMENT_VARIABLES_MAPPING.items():
        if os.environ.get(environment_variable_field):
            environment_variable_value = os.environ[environment_variable_field]

            if type(namespace_field) == list:
                namespace_field, namespace_field_type = namespace_field
                environment_variable_value = namespace_field_type(environment_variable_value)

            setattr(namespace, namespace_field, environment_variable_value)

    return namespace


def get_settings_using_namespace(namespace: Namespace) \
     -> tuple[DatabaseConnectionSettings, StorageConnectionSettings]:
    """Get settings using an namespace.

    Returns:
        tuple[DatabaseConnectionSettings, StorageConnectionSettings]: Settings.
    """

    database_connection_settings = DatabaseConnectionSettings(
        instance_hostname=namespace.database_instance_hostname,
        instance_port=namespace.database_instance_port,
        credentials_username=namespace.database_credentials_username,
        credentials_password=namespace.database_credentials_password,
        database_name=namespace.database_name,
        pool_minimum_size=3,
        pool_maximum_size=10
    )

    storage_connection_settings = StorageConnectionSettings(
        instance_url=namespace.storage_instance_url,
        instance_region_name=namespace.storage_instance_region_name,
        credentials_access_key=namespace.storage_credentials_access_key,
        credentials_secret_access_key=namespace.storage_credentials_secret_access_key,
        bucket_name=namespace.storage_bucket_name,
        public_url_base=namespace.storage_public_base_url
    )

    return database_connection_settings, storage_connection_settings
