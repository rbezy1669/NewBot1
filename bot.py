
import pytesseract
from PIL import Image
from io import BytesIO

# OCR STATES
PHOTO_UPLOAD, PHOTO_CONFIRM = range(10, 12)


async def start_ocr_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Отправьте фотографию счётчика крупным планом.\n\n"
        "Изображение должно быть чётким, без бликов и с читаемыми цифрами.",
        reply_markup=CANCEL_MARKUP
    )
    return PHOTO_UPLOAD


async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image = Image.open(BytesIO(photo_bytes))

    try:
        text = pytesseract.image_to_string(image, config="--psm 6 digits")
        digits = "".join(filter(str.isdigit, text))
        if not digits:
            await update.message.reply_text("❌ Не удалось распознать цифры на изображении. Попробуйте ещё раз или введите вручную.", reply_markup=CANCEL_MARKUP)
            return PHOTO_UPLOAD

        context.user_data["ocr_reading"] = int(digits)
        await update.message.reply_text(
            f"🔍 Распознано значение: {digits}\n\nПодтвердить?",
            reply_markup=ReplyKeyboardMarkup(
                [['✅ Да', '❌ Нет']], resize_keyboard=True)
        )
        return PHOTO_CONFIRM
    except Exception as e:
        logger.error(f"OCR error: {e}")
        await update.message.reply_text("⚠️ Ошибка при распознавании. Попробуйте снова.", reply_markup=CANCEL_MARKUP)
        return PHOTO_UPLOAD


async def confirm_ocr_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "✅ Да":
        reading_value = context.user_data.get("ocr_reading")
        telegram_id = update.effective_user.id
        db.add_reading(telegram_id, reading_value)
        await update.message.reply_text(
            f"✅ Показания успешно приняты: {reading_value}",
            reply_markup=MAIN_MARKUP
        )
    else:
        await update.message.reply_text("❌ Отменено. Вы можете повторить попытку.", reply_markup=MAIN_MARKUP)

    context.user_data.clear()
    return ConversationHandler.END
