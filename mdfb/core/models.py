from pydantic import BaseModel
from atproto_client.models.app.bsky.feed.defs import PostView

class EnrichedPost(BaseModel):
    response: PostView
    did: str 
    rkey: str 
    text: str 
    handle: str 
    display_name: str 
    media_type: list[str] = []
    images_cid: list[str] = []
    video_cids: list[str] = []
    mime_type: str | None = None
    user_did: str | None = None
    user_post_uri: list[str] | None = None
    poster_post_uri: str | None = None
    feed_type: list[str] | None = None
