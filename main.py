import asyncio
import logging
import signal
import json
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.callback_data import CallbackData
from aiogram.exceptions import TelegramBadRequest

with open('config.json') as f:
    config = json.load(f)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config['bot_token'])
dp = Dispatcher()
telethon_client = TelegramClient("anon", config['api_id'], config['api_hash'])

class MenuCallback(CallbackData, prefix="menu"):
    category: str
    action: str = "main"

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
    builder.button(text="Добавить", callback_data=MenuCallback(category="users", action="add"))
    builder.button(text="Удалить", callback_data=MenuCallback(category="users", action="remove"))
    builder.button(text="Назад", callback_data=MenuCallback(category="main"))
    builder.adjust(1)
    return builder.as_markup()

def create_channels_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить", callback_data=MenuCallback(category="channels", action="add"))
    builder.button(text="Удалить", callback_data=MenuCallback(category="channels", action="remove"))
    builder.button(text="Назад", callback_data=MenuCallback(category="main"))
    builder.adjust(1)
    return builder.as_markup()

def create_text_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Изменить", callback_data=MenuCallback(category="text", action="edit"))
    builder.button(text="Назад", callback_data=MenuCallback(category="main"))
    builder.adjust(1)
    return builder.as_markup()

def is_admin(username: str) -> bool:
    if not username:
        return False
    return f"@{username}" in config['admin_usernames']

async def update_telethon_channels():
    global telethon_handler
    if telethon_handler:
        telethon_client.remove_event_handler(telethon_handler)

    @telethon_client.on(events.NewMessage(chats=config['channels_to_track']))
    async def handler(event):
        channel = await event.get_chat()
        post_link = f"https://t.me/{channel.username}/{event.message.id}" if channel.username else f"{channel.title}/{event.message.id}"
        text = f"{config['notification_text']}\n\n------------\n{post_link}"
        
        for user in config['notify_users_usernames']:
            try:
                await telethon_client.send_message(user, text)
                logger.info(f"Sent to {user}")
            except Exception as e:
                logger.error(f"Error sending to {user}: {e}")

    telethon_handler = handler

@dp.message(CommandStart())
async def start(message: types.Message):
    if not message.from_user.username:
        await message.answer("У вас не установлен username в Telegram!")
        return

    if not is_admin(message.from_user.username):
        await message.answer("Доступ запрещен")
        return
        
    await message.answer("Настройки:", reply_markup=create_main_keyboard())
    
@dp.callback_query(MenuCallback.filter(F.category == "main"))
async def main_menu(query: types.CallbackQuery):
    await query.message.edit_text("Настройки:", reply_markup=create_main_keyboard())

@dp.callback_query(MenuCallback.filter(F.category == "users"))
async def users_menu(query: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    if callback_data.action == "add":
        await query.message.edit_text("Введите @username:", reply_markup=create_back_keyboard("users"))
        await state.set_state(UserForm.add_user)
    elif callback_data.action == "remove":
        builder = InlineKeyboardBuilder()
        for idx, user in enumerate(config['notify_users_usernames']):
            builder.button(text=f"❌ {user}", callback_data=MenuCallback(category="users", action=f"remove_{idx}"))
        builder.button(text="Назад", callback_data=MenuCallback(category="users"))
        builder.adjust(1)
        await query.message.edit_text("Выберите пользователя:", reply_markup=builder.as_markup())
    else:
        await query.message.edit_text(f"Пользователи: {', '.join(config['notify_users_usernames'])}", reply_markup=create_users_keyboard())

@dp.callback_query(MenuCallback.filter(F.category == "users") & F.action.startswith("remove_"))
async def remove_user(query: types.CallbackQuery):
    idx = int(query.data.split("_")[-1])
    user = config['notify_users_usernames'].pop(idx)
    save_config()
    await query.answer(f"Удален: {user}")
    await users_menu(query, MenuCallback(category="users"), None)

@dp.message(UserForm.add_user)
async def add_user(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if username not in config['notify_users_usernames']:
        config['notify_users_usernames'].append(username)
        save_config()
    await state.clear()
    await message.answer("Добавлен!", reply_markup=create_users_keyboard())

@dp.callback_query(MenuCallback.filter(F.category == "channels"))
async def channels_menu(query: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext):
    if callback_data.action == "add":
        await query.message.edit_text("Введите @channel:", reply_markup=create_back_keyboard("channels"))
        await state.set_state(ChannelForm.add_channel)
    elif callback_data.action == "remove":
        builder = InlineKeyboardBuilder()
        for idx, channel in enumerate(config['channels_to_track']):
            builder.button(text=f"❌ {channel}", callback_data=MenuCallback(category="channels", action=f"remove_{idx}"))
        builder.button(text="Назад", callback_data=MenuCallback(category="channels"))
        builder.adjust(1)
        await query.message.edit_text("Выберите канал:", reply_markup=builder.as_markup())
    else:
        await query.message.edit_text(f"Каналы: {', '.join(config['channels_to_track'])}", reply_markup=create_channels_keyboard())

@dp.callback_query(MenuCallback.filter(F.category == "channels") & F.action.startswith("remove_"))
async def remove_channel(query: types.CallbackQuery):
    idx = int(query.data.split("_")[-1])
    channel = config['channels_to_track'].pop(idx)
    save_config()
    await update_telethon_channels()
    await query.answer(f"Удален: {channel}")
    await channels_menu(query, MenuCallback(category="channels"), None)

@dp.message(ChannelForm.add_channel)
async def add_channel(message: types.Message, state: FSMContext):
    try:
        channel = message.text.strip()
        entity = await telethon_client.get_entity(channel)
        if isinstance(entity, (Channel, Chat)) and channel not in config['channels_to_track']:
            config['channels_to_track'].append(channel)
            save_config()
            await update_telethon_channels()
    except Exception:
        await message.answer("Ошибка добавления канала")
    finally:
        await state.clear()
        await message.answer("Добавлен!", reply_markup=create_channels_keyboard())

@dp.callback_query(MenuCallback.filter(F.category == "text"))
async def text_menu(query: types.CallbackQuery, state: FSMContext):
    if query.data.split(":")[-1] == "edit":
        await query.message.edit_text("Введите новый текст:")
        await state.set_state(TextForm.edit_text)
    else:
        await query.message.edit_text(f"Текст: {config['notification_text']}", reply_markup=create_text_keyboard())

@dp.message(TextForm.edit_text)
async def edit_text(message: types.Message, state: FSMContext):
    config['notification_text'] = message.text
    save_config()
    await state.clear()
    await message.answer("Текст обновлен!", reply_markup=create_text_keyboard())

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
