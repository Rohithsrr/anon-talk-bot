import telegram.error
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand, BotCommandScopeChat
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
import os
import sqlite3
import time
import asyncio
import html
from datetime import datetime

# --- Configuration ---
BOT_TOKEN = "7466135203:AAEmRO7RyrmL3VW-lBt2L2xFKJBELUocTr4"
ADMIN_IDS = {2076441468}
REFERRAL_THRESHOLD = 3

# --- Database Setup ---
DB_FILE = "anontalk.db"

def init_db():
    """Initializes the DB and adds new columns if they don't exist."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referred_by INTEGER,
            referral_count INTEGER DEFAULT 0,
            gender TEXT
        )
    ''')
    # NEW: Add join_date column to track daily users, if it doesn't exist
    try:
        cur.execute("ALTER TABLE users ADD COLUMN join_date INTEGER")
        print("Database updated: Added 'join_date' column to users table.")
    except sqlite3.OperationalError:
        pass # Column already exists

    con.commit()
    con.close()

def db_execute(query, params=()):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(query, params)
    con.commit()
    con.close()

def db_fetchone(query, params=()):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(query, params)
    result = cur.fetchone()
    con.close()
    return result

def db_fetchall(query, params=()):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(query, params)
    result = cur.fetchall()
    con.close()
    return result

# --- State Management & Keyboards (Unchanged) ---
waiting_users = []
active_chats = {}

def can_use_gender_filter(user_id: int) -> bool:
    user = db_fetchone("SELECT referral_count FROM users WHERE user_id = ?", (user_id,))
    if not user:
        return False
    return user[0] >= REFERRAL_THRESHOLD

start_buttons = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔎 Find a Partner", callback_data="chat")],
    [InlineKeyboardButton("🤝 Refer a Friend", callback_data="refer")],
])

chat_buttons = InlineKeyboardMarkup([
    [InlineKeyboardButton("⏭ Next", callback_data="next"),
     InlineKeyboardButton("🚫 Stop", callback_data="stop")],
])

gender_choice_buttons = InlineKeyboardMarkup([
    [InlineKeyboardButton("Random Partner", callback_data="setgender_any")],
    [InlineKeyboardButton("Talk to a Boy 👦", callback_data="setgender_male")],
    [InlineKeyboardButton("Talk to a Girl 👧", callback_data="setgender_female")],
])

# --- Helper & Core Command Functions ---

async def get_reply(update: Update):
    return update.message if update.message else update.callback_query.message

# MODIFIED: start function now records the join date
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    existing_user = db_fetchone("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not existing_user:
        # NEW: Store the current timestamp when a new user joins
        join_timestamp = int(time.time())
        db_execute("INSERT INTO users (user_id, join_date) VALUES (?, ?)", (user_id, join_timestamp))

    # Referral handling logic (unchanged)
    args = context.args
    if args and args[0].startswith("from_"):
        referrer_id = args[0].replace("from_", "")
        if referrer_id.isdigit() and str(user_id) != referrer_id:
            referrer_id = int(referrer_id)
            if not db_fetchone("SELECT referred_by FROM users WHERE user_id = ? AND referred_by IS NOT NULL", (user_id,)):
                db_execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
                db_execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
                try:
                    new_count = db_fetchone('SELECT referral_count FROM users WHERE user_id = ?', (referrer_id,))[0]
                    await context.bot.send_message(chat_id=referrer_id, text=f"🎉 You have a new referral! Your total is now {new_count}.")
                    if new_count >= REFERRAL_THRESHOLD:
                         await context.bot.send_message(chat_id=referrer_id, text="Congratulations! You have unlocked the gender filter feature.")
                except telegram.error.Forbidden:
                    print(f"Bot was blocked by referrer {referrer_id}")

    await (await get_reply(update)).reply_text(
        "👋 Welcome to AnonTalk AI!\n\nFind random strangers to chat with anonymously. Get started below!",
        reply_markup=start_buttons
    )

# MODIFIED: stats command now shows daily new users
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    
    # Get total users
    total_users = db_fetchone("SELECT COUNT(*) FROM users")[0]
    
    # NEW: Get users who joined today
    today = datetime.utcnow().date()
    start_of_day_timestamp = int(datetime.combine(today, datetime.min.time()).timestamp())
    new_users_today = db_fetchone("SELECT COUNT(*) FROM users WHERE join_date >= ?", (start_of_day_timestamp,))[0]

    top_referrers = db_fetchall("SELECT user_id, referral_count FROM users ORDER BY referral_count DESC LIMIT 5")
    
    text = (
        f"📊 *Bot Statistics*\n\n"
        f"New Users Today: *{new_users_today}*\n"
        f"Total Users: *{total_users}*\n\n"
        f"🏆 *Top Referrers:*\n"
    )
    for i, (uid, count) in enumerate(top_referrers):
        text += f"{i+1}. User `{uid}`: {count} referrals\n"
        
    await (await get_reply(update)).reply_text(text, parse_mode="Markdown")

# --- All other handlers (chat, stop, next, refer, etc.) remain unchanged ---
# They are included below for the complete code.

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await (await get_reply(update)).reply_text("⚠️ You are already in a chat. Use /stop to end it first.")
        return
    if any(u[0] == user_id for u in waiting_users):
        await (await get_reply(update)).reply_text("⏳ You are already in the waiting queue.")
        return
    user_record = db_fetchone("SELECT gender FROM users WHERE user_id = ?", (user_id,))
    user_gender = user_record[0] if user_record else None
    if not user_gender:
        if not user_record:
            db_execute("INSERT INTO users (user_id, join_date) VALUES (?, ?)", (user_id, int(time.time())))
        await context.bot.send_message(
            user_id,
            "To help us connect you better, please tell us your gender. This is only asked once.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("I'm a Boy 👦", callback_data="setmygender_male")],
                [InlineKeyboardButton("I'm a Girl 👧", callback_data="setmygender_female")],
            ])
        )
        return
    await (await get_reply(update)).reply_text("Who would you like to talk to?", reply_markup=gender_choice_buttons)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if any(u[0] == user_id for u in waiting_users):
        waiting_users[:] = [u for u in waiting_users if u[0] != user_id]
        await (await get_reply(update)).reply_text("You have been removed from the queue.", reply_markup=start_buttons)
        return
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        end_message = "Chat ended! Found someone cool? Share AnonTalk with your friends! 🤝"
        await context.bot.send_message(user_id, end_message, reply_markup=start_buttons)
        try:
            await context.bot.send_message(partner_id, "Your partner has left the chat.", reply_markup=start_buttons)
        except telegram.error.Forbidden:
            print(f"Bot was blocked by user {partner_id}")
    else:
        await (await get_reply(update)).reply_text("⚠️ You are not in a chat or queue.", reply_markup=start_buttons)

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop(update, context)
    await chat(update, context)

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=from_{user.id}"
    count = db_fetchone("SELECT referral_count FROM users WHERE user_id = ?", (user.id,))[0]
    await (await get_reply(update)).reply_text(
        f"💌 Invite your friends to unlock the gender filter!\n\n"
        f"Your referral link:\n`{link}`\n\n"
        f"Total users invited: *{count}*\n"
        f"You need *{REFERRAL_THRESHOLD}* referrals to get free access.",
        parse_mode="Markdown"
    )

async def set_my_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    gender = query.data.split('_')[1]
    db_execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
    await query.message.delete()
    await context.bot.send_message(user_id, f"✅ Great! Your gender is set to {gender}. Now, let's find you a partner.")
    await chat(update, context)

async def set_partner_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    preference = query.data.split('_')[1]
    if preference in ['male', 'female'] and not can_use_gender_filter(user_id):
        await query.message.edit_text(
            f"⚠️ Gender filter is a premium feature.\n\n"
            f"You can unlock it for free by referring **{REFERRAL_THRESHOLD}** friends.",
            parse_mode="Markdown"
        )
        return
    await query.message.edit_text("⏳ Searching for a partner...")
    my_gender = db_fetchone("SELECT gender FROM users WHERE user_id = ?", (user_id,))[0]
    partner = None
    for i, (p_id, p_preference) in enumerate(waiting_users):
        partner_gender = db_fetchone("SELECT gender FROM users WHERE user_id = ?", (p_id,))[0]
        if (preference == 'any' or preference == partner_gender) and (p_preference == 'any' or p_preference == my_gender):
            partner = waiting_users.pop(i)
            break
    if partner:
        partner_id = partner[0]
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        for uid in [user_id, partner_id]:
            try:
                await context.bot.send_message(uid, "✅ You are now connected! Say hi.", reply_markup=chat_buttons)
            except telegram.error.Forbidden:
                other_user = active_chats.pop(uid, None)
                if other_user and other_user in active_chats:
                    active_chats.pop(other_user)
                    await context.bot.send_message(other_user, "❌ Connection failed. Please try again.")
                print(f"Bot blocked by {uid}, failed to start chat.")
    else:
        waiting_users.append((user_id, preference))
        await context.bot.send_message(user_id, "⏳ All our users are busy right now. We'll notify you as soon as someone connects.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    if data.startswith("setmygender_"): await set_my_gender(update, context)
    elif data.startswith("setgender_"): await set_partner_preference(update, context)
    elif data == "chat":
        await query.message.delete()
        await chat(update, context)
    elif data == "stop": await stop(update, context)
    elif data == "next": await next_chat(update, context)
    elif data == "refer": await refer(update, context)

async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in active_chats:
        await update.message.reply_text("⚠️ You are not in a chat. Use /chat to find a partner.", reply_markup=start_buttons)
        return
    partner_id = active_chats[uid]
    msg = update.message
    try:
        if msg.text: await context.bot.send_message(partner_id, msg.text)
        elif msg.photo: await context.bot.send_photo(partner_id, msg.photo[-1].file_id, caption=msg.caption)
        elif msg.video: await context.bot.send_video(partner_id, msg.video.file_id, caption=msg.caption)
        elif msg.voice: await context.bot.send_voice(partner_id, msg.voice.file_id)
        elif msg.sticker: await context.bot.send_sticker(partner_id, msg.sticker.file_id)
        else: await msg.reply_text("⚠️ This media type cannot be sent.")
    except telegram.error.Forbidden:
        await msg.reply_text("⚠️ Could not send message. The other user may have blocked the bot.")
        await stop(update, context)
    except Exception as e:
        await msg.reply_text("⚠️ An error occurred while sending your message.")
        print(f"Relay error: {e}")

# --- Bot Setup and Main Loop ---

# MODIFIED: post_init now sets different commands for admins
async def post_init(application: telegram.ext.Application):
    """Sets bot commands for regular users and admins after initialization."""
    # Commands for regular users
    user_commands = [
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("chat", "🔎 Find a new partner"),
        BotCommand("next", "⏭ Find another partner"),
        BotCommand("stop", "🚫 Stop the current chat"),
        BotCommand("refer", "🤝 Refer friends"),
    ]
    await application.bot.set_my_commands(user_commands)

    # NEW: Extra commands for admins
    admin_commands = user_commands + [
        BotCommand("stats", "📊 View bot statistics"),
        BotCommand("broadcast", "📢 Send a message to all users"),
    ]
    for admin_id in ADMIN_IDS:
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(admin_id))
        except Exception as e:
            print(f"Could not set commands for admin {admin_id}: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"An exception was raised while handling an update: {context.error}")

def main():
    print("Initializing database...")
    init_db()
    
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Register handlers
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("refer", refer))
    # NEW: Add handlers for admin commands
    app.add_handler(CommandHandler("stats", stats))
    # The broadcast handler was missing, adding it back
    async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        if not context.args:
            await update.message.reply_text("Usage: /broadcast <message>")
            return
        message_text = " ".join(context.args)
        all_users = db_fetchall("SELECT user_id FROM users")
        await update.message.reply_text(f"📢 Starting broadcast to {len(all_users)} users...")
        sent_count, failed_count = 0, 0
        for (uid,) in all_users:
            try:
                await context.bot.send_message(uid, f"📢 *Broadcast Message*\n\n{message_text}", parse_mode="Markdown")
                sent_count += 1
            except Exception:
                failed_count += 1
            await asyncio.sleep(0.1)
        await update.message.reply_text(f"Broadcast finished.\n\nSent: {sent_count}\nFailed: {failed_count}")

    app.add_handler(CommandHandler("broadcast", broadcast))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, relay))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
