import os
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)
from flask import Flask, request, Response

# === НАСТРОЙКИ (берутся из env) ===
TOKEN      = os.environ["BOT_TOKEN"]
ADMIN_ID   = int(os.environ["ADMIN_ID"])
PUBLIC_URL = os.environ["PUBLIC_URL"]  # ваш Railway URL

# === Инициализируем телеграм-приложение ===
app_telegram = ApplicationBuilder().token(TOKEN).build()

# === Команды бота ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! Я живой."
    )

async def secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Это секрет для админа!")

# Регистрируем хендлеры
app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("secret", secret))


# === Flask-сервер для Webhook ===
app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def receive_update():
    """Telegram шлет сюда POST с обновлениями."""
    data = request.get_json(force=True)
    update = Update.de_json(data, Bot(TOKEN))
    # кладем апдейт в очередь обработчика
    app_telegram.update_queue.put(update)
    return Response("OK", status=200)


if __name__ == "__main__":
    # ставим webhook у бота на наш public URL
    webhook_url = f"{PUBLIC_URL}/webhook/{TOKEN}"
    Bot(TOKEN).set_webhook(webhook_url)

    # запускаем Flask на нужном порту
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
