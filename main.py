import asyncio
from telethon import TelegramClient, events
import config

api_id = config.api_id
api_hash = config.api_hash
user_to_notify_username = config.user_to_notify_username
channels_to_track = config.channels_to_track
notification_text = config.notification_text

async def main():
    client = TelegramClient('anon', api_id, api_hash)

    await client.start()
    print("Telethon client started")

    print(f"Отслеживаем каналы: {channels_to_track}")
    print(f"Уведомления отправляем пользователю: {user_to_notify_username}")

    try:
        await client.send_message(user_to_notify_username, "Бот запущен и готов к работе!")
        print(f"Тестовое сообщение отправлено пользователю {user_to_notify_username}")
    except Exception as e:
        print(f"Ошибка при отправке тестового сообщения: {e}")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
