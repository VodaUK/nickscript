# main.py

import asyncio
from telethon import TelegramClient, events
import config  # Импортируем настройки из config.py

# *** Замените на свои значения из config.py ***
api_id = config.api_id
api_hash = config.api_hash
user_to_notify_username = config.user_to_notify_username
channels_to_track = config.channels_to_track
notification_text = config.notification_text


async def main():
    client = TelegramClient('anon', api_id, api_hash) # 'anon' - имя сессии, можно любое

    await client.start()
    print("Telethon client started")

    # *** Здесь будет основная логика отслеживания каналов и отправки уведомлений ***
    # Пока просто для примера выведем настройки:
    print(f"Отслеживаем каналы: {channels_to_track}")
    print(f"Уведомления отправляем пользователю: {user_to_notify_username}")

    # *** Пример: отправка тестового сообщения (убрать потом) ***
    try:
        await client.send_message(user_to_notify_username, "Бот запущен и готов к работе!")
        print(f"Тестовое сообщение отправлено пользователю {user_to_notify_username}")
    except Exception as e:
        print(f"Ошибка при отправке тестового сообщения: {e}")


    # *** Здесь можно добавить код для отслеживания новых постов и отправки уведомлений ***
    # ...

    await client.run_until_disconnected() # Чтобы клиент работал постоянно


if __name__ == "__main__":
    asyncio.run(main())
