import os
import logging
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fastapi import FastAPI
import uvicorn

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Создаем приложения
app = FastAPI(title="MindMate Bot")
bot_app = None

# Инициализируем бота только если есть токен
if TOKEN:
    try:
        bot_app = Application.builder().token(TOKEN).build()
        logger.info("✅ Telegram bot initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize bot: {e}")
        bot_app = None
else:
    logger.warning("⚠️ TELEGRAM_BOT_TOKEN not found. Telegram functions disabled.")

# База данных в памяти
user_data = {}

# Техники для релаксации
RELAXATION_TECHNIQUES = [
    "🧘 **Дыхание 4-7-8**: Вдох на 4 счета, задержка на 7, выдох на 8. Повтори 3 раза.",
    "👁️ **Техника 5-4-3-2-1**: Назови 5 вещей, которые видишь, 4 которые ощущаешь, 3 которые слышишь, 2 которые нюхаешь, 1 которую пробуешь."
]

POSITIVE_AFFIRMATIONS = [
    "Ты справляешься лучше, чем думаешь! 💪",
    "Это временные трудности, ты станешь сильнее! 🌱"
]

# ========== ОБРАБОТЧИКИ TELEGRAM ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я MindMate Bot 🤗")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    if user_text.isdigit() and 1 <= int(user_text) <= 10:
        mood_score = int(user_text)
        user_id = update.effective_user.id
        
        if user_id not in user_data:
            user_data[user_id] = []
        user_data[user_id].append(mood_score)
        
        await update.message.reply_text(f"✅ Записал настроение: {mood_score}/10")
    else:
        await update.message.reply_text("Спасибо за сообщение! 🤗")

# ========== WEBHOOK ENDPOINTS ==========
@app.get("/")
async def root():
    status = "MindMate Bot is running! 🚀"
    if bot_app:
        status += " (Telegram active)"
    else:
        status += " (Telegram inactive - check token)"
    return {"status": status}

@app.post("/webhook")
async def webhook(request: dict):
    """Endpoint для вебхука от Telegram."""
    if not bot_app:
        return {"status": "error", "message": "Bot not initialized"}
    
    try:
        # Инициализируем обработчики при первом запросе
        if not bot_app.handlers:
            bot_app.add_handler(CommandHandler("start", start))
            bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            await bot_app.initialize()
            logger.info("✅ Bot handlers initialized")
        
        update = Update.de_json(request, bot_app.bot)
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.on_event("startup")
async def on_startup():
    """Настройка при запуске."""
    if bot_app:
        try:
            # Устанавливаем вебхук
            webhook_url = os.getenv('RENDER_EXTERNAL_URL', '') + "/webhook"
            if webhook_url:
                await bot_app.bot.set_webhook(webhook_url)
                logger.info(f"✅ Webhook установлен: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Startup error: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
