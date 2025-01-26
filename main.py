import asyncio
import logging
import signal
import json
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

with open('config.json') as f:
    config = json.load(f)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config['bot_token'])
dp = Dispatcher()
telethon_client = TelegramClient("anon", config['api_id'], config['api_hash'])

class UserForm(StatesGroup):
    add_user = State()
    remove_user = State()

class ChannelForm(StatesGroup):
    add_channel = State()
    remove_channel = State()

class TextForm(StatesGroup):
    edit_text = State()

telethon_handler = None

def save_config():
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    logger.info("Config saved to config.json")

    with open('config.json') as f:
        global config
        config = json.load(f)
    logger.info("Config reloaded from config.json")
def create_back_keyboard(category: str):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Назад",
        callback_data=f"menu_{category}"
    ))
    return builder.as_markup()

def create_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Пользователи", callback_data="menu_users")
    builder.button(text="Каналы", callback_data="menu_channels")
    builder.button(text="Текст", callback_data="menu_text")
    builder.adjust(1)
    return builder.as_markup()

def create_users_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить", callback_data="users_add")
    builder.button(text="Удалить", callback_data="users_remove")
    builder.button(text="Назад", callback_data="menu_main")
    builder.adjust(1)
    return builder.as_markup()

def create_channels_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить", callback_data="channels_add")
    builder.button(text="Удалить", callback_data="channels_remove")
    builder.button(text="Назад", callback_data="menu_main")
    builder.adjust(1)
    return builder.as_markup()

def create_text_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Изменить", callback_data="text_edit")
    builder.button(text="Назад", callback_data="menu_main")
    builder.adjust(1)
    return builder.as_markup()

def is_admin(username: str) -> bool:
    if not username:
        return False
    return f"@{username.lower()}" in [u.lower() for u in config['admin_usernames']]

async def update_telethon_channels():
    global telethon_handler
    if telethon_handler:
        telethon_client.remove_event_handler(telethon_handler)

    @telethon_client.on(events.NewMessage(chats=config['channels_to_track']))
    async def handler(event):
        channel = await event.get_chat()
        post_link = f"https://t.me/{channel.username}/{event.message.id}"
        text = f"{config['notification_text']}\n\n------------\n{post_link}"

        for user in config['notify_users_usernames']:
            try:
                await telethon_client.send_message(user, text)
            except Exception as e:
                logger.error(f"Error sending to {user}: {e}")

    telethon_handler = handler
    logger.info(f"Telethon handler updated for channels: {config['channels_to_track']}") # Логирование обновления

@dp.message(CommandStart())
async def start(message: types.Message):
    user = message.from_user
    if not user.username:
        await message.answer("Установите username в настройках Telegram!")
        return

    if not is_admin(user.username):
        await message.answer("Доступ запрещен")
        return

    await message.answer("Панель управления:", reply_markup=create_main_keyboard())

@dp.callback_query(F.data == "menu_main")
async def main_menu(query: types.CallbackQuery):
    try:
        await query.message.edit_text("Панель управления:", reply_markup=create_main_keyboard())
        await query.answer()
    except TelegramBadRequest:
        pass

@dp.callback_query(F.data.startswith("menu_"))
async def menu_handler(query: types.CallbackQuery):
    category = query.data.split("_")[1]

    if category == "users":
        await users_menu(query)
    elif category == "channels":
        await channels_menu(query)
    elif category == "text":
        await text_menu(query)

async def users_menu(query: types.CallbackQuery):
    try:
        await query.message.edit_text(
            text=f"Пользователи:\n{', '.join(config['notify_users_usernames'])}",
            reply_markup=create_users_keyboard()
        )
        await query.answer()
    except Exception as e:
        logger.error(f"Users menu error: {e}")

@dp.callback_query(F.data.startswith("users_"))
async def users_actions(query: types.CallbackQuery, state: FSMContext):
    action = query.data.split("_")[1]

    if action == "add":
        await query.message.edit_text(
            text="Введите @username пользователя:",
            reply_markup=create_back_keyboard("users")
        )
        await state.set_state(UserForm.add_user)
    elif action == "remove":
        builder = InlineKeyboardBuilder()
        for idx, user in enumerate(config['notify_users_usernames']):
            builder.button(text=f"Удалить {user}", callback_data=f"remove_user_{idx}")
        builder.button(text="Назад", callback_data="menu_users")
        builder.adjust(1)
        await query.message.edit_text("Выберите пользователя:", reply_markup=builder.as_markup())
    await query.answer()

