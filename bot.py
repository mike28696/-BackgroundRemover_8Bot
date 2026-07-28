"""
@BackgroundRemover_8Bot
A Telegram bot that removes the background from photos users send it.

Environment variables required:
- BOT_TOKEN : the token you get from @BotFather on Telegram.

Run locally:
    pip install -r requirements.txt
    export BOT_TOKEN="123456:ABC-your-token"
    python bot.py
"""

import io
import logging
import os

from PIL import Image
from rembg import remove
from telegram import Update, InputFile
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

MAX_IMAGE_DIMENSION = 2000  # downscale very large images to keep memory/time reasonable


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hi! I'm Background Remover.\n\n"
        "Send me any photo and I'll remove its background and send it back "
        "as a transparent PNG.\n\n"
        "Tip: send the image as a *file/document* (not compressed photo) for "
        "the best quality result.",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Just send me a photo 📷 and I'll strip the background out.\n"
        "Commands:\n"
        "/start - intro message\n"
        "/help - this message"
    )


def _remove_background(image_bytes: bytes) -> bytes:
    """Runs rembg on raw image bytes and returns PNG bytes with transparency."""
    image = Image.open(io.BytesIO(image_bytes))

    if max(image.size) > MAX_IMAGE_DIMENSION:
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

    buf_in = io.BytesIO()
    image.save(buf_in, format="PNG")

    result_bytes = remove(buf_in.getvalue())
    return result_bytes


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message

    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        file_id = message.document.file_id

    if not file_id:
        await message.reply_text("Please send an image (photo or image file).")
        return

    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.UPLOAD_PHOTO)
    status_msg = await message.reply_text("⏳ Removing background...")

    try:
        tg_file = await context.bot.get_file(file_id)
        image_bytes = bytes(await tg_file.download_as_bytearray())

        result_bytes = _remove_background(image_bytes)

        output = io.BytesIO(result_bytes)
        output.name = "background_removed.png"

        await message.reply_document(
            document=InputFile(output, filename="background_removed.png"),
            caption="✅ Done! Here's your image with the background removed.",
        )
    except Exception:
        logger.exception("Failed to process image")
        await message.reply_text(
            "⚠️ Sorry, something went wrong while processing that image. "
            "Please try a different photo."
        )
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Please send me a photo or an image file 📷.")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set. "
            "Get a token from @BotFather and set it before running the bot."
        )

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
    application.add_handler(MessageHandler(~filters.COMMAND, handle_other))

    logger.info("Bot starting (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
