import os

api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")

user_to_notify_username = "@rodionmurzo"

channels_to_track = [
    "@exposergmd",
]

notification_text = "Новый пост в канале {channel_name}:\n\n{post_text}\n\nСсылка: {post_link}"