@dp.callback_query(F.data.startswith("remove_user_"))
async def remove_user(query: types.CallbackQuery):
    try:
        idx = int(query.data.split("_")[-1])
        user = config['notify_users_usernames'].pop(idx)
        save_config()
        await update_telethon_channels() # Важно обновить обработчик после изменения списка пользователей
        await query.answer(f"Удален: {user}")
        await users_menu(query)
    except Exception as e:
        logger.error(f"Remove user error: {e}")

@dp.message(UserForm.add_user)
async def add_user(message: types.Message, state: FSMContext):
    try:
        username = message.text.strip().lower()
        if not username.startswith("@"):
            username = f"@{username}"

        if username not in config['notify_users_usernames']:
            config['notify_users_usernames'].append(username)
            save_config()
            await update_telethon_channels() # Важно обновить обработчик после изменения списка пользователей

        await message.answer("Пользователь добавлен!", reply_markup=create_users_keyboard())
    except Exception as e:
        await message.answer("Ошибка добавления")
        logger.error(f"Add user error: {e}")
    finally:
        await state.clear()

async def channels_menu(query: types.CallbackQuery):
    try:
        await query.message.edit_text(
            text=f"Каналы:\n{', '.join(config['channels_to_track'])}",
            reply_markup=create_channels_keyboard()
        )
        await query.answer()
    except Exception as e:
        logger.error(f"Channels menu error: {e}")

@dp.callback_query(F.data.startswith("channels_"))
async def channels_actions(query: types.CallbackQuery, state: FSMContext):
    action = query.data.split("_")[1]

    if action == "add":
        await query.message.edit_text(
            text="Введите @username канала:",
            reply_markup=create_back_keyboard("channels")
        )
        await state.set_state(ChannelForm.add_channel)
    elif action == "remove":
        builder = InlineKeyboardBuilder()
        for idx, channel in enumerate(config['channels_to_track']):
            builder.button(text=f"Удалить {channel}", callback_data=f"remove_channel_{idx}")
        builder.button(text="Назад", callback_data="menu_channels")
        builder.adjust(1)
        await query.message.edit_text("Выберите канал:", reply_markup=builder.as_markup())
    await query.answer()

@dp.callback_query(F.data.startswith("remove_channel_"))
async def remove_channel(query: types.CallbackQuery):
    try:
        idx = int(query.data.split("_")[-1])
        channel = config['channels_to_track'].pop(idx)
        save_config()
        await update_telethon_channels() # Важно обновить обработчик после изменения списка каналов
        await query.answer(f"Удален: {channel}")
        await channels_menu(query)
    except Exception as e:
        logger.error(f"Remove channel error: {e}")

@dp.message(ChannelForm.add_channel)
async def add_channel(message: types.Message, state: FSMContext):
    try:
        channel = message.text.strip().lower()
        if not channel.startswith("@"):
            channel = f"@{channel}"

        entity = await telethon_client.get_entity(channel)
        if isinstance(entity, (Channel, Chat)) and channel not in config['channels_to_track']:
            config['channels_to_track'].append(channel)
            save_config()
            await update_telethon_channels() # Важно обновить обработчик после изменения списка каналов

        await message.answer("Канал добавлен!", reply_markup=create_channels_keyboard())
    except Exception as e:
        await message.answer("Ошибка добавления канала")
        logger.error(f"Add channel error: {e}")
    finally:
        await state.clear()

async def text_menu(query: types.CallbackQuery):
    try:
        await query.message.edit_text(
            text=f"Текст уведомления:\n{config['notification_text']}",
            reply_markup=create_text_keyboard()
        )
        await query.answer()
    except Exception as e:
        logger.error(f"Text menu error: {e}")

@dp.callback_query(F.data == "text_edit")
async def text_edit_handler(query: types.CallbackQuery, state: FSMContext):
    try:
        await query.message.edit_text("Введите новый текст уведомления:")
        await state.set_state(TextForm.edit_text)
        await query.answer()
    except Exception as e:
        logger.error(f"Text edit error: {e}")

@dp.message(TextForm.edit_text)
async def edit_text(message: types.Message, state: FSMContext):
    try:
        config['notification_text'] = message.text
        save_config()
        await message.answer("Текст обновлен!", reply_markup=create_text_keyboard())
    except Exception as e:
        await message.answer("Ошибка сохранения")
        logger.error(f"Edit text error: {e}")
    finally:
        await state.clear()

async def shutdown(signal, loop):
    logger.info("Завершение работы...")
    await telethon_client.disconnect()
    await bot.session.close()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(sig, loop)))

    await telethon_client.start()
    await update_telethon_channels()
    await asyncio.gather(
        dp.start_polling(bot),
        telethon_client.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())
