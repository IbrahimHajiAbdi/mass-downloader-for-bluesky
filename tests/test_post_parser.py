import logging

from atproto_client.models import AppBskyEmbedImages, AppBskyEmbedVideo
from atproto_client.models.app.bsky.actor.defs import ProfileViewBasic

from mdfb.core.models import EnrichedPost
from mdfb.core.post_parser import PostParser
from tests.helpers import load_fixture_json, load_postview

IMAGE_CID = "bafkreiamy7yinrdcqrqtka4xwhhkbcblv4zxudjlupslnuamzm6tbxofze"
VIDEO_CID = "bafkreic5qzdlpdt6gqakxzx27lsp6phmltk2fv6bpyfleoumo4nxytvleq"


class TestExtractMedia:
    def test_extract_media_image(self):
        embed = AppBskyEmbedImages.Main.model_validate(load_fixture_json("post_image")["record"]["embed"])
        assert PostParser._extract_media(embed) == {
            "media_type": ["image"],
            "mime_type": "image/jpeg",
            "images_cid": [IMAGE_CID],
        }

    def test_extract_media_video(self):
        embed = AppBskyEmbedVideo.Main.model_validate(load_fixture_json("post_video")["record"]["embed"])
        assert PostParser._extract_media(embed) == {
            "media_type": ["video"],
            "mime_type": "video/mp4",
            "video_cids": [VIDEO_CID],
        }

    def test_extract_media_text(self):
        # A non-media embed (or None) falls through to a text post.
        assert PostParser._extract_media(None) == {"media_type": ["text"], "mime_type": ""}


class TestPostParserUtils:
    def test_get_rkey(self):
        uri = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3lax5zxh7bc2p"
        assert PostParser._get_rkey(uri) == "3lax5zxh7bc2p"

    def test_extract_cursor(self):
        uri = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3lax5zxh7bc2p"
        assert PostParser.extract_cursor(uri) == "3lax5zxh7bc2p"

    def test_get_author_details(self):
        author = ProfileViewBasic.model_validate(load_fixture_json("post_image")["author"])
        assert PostParser._get_author_details(author) == {
            "did": "did:plc:3eatnvb2dim4l7fiwln5wow6",
            "handle": "dailybunnies.bsky.social",
            "display_name": "daily bunnies",
        }


class TestParsePost:
    def test_parse_post_text(self):
        post = load_postview("post_text")
        seen = set()
        result = PostParser.parse_post(post, seen, logging.getLogger("test"))

        assert isinstance(result, EnrichedPost)
        assert result.did == "did:plc:vc7f4oafdgxsihk4cry2xpze"
        assert result.handle == "jcsalterego.bsky.social"
        assert result.media_type == ["text"]
        assert post.uri in seen

    def test_parse_post_image_records_media(self):
        post = load_postview("post_image")
        result = PostParser.parse_post(post, set(), logging.getLogger("test"))

        assert result.media_type == ["image"]
        assert result.images_cid == [IMAGE_CID]
        assert result.mime_type == "image/jpeg"


class TestFilterMediaTypes:
    def _post(self, media_type):
        return EnrichedPost(
            response=load_postview("post_text"),
            did="d",
            rkey="r",
            text="t",
            handle="h",
            media_type=media_type,
        )

    def test_filter_keeps_matching(self):
        posts = [self._post(["image"]), self._post(["text"]), self._post(["video"])]
        result = PostParser.filter_media_types(posts, ["image", "video"])
        assert [p.media_type for p in result] == [["image"], ["video"]]

    def test_filter_drops_all(self):
        posts = [self._post(["text"])]
        assert PostParser.filter_media_types(posts, ["image"]) == []
