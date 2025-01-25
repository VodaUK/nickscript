import asyncio
import logging
import signal
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.callback_data import CallbackData
import config
import pytz
from datetime import timedelta
from aiogram.exceptions import TelegramBadRequest

API_ID = config.api_id
API_HASH = config.api_hash
BOT_TOKEN = config.bot_token
ADMIN_USERNAMES = config.admin_usernames
notify_users_usernames = config.notify_users_usernames
channels_to_track = config.channels_to_track
notification_text = config.notification_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
telethon_client = TelegramClient("anon", API_ID, API_HASH)
msk_timezone = pytz.timezone('Europe/Moscow')

class MenuCallback(CallbackData, prefix="menu"):
    category: str
    action: str = "main"

class UserForm(StatesGroup):
    add_user = State()
    remove_user = State()

class ChannelForm(StatesGroup):
    add_channel = State()
    remove_channel = State()
    cancel_channel = State()

class TextForm(StatesGroup):
    edit_text = State()
    cancel_text = State()

def create_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Пользователи", callback_data=MenuCallback(category="users"))
    builder.button(text="Каналы", callback_data=MenuCallback(category="channels"))
    builder.button(text="Текст", callback_data=MenuCallback(category="text"))
    builder.button(text="Настройки", callback_data=MenuCallback(category="settings"))
    builder.adjust(1)
    return builder.as_markup()

def create_users_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить пользователя", callback_data=MenuCallback(category="users", action="add"))
    builder.button(text="Удалить пользователя", callback_data=MenuCallback(category="users", action="remove"))
    builder.button(text="Назад", callback_data=MenuCallback(category="main"))
    builder.adjust(1)
    return builder.as_markup()

def create_channels_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить канал", callback_data=MenuCallback(category="channels", action="add"))
    builder.button(text="Удалить канал", callback_data=MenuCallback(category="channels", action="remove"))
    builder.button(text="Назад", callback_data=MenuCallback(category="main"))
    builder.adjust(1)
    return builder.as_markup()

def create_text_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Изменить текст", callback_data=MenuCallback(category="text", action="edit"))
    builder.button(text="Назад", callback_data=MenuCallback(category="main"))
    builder.adjust(1)
    return builder.as_markup()

def create_settings_keyboard():
    builder = InlineKeyboardBuilder() # Используем InlineKeyboardBuilder
    current_users_display = ", ".join(config.notify_users_usernames) if config.notify_users_usernames else "Не заданы"
    current_channels_display = ", ".join(channels_to_track) if channels_to_track else "Не заданы"
    builder.button(text=f"Пользователи: {current_users_display}", callback_data=MenuCallback(category="users"))
    builder.button(text=f"Каналы: {current_channels_display}", callback_data=MenuCallback(category="channels"))
    builder.button(text=f"Текст: {notification_text}", callback_data=MenuCallback(category="text"))
    builder.button(text="Назад", callback_data=MenuCallback(category="main"))
    builder.adjust(1)
    return builder.as_markup() # Возвращаем клавиатуру, созданную билдером

def create_back_to_channels_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data=MenuCallback(category="channels"))
    builder.adjust(1)
    return builder.as_markup()

def create_cancel_keyboard(category):
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data=MenuCallback(category=category))
    builder.adjust(1)
    return builder.as_markup()

def is_admin(username: str) -> bool:
    return username in ADMIN_USERNAMES

telethon_new_message_handler = None # Declare it globally, initially None

async def update_telethon_channels():
    global telethon_new_message_handler # Indicate we're modifying the global variable
    logger.info(f"Выполняется update_telethon_channels(), текущие каналы: {channels_to_track}") # <--- ЛОГ
    if telethon_new_message_handler: # Check if handler is already set before trying to remove
        telethon_client.remove_event_handler(telethon_new_message_handler)

    @telethon_client.on(events.NewMessage(chats=channels_to_track))
    async def telethon_new_message_handler(event): # Now this is correctly re-assigned to the global name
        channel = await event.get_chat()
        channel_username = channel.username if channel.username else channel.title
        post_link = f"https://t.me/{channel_username}/{event.message.id}"
        formatted_notification_text = f"""{notification_text}

------------

{post_link}
"""
        for username in config.notify_users_usernames: # Итерируемся по списку пользователей
            try:
                await telethon_client.send_message(username, formatted_notification_text, parse_mode='markdown') # Отправляем каждому пользователю
                logger.info(f"Уведомление из {channel.title} -> {username}")
            except Exception as e:
                logger.error(f"Ошибка уведомления для пользователя {username}: {e}")


