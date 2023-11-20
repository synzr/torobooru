from core.models import PivixArtwork, PivixUser, URN

from aiohttp import ClientSession
from fake_useragent import FakeUserAgent


class PixivProvider:
    """Pixiv data provider."""

    PIXIV_BASE_URL = "https://www.pixiv.net/"

    PIXIV_ARTWORK_BASE_URL = "https://www.pixiv.net/artworks/{artwork_id}"
    PIXIV_USER_BASE_URL = "https://www.pixiv.net/users/{user_id}"

    PIXIV_AJAX_ARTWORK_URL = "https://www.pixiv.net/ajax/illust/{artwork_id}?full=0"
    PIXIV_AJAX_USER_URL = "https://www.pixiv.net/ajax/user/{user_id}?full=1"

    def __init__(self) -> None:
        """Class constructor."""

        self.__user_agent = FakeUserAgent().random

    async def __fetch_artwork(self, artwork_id: int) -> PivixArtwork | None:
        headers = {"User-Agent": self.__user_agent, "Referer": self.PIXIV_BASE_URL}

        async with ClientSession(headers=headers) as session:
            url = self.PIXIV_AJAX_ARTWORK_URL.format(artwork_id=artwork_id)

            async with session.get(url) as response:
                result = await response.json()
                if result["error"]: return None

                artwork_id = int(result["body"]["illustId"], 10)
                artwork_full_url = self.PIXIV_ARTWORK_BASE_URL.format(artwork_id=artwork_id)
                artwork_title = result["body"]["illustTitle"]
                artwork_comment = result["body"]["illustComment"]
                artwork_hq_image_url = result["body"]["urls"]["regular"]
                artwork_author_id = int(result["body"]["userId"], 10)
                artwork_author_full_url = self.PIXIV_USER_BASE_URL.format(user_id=artwork_author_id)

                return PivixArtwork(
                    artwork_id=artwork_id,
                    artwork_full_url=artwork_full_url,
                    artwork_title=artwork_title,
                    artwork_comment=artwork_comment,
                    artwork_hq_image_url=artwork_hq_image_url,
                    artwork_author_id=artwork_author_id,
                    artwork_author_full_url=artwork_author_full_url
                )

    async def __fetch_user(self, user_id: int) -> PivixUser | None:
        headers = {"User-Agent": self.__user_agent, "Referer": self.PIXIV_BASE_URL}

        async with ClientSession(headers=headers) as session:
            url = self.PIXIV_AJAX_USER_URL.format(user_id=user_id)

            async with session.get(url) as response:
                result = await response.json()
                if result["error"]: return None

                user_id = int(result["body"]["userId"], 10)
                user_full_url = self.PIXIV_USER_BASE_URL.format(user_id=user_id)
                user_name = result["body"]["name"]
                user_hq_avatar_url = result["body"]["imageBig"]
                user_following_count = result["body"]["following"]
                user_twitter_account_url = None

                if result["body"]["social"] and "twitter" in result["body"]["social"]:
                    user_twitter_account_url = result["body"]["social"]["twitter"]["url"]

                return PivixUser(
                    user_id=user_id,
                    user_full_url=user_full_url,
                    user_name=user_name,
                    user_hq_avatar_url=user_hq_avatar_url,
                    user_following_count=user_following_count,
                    user_twitter_account_url=user_twitter_account_url
                )

    async def fetch(self, urn: URN) -> PivixArtwork | PivixUser | None:
        """Fetch the object using an identifier.

        Args:
            urn (URN): URN.

        Returns:
            PivixArtwork: Pivix artwork information.
            PivixUser: Pivix user information.
            None: Nothing.
        """

        if urn.urn_object == "artwork":
            artwork_id = int(urn.urn_identifier, 10)
            return await self.__fetch_artwork(artwork_id)

        if urn.urn_object == "user":
            user_id = int(urn.urn_identifier, 10)
            return await self.__fetch_user(user_id)

        return None
