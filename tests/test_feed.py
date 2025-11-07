from atproto import Client
import os
from dotenv import load_dotenv
import json 
from time import sleep

load_dotenv()

# Create a client instance
client = Client()

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

# Optional: Login if you need authenticated access
client.login(USERNAME, PASSWORD)

next_page = ""

for _ in range(3):
    # Get the feed
    data = client.app.bsky.feed.get_feed({
        'feed': 'at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot',
        'limit': 30,
        'cursor': next_page
    })

    feed = data.feed
    next_page = data.cursor

    print(json.dumps(json.loads(data.model_dump_json())["feed"][0], indent=4))
# print(next_page)






