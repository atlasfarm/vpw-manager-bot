```python
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import os
import time
from collections import defaultdict, deque

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8615034394

GROUPS = {
    "101": -1003914286406,
    "102": -1003914681805,
    "103": -1003709655723,
    "104": -1003922936210,
    "105": -1003999685997,
    "111": -1003828994218,
    "112": -1004294894289,
    "113": -1003722823254,
    "114": -1003953094321,
    "116": -1003856893148,
    "119": -1003962766599,
    "agfx": -1003530852225,
    "midf": -1003910206191,
}

SPAM_LIMIT = 8
TIME_WINDOW = 10
MUTE_DURATION = 3600  # 1 jam

# chat_id -> user_id -> deque(timestamp, message_id)
user_messages = defaultdict(
    lambda: defaultdict(
        lambda: deque(maxlen=50)
    )
)

# Elak trigger banyak kali
cooldowns = {}


# =========================
# HELPERS
# =========================

def is_owner(user_id):
    return user_id == OWNER_ID


async def close_group(bot, group_id):
    await bot.set_chat_permissions(
        chat_id=group_id,
        permissions=ChatPermissions(
            can_send_messages=False
        )
    )


async def open_group(bot, group_id):
    await bot.set_chat_permissions(
        chat_id=group_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_invite_users=True
        )
    )


# =========================
# MENU
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return

    if not is_owner(update.effective_user.id):
        return

    keyboard = [
        [InlineKeyboardButton("📊 Status", callback_data="status")],
        [
            InlineKeyboardButton("🔓 Open All", callback_data="openall"),
            InlineKeyboardButton("🔒 Close All", callback_data="closeall")
        ]
    ]

    await update.message.reply_text(
        "🤖 VPW Manager Control Panel",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    if query.data == "status":

        await query.message.reply_text(
            f"🤖 VPW Manager Online\n\n"
            f"📊 Total Groups : {len(GROUPS)}\n"
            f"🛡 Anti Spam : {SPAM_LIMIT} mesej / {TIME_WINDOW} saat"
        )

    elif query.data == "openall":

        success = 0

        for gid in GROUPS.values():

            try:
                await open_group(context.bot, gid)
                success += 1

            except Exception as e:
                print(f"OPEN ERROR {gid}: {e}")

        await query.message.reply_text(
            f"🔓 Semua group dibuka.\n"
            f"✅ {success}/{len(GROUPS)} berjaya."
        )

    elif query.data == "closeall":

        success = 0

        for gid in GROUPS.values():

            try:
                await close_group(context.bot, gid)
                success += 1

            except Exception as e:
                print(f"CLOSE ERROR {gid}: {e}")

        await query.message.reply_text(
            f"🔒 Semua group ditutup.\n"
            f"✅ {success}/{len(GROUPS)} berjaya."
        )


# =========================
# COMMANDS
# =========================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return

    if not is_owner(update.effective_user.id):
        return

    await update.message.reply_text(
        f"🤖 VPW Manager Online\n\n"
        f"📊 Total Groups : {len(GROUPS)}\n"
        f"🛡 Anti Spam : {SPAM_LIMIT} mesej / {TIME_WINDOW} saat"
    )


async def openall(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return

    if not is_owner(update.effective_user.id):
        return

    success = 0

    for gid in GROUPS.values():

        try:
            await open_group(context.bot, gid)
            success += 1

        except Exception as e:
            print(f"OPEN ERROR {gid}: {e}")

    await update.message.reply_text(
        f"🔓 Semua group dibuka.\n"
        f"✅ {success}/{len(GROUPS)} berjaya."
    )


async def closeall(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return

    if not is_owner(update.effective_user.id):
        return

    success = 0

    for gid in GROUPS.values():

        try:
            await close_group(context.bot, gid)
            success += 1

        except Exception as e:
            print(f"CLOSE ERROR {gid}: {e}")

    await update.message.reply_text(
        f"🔒 Semua group ditutup.\n"
        f"✅ {success}/{len(GROUPS)} berjaya."
    )


# =========================
# ANTI SPAM
# =========================

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user = update.effective_user
    chat = update.effective_chat
    message = update.message

    if not user or not chat:
        return

    # Ignore private chat
    if chat.type == "private":
        return

    # Owner bypass
    if user.id == OWNER_ID:
        return

    # Ignore service messages
    if (
        message.new_chat_members or
        message.left_chat_member or
        message.group_chat_created or
        message.supergroup_chat_created or
        message.channel_chat_created or
        message.pinned_message
    ):
        return

    # Admin bypass
    try:

        member = await context.bot.get_chat_member(
            chat.id,
            user.id
        )

        if member.status in ("administrator", "creator"):
            return

    except Exception:
        return

    now = time.time()

    cooldown_key = (chat.id, user.id)

    # Elak trigger banyak kali
    if cooldown_key in cooldowns:

        if now - cooldowns[cooldown_key] < 60:
            return

        del cooldowns[cooldown_key]

    records = user_messages[chat.id][user.id]

    records.append(
        (
            now,
            message.message_id
        )
    )

    recent = deque(
        [
            msg
            for msg in records
            if now - msg[0] <= TIME_WINDOW
        ],
        maxlen=50
    )

    user_messages[chat.id][user.id] = recent

    # Belum capai limit
    if len(recent) < SPAM_LIMIT:
        return

    cooldowns[cooldown_key] = now

    try:

        # Delete mesej spam
        for _, msg_id in recent:

            try:
                await context.bot.delete_message(
                    chat_id=chat.id,
                    message_id=msg_id
                )

            except Exception:
                pass

        # Mute user selama 1 jam
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            ),
            until_date=int(now) + MUTE_DURATION
        )

        user_messages[chat.id][user.id].clear()

        await context.bot.send_message(
            chat.id,
            f"🚫 {user.mention_html()} telah dimute selama 1 jam kerana spam.",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"ANTI SPAM ERROR: {e}")


# =========================
# MAIN
# =========================

def main():

    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN tidak dijumpai dalam Railway Variables."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    # Menu
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Commands
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("openall", openall))
    app.add_handler(CommandHandler("closeall", closeall))

    # Anti Spam
    app.add_handler(
        MessageHandler(
            (
                filters.TEXT |
                filters.PHOTO |
                filters.VIDEO |
                filters.Document.ALL |
                filters.Sticker.ALL |
                filters.VOICE |
                filters.AUDIO |
                filters.ANIMATION
            ) & ~filters.COMMAND,
            anti_spam
        )
    )

    print("VPW Manager Bot Running...")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
```
