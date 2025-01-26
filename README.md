# nickxd notifications bot

[![Telegram Бот](https://img.shields.io/badge/Telegram-Бот-blue.svg)](https://t.me/nickxd_bot)

Бот для пересылки новых постов из Telegram-каналов. Будьте в курсе обновлений, получая все в одном месте.

## ✨ Возможности

*   **Мгновенные уведомления:**  Узнавайте о новых постах сразу.
*   **Отслеживание каналов:** Мониторьте несколько каналов.
*   **Управление пользователями:**  Настройте, кто будет получать уведомления.
*   **Простая установка:** Быстрый запуск.
*   **Панель управления:** Настройки бота в Telegram.

## 🛠️ Библиотеки

*   **Python:** Основной код бота.
*   **aiogram 3.17.0:**  Для управления ботом в Telegram.
*   **Telethon:** Для доступа к хеш-данным.

## 🚀 Как запустить?

1.  **Клонировать:**
    ```bash
    git clone https://github.com/VodaUK/nickscript.git
    cd [путь к проекту, допустим: cd Download/nickscript]
    ```
2.  **Установить:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Настроить:** Файл `config.json`:
    *   Ключи API Telegram (`api_id`, `api_hash`)
    *   Токен бота (`bot_token`)
    *   Администраторы (`admin_usernames`)
    *   Каналы для отслеживания (`channels_to_track`)
    *   Текст уведомления (`notification_text`)
4.  **Запустить:**
    ```bash
    python main.py
    ```

## 🕹️ Команды бота

*   `/start`: Открыть меню настроек.
*   В меню:
    *   Управление пользователями
    *   Управление каналами
    *   Изменить текст уведомления
    *   Просмотр настроек

Администраторы управляют ботом через меню.

## 📄 Лицензия

[Канал @lumohn](https://t.me/lumohn)
