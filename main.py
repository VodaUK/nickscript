import asyncio
import logging
import signal
import json
from datetime import datetime
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

class MultiAction(StatesGroup):
    selecting = State()
    confirming = State()

telethon_handler = None

def save_config():
    global config
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    with open('config.json') as f:
        config = json.load(f)

def create_back_keyboard(category: str):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Назад", callback_data=f"menu_{category}"))
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
    builder.button(text="Удалить", callback_data="text_delete")  # Новая кнопка
    builder.button(text="Назад", callback_data="menu_main")
    builder.adjust(1)
    return builder.as_markup()

def load_history():
    try:
        with open('history.json') as f:
            return json.load(f)
    except:
        return {"stats": {}, "history": []}

def save_history(data):
    with open('history.json', 'w') as f:
        json.dump(data, f, indent=2)

def create_stats_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="История", callback_data="stats_history")
    builder.button(text="Очистить историю", callback_data="stats_clear")
    builder.button(text="Назад", callback_data="menu_main")
    builder.adjust(1)
    return builder.as_markup()

def is_admin(username: str) -> bool:
    return username and f"@{username.lower()}" in [u.lower() for u in config['admin_usernames']]

async def update_telethon_channels():
    global telethon_handler
    if telethon_handler:
        telethon_client.remove_event_handler(telethon_handler)
    if not config['channels_to_track']:
        return
    @telethon_client.on(events.NewMessage(chats=config['channels_to_track']))
    async def handler(event):
        channel = await event.get_chat()
        post_link = f"https://t.me/{channel.username}/{event.message.id}"
        text = f"{config['notification_text']}\n------------\n{post_link}"
        for user in config['notify_users_usernames']:
            try:
                await telethon_client.send_message(user, text)
            except Exception as e:
                logger.error(f"Error sending to {user}: {e}")
    telethon_handler = handler

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

@dp.callback_query(F.data.startswith("remove_user_"))
async def remove_user(query: types.CallbackQuery):
    try:
        idx = int(query.data.split("_")[-1])
        user = config['notify_users_usernames'].pop(idx)
        save_config()
        await update_telethon_channels()
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
            await update_telethon_channels()
        await message.answer("Пользователь добавлен!", reply_markup=create_users_keyboard())
    except Exception as e:
        await message.answer("Ошибка добавления")
        logger.error(f"Add user error: {e}")
    finally:
        await state.clear()

async def channels_menu(query: types.CallbackQuery):
    try:
        channels = config['channels_to_track']
        text = "Каналы:\n" + (', '.join(channels) if channels else "Список пуст")
        await query.message.edit_text(text=text, reply_markup=create_channels_keyboard())
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

@dp.callback_query(F.data.startswith("remove_channel_"))
async def remove_channel(query: types.CallbackQuery):
    try:
        idx = int(query.data.split("_")[-1])
        channel = config['channels_to_track'].pop(idx)
        save_config()
        await update_telethon_channels()
        await query.answer(f"Удален: {channel}")
        await channels_menu(query)
    except Exception as e:
        logger.error(f"Remove channel error: {e}")

@dp.message(ChannelForm.add_channel)
async def add_channel(message: types.Message, state: FSMContext):
    try:
        channel = message.text.strip().lower()
        if not channel:
            await message.answer("❌ Пустое значение!")
            return
        if not channel.startswith("@"):
            channel = f"@{channel}"
        entity = await telethon_client.get_entity(channel)
        if isinstance(entity, (Channel, Chat)) and channel not in config['channels_to_track']:
            config['channels_to_track'].append(channel)
            save_config()
            await update_telethon_channels()
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
    except Exception as e:
        logger.error(f"Text menu error: {e}")

@dp.callback_query(F.data == "text_edit")
async def text_edit_handler(query: types.CallbackQuery, state: FSMContext):
    try:
        await query.message.edit_text("Введите новый текст уведомления:")
        await state.set_state(TextForm.edit_text)
    except Exception as e:
        logger.error(f"Text edit error: {e}")

@dp.callback_query(F.data == "text_delete")
async def text_delete_handler(query: types.CallbackQuery):
    try:
        config['notification_text'] = ""
        save_config()
        await query.message.edit_text(
            text="Текст уведомления удален!",
            reply_markup=create_text_keyboard()
        )
        await query.answer()
    except Exception as e:
        logger.error(f"Text delete error: {e}")

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

@dp.message(ChannelForm.add_channel)
@dp.message(UserForm.add_user)
async def bulk_add_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    items = [i.strip() for i in message.text.split(',')]
    
    success = []
    errors = []
    
    for item in items:
        try:
            if current_state == ChannelForm.add_channel:
                entity = await telethon_client.get_entity(item)
                if isinstance(entity, (Channel, Chat)):
                    config['channels_to_track'].append(item)
            else:
                if item not in config['notify_users_usernames']:
                    config['notify_users_usernames'].append(item)
            success.append(item)
        except Exception as e:
            errors.append(f"{item}: {str(e)}")
    
    if success:
        save_config()
        await update_telethon_channels()
    
    response = []
    if success:
        response.append(f"✅ Успешно: {', '.join(success)}")
    if errors:
        response.append(f"❌ Ошибки:\n" + '\n'.join(errors))
    
    await message.answer('\n'.join(response))
    await state.clear()

@dp.callback_query(F.data.startswith("multi_remove_"))
async def multi_remove_start(query: types.CallbackQuery, state: FSMContext):
    category = query.data.split("_")[-1]
    items = config[f"{category}_to_track"]
    
    await state.update_data(selected=[])
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=f"◻️ {item}", callback_data=f"toggle_{category}_{item}")
    builder.button(text="Подтвердить", callback_data=f"confirm_remove_{category}")
    builder.button(text="Отмена", callback_data=f"menu_{category}")
    builder.adjust(1)
    
    await query.message.edit_text(
        "Выберите элементы:",
        reply_markup=builder.as_markup()
    )

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
    if not config['channels_to_track']:
        logger.warning("No channels to track")
    await dp.start_polling(bot, skip_updates=True)
    await telethon_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
