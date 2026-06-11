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

# Simpan sehingga 200 mesej setiap user
user_messages = defaultdict(lambda: deque(maxlen=200))

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
            can_send_messages=True
        )
    )


# =========================
# MENU
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

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
                print("OPEN ERROR:", e)

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
                print("CLOSE ERROR:", e)

        await query.message.reply_text(
            f"🔒 Semua group ditutup.\n"
            f"✅ {success}/{len(GROUPS)} berjaya."
        )


# =========================
# COMMANDS
# =========================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update.effective_user.id):
        return

    await update.message.reply_text(
        f"🤖 VPW Manager Online\n\n"
        f"📊 Total Groups : {len(GROUPS)}\n"
        f"🛡 Anti Spam : {SPAM_LIMIT} mesej / {TIME_WINDOW} saat"
    )


async def openall(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update.effective_user.id):
        return

    success = 0

    for gid in GROUPS.values():
        try:
            await open_group(context.bot, gid)
            success += 1
        except Exception as e:
            print("OPEN ERROR:", e)

    await update.message.reply_text(
        f"🔓 Semua group dibuka.\n"
        f"✅ {success}/{len(GROUPS)} berjaya."
    )


async def closeall(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update.effective_user.id):
        return

    success = 0

    for gid in GROUPS.values():
        try:
            await close_group(context.bot, gid)
            success += 1
        except Exception as e:
            print("CLOSE ERROR:", e)

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

    if not update.effective_user:
        return

    if not update.effective_chat:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message

    # Owner bypass
    if user.id == OWNER_ID:
        return

    # Ignore private chat
    if update.effective_chat.type == "private":
        return

    # Admin bypass
    try:
        member = await context.bot.get_chat_member(
            chat_id,
            user.id
        )

        if member.status in ["administrator", "creator"]:
            return
    except:
        pass

    now = time.time()

    user_messages[user.id].append(
        (now, message.message_id, chat_id)
    )

    recent = [
        x for x in user_messages[user.id]
        if now - x[0] <= TIME_WINDOW
    ]

    user_messages[user.id] = deque(
        recent,
        maxlen=200
    )

    if len(recent) < SPAM_LIMIT:
        return

    try:

        all_messages = list(user_messages[user.id])

        # delete semua mesej spam yang direkod
        for _, msg_id, c_id in all_messages:

            try:
                await context.bot.delete_message(
                    chat_id=c_id,
                    message_id=msg_id
                )
            except:
                pass

        # kick user
        await context.bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user.id
        )

        # benarkan join semula
        await context.bot.unban_chat_member(
            chat_id=chat_id,
            user_id=user.id
        )

        user_messages[user.id].clear()

        await context.bot.send_message(
            chat_id,
            f"🚫 {user.first_name} dikeluarkan kerana spam."
        )

    except Exception as e:
        print("ANTI SPAM ERROR:", e)


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

    # Anti spam
    app.add_handler(
        MessageHandler(
            filters.ALL,
            anti_spam
        )
    )

    print("VPW Manager Bot Running...")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
