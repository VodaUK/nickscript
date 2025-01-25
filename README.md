# Channel Post Notifier Bot

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/nickxd_bot)

Keep up with your favorite Telegram channels effortlessly. This bot forwards new posts from the channels you choose directly to you, or a select group of users, ensuring you never miss an update.

## ✨ Key Features

*   **Instant Updates:** Get notified the moment new content is posted in tracked channels.
*   **Centralized Content:** Aggregate updates from multiple channels into a single, convenient stream.
*   **Flexible User Management:** Easily add and remove users who receive notifications, perfect for teams or groups.
*   **Effortless Setup:** Get the bot running quickly with a straightforward configuration process.
*   **Intuitive Admin Panel:** Manage all bot settings directly within Telegram using simple commands.

## 🛠️ Technologies

*   **Python:** Built with the versatility and power of Python.
*   **aiogram 3.17.0:** Leveraging the robust and asynchronous aiogram framework for efficient bot operations.
*   **Telethon:** Utilizing Telethon for seamless and reliable access to Telegram channel content.

## 🚀 Quick Start

1.  **Clone:**
    ```bash
    git clone [repository-link]
    cd [repository-directory]
    ```
2.  **Install:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure:**  Edit `config.py` with:
    *   Your Telegram API keys (`api_id`, `api_hash`)
    *   Bot token (`bot_token`)
    *   Admin usernames (`admin_usernames`)
    *   Channels to monitor (`channels_to_track`)
    *   Custom notification message (`notification_text`)
4.  **Run:**
    ```bash
    python main.py
    ```

## 🕹️ Bot Commands

*   `/start`: Opens the settings menu to configure the bot.
*   Navigate through the interactive menu to manage:
    *   Notification users
    *   Tracked channels
    *   Custom notification text
    *   View current bot settings

Administrators can use the menu to tailor the bot to their specific notification needs.

## 📄 License

[Channel by @lumohn](https://t.me/lumohn)
