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
    builder.button(text="Статистика", callback_data="menu_stats")
    builder.adjust(1)
    return builder.as_markup()

def create_users_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить", callback_data="users_add")
    builder.button(text="Удалить", callback_data="users_remove")
    builder.button(text="Удалить всех", callback_data="users_remove_all")
    builder.button(text="Назад", callback_data="menu_main")
    builder.adjust(1)
    return builder.as_markup()

def create_channels_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить", callback_data="channels_add")
    builder.button(text="Удалить", callback_data="channels_remove")
    builder.button(text="Удалить всех", callback_data="channels_remove_all")
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
    elif category == "stats":
        await stats_menu(query)

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
            text="Введите @username через запятую:",
            reply_markup=create_back_keyboard("users")
        )
        await state.set_state(UserForm.add_user)
    elif action == "remove":
        builder = InlineKeyboardBuilder()
        for user in config['notify_users_usernames']:
            builder.button(text=f"◻️ {user}", callback_data=f"toggle_users_{user}")
        builder.button(text="Подтвердить удаление", callback_data="confirm_remove_users")
        builder.button(text="Назад", callback_data="menu_users")
        builder.adjust(1)
        await query.message.edit_text("Выберите пользователей:", reply_markup=builder.as_markup())
    elif action == "remove_all":
        await remove_all_users(query)

async def remove_all_users(query: types.CallbackQuery):
    deleted = config['notify_users_usernames'].copy()
    config['notify_users_usernames'].clear()
    save_config()
    history = load_history()
    history['history'].append({
        "action": "remove_all",
        "category": "users",
        "items": deleted,
        "timestamp": datetime.now().isoformat()
    })
    save_history(history)
    await query.answer(f"Удалено {len(deleted)} пользователей")
    await users_menu(query)

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
            text="Введите @username каналов через запятую:",
            reply_markup=create_back_keyboard("channels")
        )
        await state.set_state(ChannelForm.add_channel)
    elif action == "remove":
        builder = InlineKeyboardBuilder()
        for channel in config['channels_to_track']:
            builder.button(text=f"◻️ {channel}", callback_data=f"toggle_channels_{channel}")
        builder.button(text="Подтвердить удаление", callback_data="confirm_remove_channels")
        builder.button(text="Назад", callback_data="menu_channels")
        builder.adjust(1)
        await query.message.edit_text("Выберите каналы:", reply_markup=builder.as_markup())
    elif action == "remove_all":
        await remove_all_channels(query)

async def remove_all_channels(query: types.CallbackQuery):
    deleted = config['channels_to_track'].copy()
    config['channels_to_track'].clear()
    save_config()
    history = load_history()
    history['history'].append({
        "action": "remove_all",
        "category": "channels",
        "items": deleted,
        "timestamp": datetime.now().isoformat()
    })
    save_history(history)
    await query.answer(f"Удалено {len(deleted)} каналов")
    await channels_menu(query)

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_selection(query: types.CallbackQuery, state: FSMContext):
    data = query.data.split("_")
    category = data[1]
    item = "_".join(data[2:])
    user_data = await state.get_data()
    selected = user_data.get("selected", [])
    
    items = config['notify_users_usernames'] if category == "users" else config['channels_to_track"]
    
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
    builder.button(text="Отмена", callback_data=f"menu_{category}")
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

@dp.message(ChannelForm.add_channel)
@dp.message(UserForm.add_user)
async def bulk_add_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    items = [i.strip().lower() for i in message.text.split(',')]
    success = []
    errors = []
    category = "channels" if "ChannelForm" in current_state else "users"
    
    for item in items:
        try:
            if not item.startswith("@"):
                item = f"@{item}"
            
            if category == "channels":
                entity = await telethon_client.get_entity(item)
                if not isinstance(entity, (Channel, Chat)):
                    raise ValueError("Not a channel")
                if item in config['channels_to_track']:
                    continue
                config['channels_to_track'].append(item)
            else:
                if item in config['notify_users_usernames']:
                    continue
                config['notify_users_usernames'].append(item)
            
            success.append(item)
        except Exception as e:
            errors.append(f"{item}: {str(e)}")
    
    if success:
        save_config()
        await update_telethon_channels()
        history = load_history()
        history['history'].append({
            "action": "add",
            "category": category,
            "items": success,
            "timestamp": datetime.now().isoformat()
        })
        save_history(history)
    
    response = []
    if success:
        response.append(f"✅ Добавлено: {', '.join(success)}")
    if errors:
        response.append(f"❌ Ошибки:\n" + '\n'.join(errors))
    
    await message.answer('\n'.join(response), reply_markup=create_main_keyboard())
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
    config['notification_text'] = ""
    save_config()
    await query.message.edit_text(
        text="Текст уведомления удален!",
        reply_markup=create_text_keyboard()
    )
    await query.answer()

@dp.message(TextForm.edit_text)
async def edit_text(message: types.Message, state: FSMContext):
    old_text = config['notification_text']
    new_text = message.text
    config['notification_text'] = new_text
    save_config()
    history = load_history()
    history['history'].append({
        "action": "edit_text",
        "old": old_text,
        "new": new_text,
        "timestamp": datetime.now().isoformat()
    })
    save_history(history)
    await message.answer("Текст обновлен!", reply_markup=create_main_keyboard())
    await state.clear()

@dp.callback_query(F.data == "menu_stats")
async def stats_menu(query: types.CallbackQuery):
    history = load_history()
    stats = history.get('stats', {})
    text = f"""📊 Статистика:
Пользователей: {len(config['notify_users_usernames'])}
Каналов: {len(config['channels_to_track'])}
Последняя активность: {stats.get('last_activity', 'нет данных')}"""
    await query.message.edit_text(text, reply_markup=create_stats_keyboard())

@dp.callback_query(F.data == "stats_history")
async def show_history(query: types.CallbackQuery):
    history_data = load_history()
    items = history_data['history']
    builder = InlineKeyboardBuilder()
    for idx, entry in enumerate(items[-10:], start=1):
        builder.button(text=f"{idx}. {entry['action']} ({entry['timestamp'][:10]})", 
                      callback_data=f"history_detail_{len(items)-10+idx-1}")
    builder.button(text="Назад", callback_data="menu_stats")
    builder.adjust(1)
    await query.message.edit_text("Последние 10 записей:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("history_detail_"))
async def history_detail(query: types.CallbackQuery):
    idx = int(query.data.split("_")[-1])
    history_data = load_history()
    try:
        entry = history_data['history'][idx]
        text = f"""📝 Детали записи:
Действие: {entry['action']}
Категория: {entry.get('category', 'N/A')}
Дата: {entry['timestamp']}
Данные: {json.dumps(entry, indent=2, ensure_ascii=False)}"""
        await query.message.edit_text(text, reply_markup=create_back_keyboard("stats"))
    except IndexError:
        await query.answer("Запись не найдена")

@dp.callback_query(F.data == "stats_clear")
async def clear_history(query: types.CallbackQuery):
    save_history({"stats": {}, "history": []})
    await query.answer("История очищена")
    await stats_menu(query)

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
