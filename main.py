import asyncio
import logging
from datetime import timedelta
import pytz  # Библиотека для работы с часовыми поясами
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from telethon import TelegramClient, events
import config

API_ID = config.api_id
API_HASH = config.api_hash
BOT_TOKEN = config.bot_token
ADMIN_USERNAMES = config.admin_usernames # Список админов из config

notify_user_username = config.user_to_notify_username
channels_to_track = config.channels_to_track[:]
notification_text = config.notification_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
telethon_client = TelegramClient('anon', API_ID, API_HASH)
msk_timezone = pytz.timezone('Europe/Moscow') # Часовой пояс Москвы

class SettingsForm(StatesGroup):
    notify_user = State()

class SettingsMenuCallback(types.InlineCallbackData, prefix="settings_menu"):
    action: str

settings_menu_callback = SettingsMenuCallback.as_markup()

def create_settings_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Изменить пользователя", callback_data=SettingsMenuCallback(action="notify_user"))
    builder.button(text="Каналы (скоро)", callback_data=SettingsMenuCallback(action="channels"))
    builder.button(text="Текст (скоро)", callback_data=SettingsMenuCallback(action="notification_text"))
    builder.adjust(1)
    return builder.as_markup()

def is_admin(username: str) -> bool:
    return username in ADMIN_USERNAMES

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    user_username = message.from_user.username
    if not user_username or not is_admin(user_username):
        await message.answer("Доступ запрещен.")
        return
    await message.answer(f"Привет, {message.from_user.full_name}!\nЯ бот для отслеживания каналов.\nИспользуй /settings для настройки.")

@dp.message(commands=["settings"])
async def command_settings_handler(message: types.Message) -> None:
    user_username = message.from_user.username
    if not user_username or not is_admin(user_username):
        await message.answer("Доступ запрещен.")
        return
    keyboard = create_settings_keyboard()
    await message.answer("⚙️ Настройки бота:", reply_markup=keyboard)

@dp.callback_query(SettingsMenuCallback.filter(F.action == "notify_user"))
async def settings_notify_user_callback_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True) # Alert вместо обычного ответа
        return
    await query.message.edit_text("Введите имя пользователя для уведомлений (например, @username):")
    await state.set_state(SettingsForm.notify_user)
    await query.answer()

@dp.message(StateFilter(SettingsForm.notify_user))
async def process_notify_user_input(message: types.Message, state: FSMContext) -> None:
    user_username = message.from_user.username
    if not user_username or not is_admin(user_username):
        await message.answer("Доступ запрещен.")
        await state.clear() # Сброс состояния на всякий случай
        return
    global notify_user_username
    username = message.text.strip()
    if username.startswith('@'):
        notify_user_username = username
        await state.clear()
        keyboard = create_settings_keyboard()
        await message.answer(f"✅ Пользователь изменен на: {notify_user_username}", reply_markup=keyboard)
        await message.delete()
    else:
        await message.answer("Неверный формат. Начните с '@'. Введите еще раз:")

@dp.callback_query(SettingsMenuCallback.filter(F.action == "channels"))
async def settings_channels_callback_handler(query: types.CallbackQuery) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    await query.answer("Раздел в разработке")
    await query.message.edit_text("Каналы (скоро):", reply_markup=create_settings_keyboard())

@dp.callback_query(SettingsMenuCallback.filter(F.action == "notification_text"))
async def settings_notification_text_callback_handler(query: types.CallbackQuery) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    await query.answer("Раздел в разработке")
    await query.message.edit_text("Текст (скоро):", reply_markup=create_settings_keyboard())

@telethon_client.on(events.NewMessage(chats=channels_to_track))
async def telethon_new_message_handler(event):
    channel = await event.get_chat()
    channel_username = channel.username if channel.username else channel.title
    post_link = f"https://t.me/{channel_username}/{event.message.id}"
    post_time_utc = event.message.date
    post_time_msk = post_time_utc.astimezone(msk_timezone) # Конвертация в МСК с pytz
    post_time_formatted = post_time_msk.strftime("%d.%m.%Y %H:%M:%S")

    formatted_notification_text = f"""
    *--------------------*
    📢  {channel.title}
    ⏱️  {post_time_formatted} (МСК)
    *--------------------*
    {post_link}
    *--------------------*
    """
    try:
        await telethon_client.send_message(notify_user_username, formatted_notification_text, parse_mode='markdown') # Markdown для обводки
        logger.info(f"Уведомление из {channel.title} -> {notify_user_username}")
    except Exception as e:
        logger.error(f"Ошибка уведомления: {e}")

async def main():
    logger.info("Запуск бота и Telethon клиента")
    await asyncio.gather(
        dp.start_polling(bot),
        telethon_client.start(bot_token=BOT_TOKEN),
        telethon_client.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())
