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

    def add_provider(self,
                     provider_name: str,
                     provider_class: any,
                     provider_objects: dict[str, any]) -> None:
        """Add provider to the manager.

        Args:
            provider_name (str): Provider name.
            provider_class (any): Provider class.
            provider_objects (dict[str, any]): Objects of the provider.
        """

        if provider_name in self.__providers:
            return

        self.__providers[provider_name] = {
            "class_instance": provider_class(),
            "avaliable_objects": provider_objects
        }

    def __parse_urn(self, urn: str) -> URN | None:
        if not urn.startswith("urn:"):
            return None

        elements = urn.split(":")[1:]

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
        external_data_urn_check = " AND ".join(external_data_urn_check)

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

        return result

    async def __get_dictionary_using_providers(self,
                                               urns: list[str],
                                               cursor: aiomysql.Cursor) -> dict[str, ExternalData]:
        result = {}
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

                    for urn in urns:
                        if urn in result.keys():
                            urns.remove(urn)

                result.update(await self.__get_dictionary_using_providers(urns, cursor))
                await connection.commit()

                return result
