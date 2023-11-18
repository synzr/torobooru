from core.models import StorageConnectionSettings, ImageType
from enum import Enum

from aiohttp import ClientSession
import aiobotocore.session

from PIL import Image
from io import BytesIO

from hashlib import md5

DOWNLOAD_CHUNK_SIZE = 4096
BLACK_COLOR = (0, 0, 0)

IMAGE_SETTINGS = {
    ImageType.MEDIA: {
        "maximum_height": 1024,
        "jpeg_quality": 93,
        "storage_directory_name": "media"
    },
    ImageType.THUMBNAIL: {
        "maximum_height": 200,
        "jpeg_quality": 46,
        "storage_directory_name": "thumbnails"
    },
    ImageType.AVATAR: {
        "maximum_height": 200,
        "jpeg_quality": 62,
        "storage_directory_name": "avatars"
    }
}


class MediaProcessingManager:
    """Media processing manager."""

    def __init__(self,
                 storage_connection_settings: StorageConnectionSettings) -> None:
        """Class constructor that connects to the storage.

        Args:
            storage_connection_settings (StorageConnectionSettings): Storage connection settings.
        """

        self.__storage_connection_settings = storage_connection_settings

    async def __download_image_to_memory(self, source_url: str) -> Image:
        async with ClientSession() as session:
            async with session.get(source_url) as image_response:
                image_contents = BytesIO()

                async for chunk in image_response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                    image_contents.write(chunk)

                return Image.open(image_contents)

    def __process_image(self, source_image: Image, destination_image_type: ImageType) -> Image:
        destination_image = source_image

        if destination_image.mode[-1] == "A":
            background_image = Image.new(destination_image.mode, destination_image.size, BLACK_COLOR)
            destination_image = Image.alpha_composite(source_image, background_image).convert(destination_image.mode[:-1])

        maximum_height = IMAGE_SETTINGS[destination_image_type]["maximum_height"]

        if destination_image.size[1] > maximum_height:
            destination_image_aspect_ratio = destination_image.size[1] / destination_image.size[0]

            destination_image_size = int(maximum_height // destination_image_aspect_ratio), maximum_height
            destination_image = destination_image.resize(destination_image_size)

        return destination_image.convert("RGB")

    async def __upload_image_to_storage(self, image: Image, image_type: ImageType) -> str:
        session = aiobotocore.session.get_session()
        image_contents = BytesIO()

        jpeg_quality = IMAGE_SETTINGS[image_type]["jpeg_quality"]
        image.save(image_contents, format="jpeg", quality=jpeg_quality)

        image_contents.seek(0)
        image_hash = md5(image_contents.getvalue()).hexdigest()

        image_contents.seek(0)

        async with session.create_client("s3",
                                         region_name=self.__storage_connection_settings.instance_region_name,
                                         endpoint_url=self.__storage_connection_settings.instance_url,
                                         aws_access_key_id=self.__storage_connection_settings.credentials_access_key,
                                         aws_secret_access_key=self.__storage_connection_settings.credentials_secret_access_key) as storage:
            storage_directory_name = IMAGE_SETTINGS[image_type]["storage_directory_name"]
            image_path = f"{storage_directory_name}/{image_hash}.jpeg"

            await storage.put_object(
                Body=image_contents,
                Bucket=self.__storage_connection_settings.bucket_name,
                Key=image_path,
                ContentType="image/jpeg"
            )

            return image_path

    async def process_images_from_urls(self,
                                       image_urls: dict[str, list[ImageType]]) -> dict[str, dict[ImageType, str]]:
        """Process image(s) from URL(s).

        Args:
            image_urls (dict[str, list[ImageType]]): Image URL(s) with needed image types.

        Returns:
            dict[str, dict[ImageType, str]]: Processed images.
        """

        processed_images = {}

        for image_url in image_urls:
            image = await self.__download_image_to_memory(image_url)
            processed_images[image_url] = {}

            for image_type in image_urls[image_url]:
                processed_image = self.__process_image(image, image_type)
                processed_images[image_url][image_type] = \
                    await self.__upload_image_to_storage(processed_image, image_type)

        return processed_images
