import re
import logging

from atproto_client.models.app.bsky.feed.defs import PostView

from mdfb.core.models import EnrichedPost
from atproto_client.models.app.bsky.actor.defs import ProfileViewBasic
import atproto_client
from atproto_client import models

class PostParser:

    @staticmethod
    def parse_post(post: PostView, seen_uris: set, logger: logging.Logger) -> EnrichedPost:
        uri = post.uri

        seen_uris.add(uri)
        post_details = PostParser._extract_post_details(post)

        logger.info("Post details retrieved for URI: %s", uri)
        return post_details

    @staticmethod
    def _extract_media(
        embed: atproto_client.models.app.bsky.embed.external.Main | 
               atproto_client.models.app.bsky.embed.images.Main | 
               atproto_client.models.app.bsky.embed.video.Main | 
               atproto_client.models.app.bsky.embed.gallery.Main | 
               atproto_client.models.app.bsky.embed.record.Main | 
               atproto_client.models.app.bsky.embed.record_with_media.Main 
               | None
        ) -> dict:
        media_links = {"media_type": [], "mime_type": ""}

        if isinstance(embed, models.AppBskyEmbedImages.Main):
            media_links.setdefault("images_cid", []).extend(
                str(image.image.cid) for image in embed.images
            )
            media_links["media_type"].extend(["image"] * len(embed.images))
            media_links["mime_type"] = embed.images[0].image.mime_type
        elif isinstance(embed, models.AppBskyEmbedVideo.Main):
            media_links.setdefault("video_cids", []).append(str(embed.video.cid))
            media_links["media_type"].append("video")
            media_links["mime_type"] = embed.video.mime_type
        elif isinstance(embed, models.AppBskyEmbedGallery.Main):
            media_links.setdefault("images_cid", []).extend(
                str(image.image.cid) for image in embed.items
            )
            media_links["media_type"].extend(["image"] * len(embed.items))
            media_links["mime_type"] = embed.items[0].image.mime_type
        elif isinstance(embed, models.AppBskyEmbedRecordWithMedia.Main):
            media_links = PostParser._extract_media(embed.media)
        else:
            media_links["media_type"].append("text")
        return media_links

    @staticmethod
    def _get_rkey(at_uri: str) -> str:
        match = re.search(r"\w+$", at_uri)
        return match.group()

    @staticmethod
    def _get_author_details(author: ProfileViewBasic) -> dict:
        author_details = {}
        author_details["did"] = author.did
        author_details["handle"] = author.handle
        author_details["display_name"] = author.display_name
        return author_details

    @staticmethod
    def _extract_post_details(post: PostView) -> EnrichedPost:
        post_details = {
            "rkey": PostParser._get_rkey(post.uri),
            "text": post.record.text,
            **PostParser._get_author_details(post.author),
            **(PostParser._extract_media(post.record.embed) if post.record.embed else {"media_type": ["text"]})
        }

        enriched_post = EnrichedPost(
            response=post,
            **post_details
        )

        # Optional only because the FetchFeedDetails class cannot get these values, and they are used in the database as
        # the columns. Thus, you cannot add any of the post retrieved from feed to the database
        optional_fields = ["user_did", "user_post_uri", "poster_post_uri", "feed_type"]
        for field in optional_fields:
            if getattr(enriched_post, field, None):
                post_details[field] = getattr(enriched_post, field, None)

        return enriched_post

    @staticmethod
    def _extract_cursor(uri: str) -> str:
        match = re.search(r"\w+$", uri)
        return match[0] if match else ""

    @staticmethod
    def _create_post_identifier(feed_type: str, did: str, record: dict) -> dict:
        if feed_type == "post":
            uri = record["uri"]
        else:
            uri = record["value"]["subject"]["uri"]

        uris = {
            "user_did": did,
            "user_post_uri": [record["uri"]],
            "feed_type": [feed_type],
            "poster_post_uri": uri,
        }
        return uris

    @staticmethod
    def _extract_handle(feed_url: str) -> str:
        """Extracts just the handle."""
        pattern = r'https://bsky\.app/profile/([^/]+)/feed/[^/]+'
        match = re.search(pattern, feed_url)
        return match.group(1)

    @staticmethod
    def _extract_feed_name(feed_url: str) -> str:
        """Extracts just the feed name."""
        pattern = r'https://bsky\.app/profile/[^/]+/feed/([^/]+)'
        match = re.search(pattern, feed_url)
        return match.group(1)
