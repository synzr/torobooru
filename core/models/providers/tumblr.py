from dataclasses import dataclass


@dataclass
class TumblrBlog:
    """Tumblr blog information."""

    blog_name: str
    blog_url: str
    blog_title: str
    blog_hq_avatar_url: str


@dataclass
class TumblrPost:
    """Tumblr post information."""

    post_id: int | str
    post_url: str
    post_images: list[str]
    blog_name: str
    blog_url: str
