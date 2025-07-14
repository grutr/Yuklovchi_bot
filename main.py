import os
import json
import logging
import asyncio
import tempfile
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
import yt_dlp
import requests
from urllib.parse import urlparse
import re

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token (environment variable orqali yoki to'g'ridan-to'g'ri)
BOT_TOKEN = "8110948714:AAFKy8AjEc5FXLedZl-x8J5kqYrt79dYyLQ"

# Tillar ro'yxati
LANGUAGES = {
    'uz': '🇺🇿 O\'zbekcha',
    'ru': '🇷🇺 Русский',
    'en': '🇺🇸 English'
}

# Platformalar
PLATFORMS = {
    'youtube': '📺 YouTube',
    'tiktok': '🎵 TikTok',
    'instagram': '📸 Instagram'
}

# Foydalanuvchi ma'lumotlari
user_data = {}


# Tillar fayli
def load_locales():
    locales = {}
    for lang in ['uz', 'ru', 'en']:
        try:
            with open(f'locales/{lang}.json', 'r', encoding='utf-8') as f:
                locales[lang] = json.load(f)
        except FileNotFoundError:
            # Agar fayl topilmasa, standart matnlar
            locales[lang] = get_default_texts(lang)
    return locales


def get_default_texts(lang):
    texts = {
        'uz': {
            'welcome': "Assalomu alaykum! Video yuklovchi botga xush kelibsiz!\n\nIltimos, tilni tanlang:",
            'choose_platform': "Platformani tanlang:",
            'send_link': "Iltimos, video havolasini yuboring:",
            'processing': "Video yuklanmoqda... Iltimos, kuting ⏳",
            'error': "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
            'invalid_link': "Noto'g'ri havola. Iltimos, to'g'ri havola yuboring.",
            'download_complete': "Video muvaffaqiyatli yuklandi! 📹",
            'file_too_large': "Fayl hajmi juda katta. Telegram 50MB gacha fayllarni qo'llab-quvvatlaydi.",
            'back': "⬅️ Orqaga"
        },
        'ru': {
            'welcome': "Добро пожаловать в бот для загрузки видео!\n\nПожалуйста, выберите язык:",
            'choose_platform': "Выберите платформу:",
            'send_link': "Пожалуйста, отправьте ссылку на видео:",
            'processing': "Видео загружается... Пожалуйста, подождите ⏳",
            'error': "Произошла ошибка. Пожалуйста, попробуйте еще раз.",
            'invalid_link': "Неверная ссылка. Пожалуйста, отправьте правильную ссылку.",
            'download_complete': "Видео успешно загружено! 📹",
            'file_too_large': "Файл слишком большой. Telegram поддерживает файлы до 50MB.",
            'back': "⬅️ Назад"
        },
        'en': {
            'welcome': "Welcome to the Video Downloader Bot!\n\nPlease choose your language:",
            'choose_platform': "Choose a platform:",
            'send_link': "Please send the video link:",
            'processing': "Video is downloading... Please wait ⏳",
            'error': "An error occurred. Please try again.",
            'invalid_link': "Invalid link. Please send a correct link.",
            'download_complete': "Video downloaded successfully! 📹",
            'file_too_large': "File is too large. Telegram supports files up to 50MB.",
            'back': "⬅️ Back"
        }
    }
    return texts[lang]


# Lokallar yuklash
LOCALES = load_locales()


def get_text(user_id, key):
    lang = user_data.get(user_id, {}).get('language', 'uz')
    return LOCALES[lang].get(key, key)


