from core.models import (
    DatabaseConnectionSettings,
    StorageConnectionSettings,
    ViewTagType,
    ViewOrderType,
    ViewSettings,
    Content,
    ContentViewResult,
    ImageType
)

from .media_processing import MediaProcessingManager

import aiomysql
import aiobotocore.session

import asyncio
import ujson


class ContentManager:
    """Content manager implementation."""

    CONTENT_SQL_QUERY_BASE = """
        SELECT *
        FROM `contents`
        WHERE ({nesseccary_tags_check_expression})
        AND NOT ({blocked_tags_check_expression})
        ORDER BY `contents`.`content_submitted_at` {order_type}
        LIMIT {limit_value}
        OFFSET {offset_value};
    """

    INSERT_CONTENT_SQL_QUERY = """
        INSERT INTO
        `contents` (
            `contents`.`content_submission_urn`, `contents`.`content_source_urn`,
            `contents`.`content_origin_urn`, `contents`.`content_media_url`,
            `contents`.`content_thumbnail_url`, `contents`.`content_tags`
        )
        VALUES (%s, %s, %s, %s, %s, %s);
    """

    INSERT_CONTENT_KEYS = [
        "content_submission_urn", "content_source_urn", "content_origin_urn",
        "content_media_url", "content_thumbnail_url", "content_tags"
    ]

    def __init__(self,
                 database_connection_settings: DatabaseConnectionSettings,
                 storage_connection_settings: StorageConnectionSettings,
                 media_processing_manager: MediaProcessingManager) -> None:
        """Class constructor.

        Args:
            database_connection_settings (DatabaseConnectionSettings): Database connection settings.
            storage_connection_settings (StorageConnectionSettings): Storage connection settings.
            media_processing_manager (MediaProcessingManager): Media processing manager.
        """

        self.__storage_connection_settings = storage_connection_settings
        self.__media_processing_manager = media_processing_manager

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

        return self.CONTENT_SQL_QUERY_BASE.format(
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

            async with connection.cursor() as cursor:
                await cursor.execute(query, query_arguments)

                results = []

                for row in await cursor.fetchall():
                    content = Content(**row)
                    content.content_tags = ujson.loads(content.content_tags)

                    results.append(content)

                # Maximum size of `len(results)` is equals to `view_settings.page_size + 1``
                has_more = len(results) == view_settings.page_size + 1
                if has_more: results = results[:-1]

                return ContentViewResult(results=results,
                                         has_more=has_more)

    def __get_storage_url(self, file_path: str) -> str:
        instance_url = self.__storage_connection_settings.instance_url
        bucket_name = self.__storage_connection_settings.bucket_name

        base_url = f"{instance_url}/{bucket_name}/" \
            if not instance_url.endswith("/") \
                else f"{instance_url}{bucket_name}/"

        public_url_base = self.__storage_connection_settings.public_url_base

        if public_url_base:
            base_url = public_url_base if public_url_base.endswith("/") \
                else public_url_base + "/"

        return base_url + file_path

    async def add_contents(self, contents: list[Content], process_media: bool) -> int:
        """Add an multiple content information to the database.

        Args:
            contents (list[Content]): Content information.
            process_media (bool): Is need to process the media?

        Returns:
            list: Count of added contents.
        """

        async with self.__database_pool.acquire() as connection:
            arguments_of_queries = []

            for content in contents:
                if process_media:
                    source_image_url = content.content_media_url

                    processed_images = await self.__media_processing_manager.process_images_from_urls({
                        source_image_url: [ImageType.MEDIA, ImageType.THUMBNAIL]
                    })

                    content.content_media_url = self.__get_storage_url(
                        processed_images[source_image_url][ImageType.MEDIA]
                    )

                    content.content_thumbnail_url = self.__get_storage_url(
                        processed_images[source_image_url][ImageType.THUMBNAIL]
                    )

                content.content_tags = ujson.dumps(content.content_tags)
                query_arguments = [getattr(content, key) for key in self.INSERT_CONTENT_KEYS]

                arguments_of_queries.append(query_arguments)

            async with connection.cursor() as cursor:
                await cursor.executemany(self.INSERT_CONTENT_SQL_QUERY, arguments_of_queries)
                await connection.commit()

                return cursor.rowcount
