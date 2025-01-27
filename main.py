import asyncio
import logging
import signal
import json
import re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, PeerChannel
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

class SettingsForm(StatesGroup):
    set_notification_type = State()

telethon_handler = None

def save_config():
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)

def load_history():
    try:
        with open('history.json') as f:
            return json.load(f)
    except:
        return {"stats": {}, "history": []}

def save_history(data):
    data['stats'] = {
        "total_actions": len(data['history']),
        "last_activity": datetime.now().isoformat()
    }
    with open('history.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_back_keyboard(category: str):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Назад", callback_data=f"menu_{category}"))
    return builder.as_markup()

def create_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Пользователи", callback_data="menu_users")
    builder.button(text="Каналы", callback_data="menu_channels")
    builder.button(text="Текст", callback_data="menu_text")
    builder.button(text="Настройки", callback_data="menu_settings")  # Добавлена новая кнопка
    builder.button(text="Статистика", callback_data="menu_stats")
    builder.adjust(1)
    return builder.as_markup()

def create_settings_keyboard():
    builder = InlineKeyboardBuilder()
    current_type = config.get('notification_type', 'link')
    types_info = {
        'link': ('Ссылка', '🔗'),
        'forward': ('Пересыл', '🔄'),
        'text': ('Текст', '📝')
    }
    
    for nt in ['link', 'forward', 'text']:
        name, icon = types_info[nt]
        is_selected = current_type == nt
        text = f"{icon} {name} {'✅' if is_selected else ''}"
        builder.button(text=text, callback_data=f"set_type_{nt}")
    
    builder.button(text="Назад", callback_data="menu_main")
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
    builder.button(text="Удалить", callback_data="text_delete")
    builder.button(text="Назад", callback_data="menu_main")
    builder.adjust(1)
    return builder.as_markup()

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
    elif category == "settings":
        await settings_menu(query)
    elif category == "stats":
        await stats_menu(query)
    elif category == "main":
        await main_menu(query)

async def users_menu(query: types.CallbackQuery):
    try:
        await query.message.edit_text(
            text=f"👥 Пользователи:\n{', '.join(config['notify_users_usernames']) or 'Список пуст'}",
            reply_markup=create_users_keyboard()
        )
    except Exception as e:
        logger.error(f"Users menu error: {e}")

async def channels_menu(query: types.CallbackQuery):
    try:
        channels = config['channels_to_track']
        text = "📢 Каналы:\n" + (', '.join(channels) if channels else "Список пуст")
        await query.message.edit_text(text=text, reply_markup=create_channels_keyboard())
    except Exception as e:
        logger.error(f"Channels menu error: {e}")

async def text_menu(query: types.CallbackQuery):
    try:
        current_text = config['notification_text'] or "Не задан"
        await query.message.edit_text(
            text=f"📝 Текст уведомления:\n{current_text}",
            reply_markup=create_text_keyboard()
        )
    except Exception as e:
        logger.error(f"Text menu error: {e}")

async def settings_menu(query: types.CallbackQuery):
    current_type = config.get('notification_type', 'link')
    type_descriptions = {
        'link': '🔗 Отправлять только ссылку на пост',
        'forward': '🔄 Пересылать исходное сообщение',
        'text': '📄 Отправлять только кастомный текст'
    }
    text = f"⚙️ Настройки уведомлений:\nТекущий режим: {type_descriptions[current_type]}"
    try:
        await query.message.edit_text(text=text, reply_markup=create_settings_keyboard())
    except Exception as e:
        logger.error(f"Settings menu error: {e}")

async def stats_menu(query: types.CallbackQuery):
    history = load_history()
    stats = history.get('stats', {})
    text = f"""📊 Статистика:
👤 Пользователей: {len(config['notify_users_usernames'])}
📢 Каналов: {len(config['channels_to_track'])}
🔢 Всего действий: {stats.get('total_actions', 0)}
⏰ Последняя активность: {datetime.fromisoformat(stats['last_activity']).strftime('%d.%m.%Y %H:%M') if stats.get('last_activity') else 'нет данных'}"""
    await query.message.edit_text(text, reply_markup=create_stats_keyboard())

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_selection(query: types.CallbackQuery, state: FSMContext):
    data = query.data.split("_")
    category = data[1]
    item = "_".join(data[2:])
    user_data = await state.get_data()
    selected = user_data.get("selected", [])
    
    items = config['notify_users_usernames'] if category == "users" else config['channels_to_track']
    
    if item in selected:
        selected.remove(item)
    else:
        selected.append(item)
    
    await state.update_data(selected=selected)
    builder = InlineKeyboardBuilder()
    for i in items:
        emoji = "✅" if i in selected else "◻️"
        builder.button(text=f"{emoji} {i}", callback_data=f"toggle_{category}_{i}")
    builder.button(text="Подтвердить удаление", callback_data=f"confirm_remove_{category}")
    builder.button(text="Назад", callback_data=f"menu_{category}")
    builder.adjust(1)
    await query.message.edit_reply_markup(reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("confirm_remove_"))
async def confirm_remove(query: types.CallbackQuery, state: FSMContext):
    category = query.data.split("_")[-1]
    user_data = await state.get_data()
    selected = user_data.get("selected", [])
    
    if not selected:
        await query.answer("Ничего не выбрано!")
        return
    
    if category == "users":
        config['notify_users_usernames'] = [u for u in config['notify_users_usernames'] if u not in selected]
    else:
        config['channels_to_track'] = [c for c in config['channels_to_track'] if c not in selected]
    
    save_config()
    await update_telethon_channels()
    history = load_history()
    history['history'].append({
        "action": "remove",
        "category": category,
        "items": selected,
        "timestamp": datetime.now().isoformat()
    })
    save_history(history)
    await query.answer(f"Удалено {len(selected)} элементов")
    await state.clear()
    await globals()[f"{category}_menu"](query)

@dp.callback_query(F.data.startswith("set_type_"))
async def set_notification_type(query: types.CallbackQuery):
    new_type = query.data.split("_")[-1]
    config['notification_type'] = new_type
    save_config()
    
    history = load_history()
    history['history'].append({
        "action": "change_notification_type",
        "new_type": new_type,
        "timestamp": datetime.now().isoformat()
    })
    save_history(history)
    
    await query.answer(f"Тип уведомления изменён на: {new_type}")
    await settings_menu(query)

async def process_channel_input(input_str: str):
    try:
        input_str = input_str.strip()
        if input_str.startswith("https://t.me/+"):
            entity = await telethon_client.get_entity(input_str)
            return f"https://t.me/c/{entity.id}/"
        
        if input_str.startswith("@"):
            return input_str.lower()
        
        if input_str.startswith("https://t.me/c/"):
            parts = input_str.split("/")
            return f"https://t.me/c/{parts[-2]}/"
        
        match = re.match(r"https://t.me/(.+?)/(\d+)", input_str)
        if match:
            return f"@{match.group(1)}"
            
        return input_str
    except Exception as e:
        logger.error(f"Error processing channel input: {e}")
        raise ValueError("Неверный формат канала")

async def send_notification(user: str, event):
    notification_type = config.get('notification_type', 'link')
    message = event.message
    chat = await event.get_chat()
    
    try:
        if notification_type == 'link':
            if hasattr(chat, 'username') and chat.username:
                post_link = f"https://t.me/{chat.username}/{message.id}"
            else:
                post_link = f"https://t.me/c/{chat.id}/{message.id}"
            
            text = config['notification_text'] or "Новое сообщение из канала!"
            await telethon_client.send_message(
                user, 
                f"{text}\n\n🔗 Ссылка: {post_link}",
                link_preview=False
            )
            
        elif notification_type == 'forward':
            await telethon_client.forward_messages(user, message)
            
            if config['notification_text']:
                await telethon_client.send_message(user, config['notification_text'])
            
        elif notification_type == 'text' and config['notification_text']:
            await telethon_client.send_message(user, config['notification_text'])
            
    except Exception as e:
        logger.error(f"Error sending to {user}: {e}")

@dp.callback_query(F.data == "stats_history")
async def show_history(query: types.CallbackQuery):
    history_data = load_history()
    items = history_data['history']
    
    text = "📝 Последние 10 действий:\n\n"
    for idx, entry in enumerate(reversed(items[-10:]), start=1):
        text += f"{idx}. {format_history_entry(entry)}\n\n"

    await query.message.edit_text(text, reply_markup=create_history_keyboard())

def format_history_entry(entry):
    action_map = {
        "add": "➕ Добавлено",
        "remove": "➖ Удалено",
        "edit_text": "✏️ Изменен текст",
        "change_notification_type": "⚙️ Изменен тип уведомлений"
    }
    date = datetime.fromisoformat(entry['timestamp']).strftime("%d.%m.%Y %H:%M")
    
    if entry['action'] in ['add', 'remove']:
        category = 'пользователей' if entry['category'] == 'users' else 'каналов'
        return f"{action_map[entry['action']]} {len(entry['items'])} {category} ({date})"
    elif entry['action'] == 'change_notification_type':
        return f"{action_map[entry['action']]} → {entry['new_type']} ({date})"
    return f"{action_map.get(entry['action'], entry['action'])} ({date})"

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
    await dp.start_polling(bot, skip_updates=True)
    await telethon_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