@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    user_username = message.from_user.username
    if not user_username or not is_admin(user_username):
        await message.answer("Доступ запрещен.")
        return
    keyboard = create_main_keyboard()
    await message.answer("Настройки бота:", reply_markup=keyboard)

@dp.callback_query(MenuCallback.filter(F.category == "main"))
async def main_menu_callback_handler(query: types.CallbackQuery) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    keyboard = create_main_keyboard()
    await query.message.edit_text("Настройки бота:", reply_markup=keyboard)
    await query.answer()

@dp.callback_query(MenuCallback.filter(F.category == "users"))
async def users_menu_callback_handler(query: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    if callback_data.action == "add":
        await query.message.edit_text("Введите username пользователя для добавления (например, @username):", reply_markup=create_cancel_keyboard("users"))
        await state.set_state(UserForm.add_user)
        await query.answer()
    elif callback_data.action == "remove":
        if not config.notify_users_usernames: # Проверяем, есть ли пользователи для удаления
            await query.message.edit_text("Не добавлено ни одного пользователя.", reply_markup=create_users_keyboard())
            await query.answer()
            return
        current_users = "\n".join([f"{i+1}. {user}" for i, user in enumerate(config.notify_users_usernames)]) # Отображаем список пользователей
        keyboard = InlineKeyboardBuilder()
        for i, user in enumerate(config.notify_users_usernames):
            keyboard.button(text=f"Удалить {user}", callback_data=MenuCallback(category="users", action=f"remove_user_item_{i}")) # Кнопки для удаления каждого пользователя
        keyboard.button(text="Назад", callback_data=MenuCallback(category="users"))
        keyboard.adjust(1)
        await query.message.edit_text(f"Выберите пользователя для удаления:\n{current_users}", reply_markup=keyboard.as_markup())
        await query.answer()
    else: # Действие по умолчанию - показать список пользователей
        current_users_display = ", ".join(config.notify_users_usernames) if config.notify_users_usernames else "Не заданы"
        keyboard = create_users_keyboard()
        await query.message.edit_text(f"Текущие пользователи: {current_users_display}", reply_markup=keyboard) # Показываем список пользователей
        await query.answer()

@dp.callback_query(lambda query: query.data and MenuCallback.unpack(query.data).category == "users" and MenuCallback.unpack(query.data).action.startswith("remove_user_item_"))
async def process_remove_user_callback_handler(query: types.CallbackQuery) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    callback_data = MenuCallback.unpack(query.data)
    index_str = callback_data.action.split("_")[-1] # Получаем индекс как строку
    logger.info(f"process_remove_user_callback_handler: action={callback_data.action}, index_str={index_str}") # ЛОГ
    try:
        index = int(index_str) # Пытаемся преобразовать в int
    except ValueError:
        logger.error(f"process_remove_user_callback_handler: Ошибка преобразования индекса в int: index_str={index_str}") # ЛОГ ошибки
        await query.message.edit_text("Ошибка: неверный индекс пользователя.", reply_markup=create_users_keyboard())
        await query.answer()
        return

    logger.info(f"process_remove_user_callback_handler: index={index}, notify_users_usernames до удаления: {config.notify_users_usernames}")
    if 0 <= index < len(config.notify_users_usernames):
        removed_user = config.notify_users_usernames.pop(index)
        logger.info(f"process_remove_user_callback_handler: Пользователь {removed_user} удален из notify_users_usernames, notify_users_usernames после удаления: {config.notify_users_usernames}")
        current_users_str = ", ".join(config.notify_users_usernames) if config.notify_users_usernames else "Не заданы"
        keyboard = create_users_keyboard()
        await query.message.edit_text(f"Пользователь {removed_user} удален.\nТекущие пользователи: {current_users_str}", reply_markup=keyboard)
    else:
        logger.warning(f"process_remove_user_callback_handler: Неверный индекс пользователя для удаления: {index}, notify_users_usernames: {config.notify_users_usernames}")
        await query.message.edit_text("Неверный выбор.", reply_markup=create_users_keyboard())
    await query.answer()

@dp.message(StateFilter(UserForm.add_user))
async def process_add_user_input(message: types.Message, state: FSMContext) -> None:
    user_username = message.from_user.username
    if not user_username or not is_admin(user_username):
        await message.answer("Доступ запрещен.")
        await state.clear()
        return
    username = message.text.strip()
    if username.startswith('@'):
        if username in config.notify_users_usernames: # Проверяем, не добавлен ли уже пользователь
            await message.answer("Пользователь уже добавлен.", reply_markup=create_users_keyboard())
        else:
            config.notify_users_usernames.append(username) # Добавляем пользователя в список
            await state.clear()
            keyboard = create_users_keyboard()
            await message.answer(f"Пользователь {username} добавлен.", reply_markup=keyboard)
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
    else:
        await message.answer("Неверный формат. Начните с '@'. Введите еще раз:", reply_markup=create_cancel_keyboard("users"))
        try:
            await message.delete()
        except TelegramBadRequest:
            pass

@dp.callback_query(MenuCallback.filter(F.category == "channels"))
async def channels_menu_callback_handler(query: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    if callback_data.action == "add":
        await query.message.edit_text("Введите username канала (например, @channelname):", reply_markup=create_cancel_keyboard("channels"))
        await state.set_state(ChannelForm.add_channel)
        await query.answer()
    elif callback_data.action == "remove":
        if not channels_to_track:
            await query.message.edit_text("Не добавлено ни одного канала.", reply_markup=create_back_to_channels_keyboard())
            await query.answer()
            return
        current_channels = "\n".join([f"{i+1}. {channel}" for i, channel in enumerate(channels_to_track)])
        keyboard = InlineKeyboardBuilder()
        for i, channel in enumerate(channels_to_track):
            keyboard.button(text=f"Удалить {channel}", callback_data=MenuCallback(category="channels", action=f"remove_item_{i}"))
        keyboard.button(text="Назад", callback_data=MenuCallback(category="channels"))
        keyboard.adjust(1)
        await query.message.edit_text(f"Выберите канал для удаления:\n{current_channels}", reply_markup=keyboard.as_markup())
        await query.answer()
    else:
        current_channels_str = ", ".join(channels_to_track) if channels_to_track else "Не добавлено ни одного канала"
        keyboard = create_channels_keyboard()
        await query.message.edit_text(f"Каналы: {current_channels_str}", reply_markup=keyboard)
        await query.answer()

@dp.callback_query(lambda query: query.data and MenuCallback.unpack(query.data).category == "channels" and MenuCallback.unpack(query.data).action.startswith("remove_item_"))
async def process_remove_channel_callback_handler(query: types.CallbackQuery) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    callback_data = MenuCallback.unpack(query.data)
    index_str = callback_data.action.split("_")[-1] # Получаем индекс как строку
    logger.info(f"process_remove_channel_callback_handler: action={callback_data.action}, index_str={index_str}") # ЛОГ
    try:
        index = int(index_str) # Пытаемся преобразовать в int
    except ValueError:
        logger.error(f"process_remove_channel_callback_handler: Ошибка преобразования индекса в int: index_str={index_str}") # ЛОГ ошибки
        await query.message.edit_text("Ошибка: неверный индекс канала.", reply_markup=create_back_to_channels_keyboard())
        await query.answer()
        return

    logger.info(f"process_remove_channel_callback_handler: index={index}, channels_to_track до удаления: {channels_to_track}")
    if 0 <= index < len(channels_to_track):
        removed_channel = channels_to_track.pop(index)
        logger.info(f"process_remove_channel_callback_handler: Канал {removed_channel} удален из channels_to_track, channels_to_track после удаления: {channels_to_track}")
        await update_telethon_channels()
        logger.info(f"process_remove_channel_callback_handler: Вызвана update_telethon_channels() после удаления канала")
        await channels_menu_callback_handler(query, MenuCallback(category="channels"), state=FSMContext.get_current())
        await query.answer()
    else:
        logger.warning(f"process_remove_channel_callback_handler: Неверный индекс канала для удаления: {index}, channels_to_track: {channels_to_track}")
        await query.message.edit_text("Неверный выбор.", reply_markup=create_back_to_channels_keyboard())
        await query.answer()

@dp.message(StateFilter(ChannelForm.add_channel))
async def process_add_channel_input(message: types.Message, state: FSMContext) -> None:
    user_username = message.from_user.username
    if not user_username or not is_admin(user_username):
        await message.answer("Доступ запрещен.")
        await state.clear()
        return
    global channels_to_track
    channel = message.text.strip()
    if channel.startswith('@'):
        if channel in channels_to_track:
            await message.answer("Канал уже добавлен.", reply_markup=create_back_to_channels_keyboard())
        else:
            channels_to_track.append(channel)
            logger.info(f"Канал {channel} добавлен в channels_to_track: {channels_to_track}") # <--- Добавляем лог
            await message.answer(f"Канал {channel} добавлен.", reply_markup=create_back_to_channels_keyboard())
        await state.clear()
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        await update_telethon_channels()
        logger.info(f"Вызвана update_telethon_channels()") # <--- Добавляем лог
    else:
        await message.answer("Неверный формат. Начните с '@'. Введите еще раз:", reply_markup=create_cancel_keyboard("channels"))
        try:
            await message.delete()
        except TelegramBadRequest:
            pass

@dp.callback_query(MenuCallback.filter(F.category == "text"))
async def text_menu_callback_handler(query: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    if callback_data.action == "edit":
        await query.message.edit_text(f"Введите новый текст уведомления:\nТекущий текст: {notification_text}", reply_markup=create_cancel_keyboard("text"))
        await state.set_state(TextForm.edit_text)
        await query.answer()
    else:
        keyboard = create_text_keyboard()
        await query.message.edit_text("Текст уведомления:", reply_markup=keyboard)
        await query.answer()

@dp.message(StateFilter(TextForm.edit_text))
async def process_edit_text_input(message: types.Message, state: FSMContext) -> None:
    user_username = message.from_user.username
    if not user_username or not is_admin(user_username):
        await message.answer("Доступ запрещен.")
        await state.clear()
        return
    global notification_text
    new_text = message.text.strip()
    notification_text = new_text
    await state.clear()
    keyboard = create_text_keyboard()
    await message.answer(f"Текст уведомления изменен:\n{notification_text}", reply_markup=keyboard)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

@dp.callback_query(MenuCallback.filter(F.category == "settings"))
async def settings_menu_callback_handler(query: types.CallbackQuery) -> None:
    user_username = query.from_user.username
    if not user_username or not is_admin(user_username):
        await query.answer("Доступ запрещен.", show_alert=True)
        return
    current_users_display = ", ".join(config.notify_users_usernames) if config.notify_users_usernames else "Не заданы" # Отображаем список пользователей
    current_channels_display = ", ".join(channels_to_track) if channels_to_track else "Не заданы"
    settings_text = f"""
Текущие настройки:

Пользователи для уведомлений: {current_users_display} # Обновленный текст
Каналы для отслеживания: {current_channels_display}
Текст уведомления: {notification_text}
    """
    keyboard = create_settings_keyboard()
    keyboard.button(text="Назад", callback_data=MenuCallback(category="main"))
    keyboard.adjust(1)
    await query.message.edit_text(settings_text, reply_markup=keyboard.as_markup())
    await query.answer()


async def main():
    logger.info("Запуск бота и Telethon клиента")
    await telethon_client.start()
    await update_telethon_channels()
    try:
        await asyncio.gather(
            dp.start_polling(bot),
            telethon_client.run_until_disconnected()
)
    
