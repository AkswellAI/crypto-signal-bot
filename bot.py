import random
import time
from datetime import datetime
from telegram import Bot, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler
from threading import Thread
import matplotlib.pyplot as plt
import io
import os
import string
import secrets
from flask import Flask, render_template_string, redirect

# === НАСТРОЙКИ ===
TOKEN = '7943446786:AAHCIqydV95YH6uurQ_pm_XcQUhtITPVc_E'
admin_id = 6894162425
CHECK_INTERVAL = 60

COINS = [f"COIN{i}/USDT" for i in range(1, 201)]
bot = Bot(token=TOKEN)
signals_today = []
authorized_users = set()
invite_tokens = {'abc123': False, 'xyz789': False}

# === СИГНАЛ ===
def generate_fake_signal():
    coin = random.choice(COINS)
    rsi = random.randint(10, 90)
    price = round(random.uniform(1, 1000), 2)
    sma = price + random.uniform(-50, 50)

    if rsi < 30 and price > sma:
        signal_type = 'LONG'
    elif rsi > 70 and price < sma:
        signal_type = 'SHORT'
    else:
        return None

    return {
        'coin': coin,
        'type': signal_type,
        'price': price,
        'time': datetime.now(),
        'profit': round(random.uniform(0.5, 3.5) * (1 if signal_type == 'LONG' else -1), 2)
    }

# === ОТПРАВКА СИГНАЛА ===
def send_signal(signal):
    price = signal['price']
    if signal['type'] == 'LONG':
        tp = round(price * 1.025, 2)
        sl = round(price * 0.985, 2)
    else:
        tp = round(price * 0.975, 2)
        sl = round(price * 1.015, 2)

    signal['tp'] = tp
    signal['sl'] = sl

    msg = f"**Сигнал {signal['type']}**\n" \
          f"Пара: {signal['coin']}\n" \
          f"Цена входа: {price}\n" \
          f"Take Profit: {tp}\n" \
          f"Stop Loss: {sl}\n" \
          f"Время: {signal['time'].strftime('%H:%M:%S')}"

    for user_id in authorized_users:
        bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")

# === ЦИКЛ СИГНАЛОВ ===
def signal_loop():
    while True:
        signal = generate_fake_signal()
        if signal:
            signals_today.append(signal)
            send_signal(signal)
        time.sleep(CHECK_INTERVAL)

# === СТАТИСТИКА ===
def get_stats():
    today = datetime.now().date()
    today_signals = [s for s in signals_today if s['time'].date() == today]
    longs = [s for s in today_signals if s['type'] == 'LONG']
    shorts = [s for s in today_signals if s['type'] == 'SHORT']
    total_profit = sum(s['profit'] for s in today_signals)
    return f"Статистика за сегодня:\n" \
           f"Всего сигналов: {len(today_signals)}\n" \
           f"LONG: {len(longs)}\n" \
           f"SHORT: {len(shorts)}\n" \
           f"Условная прибыль: {round(total_profit, 2)}%"

# === КОМАНДЫ ===
async def start_command(update, context):
    args = context.args
    user_id = update.effective_chat.id
    username = update.effective_chat.username or "Без username"

    if not args:
        await update.message.reply_text("Используй: /start <токен>")
        return

    token = args[0]
    if token in invite_tokens and not invite_tokens[token]:
        authorized_users.add(user_id)
        invite_tokens[token] = True
        await update.message.reply_text("Добро пожаловать! Ты авторизован.")
        await bot.send_message(admin_id, text=f"@{username} (ID: {user_id}) активировал токен `{token}`.", parse_mode="Markdown")
    elif token in invite_tokens:
        await update.message.reply_text("Этот токен уже использован.")
    else:
        await update.message.reply_text("Неверный токен.")

async def stats_command(update, context):
    if update.effective_chat.id not in authorized_users:
        await update.message.reply_text("Ты не авторизован.")
        return
    await update.message.reply_text(get_stats())

