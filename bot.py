import os
import time
import random
import threading
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# === НАСТРОЙКИ ===
TOKEN         = "7943446786:AAHCIqydv95YH6uurQ_pm_xcQuhtITPVc_E"
ADMIN_ID      = 6894162425
CHECK_INTERVAL = 60  # секунд

COINS = [f"COIN{i}/USDT" for i in range(1, 201)]
signals_today = []
authorized_users = set()
invite_tokens = {"abc123": False, "xyz789": False}

# === ФУНКЦИИ БОТА ===
def generate_fake_signal():
    coin = random.choice(COINS)
    rsi  = random.randint(10, 90)
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"{coin}: RSI={rsi} at {ts}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Добро пожаловать! Отправьте /invite <токен>, чтобы получить доступ."
    )

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if len(context.args) != 1:
        return await update.message.reply_text("Используйте: /invite <токен>")
    tok = context.args[0]
    if tok in invite_tokens and not invite_tokens[tok]:
        invite_tokens[tok] = True
        authorized_users.add(uid)
        await update.message.reply_text("Токен принят! Вы авторизованы.")
    else:
        await update.message.reply_text("Неверный или уже использованный токен.")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in authorized_users:
        return await update.message.reply_text("У вас нет доступа.")
    sig = generate_fake_signal()
    signals_today.append(sig)
    await update.message.reply_text(f"Сигнал: {sig}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("Доступ только администратору.")
    last = signals_today[-10:]
    text = "\n".join(last) if last else "Нет сигналов за сегодня."
    await update.message.reply_text("Последние сигналы:\n" + text)

# === ФОНОВЫЙ ЦИКЛ СИГНАЛОВ ===
def signal_loop(app):
    while True:
        time.sleep(CHECK_INTERVAL)
        for uid in authorized_users:
            sig = generate_fake_signal()
            signals_today.append(sig)
            app.bot.send_message(chat_id=uid, text=f"Авто-сигнал: {sig}")

# === ВЕБ‑АДМИНКА НА FastAPI ===
web = FastAPI()

@web.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse("/admin")

@web.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request):
    stats = "<br>".join(signals_today[-20:]) or "Нет данных"
    token_list = "<ul>" + "".join(
        f"<li>{t} — {'OK' if used else 'Свободен'}</li>"
        for t, used in invite_tokens.items()
    ) + "</ul>"
    users_list = "<ul>" + "".join(
        f"<li>{uid}</li>" for uid in authorized_users
    ) + "</ul>"

    return f"""
    <h1>CryptoBot Admin</h1>
    <h2>Статистика последних сигналов</h2>
    <div style="white-space: pre-line;">{stats}</div>
    <h2>Токены</h2>
    {token_list}
    <h2>Пользователи</h2>
    {users_list}
    """

# === ТОЧКА ВХОДА ===
def main():
    # создаём приложение бота
    app = ApplicationBuilder().token(TOKEN).build()

    # регистрируем команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("invite", invite_command))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # запускаем фоновый цикл сигналов
    threading.Thread(target=signal_loop, args=(app,), daemon=True).start()

    # запускаем FastAPI в отдельном потоке
    threading.Thread(
        target=lambda: uvicorn.run(
            web,
            host="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            log_level="info"
        ),
        daemon=True
    ).start()

    # запускаем polling
    app.run_polling()

if __name__ == "__main__":
    main()
