from atproto_client.models.app.bsky.feed.defs import PostView
from pydantic import BaseModel


class EnrichedPost(BaseModel):
    response: PostView
    did: str
    rkey: str
    text: str
    handle: str
    display_name: str | None = None
    media_type: list[str] = []
    images_cid: list[str] = []
    video_cids: list[str] = []
    mime_type: str | None = None
    user_did: str | None = None
    user_post_uri: list[str] | None = None
    poster_post_uri: str | None = None
    feed_type: list[str] | None = None
