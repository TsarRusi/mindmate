import os
import logging
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
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

if TOKEN:
    bot_app = Application.builder().token(TOKEN).build()
else:
    bot_app = None
    logger.warning("TELEGRAM_BOT_TOKEN not found. Telegram functions disabled.")

# База данных в памяти (потом заменим на настоящую)
user_data = {}

# Техники для релаксации
RELAXATION_TECHNIQUES = [
    "🧘 **Дыхание 4-7-8**: Вдох на 4 счета, задержка на 7, выдох на 8. Повтори 3 раза.",
    "👁️ **Техника 5-4-3-2-1**: Назови 5 вещей, которые видишь, 4 которые ощущаешь, 3 которые слышишь, 2 которые нюхаешь, 1 которую пробуешь.",
    "🖐️ **Прогрессивная релаксация**: Напряги все мышцы на 5 секунд, затем полностью расслабь. Начни с пальцев ног до головы.",
    "📝 **Выписывание мыслей**: Возьми бумагу и 5 минут пиши все что приходит в голову без остановки.",
    "🚶 **Осознанная прогулка**: Пройдись 5 минут, обращая внимание на каждый шаг и дыхание."
]

POSITIVE_AFFIRMATIONS = [
    "Ты справляешься лучше, чем думаешь! 💪",
    "Это временные трудности, ты станешь сильнее! 🌱",
    "Позволь себе чувствовать все эмоции - это нормально! 🎭",
    "Ты не один - я здесь чтобы поддержать! 🤗",
    "Маленькие шаги ведут к большим изменениям! 🐢",
    "Ты заслуживаешь заботы и отдыха! 🌟",
    "Каждый день - новая возможность начать заново! 🌅"
]

# ========== ОБРАБОТЧИКИ TELEGRAM ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start."""
    user = update.effective_user
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        ["📊 Записать настроение", "🧘 Техника релаксации"],
        ["💫 Поддержка", "📈 Статистика"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = f"""
Привет, {user.first_name}! Я MindMate Bot 🤗

Я твой помощник для заботы о ментальном здоровье.

✨ Что я умею:
• Записывать твое настроение
• Предлагать техники для снятия стресса
• Делиться позитивными аффирмациями
• Показывать статистику настроения

Используй кнопки ниже или команды:
/mood - записать настроение
/relax - техника релаксации  
/affirmation - поддержка
/stats - статистика

Как твое настроение сегодня? 😊
"""
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для записи настроения."""
    await update.message.reply_text("Как твое настроение сегодня? Оцени от 1 до 10:")

async def relax_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Случайная техника релаксации."""
    technique = random.choice(RELAXATION_TECHNIQUES)
    await update.message.reply_text(f"🎯 Попробуй эту технику:\n\n{technique}")

async def affirmation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Случайная аффирмация."""
    affirmation = random.choice(POSITIVE_AFFIRMATIONS)
    await update.message.reply_text(f"💫 {affirmation}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика настроения."""
    user_id = update.effective_user.id
    
    if user_id in user_data and user_data[user_id]:
        moods = user_data[user_id]
        avg_mood = sum(moods) / len(moods)
        
        if avg_mood <= 4:
            emoji = "😔"
        elif avg_mood <= 7:
            emoji = "😐"
        else:
            emoji = "😊"
            
        await update.message.reply_text(
            f"📈 Твоя статистика {emoji}:\n"
            f"• Записей настроения: {len(moods)}\n"
            f"• Среднее настроение: {avg_mood:.1f}/10\n"
            f"• Последняя запись: {moods[-1]}/10\n\n"
            f"Продолжай отслеживать свое состояние! 🌟"
        )
    else:
        await update.message.reply_text(
            "📊 У тебя пока нет записей настроения.\n"
            "Используй 'Записать настроение' или /mood чтобы начать!"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения."""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Обработка кнопок
    if user_text == "📊 Записать настроение":
        await mood_command(update, context)
        return
    elif user_text == "🧘 Техника релаксации":
        await relax_command(update, context)
        return
    elif user_text == "💫 Поддержка":
        await affirmation_command(update, context)
        return
    elif user_text == "📈 Статистика":
        await stats_command(update, context)
        return
    
    # Сохраняем настроение если это цифра 1-10
    if user_text.isdigit() and 1 <= int(user_text) <= 10:
        mood_score = int(user_text)
        
        # Сохраняем в "базу"
        if user_id not in user_data:
            user_data[user_id] = []
        user_data[user_id].append(mood_score)
        
        # Ответ в зависимости от настроения
        if mood_score <= 3:
            response = "😔 Вижу, что тяжелый день. Хочешь технику для расслабления?"
        elif mood_score <= 6:
            response = "😐 Спасибо за честность! Помни, что все эмоции временны."
        elif mood_score <= 8:
            response = "😊 Хорошо! Рад, что у тебя неплохой день."
        else:
            response = "😍 Отлично! Ты сияешь! Поделись энергией с окружающими!"
            
        await update.message.reply_text(response)
        
    else:
        # Обычный текст
        responses = [
            "Спасибо, что делишься! Я записал твои мысли. 💭",
            "Понимаю. Хочешь обсудить что-то конкретное?",
            "Спасибо за доверие! Помни, я здесь чтобы поддержать. 🤗",
            "Записал. Хочешь поработать над своим состоянием?"
        ]
        await update.message.reply_text(random.choice(responses))

# ========== WEBHOOK ENDPOINTS ==========
@app.get("/")
async def root():
    status = "MindMate Bot is running! 🚀"
    if not TOKEN:
        status += " (Telegram token not configured)"
    return {"status": status, "version": "1.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/webhook")
async def webhook(request: dict):
    """Endpoint для вебхука от Telegram."""
    if not bot_app:
        return {"status": "error", "message": "Telegram token not configured"}
    
    try:
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
        # Регистрируем обработчики
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("mood", mood_command))
        bot_app.add_handler(CommandHandler("relax", relax_command))
        bot_app.add_handler(CommandHandler("affirmation", affirmation_command))
        bot_app.add_handler(CommandHandler("stats", stats_command))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Устанавливаем вебхук
        webhook_url = os.getenv('RENDER_EXTERNAL_URL', '') + "/webhook"
        if webhook_url:
            await bot_app.bot.set_webhook(webhook_url)
            logger.info(f"✅ Webhook установлен: {webhook_url}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
