# bot.py
import os
import random
import time
from datetime import datetime
from threading import Thread

from flask import Flask, render_template_string, redirect
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler

# === НАСТРОЙКИ ===
TOKEN = '7943446786:AAHCIqydV95YH6uurQ_pm_XcQUhtITPVc_E'
ADMIN_ID = 6894162425
CHECK_INTERVAL = 60  # каждые 60 секунд

COINS = [f"COIN{i}/USDT" for i in range(1, 201)]

# Создаём приложения
telegram_app = ApplicationBuilder().token(TOKEN).build()
flask_app    = Flask(__name__)

# Хранилище сигналов за сегодня
signals_today = []


def generate_fake_signal() -> str:
    """Генерим фейковый сигнал с TP/SL."""
    coin = random.choice(COINS)
    price = round(random.uniform(10, 1000), 2)
    tp = round(price * 1.02, 2)   # +2%
    sl = round(price * 0.98, 2)   # –2%
    ttime = datetime.now().strftime("%H:%M:%S")
    side = random.choice(["LONG", "SHORT"])
    return (
        f"**Сигнал {side}**\n"
        f"Пара: {coin}\n"
        f"Цена: {price}\n"
        f"Тейк‑Профит: {tp}\n"
        f"Стоп‑Лосс: {sl}\n"
        f"Время: {ttime}"
    )


async def send_signal_job(context):
    """Шлём сигнал в админ‑чат и сохраняем его в историю."""
    msg = generate_fake_signal()
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=msg,
        parse_mode="Markdown"
    )
    signals_today.append(msg)


def signal_loop():
    """Блокирующий цикл, каждые CHECK_INTERVAL секунд запускает отправку сигнала."""
    while True:
        time.sleep(CHECK_INTERVAL)
        telegram_app.create_task(send_signal_job(telegram_app))


@telegram_app.command("start")
async def cmd_start(update, context):
    await update.message.reply_text("Привет! Я бот CryptoBot, слежу за сигналами.")


@telegram_app.command("signal")
async def cmd_signal(update, context):
    """Выслать сигнал вручную."""
    txt = generate_fake_signal()
    await update.message.reply_text(txt, parse_mode="Markdown")


@telegram_app.command("stats")
async def cmd_stats(update, context):
    """Показать сколько сигналов пришло сегодня."""
    await update.message.reply_text(
        f"Всего сигналов сегодня: {len(signals_today)}"
    )


# ——— ВЕБ‑АДМИНКА на Flask ———

@flask_app.route("/")
def route_root():
    return redirect("/admin")


@flask_app.route("/admin")
def admin_panel():
    stats = f"Всего сигналов сегодня: {len(signals_today)}"
    html = """
    <h1>CryptoBot Admin</h1>
    <p>{{stats}}</p>
    """
    return render_template_string(html, stats=stats)


def run_flask():
    """Запуск Flask‑сервера на нужном порту."""
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)


def main():
    # 1) Запускаем веб‑панель в фоне
    Thread(target=run_flask, daemon=True).start()
    # 2) Запускаем цикл генерации сигналов в фоне
    Thread(target=signal_loop, daemon=True).start()
    # 3) Запускаем Telegram‑бота (polling)
    telegram_app.run_polling()


if __name__ == "__main__":
    main()
