from core.models import (
    DatabaseConnectionSettings,
    StorageConnectionSettings,
    ViewTagType,
    ViewOrderType,
    ViewSettings,
    Content,
    ContentViewResult
)

import aiomysql
import aiobotocore.session

import asyncio

CONTENT_SQL_QUERY_BASE = """
    SELECT *
    FROM `contents`
    WHERE ({nesseccary_tags_check_expression})
    AND NOT ({blocked_tags_check_expression})
    ORDER BY `contents`.`content_submitted_at` {order_type}
    LIMIT {limit_value}
    OFFSET {offset_value};
"""


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

        self.__storage_connection_settings = storage_connection_settings

        asyncio.get_event_loop().run_until_complete(
            self.__instantiate_pool(database_connection_settings))

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

    def __generate_content_sql_query(self, view_settings: ViewSettings) -> str:
        nesseccary_tags_executions = []
        blocked_tags_executions = []

        for tag_type in view_settings.tags.values():
            execution = "JSON_CONTAINS(`contents`.`content_tags`, %s, '$')"

            if tag_type == ViewTagType.NESSECARY: nesseccary_tags_executions.append(execution)
            if tag_type == ViewTagType.BLOCKED: blocked_tags_executions.append(execution)

        nesseccary_tags_check_expression = " AND ".join(nesseccary_tags_executions)
        blocked_tags_check_expression = " AND ".join(blocked_tags_executions)

        if len(nesseccary_tags_executions) == 0: nesseccary_tags_check_expression = "1"
        if len(blocked_tags_executions) == 0: blocked_tags_check_expression = "0"

        limit_value = view_settings.page_size + 1
        offset_value = view_settings.page_size * (view_settings.page_index - 1)

        order_type = "ASC" if view_settings.order_by == ViewOrderType.ASCENDING_ORDER else "DESC"

        return CONTENT_SQL_QUERY_BASE.format(
            nesseccary_tags_check_expression=nesseccary_tags_check_expression,
            blocked_tags_check_expression=blocked_tags_check_expression,
            limit_value=limit_value,
            offset_value=offset_value,
            order_type=order_type
        )

    def __generate_content_sql_query_arguments(self, view_settings: ViewSettings) -> list:
        nesseccary_tags = []
        blocked_tags = []

        for tag, tag_type in view_settings.tags.items():
            # Adding the quotation mark for converting to vaild JSON string
            tag = tag.center(len(tag) + 2, '"')

            if tag_type == ViewTagType.NESSECARY: nesseccary_tags.append(tag)
            if tag_type == ViewTagType.BLOCKED: blocked_tags.append(tag)

        return nesseccary_tags + blocked_tags

    async def get_contents(self, view_settings: ViewSettings) -> ContentViewResult:
        """Get contents with an view settings.

        Args:
            view_settings (ViewSettings): View settings.

        Returns:
            ContentViewResult: Contents with "has_more" value
        """

        async with self.__database_pool.acquire() as connection:
            query = self.__generate_content_sql_query(view_settings)
            query_arguments = self.__generate_content_sql_query_arguments(view_settings)

            print(query)

            async with connection.cursor() as cursor:
                await cursor.execute(query, query_arguments)

                results = [Content(**row) for row in await cursor.fetchall()]

                # Maximum size of `len(results)` is equals to `view_settings.page_size + 1``
                has_more = len(results) == view_settings.page_size + 1
                if has_more: results = results[:-1]

                return ContentViewResult(results=results,
                                         has_more=has_more)
