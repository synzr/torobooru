from core.models import TwitterUser, TwitterTweet, URN

from aiohttp import ClientSession
from fake_useragent import FakeUserAgent

import ujson
import logging


class TwitterProvider:
    """Twitter data provider."""

    TWITTER_GUEST_ACTIVATE_URL = "https://api.twitter.com/1.1/guest/activate.json"

    TWITTER_TWEET_RESULT_BY_REST_ID_URL = "https://api.twitter.com/graphql/5GOHgZe-8U2j5sVHQzEm9A/TweetResultByRestId"
    TWITTER_USER_BY_SCREEN_NAME_URL = "https://api.twitter.com/graphql/G3KGOASz96M-Qu0nwmGXNg/UserByScreenName"

    TWITTER_TWEET_FULL_URL = "https://x.com/i/status/{tweet_rest_id}"
    TWITTER_USER_FULL_URL ="https://x.com/{screen_name}/"

    TWITTER_DEFAULT_HEADERS = {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "accept-language": "en"
    }

    TWITTER_DEFAULT_FEATURES = {
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "tweetypie_unmention_optimization_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": False,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_home_pinned_timelines_enabled": True,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "responsive_web_media_download_video_enabled": False,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_enhance_cards_enabled": False,
        "hidden_profile_likes_enabled": True,
        "hidden_profile_subscriptions_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "subscriptions_verification_info_is_identity_verified_enabled": True,
        "subscriptions_verification_info_verified_since_enabled": True,
        "highlights_tweets_tab_ui_enabled": True,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "responsive_web_graphql_timeline_navigation_enabled": True
    }
    TWITTER_DEFAULT_VARIABLES = {
        "withCommunity": False,
        "includePromotedContent": False,
        "withVoice": False
    }

    def __init__(self) -> None:
        """Class constructor."""

        self.__user_agent = FakeUserAgent().random
        self.__logger = logging.getLogger("core.providers.twitter")

    async def __activate_guest_session(self, session: ClientSession) -> bool:
        session.headers["user-agent"] = self.__user_agent
        session.headers.update(self.TWITTER_DEFAULT_HEADERS)

        async with session.post(self.TWITTER_GUEST_ACTIVATE_URL) as response:
            if response.status != 200:
                return False

            result = await response.json()
            guest_token = result["guest_token"]

            session.headers.update({
                "content-type": "application/json",
                "x-guest-token": guest_token,
                "x-twitter-active-user": "yes"
            })
            session.cookie_jar.update_cookies({"guest_id": "v1%3A" + guest_token})

            self.__logger.info(f"__activate_guest_session(session={session}): Guest session activation successful")
            return True

    async def __fetch_user(self, screen_name: str) -> TwitterUser | None:
        async with ClientSession() as session:
            if not await self.__activate_guest_session(session):
                return None

            variables = {"screen_name": screen_name}
            variables.update(self.TWITTER_DEFAULT_VARIABLES)

            params = {
                "variables": ujson.dumps(variables),
                "features": ujson.dumps(self.TWITTER_DEFAULT_FEATURES)
            }

            async with session.get(self.TWITTER_USER_BY_SCREEN_NAME_URL, params=params) as response:
                if response.status != 200:
                    print(await response.text())
                    return None

                result = await response.json()

                if result["data"]["user"]["result"]["__typename"] != "User":
                    return None

                base_user = result["data"]["user"]["result"]["legacy"]

                user_rest_id = int(result["data"]["user"]["result"]["rest_id"], 10)
                user_full_url = self.TWITTER_USER_FULL_URL.format(screen_name=base_user["screen_name"])
                user_name = base_user["name"]
                user_screen_name = base_user["screen_name"]
                user_follower_count = base_user["followers_count"]
                user_avatar_url = base_user["profile_image_url_https"]

                self.__logger.info(f"__fetch_user(screen_name={screen_name}): Received user {user_name} ({user_full_url})")

                return TwitterUser(
                    user_rest_id=user_rest_id,
                    user_full_url=user_full_url,
                    user_name=user_name,
                    user_screen_name=user_screen_name,
                    user_follower_count=user_follower_count,
                    user_avatar_url=user_avatar_url
                )

    async def __fetch_tweet(self, tweet_rest_id: int) -> TwitterTweet | None:
        async with ClientSession(headers={"User-Agent": self.__user_agent}) as session:
            if not await self.__activate_guest_session(session):
                return None

            variables = {"tweetId": tweet_rest_id}
            variables.update(self.TWITTER_DEFAULT_VARIABLES)

            params = {
                "variables": ujson.dumps(variables),
                "features": ujson.dumps(self.TWITTER_DEFAULT_FEATURES)
            }

            async with session.get(self.TWITTER_TWEET_RESULT_BY_REST_ID_URL, params=params) as response:
                if response.status != 200:
                    return None

                result = await response.json()

                if result["data"]["tweetResult"]["result"]["__typename"] != "Tweet":
                    return None

                base_user = result["data"]["tweetResult"]["result"]["core"]["user_results"]["result"]
                base_tweet = result["data"]["tweetResult"]["result"]["legacy"]

                base_media = []

                if base_tweet.get("retweeted_status_result"):
                    base_media = base_tweet["retweeted_status_result"]["result"]["legacy"]["extended_entities"]

                if base_tweet["extended_entities"].get("media"):
                    base_media = base_tweet["extended_entities"]["media"]

                tweet_rest_id = int(base_tweet["id_str"], 10)
                tweet_full_url = self.TWITTER_TWEET_FULL_URL.format(tweet_rest_id=tweet_rest_id)
                tweet_favorite_count = base_tweet["favorite_count"]
                tweet_retweet_count = base_tweet["retweet_count"]
                tweet_image_urls = []
                tweet_author_user_rest_id = int(base_user["rest_id"], 10)
                tweet_author_screen_name = base_user["legacy"]["screen_name"]
                tweet_author_full_url = self.TWITTER_USER_FULL_URL.format(screen_name=tweet_author_screen_name)

                for media_entity in base_media:
                    if media_entity["type"] != "photo":
                        continue

                    tweet_image_urls.append(media_entity["media_url_https"])

                self.__logger.info(f"__fetch_tweet(tweet_rest_id={tweet_rest_id}): Received tweet {tweet_rest_id} ({tweet_full_url})")

                return TwitterTweet(
                    tweet_rest_id=tweet_rest_id,
                    tweet_full_url=tweet_full_url,
                    tweet_favorite_count=tweet_favorite_count,
                    tweet_retweet_count=tweet_retweet_count,
                    tweet_image_urls=tweet_image_urls,
                    tweet_author_user_rest_id=tweet_author_user_rest_id,
                    tweet_author_screen_name=tweet_author_screen_name,
                    tweet_author_full_url=tweet_author_full_url
                )

    async def fetch(self, urn: URN) -> TwitterUser | TwitterTweet | None:
        """Fetch the object using an identifier.

        Args:
            urn (URN): URN.

        Returns:
            TwitterUser: Twitter user information.
            TwitterTweet: Twitter tweet information.
            None: Nothing.
        """

        if urn.urn_object == "user":
            return await self.__fetch_user(urn.urn_identifier)

        if urn.urn_object == "tweet":
            tweet_rest_id = int(urn.urn_identifier, 10)
            return await self.__fetch_tweet(tweet_rest_id)

        logging.error(f"fetch(urn={urn}): Can't receive this object")
        return None
