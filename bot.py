import os
import random
import asyncio
from datetime import datetime
from threading import Thread
from flask import Flask, request, Response

from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# === НАСТРОЙКИ (из Railway переменных окружения) ===
TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
PUBLIC_URL = os.environ["PUBLIC_URL"]  # https://web-production-xxxxx.up.railway.app

# === Flask-приложение (админка) ===
flask_app = Flask(__name__)

invite_tokens = {"abc123": False, "xyz789": False}
authorized_users = set()
signals_today = []

def get_stats():
    return f"Сигналов за сегодня: {len(signals_today)}"

@flask_app.route("/")
def index():
    return "Бот работает!"

@flask_app.route("/admin")
def admin():
    stats = get_stats()
    users = "<br>".join(str(uid) for uid in authorized_users)
    tokens = "<br>".join(
        f"{token} - {'использован' if used else 'свободен'}"
        for token, used in invite_tokens.items()
    )
    return f"""
    <h1>Admin панель</h1>
    <p><b>Статистика:</b> {stats}</p>
    <p><b>Пользователи:</b><br>{users}</p>
    <p><b>Инвайт токены:</b><br>{tokens}</p>
    """

# === Telegram бота ===
app_telegram = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! Я живой."
    )

async def secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Это секрет для админа!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_stats())

app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("admin", secret))
app_telegram.add_handler(CommandHandler("stats", stats_command))

# Устанавливаем webhook (если нужно)
async def set_webhook():
    url = f"{PUBLIC_URL}/webhook"
    await app_telegram.bot.set_webhook(url)

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    await app_telegram.update_queue.put(Update.de_json(request.json, app_telegram.bot))
    return Response("ok", status=200)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

def run_bot():
    asyncio.run(app_telegram.initialize())
    asyncio.run(set_webhook())
    asyncio.run(app_telegram.start())

if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_bot()
