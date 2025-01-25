import asyncio
from telethon import TelegramClient, events
import config

api_id = config.api_id
api_hash = config.api_hash
channels_to_track = config.channels_to_track
notification_text = config.notification_text

notify_user_username = config.user_to_notify_username
admin_username = "@lumohn"

async def main():
    client = TelegramClient('anon', api_id, api_hash)
    await client.start()
    print("Telethon client started")
    print(f"Отслеживаем каналы (начальные): {channels_to_track}")
    print(f"Уведомления отправляем пользователю (начальный): {notify_user_username}")
    try:
        await client.send_message(notify_user_username, "Бот запущен и готов к работе!")
        print(f"Тестовое сообщение отправлено пользователю {notify_user_username}")
    except Exception as e:
        print(f"Ошибка при отправке тестового сообщения: {e}")

    @client.on(events.NewMessage(chats=channels_to_track))
    async def new_message_handler(event):
        channel = await event.get_chat()
        channel_username = channel.username if channel.username else channel.title
        post_link = f"https://t.me/{channel_username}/{event.message.id}"
        formatted_notification_text = notification_text.format(
            channel_name=channel.title,
            post_link=post_link
        )
        try:
            await client.send_message(notify_user_username, formatted_notification_text)
            print(f"Отправлено уведомление о новом посте из канала {channel.title} пользователю {notify_user_username}")
        except Exception as e:
            print(f"Ошибка при отправке уведомления: {e}")

    @client.on(events.NewMessage(pattern='/set_notify_user '))
    async def set_notify_user_command_handler(event):
        if event.sender.username == admin_username.lstrip('@'):
            username = event.message.message.split(' ')[1]
            global notify_user_username
            notify_user_username = username
            await event.respond(f"Имя пользователя для уведомлений изменено на: {notify_user_username}")
            print(f"Имя пользователя для уведомлений изменено на: {notify_user_username} (команда от {admin_username})")
        else:
            await event.respond("У вас нет прав на выполнение этой команды.")
            print(f"Попытка выполнить команду /set_notify_user от не-админа: {event.sender.username}")

    @client.on(events.NewMessage(pattern='/get_settings'))
    async def get_settings_command_handler(event):
        if event.sender.username == admin_username.lstrip('@'):
            settings_text = f"Текущие настройки:\n" \
                          f"- Пользователь для уведомлений: {notify_user_username}\n" \
                          f"- Отслеживаемые каналы: {channels_to_track}\n" \
                          f"- Текст уведомления: {notification_text}"
            await event.respond(settings_text)
            print(f"Отправлены текущие настройки пользователю {admin_username} (команда)")
        else:
            await event.respond("У вас нет прав на выполнение этой команды.")
            print(f"Попытка выполнить команду /get_settings от не-админа: {event.sender.username}")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
