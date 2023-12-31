from yarl import URL
from aiohttp import ClientSession

from core.models import (
    PivixArtwork,
    PivixUser,
    TumblrBlog,
    TumblrPost,
    TwitterTweet,
    TwitterUser,
    DatabaseConnectionSettings,
    ExternalData,
    URN
)
from core.providers import (
    PixivProvider,
    TumblrProvider,
    TwitterProvider
)
import dataclasses

import aiomysql
import asyncio

import ujson
import logging


class ExternalDataManager:
    """External data manager."""

    GET_EXTERNAL_DATA_SQL = """
        SELECT
            `external_data`.`external_data_urn`,
            `external_data`.`external_data`
        FROM `external_data`
        WHERE {external_data_urn_check};
    """

    ADD_OR_UPDATE_EXTERNAL_DATA_SQL = """
        INSERT
        INTO `external_data` (
            `external_data`.`external_data_urn`,
            `external_data`.`external_data`
        )
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            `external_data`.`external_data_urn` = %s,
            `external_data`.`external_data` = %s;
    """

    def __init__(self,
                 database_connection_settings: DatabaseConnectionSettings) -> None:
        """Class constructor.

        Args:
            database_connection_settings (DatabaseConnectionSettings): Database connection settings.
        """

        self.__providers = {}
        self.__logger = logging.getLogger("core.managers.external_data")

        asyncio.get_event_loop().run_until_complete(
            self.__instantiate_pool(database_connection_settings))

        self.add_provider("pixiv", PixivProvider, {"artwork": PivixArtwork, "user": PivixUser})
        self.add_provider("tumblr", TumblrProvider, {"blog": TumblrBlog, "post": TumblrPost})
        self.add_provider("twitter", TwitterProvider, {"tweet": TwitterTweet, "user": TwitterUser})

    async def __instantiate_pool(self,
                                 database_connection_settings: DatabaseConnectionSettings) -> None:
        """Instantiate the database pool.

        Args:
            database_connection_settings (DatabaseConnectionSettings): Database connection settings.
        """

        self.__database_pool = await aiomysql.create_pool(database_connection_settings.pool_minimum_size,
                                                          database_connection_settings.pool_maximum_size,
                                                          host=database_connection_settings.instance_hostname,
                                                          port=database_connection_settings.instance_port,
                                                          user=database_connection_settings.credentials_username,
                                                          password=database_connection_settings.credentials_password,
                                                          db=database_connection_settings.database_name,
                                                          cursorclass=aiomysql.DictCursor)

        self.__logger.info("__instantiate_pool(database_connection_settings=[redacted]): Instantiated an database pool")

    def add_provider(self,
                     provider_name: str,
                     provider_class: any,
                     provider_objects: dict[str, any],
                     provider_class_arguments: dict = {}) -> None:
        """Add provider to the manager.

        Args:
            provider_name (str): Provider name.
            provider_class (any): Provider class.
            provider_objects (dict[str, any]): Objects of the provider.
            provider_class_arguments (dict, optional): Arguments for provider class instance.
        """

        if provider_name in self.__providers:
            return

        self.__logger.info(f"add_provider(provider_name={provider_name}, provider_class={provider_class}, provider_objects={provider_objects}): Added provider {provider_name}")
        self.__providers[provider_name] = {
            "class_instance": provider_class(**provider_class_arguments),
            "avaliable_objects": provider_objects
        }

    # TODO(synzr): move the urn logic to provider classes
    def __parse_urn(self, urn: str) -> URN | None:
        if not urn.startswith("urn:"):
            return None

        elements = urn.split(":")[1:]

        if elements[0] == "discord" and elements[1] == "message":
            urn_provider, urn_object, channel_id, urn_identifier = elements

            return URN(
                urn_provider=urn_provider,
                urn_object=urn_object,
                urn_identifier=urn_identifier,
                urn_extra_fields={"channel_id": channel_id}
            )

        if elements[0] == "tumblr" and elements[1] == "post":
            urn_provider, urn_object, blog_name, urn_identifier = elements

            return URN(
                urn_provider=urn_provider,
                urn_object=urn_object,
                urn_identifier=urn_identifier,
                urn_extra_fields={"blog_name": blog_name}
            )

        urn_provider, urn_object, urn_identifier = elements

        return URN(
            urn_provider=urn_provider,
            urn_object=urn_object,
            urn_identifier=urn_identifier,
            urn_extra_fields=None
        )

    def __generate_get_external_data_query(self, urn_count: int) -> str:
        external_data_urn_check = ["`external_data`.`external_data_urn` = %s" for index in range(urn_count)]
        external_data_urn_check = " OR ".join(external_data_urn_check)

        return self.GET_EXTERNAL_DATA_SQL.format(
            external_data_urn_check=external_data_urn_check
        )

    async def __get_dictionary_using_cached_data(self,
                                                 urns: list[str],
                                                 cursor: aiomysql.Cursor) -> dict[str, ExternalData]:
        query = self.__generate_get_external_data_query(len(urns))
        await cursor.execute(query, urns)

        result = {}
        for row in await cursor.fetchall():
            external_data_urn_string = row["external_data_urn"]
            external_data_urn_parsed = self.__parse_urn(
                external_data_urn_string
            )

            external_data = ujson.loads(row["external_data"])
            external_data_as_object = self.__providers[
                external_data_urn_parsed.urn_provider
            ]["avaliable_objects"][
                external_data_urn_parsed.urn_object
            ](**external_data)

            result[external_data_urn_string] = ExternalData(
                urn_string=external_data_urn_string,
                urn_parsed=external_data_urn_parsed,
                external_data=external_data_as_object
            )

        self.__logger.info(f"__get_dictionary_using_cached_data(urns={urns}, cursor={cursor}): Got {len(result)} results")
        return result

    async def __get_dictionary_using_providers(self,
                                               urns: list[str],
                                               cursor: aiomysql.Cursor) -> dict[str, ExternalData]:
        result = {urn: None for urn in urns}
        result_count = 0

        for urn in urns:
            urn_parsed = self.__parse_urn(urn)

            if urn_parsed.urn_provider not in self.__providers:
                result[urn] = None
                continue

            if urn_parsed.urn_object not in self.__providers[
                urn_parsed.urn_provider
            ]["avaliable_objects"].keys():
                result[urn] = None
                continue

            external_data = await self.__providers[
                urn_parsed.urn_provider
            ]["class_instance"].fetch(urn_parsed)

            external_data_dictionary = dataclasses.asdict(external_data)
            external_data_json = ujson.dumps(
                external_data_dictionary,
                ensure_ascii=False,
                encode_html_chars=True,
                escape_forward_slashes=True
            )

            query_arguments = [urn, external_data_json, urn, external_data_json]
            await cursor.execute(self.ADD_OR_UPDATE_EXTERNAL_DATA_SQL, query_arguments)

            result[urn] = ExternalData(
                urn_string=urn,
                urn_parsed=urn_parsed,
                external_data=external_data
            )
            result_count += 1

        self.__logger.info(f"__get_dictionary_using_providers(urns={urns}, cursor={cursor}): Got {result_count} results")
        return result

    async def get_external_data(self,
                                urns: list[str],
                                force_update: bool = False) \
                                     -> dict[str, ExternalData] | None:
        """Get an external data using the URN strings.

        Args:
            urns (str): URN strings.
            force_update (bool, optional): We have to force the update of data?

        Returns:
            dict[str, ExternalData]: External data.
        """

        async with self.__database_pool.acquire() as connection:
            async with connection.cursor() as cursor:
                result = {}

                if not force_update:
                    result = await self.__get_dictionary_using_cached_data(urns, cursor)
                    urns = list(filter(lambda urn: not result[urn], urns))

                result.update(await self.__get_dictionary_using_providers(urns, cursor))
                await connection.commit()

                self.__logger.info(f"get_external_data(urns={urns}, force_update={force_update}): Got {len(result)} results")
                return result

    # TODO(synzr): move the urn logic to provider classes
    async def get_urn_from_url(self, url: str) -> str | None:
        """Get an URN identifier using URL.

        Args:
            url (str): URL.

        Returns:
            str: URN identifier.
            None: Nothing.
        """

        parsed_url = URL(url)
        is_twitter_hostname = (
            parsed_url.host == "twitter.com" or
            parsed_url.host == "x.com" or
            parsed_url.host == "vxtwitter.com" or
            parsed_url.host == "fxtwitter.com" or
            parsed_url.host == "fixvx.com" or
            parsed_url.host == "fixupx.com"
        )

        if is_twitter_hostname:
            is_tweet = "/status" in parsed_url.path
            is_unknown_page = "/i" in parsed_url.path

            if is_tweet: return f"urn:twitter:tweet:{parsed_url.parts[-1]}"
            elif not is_unknown_page: return f"urn:twitter:user:{parsed_url.parts[0]}"
            else: return None

        if parsed_url.host == "tmblr.co":
            async with ClientSession() as session:
                async with session.get(url, allow_redirects=False) as response:
                    parsed_url = URL(response.headers["location"])

        if parsed_url.host.endswith("tumblr.com"):
            is_blog_name_in_hostname = parsed_url.host != "tumblr.com"

            if is_blog_name_in_hostname: blog_name = parsed_url.host.split(".")[0]
            else: blog_name = parsed_url.parts[0]

            urn = f"urn:tumblr:blog:{blog_name}"

            if parsed_url.parts[1].isdigit():
                urn = f"urn:tumblr:post:{blog_name}:{parsed_url.parts[1]}"
            elif parsed_url.parts[2].isdigit():
                urn = f"urn:tumblr:post:{blog_name}:{parsed_url.parts[2]}"

            return urn

        if parsed_url.host.endswith("pixiv.net"):
            if parsed_url.parts[-2] == "artworks":
                return f"urn:pixiv:artwork:{parsed_url.parts[-1]}"
            elif parsed_url.parts[-2] == "users":
                return f"urn:pixiv:user:{parsed_url.parts[-1]}"

        return None
