import os

api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")

user_to_notify_username = "@rodionmurzo"

channels_to_track = [
    "@exposergmd",
]

notification_text = "{post_link}"
