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
