from dataclasses import dataclass


@dataclass
class TwitterUser:
    """Twitter user information."""

    user_rest_id: str | int
    user_full_url: str
    user_name: str
    user_screen_name: str
    user_follower_count: int
    user_avatar_url: str


@dataclass
class TwitterTweet:
    """Twitter tweet information."""

    tweet_rest_id: str | int
    tweet_full_url: str
    tweet_favorite_count: int
    tweet_retweet_count: int
    tweet_image_urls: list[str]
    tweet_author_user_rest_id: str | int
    tweet_author_screen_name: str
    tweet_author_full_url: str
