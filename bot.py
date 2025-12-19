import os
import logging
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fastapi import FastAPI
import uvicorn
import asyncio

# Импортируем наши модули
from ai_service import AIService
from crisis_handler import CrisisHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализируем сервисы
ai_service = AIService()
crisis_handler = CrisisHandler()

# Создаем приложения
app = FastAPI(title="MindMate Bot")
bot_app = None

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

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    """Основная клавиатура"""
    keyboard = [
        [KeyboardButton("📊 Записать настроение"), KeyboardButton("🧘 Техники релаксации")],
        [KeyboardButton("💫 Позитивные аффирмации"), KeyboardButton("📈 Моя статистика")],
        [KeyboardButton("💬 Чат с помощником"), KeyboardButton("🚨 Кризисная помощь")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_mood_keyboard():
    """Клавиатура для настроения"""
    keyboard = [
        [KeyboardButton("1 😫"), KeyboardButton("2 😔"), KeyboardButton("3 😟")],
        [KeyboardButton("4 😐"), KeyboardButton("5 🙂"), KeyboardButton("6 😊")],
        [KeyboardButton("7 😄"), KeyboardButton("8 🤩"), KeyboardButton("9 🥰")],
        [KeyboardButton("10 🎉"), KeyboardButton("↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_chat_keyboard():
    """Клавиатура для чата"""
    keyboard = [
        [KeyboardButton("↩️ В главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Техники релаксации
RELAXATION_TECHNIQUES = [
    {
        "name": "🧘 Дыхание 4-7-8",
        "description": "Вдох на 4 счета, задержка на 7, выдох на 8. Повтори 3 раза.",
        "steps": [
            "Сядь удобно, закрой глаза",
            "Медленно вдохни через нос на 4 счета",
            "Задержи дыхание на 7 счетов",
            "Медленно выдохни через рот на 8 счетов",
            "Повтори 3-5 раз"
        ]
    }
]

POSITIVE_AFFIRMATIONS = [
    "Ты справляешься лучше, чем думаешь! 💪",
    "Это временные трудности, ты станешь сильнее! 🌱"
]

MOOD_EMOJIS = {
    1: "😫", 2: "😔", 3: "😟", 4: "😐", 5: "🙂",
    6: "😊", 7: "😄", 8: "🤩", 9: "🥰", 10: "🎉"
}

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    user_id = user.id
    
    if user_id not in user_data:
        user_data[user_id] = {
            "mood_history": [],
            "name": user.first_name,
            "joined_date": datetime.now().isoformat(),
            "in_chat_mode": False
        }
    
    welcome_text = f"""
🤗 Привет, {user.first_name}! 

Я — *MindMate*, твой персональный помощник для заботы о ментальном здоровье.

✨ *Что я умею:*
• 📊 Отслеживать настроение
• 🧘 Техники релаксации  
• 💫 Позитивные аффирмации
• 📈 Статистика настроения
• 💬 Чат с ИИ-помощником
• 🚨 Кризисная помощь

*Используй кнопки ниже для навигации.*

*Важно:* Я - бот-помощник, а не медицинский специалист.
В критических ситуациях обращайтесь к профессионалам.
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📖 *Помощь по использованию MindMate*

*Основные функции:*
• 📊 *Записать настроение* - отслеживай свое состояние
• 🧘 *Техники релаксации* - упражнения для снятия стресса
• 💫 *Позитивные аффирмации* - поддержка в трудные моменты
• 📈 *Моя статистика* - анализ твоего настроения
• 💬 *Чат с помощником* - общение с ИИ-ассистентом
• 🚨 *Кризисная помощь* - контакты экстренных служб

*Как работать с настроением:*
1. Нажми "📊 Записать настроение"
2. Выбери цифру от 1 до 10
3. Я запомню твою оценку

*Кризисная помощь:*
Если тебе очень тяжело, нажми "🚨 Кризисная помощь"
для получения контактов специалистов.

🤗 *Помни:* обращаться за помощью - это нормально!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запись настроения"""
    user_id = update.effective_user.id
    user_data[user_id]["in_chat_mode"] = False
    
    await update.message.reply_text(
        "📊 *Оцени свое настроение от 1 до 10:*\n\n"
        "1 😫 - Очень плохо\n"
        "10 🎉 - Отлично\n\n"
        "Выбери цифру:",
        parse_mode='Markdown',
        reply_markup=get_mood_keyboard()
    )

async def relax_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Техники релаксации"""
    technique = random.choice(RELAXATION_TECHNIQUES)
    steps_text = "\n".join([f"• {step}" for step in technique["steps"]])
    
    technique_text = f"""
{technique['name']}

*{technique['description']}*

📝 *Пошагово:*
{steps_text}

⏱️ *Выполняй 5-10 минут*
"""
    await update.message.reply_text(technique_text, parse_mode='Markdown')

async def affirmation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Позитивные аффирмации"""
    affirmation = random.choice(POSITIVE_AFFIRMATIONS)
    await update.message.reply_text(f"💫 *Поддержка для тебя:*\n\n{affirmation}", parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика настроения"""
    user_id = update.effective_user.id
    
    if user_id not in user_data or not user_data[user_id]["mood_history"]:
        await update.message.reply_text(
            "📊 *У тебя пока нет записей настроения.*\n\n"
            "Используй кнопку \"📊 Записать настроение\" чтобы начать!",
            parse_mode='Markdown'
        )
        return
    
    moods = user_data[user_id]["mood_history"]
    avg_mood = sum(moods) / len(moods)
    
    stats_text = f"""
📈 *Твоя статистика:*

• 📊 Всего записей: *{len(moods)}*
• 📅 Среднее настроение: *{avg_mood:.1f}/10*
• 🎯 Последняя запись: *{moods[-1]}/10* {MOOD_EMOJIS.get(moods[-1], '')}

Продолжай заботиться о себе! 🌟
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Чат с ИИ-помощником"""
    user_id = update.effective_user.id
    user_data[user_id]["in_chat_mode"] = True
    
    await update.message.reply_text(
        "💬 *Чат с ИИ-помощником*\n\n"
        "Напиши то, что тебя беспокоит, и я постараюсь помочь.\n"
        "Если ситуация критическая - я сразу дам контакты помощи.\n\n"
        "Для выхода нажми '↩️ В главное меню'",
        parse_mode='Markdown',
        reply_markup=get_chat_keyboard()
    )

async def crisis_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кризисная помощь"""
    response = crisis_handler.get_serious_crisis_response()
    await update.message.reply_text(response, parse_mode='Markdown')

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Инициализация пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            "mood_history": [],
            "name": update.effective_user.first_name,
            "joined_date": datetime.now().isoformat(),
            "in_chat_mode": False
        }
    
    # Главное меню
    if user_text == "📊 Записать настроение":
        await mood_command(update, context)
        return
    elif user_text == "🧘 Техники релаксации":
        await relax_command(update, context)
        return
    elif user_text == "💫 Позитивные аффирмации":
        await affirmation_command(update, context)
        return
    elif user_text == "📈 Моя статистика":
        await stats_command(update, context)
        return
    elif user_text == "💬 Чат с помощником":
        await chat_command(update, context)
        return
    elif user_text == "🚨 Кризисная помощь":
        await crisis_help_command(update, context)
        return
    elif user_text == "ℹ️ Помощь":
        await help_command(update, context)
        return
    
    # Навигация
    if user_text == "↩️ Назад" or user_text == "↩️ В главное меню":
        user_data[user_id]["in_chat_mode"] = False
        await update.message.reply_text(
            "Возвращаю в главное меню! 🏠",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Обработка настроения
    if user_text.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")) and "�" in user_text:
        mood_score = int(user_text.split()[0])
        await save_mood(update, mood_score)
        return
    
    # Если пользователь в режиме чата
    if user_data[user_id].get("in_chat_mode", False):
        await handle_chat_message(update, user_text, user_id)
        return
    
    # Обычные сообщения
    responses = [
        "Используй кнопки ниже для навигации! 🤗",
        "Выбери нужную функцию из меню! 💫",
        "Нажми на одну из кнопок, чтобы продолжить! ✨"
    ]
    await update.message.reply_text(
        random.choice(responses),
        reply_markup=get_main_keyboard()
    )

async def handle_chat_message(update: Update, message: str, user_id: int):
    """Обработка сообщений в чате"""
    # Показываем "печатает..."
    await update.message.chat.send_action(action="typing")
    
    # Проверяем кризис
    crisis_level, crisis_desc = crisis_handler.detect_crisis_level(message)
    
    if crisis_level >= 2:
        # Кризисная ситуация
        crisis_response = crisis_handler.generate_crisis_response(crisis_level, message)
        await update.message.reply_text(crisis_response, parse_mode='Markdown')
        
        # Также даем ответ от ИИ
        user_context = {
            'mood_history': user_data[user_id].get('mood_history', []),
            'name': user_data[user_id].get('name', 'Пользователь')
        }
        ai_response = await ai_service.get_ai_response(message, user_context)
        await update.message.reply_text(f"🤖 *Помощник:*\n{ai_response}", parse_mode='Markdown')
    else:
        # Обычный запрос
        user_context = {
            'mood_history': user_data[user_id].get('mood_history', []),
            'name': user_data[user_id].get('name', 'Пользователь')
        }
        ai_response = await ai_service.get_ai_response(message, user_context)
        await update.message.reply_text(f"🤖 *Помощник:*\n{ai_response}", parse_mode='Markdown')

async def save_mood(update: Update, mood_score: int):
    """Сохранение настроения"""
    user_id = update.effective_user.id
    user_data[user_id]["mood_history"].append(mood_score)
    user_data[user_id]["in_chat_mode"] = False
    
    emoji = MOOD_EMOJIS.get(mood_score, "")
    
    response = f"✅ Записал твое настроение: {mood_score}/10 {emoji}"
    
    if mood_score <= 4:
        response += "\n\nВижу, что тяжелый день. Может, попробуешь технику релаксации?"
    
    await update.message.reply_text(response, reply_markup=get_main_keyboard())

# ========== WEBHOOK ENDPOINTS ==========
@app.get("/")
async def root():
    status = "MindMate Bot v2.0 is running! 🚀"
    if bot_app:
        status += f" (Users: {len(user_data)})"
    return {"status": status}

@app.post("/webhook")
async def webhook(request: dict):
    """Endpoint для вебхука"""
    if not bot_app:
        return {"status": "error", "message": "Bot not initialized"}
    
    try:
        if not bot_app.handlers:
            # Регистрируем обработчики
            bot_app.add_handler(CommandHandler("start", start))
            bot_app.add_handler(CommandHandler("help", help_command))
            bot_app.add_handler(CommandHandler("mood", mood_command))
            bot_app.add_handler(CommandHandler("relax", relax_command))
            bot_app.add_handler(CommandHandler("affirmation", affirmation_command))
            bot_app.add_handler(CommandHandler("stats", stats_command))
            bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            await bot_app.initialize()
        
        update = Update.de_json(request, bot_app.bot)
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.on_event("startup")
async def on_startup():
    """Настройка при запуске"""
    if bot_app:
        try:
            # Получаем URL из Railway
            webhook_url = os.getenv('RAILWAY_STATIC_URL', '') + "/webhook"
            if not webhook_url.startswith("http"):
                webhook_url = "https://" + webhook_url + "/webhook"
            
            await bot_app.bot.set_webhook(webhook_url)
            logger.info(f"✅ Webhook установлен: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Webhook setup error: {e}")

# Для локального запуска
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
