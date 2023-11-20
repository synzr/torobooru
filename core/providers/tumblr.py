from core.models import TumblrBlog, TumblrPost, URN

from aiohttp import ClientSession
from fake_useragent import FakeUserAgent

import ujson


class TumblrProvider:
    """Tumblr data provider."""

    TUMBLR_BLOG_URL = "https://www.tumblr.com/{blog_name}/"
    TUMBLR_POST_URL = "https://www.tumblr.com/{blog_name}/{post_id}/"

    def __init__(self) -> None:
        """Class constructor."""

        self.__user_agent = FakeUserAgent().random

    async def __get_initial_state(self, url: str) -> dict | None:
        headers = {"User-Agent": self.__user_agent}

        async with ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                response_data = await response.text()

                initial_state = response_data \
                    .split("window[\'___INITIAL_STATE___\'] = ")[-1] \
                    .split("};")[0] \
                    .replace("undefined", '"undefined"') + "}"
                initial_state = ujson.loads(initial_state)

                return initial_state

    async def __fetch_blog(self, blog_name: str) -> TumblrBlog | None:
        url = self.TUMBLR_BLOG_URL.format(blog_name=blog_name)
        initial_state = await self.__get_initial_state(url)

        if not initial_state:
            return None

        blog = initial_state["queries"]["queries"][-1]["state"]["data"]

        blog_name = blog["name"]
        blog_url = blog["blogViewUrl"]
        blog_title = blog["title"]
        blog_hq_avatar_url = blog["avatar"][0]["url"]

        return TumblrBlog(
            blog_name=blog_name,
            blog_url=blog_url,
            blog_title=blog_title,
            blog_hq_avatar_url=blog_hq_avatar_url
        )

    async def __fetch_post(self, post_id: int, blog_name: str) -> TumblrPost | None:
        url = self.TUMBLR_POST_URL.format(blog_name=blog_name, post_id=post_id)
        initial_state = await self.__get_initial_state(url)

        if not initial_state:
            return None

        post = initial_state["PeeprRoute"]["initialTimeline"]["objects"][0]

        post_id = int(post["idString"], 10)
        post_url = post["postUrl"]
        post_images = []
        blog_name = post["blogName"]
        blog_url = post["blog"]["blogViewUrl"]

        for content in post["content"]:
            if content["type"] != "image":
                continue

            post_images.append(content["media"][0]["url"])

        return TumblrPost(
            post_id=post_id,
            post_url=post_url,
            post_images=post_images,
            blog_name=blog_name,
            blog_url=blog_url
        )

    async def fetch(self, urn: URN) -> TumblrBlog | TumblrPost | None:
        """Fetch the object using an identifier.

        Args:
            urn (URN): URN.

        Returns:
            TumblrBlog: Tumblr blog information.
            TumblrPost: Tumblr post information.
            None: Nothing.
        """

        if urn.urn_object == "blog":
            return await self.__fetch_blog(urn.urn_identifier)

        if urn.urn_object == "post":
            post_id = int(urn.urn_identifier, 10)
            return await self.__fetch_post(post_id, blog_name=urn.urn_extra_fields["blog_name"])

        return None
