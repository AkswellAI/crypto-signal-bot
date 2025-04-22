import os
import random
import time
import io
import string
import secrets
from datetime import datetime
from threading import Thread

import matplotlib.pyplot as plt
from flask import Flask, render_template_string, request, redirect, send_file
from telegram import Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# === НАСТРОЙКИ ===
TOKEN = "7943446786:AAHCIqydv95YH6uurQ_pm_xcQuhtITPVc_E"
ADMIN_ID = 689416245
CHECK_INTERVAL = 60  # сек

# допустимые монеты и токены-приглашения
COINS = [f"COIN{i}/USDT" for i in range(1, 201)]
invite_tokens = {secrets.token_urlsafe(8): False for _ in range(5)}

# статистика сигналов
signals_today = []
authorized_users = set()

# инициализация Flask и Telegram Application
flask_app = Flask(__name__)
telegram_app: Application


# --- ЛОГИКА СИГНАЛОВ ---
def generate_fake_signal():
    coin = random.choice(COINS)
    rsi = random.randint(10, 90)
    when = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    signal = f"{when} — {coin}, RSI={rsi}"
    return signal

def signal_loop():
    bot = Bot(token=TOKEN)
    while True:
        s = generate_fake_signal()
        signals_today.append(s)
        for uid in list(authorized_users):
            bot.send_message(chat_id=uid, text=s)
        time.sleep(CHECK_INTERVAL)

# --- HANDLERЫ ДЛЯ TELEGRAM ---
async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли /token <твой токен>, чтобы разблокировать рассылку."
    )

async def token_command(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) != 1:
        await update.message.reply_text("Используй /token <твой_токен>.")
        return
    t = context.args[0]
    if t in invite_tokens and not invite_tokens[t]:
        invite_tokens[t] = True
        authorized_users.add(user_id)
        await update.message.reply_text("Токен принят, ты в рассылке!")
    else:
        await update.message.reply_text("Неверный или уже использованный токен.")

async def stats_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\n".join(signals_today[-10:] or ["—"]))

async def help_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Доступные команды: /start /token /stats.")

# --- ВЕБ‑АДМИНКА ---
@flask_app.route("/", methods=["GET"])
def index():
    return redirect("/admin")

@flask_app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.method == "POST":
        # сгенерировать новый токен
        new_t = secrets.token_urlsafe(8)
        invite_tokens[new_t] = False
    # список токенов
    tokens_html = "<ul>" + "".join(
        f"<li>{t} — {'использован' if used else 'свободен'}</li>"
        for t, used in invite_tokens.items()
    ) + "</ul>"
    # список пользователей
    users_html = "<ul>" + "".join(f"<li>{u}</li>" for u in authorized_users) + "</ul>"
    # график количества сигналов по часам
    times = [datetime.strptime(s.split(" — ")[0], "%Y-%m-%d %H:%M:%S UTC") for s in signals_today]
    hours = [t.hour for t in times]
    plt.figure()
    plt.hist(hours, bins=range(25))
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)

    template = """
    <h1>Admin Панель CryptoBot</h1>
    <form method="post"><button type="submit">Новый токен</button></form>
    <h2>Токены</h2>{{ tokens|safe }}
    <h2>Пользователи</h2>{{ users|safe }}
    <h2>График сигналов по часам</h2>
    <img src="/plot.png">
    """
    return render_template_string(
        template, tokens=tokens_html, users=users_html
    )

@flask_app.route("/plot.png")
def plot_png():
    # построить тот же график заново
    times = [datetime.strptime(s.split(" — ")[0], "%Y-%m-%d %H:%M:%S UTC") for s in signals_today]
    hours = [t.hour for t in times]
    plt.figure()
    plt.hist(hours, bins=range(25))
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


def main():
    global telegram_app
    # 1) Telegram
    telegram_app = ApplicationBuilder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("token", token_command))
    telegram_app.add_handler(CommandHandler("stats", stats_command))
    telegram_app.add_handler(CommandHandler("help", help_command))

    # 2) запустить цикл сигналов
    Thread(target=signal_loop, daemon=True).start()

    # 3) запустить Flask на доступном порту (Railway)
    port = int(os.environ.get("PORT", 8080))
    Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=port, debug=False),
        daemon=True
    ).start()

    # 4) инициализировать polling Telegram
    telegram_app.run_polling()


if __name__ == "__main__":
    main()
