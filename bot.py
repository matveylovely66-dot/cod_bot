import os
import asyncio
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image
from pyzbar.pyzbar import decode

TOKEN = os.getenv("TELEGRAM_TOKEN") or "ВСТАВЬ_СЮДА_ТОКЕН"

# ------------------ СТАТИСТИКА ------------------

stats = {
    "total_scans": 0,
    "scanners": {}  # user_id: username
}

# ------------------ МЕНЮ ------------------

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟨 Создать код", callback_data="create"),
            InlineKeyboardButton("📷 Сканировать", callback_data="scan")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ]
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

def create_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔳 QR-код", callback_data="qr")],
        [InlineKeyboardButton("▌▌ Штрихкод", callback_data="barcode")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

# ------------------ ЭФФЕКТ СОЗДАНИЯ ------------------

async def creation_effect(update: Update):
    size = 6
    msg = await update.message.reply_text("Создаю код… ⏳")

    for i in range(1, size + 1):
        frame = "\n".join(
            "[" + "🟨"*i + "⬜"*(size-i) + "]"
            for _ in range(i)
        )
        await msg.edit_text(frame)
        await asyncio.sleep(0.25)

# ------------------ /start ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "━━━━━━━━━━━━━━\n"
        "🔲 QR / BAR HUB\n"
        "━━━━━━━━━━━━━━\n\n"
        "Создавай • Сканируй • Делись\n\n"
        "Выбери действие 👇"
    )
    await update.message.reply_text(text, reply_markup=main_menu())

# ------------------ КНОПКИ ------------------

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        await query.edit_message_text("Главное меню 👇", reply_markup=main_menu())

    elif data == "create":
        await query.edit_message_text("🔲 Что будем создавать?", reply_markup=create_menu())

    elif data == "qr":
        context.user_data["mode"] = "qr"
        await query.edit_message_text(
            "✍️ Отправь текст или ссылку для QR-кода",
            reply_markup=back_menu()
        )

    elif data == "barcode":
        context.user_data["mode"] = "barcode"
        await query.edit_message_text(
            "✍️ Отправь ТОЛЬКО цифры для штрихкода",
            reply_markup=back_menu()
        )

    elif data == "scan":
        context.user_data["mode"] = "scan"
        await query.edit_message_text(
            "📷 Отправь фото с QR или штрихкодом",
            reply_markup=back_menu()
        )

    elif data == "stats":
        scanners_list = "\n".join(
            f"• {u}" for u in stats["scanners"].values()
        ) or "Пока никто"

        text = (
            "📊 СТАТИСТИКА\n\n"
            f"📷 Всего сканирований: {stats['total_scans']}\n\n"
            "👥 Кто сканировал:\n"
            f"{scanners_list}"
        )

        await query.edit_message_text(text, reply_markup=back_menu())

    elif data == "help":
        await query.edit_message_text(
            "❓ Помощь\n\n"
            "🔲 Создание QR и штрихкодов\n"
            "📷 Сканирование по фото\n"
            "📊 Общая статистика\n\n"
            "Просто выбери действие 👇",
            reply_markup=back_menu()
        )

# ------------------ ТЕКСТ ------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text

    if mode == "qr":
        await creation_effect(update)
        img = qrcode.make(text)
        img.save("qr.png")
        await update.message.reply_photo(
            photo=open("qr.png", "rb"),
            caption="✅ QR-код готов",
            reply_markup=back_menu()
        )

    elif mode == "barcode":
        await creation_effect(update)
        CODE128 = barcode.get_barcode_class("code128")
        bar = CODE128(text, writer=ImageWriter())
        bar.save("barcode")
        await update.message.reply_photo(
            photo=open("barcode.png", "rb"),
            caption="✅ Штрихкод готов",
            reply_markup=back_menu()
        )

    else:
        await update.message.reply_text("Выбери действие 👇", reply_markup=main_menu())

# ------------------ ФОТО ------------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "scan":
        return

    photo = await update.message.photo[-1].get_file()
    await photo.download_to_drive("scan.png")

    img = Image.open("scan.png")
    decoded = decode(img)

    if not decoded:
        await update.message.reply_text("❌ Код не найден", reply_markup=back_menu())
        return

    result = decoded[0].data.decode("utf-8")

    # --- обновляем статистику ---
    stats["total_scans"] += 1
    user = update.message.from_user
    stats["scanners"][user.id] = user.username or f"id:{user.id}"

    await update.message.reply_text(
        f"✅ Найдено:\n\n{result}",
        reply_markup=back_menu()
    )

# ------------------ ЗАПУСК ------------------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

app.run_polling()