async def plot_command(update, context):
    if update.effective_chat.id not in authorized_users:
        await update.message.reply_text("Ты не авторизован.")
        return

    today = datetime.now().date()
    data = [s for s in signals_today if s['time'].date() == today]
    if not data:
        await update.message.reply_text("Сигналов нет.")
        return

    times = [s['time'].strftime('%H:%M') for s in data]
    profits = [sum(s['profit'] for s in data[:i+1]) for i in range(len(data))]

    plt.figure(figsize=(8, 4))
    plt.plot(times, profits, marker='o')
    plt.xticks(rotation=45)
    plt.title("Прибыль за сегодня")
    plt.xlabel("Время")
    plt.ylabel("Прибыль (%)")
    plt.grid(True)

    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    await update.message.reply_photo(InputFile(buffer, filename='plot.png'))
    buffer.close()

async def generate_token_command(update, context):
    if update.effective_chat.id != admin_id:
        await update.message.reply_text("Нет прав.")
        return
    token = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    invite_tokens[token] = False
    await update.message.reply_text(f"Новый токен: `{token}`", parse_mode='Markdown')

async def users_command(update, context):
    if update.effective_chat.id != admin_id:
        await update.message.reply_text("Нет доступа.")
        return
    if not authorized_users:
        await update.message.reply_text("Пользователи не авторизованы.")
        return
    users = "\n".join([f"{i+1}. ID: {uid}" for i, uid in enumerate(authorized_users)])
    await update.message.reply_text("Пользователи:\n" + users)

async def tokens_command(update, context):
    if update.effective_chat.id != admin_id:
        await update.message.reply_text("Нет доступа.")
        return
    tokens = "\n".join([f"{tkn} — {'OK' if used else 'Свободен'}" for tkn, used in invite_tokens.items()])
    await update.message.reply_text("Токены:\n" + tokens)

# === ВЕБ-АДМИНКА ===
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return redirect("/admin")

@flask_app.route('/admin')
def admin_panel():
    stats = get_stats()
    token_list = "<ul>" + "".join(
        f"<li>{tkn} — {'OK' if used else 'Свободен'}</li>" for tkn, used in invite_tokens.items()
    ) + "</ul>"
    users_list = "<ul>" + "".join(f"<li>{uid}</li>" for uid in authorized_users) + "</ul>"
    html = f"""
    <h1>CryptoBot Admin</h1>
    <form method='post' action='/generate'><button>Создать токен</button></form>
    <h2>Статистика</h2>
    <pre>{stats}</pre>
    <h2>График прибыли</h2>
    <img src='/plot.png'>
    <h2>Токены</h2>
    {token_list}
    <h2>Пользователи</h2>
    {users_list}
    """
    return render_template_string(html)

@flask_app.route('/generate', methods=['POST'])
def generate_token_web():
    token = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    invite_tokens[token] = False
    return redirect('/admin')

@flask_app.route('/plot.png')
def plot_web():
    today = datetime.now().date()
    data = [s for s in signals_today if s['time'].date() == today]
    times = [s['time'].strftime('%H:%M') for s in data]
    profits = [sum(s['profit'] for s in data[:i+1]) for i in range(len(data))]

    plt.figure(figsize=(8, 4))
    plt.plot(times, profits, marker='o')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return InputFile(buf, filename='plot.png').to_dict()['media']

# === ЗАПУСК ===
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("plot", plot_command))
    app.add_handler(CommandHandler("generate_token", generate_token_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("tokens", tokens_command))

    import os

Thread(target=signal_loop, daemon=True).start()

# Поддержка Railway порта
port = int(os.environ.get("PORT", 8080))
Thread(target=lambda: flask_app.run(host="0.0.0.0", port=port), daemon=True).start()

application.run_polling()


if __name__ == '__main__':
    main()
import os

def main():
    # Команды Telegram
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("plot", plot_command))
    app.add_handler(CommandHandler("generate_token", generate_token_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("tokens", tokens_command))

    # Запуск сигнального потока
    Thread(target=signal_loop, daemon=True).start()

    # Flask для админки
    port = int(os.environ.get("PORT", 8080))
    Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=port),
        daemon=True
    ).start()

    # Запуск Telegram-бота только локально
    if os.environ.get("RAILWAY_ENVIRONMENT") is None:
        app.run_polling()
