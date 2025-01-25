# config.py

# *** Замените на свои значения после получения с my.telegram.org/apps ***
api_id = "YOUR_API_ID"
api_hash = "YOUR_API_HASH"

# *** ID или username пользователя, которому будут отправляться уведомления ***
user_to_notify_username = "@username_получателя"  # Или user_to_notify_id = 123456789

# *** Список каналов для отслеживания (username или ID) ***
channels_to_track = [
    "название_канала_1",
    "название_канала_2",
    # Можно добавить еще каналы
]

# *** Текст уведомления ***
notification_text = "Новый пост в канале {channel_name}:\n\n{post_text}\n\nСсылка: {post_link}"
