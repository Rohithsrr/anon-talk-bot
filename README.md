# 🤖 AnonTalk AI - Anonymous Telegram Chat Bot

This is a feature-rich anonymous chat bot for Telegram, built with Python using the `python-telegram-bot` library and `sqlite3` for the database. It allows users to connect and chat with random strangers one-on-one.

The bot includes a referral system to unlock a gender-based partner filter, along with special commands for bot administrators to monitor and manage the community.

## ✨ Features

-   **👤 Anonymous Chatting**: Connects two random users for a private, one-on-one conversation.
-   **🤝 Referral System**: Users can invite friends with a unique link. Reaching a certain number of referrals unlocks premium features.
-   **🚻 Gender-Based Filtering**: Users can choose to be connected with a male, female, or random partner. This feature is unlocked via the referral system.
-   **📊 Admin Dashboard**: Bot administrators have access to special commands like `/stats` to view user statistics (total users, new users today) and `/broadcast` to send messages to all users.
-   **🖼️ Full Media Support**: Relays text messages, photos, videos, voice notes, and stickers between chat partners.
-   **⚙️ Persistent Database**: Uses SQLite to store user information, referral counts, and gender preferences.
-   **✅ Clean Interface**: Uses inline keyboard buttons for a smooth and intuitive user experience.

---

## ⚙️ How It Works

1.  **User Starts**: A user starts the bot, optionally with a referral code. New users are saved to the database.
2.  **Set Gender**: On the first chat attempt, the user is asked to set their gender (Male/Female), which is stored for future matchmaking.
3.  **Find Partner**: The user chooses their partner preference (Any/Male/Female).
4.  **Matchmaking**:
    -   The bot checks if the user has unlocked the gender filter (by meeting the referral threshold).
    -   It then looks for a user in the "waiting queue" who matches the criteria.
    -   If a match is found, a chat session is established between the two users.
    -   If not, the user is added to the waiting queue.
5.  **Relay Messages**: All messages and supported media sent by one user are anonymously forwarded to the other.
6.  **End Chat**: Users can stop the chat at any time with the `🚫 Stop` button or start a new one with `⏭ Next`.

---

## 🚀 Setup and Installation

Follow these steps to get the bot running.

### Prerequisites

-   Python 3.8 or higher
-   A Telegram account

### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
cd your-repository-name
```

### 2. Install Dependencies

It is highly recommended to use a virtual environment.

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the required Python package
pip install python-telegram-bot
```

### 3. Get a Telegram Bot Token

1.  Open Telegram and search for the **@BotFather** user.
2.  Start a chat with him and send the `/newbot` command.
3.  Follow the instructions to choose a name and username for your bot.
4.  BotFather will give you a unique **BOT TOKEN**. Copy it.
5.  Paste the token into the script:
    ```python
    BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
    ```

### 4. Configure Admin Users

1.  You need your numerical Telegram User ID. You can get it by messaging a bot like **@userinfobot**.
2.  Add your User ID to the `ADMIN_IDS` set in the script. You can add multiple IDs.
    ```python
    ADMIN_IDS = {123456789, 987654321} # Replace with your admin ID(s)
    ```

### 5. Configure Referral Threshold

You can change the number of referrals needed to unlock the gender filter.

```python
REFERRAL_THRESHOLD = 3 # Set to your desired number
```

---

## 🏃‍♀️ Usage

Once the configuration is complete, run the bot from your terminal:

```bash
python your_script_name.py
```

The script will initialize the database (`anontalk.db`) if it doesn't exist and the bot will start polling for new messages.

### User Commands
-   `/start` - Initializes the bot.
-   `/chat` - Starts the process of finding a partner.
-   `/next` - Ends the current chat and looks for a new one.
-   `/stop` - Ends the current chat or removes you from the waiting queue.
-   `/refer` - Gets your unique referral link.

### Admin-Only Commands
-   `/stats` - Shows bot statistics (total users, daily new users, top referrers).
-   `/broadcast <message>` - Sends a message to all users of the bot.

---

## ⚠️ Security: Protect Your Token!

Your **Bot Token is extremely sensitive**. Anyone with your token can take full control of your bot.

**DO NOT** commit it to a public repository. It's best to load it from an environment variable or a local config file that is ignored by Git.

Create a `.gitignore` file in your project directory with the following contents to prevent uploading sensitive files:

```
# Python virtual environment
venv/

# SQLite Database
*.db

# Other
__pycache__/
*.pyc
```
