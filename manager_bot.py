from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
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

# user_id -> deque[(timestamp, msg_id, chat_id)]
user_messages = defaultdict(lambda: deque(maxlen=200))


# =========================
# HELPERS
# =========================

def is_owner(user_id: int) -> bool:
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
# COMMANDS
# =========================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    await update.message.reply_text(
        f"🤖 VPW Manager Online\n"
        f"📊 Total Groups: {len(GROUPS)}\n"
        f"🛡 Anti Spam: {SPAM_LIMIT} mesej / {TIME_WINDOW} saat"
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
        f"🔓 Semua group dibuka.\n✅ {success}/{len(GROUPS)} berjaya."
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
        f"🔒 Semua group ditutup.\n✅ {success}/{len(GROUPS)} berjaya."
    )


async def open_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "Contoh:\n/open 101"
        )
        return

    code = context.args[0].lower()

    if code not in GROUPS:
        await update.message.reply_text("❌ Group tidak dijumpai.")
        return

    try:
        await open_group(context.bot, GROUPS[code])
        await update.message.reply_text(f"🔓 Group {code} dibuka.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n{e}")


async def close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "Contoh:\n/close 101"
        )
        return

    code = context.args[0].lower()

    if code not in GROUPS:
        await update.message.reply_text("❌ Group tidak dijumpai.")
        return

    try:
        await close_group(context.bot, GROUPS[code])
        await update.message.reply_text(f"🔒 Group {code} ditutup.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n{e}")


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

    # owner bypass
    if user.id == OWNER_ID:
        return

    # private chat ignore
    if update.effective_chat.type == "private":
        return

    now = time.time()

    user_messages[user.id].append(
        (now, message.message_id, chat_id)
    )

    recent = [
        x for x in user_messages[user.id]
        if now - x[0] <= TIME_WINDOW
    ]

    user_messages[user.id] = deque(recent, maxlen=30)

    if len(recent) < SPAM_LIMIT:
        return

    try:

        # delete spam messages
        for _, msg_id, c_id in recent:
            try:
                await context.bot.delete_message(
                    chat_id=c_id,
                    message_id=msg_id
                )
            except Exception:
                pass

        # kick user
        await context.bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user.id
        )

        # unban supaya boleh join semula
        await context.bot.unban_chat_member(
            chat_id=chat_id,
            user_id=user.id
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚫 {user.first_name} dikeluarkan kerana spam."
        )

        user_messages[user.id].clear()

    except Exception as e:
        print("ANTI SPAM ERROR:", e)


# =========================
# MAIN
# =========================

def main():

    if not TOKEN:
        raise ValueError("BOT_TOKEN tidak dijumpai dalam Railway Variables.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("openall", openall))
    app.add_handler(CommandHandler("closeall", closeall))

    app.add_handler(CommandHandler("open", open_cmd))
    app.add_handler(CommandHandler("close", close_cmd))

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL,
            anti_spam
        )
    )

    print("VPW Manager Bot Running...")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
