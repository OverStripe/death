from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
)
from pyrogram import Client
from pyrogram.errors import RPCError, UserNotParticipant, UserNotFound
import sqlite3
import asyncio
import re
from datetime import datetime

# ---------------------
# Configuration
# ---------------------
BOT_TOKEN = 'YOUR_BOT_TOKEN'
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
OWNER_ID = 7222795580  # Owner's Telegram User ID
OWNER_HANDLE = '@PhiloWise'
SESSION_NAMES = ['session1', 'session2', 'session3']

# ---------------------
# Database Initialization
# ---------------------
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    chat_link TEXT,
    status TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    account_creation TEXT,
    status TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()

# ---------------------
# Utility Functions
# ---------------------

# Restrict access to the owner only
def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            await update.message.reply_text("🚫 **Access Denied:** This command is restricted to the bot owner.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Extract Chat ID from a link
def extract_chat_id_from_link(link: str) -> str:
    match = re.search(r'(https?://t\.me/|@)([\w\d_]+)', link)
    if match:
        return match.group(2)
    return None

# Fetch User Info via Pyrogram
async def get_user_info(username: str):
    async with Client("info_session", api_id=API_ID, api_hash=API_HASH) as app:
        try:
            user = await app.get_users(username)
            user_info = {
                "id": user.id,
                "username": user.username or "N/A",
                "first_name": user.first_name or "N/A",
                "last_name": user.last_name or "N/A",
                "is_bot": user.is_bot,
                "dc_id": user.dc_id,
                "creation_date": datetime.utcfromtimestamp(user.date).strftime('%Y-%m-%d') if hasattr(user, 'date') else "N/A"
            }
            return user_info
        except UserNotFound:
            return {"error": "❌ User not found."}
        except RPCError as e:
            return {"error": f"❌ RPC Error: {e}"}
        except Exception as e:
            return {"error": f"❌ Unknown Error: {e}"}

# ---------------------
# Telegram Bot Handlers
# ---------------------

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = f"""
👋 **Welcome to the Advanced Bot!**

🔹 Use `/help` to see all available commands.  
🔹 Contact the bot owner: {OWNER_HANDLE}  

🚀 Let's get started!
"""
    keyboard = [
        [InlineKeyboardButton("📚 Help", callback_data='help')],
        [InlineKeyboardButton("📊 Status", callback_data='status')],
        [InlineKeyboardButton("👑 Owner", callback_data='owner')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# /help Command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **Available Commands:**

/start - 🏁 Display the welcome message  
/help - 📚 Show all available commands  
/status - 📊 Show bot status  
/owner - 👑 Contact the bot owner  

🔒 **Owner Only Commands:**  
/report <chat_link> - 🚨 Mass report a Telegram chat as spam  
/broadcast <message> - 📢 Send a message to all sessions  
/info @username - 🛠️ Get detailed information about a user  
"""
    await update.message.reply_text(help_text)

# /owner Command
async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👑 **Bot Owner:** {OWNER_HANDLE}\n💬 Feel free to reach out!")

# /info Command (Restricted to Owner)
@owner_only
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/info @username`")
        return

    username = context.args[0]
    await update.message.reply_text("⏳ **Fetching user information... Please wait.**")
    user_info = await get_user_info(username)

    if "error" in user_info:
        await update.message.reply_text(user_info["error"])
        return

    cursor.execute('INSERT INTO user_info (telegram_id, username, first_name, last_name, account_creation, status) VALUES (?, ?, ?, ?, ?, ?)', 
                   (user_info['id'], user_info['username'], user_info['first_name'], user_info['last_name'], user_info['creation_date'], "Fetched"))
    conn.commit()

    info_message = f"""
🛠️ **User Information:**
👤 **Name:** {user_info['first_name']} {user_info['last_name']}
🆔 **User ID:** `{user_info['id']}`
🔗 **Username:** @{user_info['username']}
📅 **Account Created:** {user_info['creation_date']}
🌐 **DC ID:** {user_info['dc_id']}
"""
    await update.message.reply_text(info_message)

# /status Command
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute('SELECT COUNT(*) FROM reports')
    report_count = cursor.fetchone()[0]
    await update.message.reply_text(f"✅ **Bot Status:** 🟢 Active\n📊 **Total Reports:** {report_count}")

# ---------------------
# Main Function
# ---------------------

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("owner", owner_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("info", info_command))
    
    print("🔄 Initializing Pyrogram sessions...")
    asyncio.run(bulk_session_init())

    print("🚀 Bot is now running...")
    application.run_polling()

# ---------------------
# Run Bot
# ---------------------
if __name__ == '__main__':
    main()
  