# Start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton(LANGUAGES['uz'], callback_data='lang_uz')],
        [InlineKeyboardButton(LANGUAGES['ru'], callback_data='lang_ru')],
        [InlineKeyboardButton(LANGUAGES['en'], callback_data='lang_en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎬 Video Downloader Bot\n\nChoose your language / Выберите язык / Tilni tanlang:",
        reply_markup=reply_markup
    )


# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith('lang_'):
        # Til tanlash
        lang = data.split('_')[1]
        user_data[user_id] = {'language': lang}

        keyboard = [
            [InlineKeyboardButton(PLATFORMS['youtube'], callback_data='platform_youtube')],
            [InlineKeyboardButton(PLATFORMS['tiktok'], callback_data='platform_tiktok')],
            [InlineKeyboardButton(PLATFORMS['instagram'], callback_data='platform_instagram')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            get_text(user_id, 'choose_platform'),
            reply_markup=reply_markup
        )

    elif data.startswith('platform_'):
        # Platforma tanlash
        platform = data.split('_')[1]
        user_data[user_id]['platform'] = platform

        keyboard = [[InlineKeyboardButton(get_text(user_id, 'back'), callback_data='back_to_platforms')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            get_text(user_id, 'send_link'),
            reply_markup=reply_markup
        )

    elif data == 'back_to_platforms':
        # Platformalar menyusiga qaytish
        keyboard = [
            [InlineKeyboardButton(PLATFORMS['youtube'], callback_data='platform_youtube')],
            [InlineKeyboardButton(PLATFORMS['tiktok'], callback_data='platform_tiktok')],
            [InlineKeyboardButton(PLATFORMS['instagram'], callback_data='platform_instagram')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            get_text(user_id, 'choose_platform'),
            reply_markup=reply_markup
        )


# URL validatsiya
def is_valid_url(url, platform):
    patterns = {
        'youtube': r'(youtube\.com|youtu\.be)',
        'tiktok': r'tiktok\.com',
        'instagram': r'instagram\.com'
    }

    if platform in patterns:
        return bool(re.search(patterns[platform], url))
    return False


# YouTube video yuklab berish
async def download_youtube(url, temp_dir):
    ydl_opts = {
        'format': 'best[filesize<50M]/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'extractaudio': False,
        'audioformat': 'mp3',
        'ignoreerrors': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename, info.get('title', 'Video')
    except Exception as e:
        logger.error(f"YouTube yuklab berish xatoligi: {e}")
        return None, None


# TikTok video yuklab berish (oddiy API)
async def download_tiktok(url, temp_dir):
    try:
        # Bu yerda TikTok API yoki web scraping ishlatiladi
        # Hozircha placeholder
        return None, None
    except Exception as e:
        logger.error(f"TikTok yuklab berish xatoligi: {e}")
        return None, None


# Instagram video yuklab berish
async def download_instagram(url, temp_dir):
    try:
        # Bu yerda Instagram API yoki web scraping ishlatiladi
        # Hozircha placeholder
        return None, None
    except Exception as e:
        logger.error(f"Instagram yuklab berish xatoligi: {e}")
        return None, None


# Xabarni qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text

    if user_id not in user_data or 'platform' not in user_data[user_id]:
        await update.message.reply_text("Iltimos, /start buyrug'ini bosing.")
        return

    platform = user_data[user_id]['platform']

    # URL validatsiya
    if not is_valid_url(message_text, platform):
        await update.message.reply_text(get_text(user_id, 'invalid_link'))
        return

    # Yuklab berish jarayoni
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)

    status_message = await update.message.reply_text(get_text(user_id, 'processing'))

    try:
        # Vaqtinchalik papka yaratish
        with tempfile.TemporaryDirectory() as temp_dir:
            filename = None
            title = None

            if platform == 'youtube':
                filename, title = await download_youtube(message_text, temp_dir)
            elif platform == 'tiktok':
                filename, title = await download_tiktok(message_text, temp_dir)
            elif platform == 'instagram':
                filename, title = await download_instagram(message_text, temp_dir)

            if filename and os.path.exists(filename):
                # Fayl hajmini tekshirish
                file_size = os.path.getsize(filename)
                if file_size > 50 * 1024 * 1024:  # 50MB
                    await status_message.edit_text(get_text(user_id, 'file_too_large'))
                    return

                # Faylni yuborish
                with open(filename, 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video_file,
                        caption=f"📹 {title}" if title else get_text(user_id, 'download_complete'),
                        supports_streaming=True
                    )

                await status_message.delete()
            else:
                await status_message.edit_text(get_text(user_id, 'error'))

    except Exception as e:
        logger.error(f"Xatolik: {e}")
        await status_message.edit_text(get_text(user_id, 'error'))


# Asosiy funksiya
def main():
    # Papkalarni yaratish
    os.makedirs('locales', exist_ok=True)
    os.makedirs('temp_files', exist_ok=True)

    # Botni yaratish
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Botni ishga tushirish
    print("Bot ishga tushirildi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()