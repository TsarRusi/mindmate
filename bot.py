import os
import logging
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fastapi import FastAPI
import uvicorn

# Импортируем наши модули
from ai_service import ai_service
from crisis_handler import crisis_handler

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

if TOKEN:
    try:
        bot_app = Application.builder().token(TOKEN).build()
        logger.info("✅ Telegram bot initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize bot: {e}")
        bot_app = None
else:
    logger.warning("⚠️ TELEGRAM_BOT_TOKEN not found. Telegram functions disabled.")

# База данных в памяти (временно, можно заменить на базу)
user_data = {}

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    """Основная клавиатура с кнопками"""
    keyboard = [
        [KeyboardButton("📊 Записать настроение"), KeyboardButton("🧘 Техники релаксации")],
        [KeyboardButton("💫 Позитивные аффирмации"), KeyboardButton("📈 Моя статистика")],
        [KeyboardButton("💬 Чат с ИИ-помощником"), KeyboardButton("🚨 Кризисная помощь")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_mood_keyboard():
    """Клавиатура для выбора настроения"""
    keyboard = [
        [KeyboardButton("1 😫"), KeyboardButton("2 😔"), KeyboardButton("3 😟")],
        [KeyboardButton("4 😐"), KeyboardButton("5 🙂"), KeyboardButton("6 😊")],
        [KeyboardButton("7 😄"), KeyboardButton("8 🤩"), KeyboardButton("9 🥰")],
        [KeyboardButton("10 🎉"), KeyboardButton("↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_chat_mode_keyboard():
    """Клавиатура в режиме чата"""
    keyboard = [
        [KeyboardButton("🔄 Новый вопрос"), KeyboardButton("🚨 Кризисная помощь")],
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
    },
    {
        "name": "👁️ Техника 5-4-3-2-1",
        "description": "Вернись в настоящее через органы чувств.",
        "steps": [
            "Назови 5 вещей, которые видишь вокруг",
            "Найди 4 вещи, к которым можешь прикоснуться",
            "Прислушайся к 3 звукам вокруг себя",
            "Найди 2 запаха, которые чувствуешь",
            "Вспомни 1 вкус, который тебе нравится"
        ]
    }
]

POSITIVE_AFFIRMATIONS = [
    "Ты справляешься лучше, чем думаешь! 💪",
    "Это временные трудности, ты станешь сильнее! 🌱",
    "Позволь себе чувствовать все эмоции - это нормально! 🎭",
    "Ты не один - я здесь чтобы поддержать! 🤗",
    "Маленькие шаги ведут к большим изменениям! 🐢"
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
    
    # Инициализация пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            "mood_history": [],
            "name": user.first_name,
            "joined_date": datetime.now().isoformat(),
            "in_chat_mode": False,
            "chat_history": []
        }
    
    welcome_text = f"""
🤗 Привет, {user.first_name}! 

Я — *MindMate*, твой персональный помощник для заботы о ментальном здоровье.

✨ *Что я умею:*
• 📊 *Отслеживать настроение* — помогу заметить закономерности
• 🧘 *Техники релаксации* — упражнения для снятия стресса  
• 💫 *Позитивные аффирмации* — поддержка в трудные моменты
• 📈 *Статистика* — анализ твоего эмоционального состояния
• 💬 *Чат с ИИ-помощником* — умные ответы на твои вопросы
• 🚨 *Кризисная помощь* — контакты экстренных служб

🎯 *Используй кнопки ниже для навигации!*

*Важно:* Я - бот-помощник, а не медицинский специалист.
В критических ситуациях обращайтесь к профессионалам.
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📖 *Помощь по использованию MindMate*

*Основные функции:*
• 📊 *Записать настроение* — отслеживай свое состояние
• 🧘 *Техники релаксации* — упражнения для снятия стресса
• 💫 *Позитивные аффирмации* — поддержка в трудные моменты
• 📈 *Моя статистика* — анализ твоего настроения
• 💬 *Чат с ИИ-помощником* — общение с умным помощником
• 🚨 *Кризисная помощь* — контакты экстренных служб

*Как работает чат с ИИ:*
1. Нажми кнопку "💬 Чат с ИИ-помощником"
2. Напиши то, что тебя беспокоит
3. Получи поддержку и полезные советы
4. Используй "🔄 Новый вопрос" для продолжения

*Кризисная помощь:*
Если тебе очень тяжело, нажми "🚨 Кризисная помощь"
для получения контактов специалистов.

🤗 *Помни:* обращаться за помощью — это нормально!
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
    
    # Анализ
    if avg_mood <= 4:
        analysis = "💔 Сложный период. Помни, что это временно."
    elif avg_mood <= 7:
        analysis = "💛 Стабильно. Продолжай отслеживать свое состояние."
    else:
        analysis = "💚 Отлично! Ты хорошо справляешься."
    
    stats_text = f"""
📈 *Твоя статистика:*

• 📊 Всего записей: *{len(moods)}*
• 📅 Среднее настроение: *{avg_mood:.1f}/10*
• 🎯 Последняя запись: *{moods[-1]}/10* {MOOD_EMOJIS.get(moods[-1], '')}

*Анализ:*
{analysis}

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
        "Я использую DeepSeek AI для умных ответов.\n\n"
        "*Что можно спросить:*\n"
        "• Как справиться с тревогой?\n"
        "• Что делать при стрессе?\n"
        "• Как улучшить настроение?\n"
        "• Или просто поделиться переживаниями\n\n"
        "Используй кнопки ниже для навигации:",
        parse_mode='Markdown',
        reply_markup=get_chat_mode_keyboard()
    )

async def crisis_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кризисная помощь"""
    response = crisis_handler.get_crisis_response()
    await update.message.reply_text(response, parse_mode='Markdown')

async def new_question_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Новый вопрос в чате"""
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id]["chat_history"] = []
    
    await update.message.reply_text(
        "🔄 *Новый диалог*\n\n"
        "Задай новый вопрос или поделись тем, что тебя беспокоит:",
        parse_mode='Markdown',
        reply_markup=get_chat_mode_keyboard()
    )

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений и кнопок"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Инициализация пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            "mood_history": [],
            "name": update.effective_user.first_name,
            "joined_date": datetime.now().isoformat(),
            "in_chat_mode": False,
            "chat_history": []
        }
    
    # Обработка кнопок главного меню
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
    elif user_text == "💬 Чат с ИИ-помощником":
        await chat_command(update, context)
        return
    elif user_text == "🚨 Кризисная помощь":
        await crisis_help_command(update, context)
        return
    elif user_text == "ℹ️ Помощь":
        await help_command(update, context)
        return
    elif user_text == "🔄 Новый вопрос":
        await new_question_command(update, context)
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
    
    # Если пользователь в режиме чата с ИИ
    if user_id in user_data and user_data[user_id].get("in_chat_mode", False):
        await handle_ai_chat(update, user_text, user_id)
        return
    
    # Обработка цифр настроения (без эмодзи)
    if user_text.isdigit() and 1 <= int(user_text) <= 10:
        await save_mood(update, int(user_text))
        return
    
    # Обычные сообщения (не в режиме чата)
    responses = [
        "Используй кнопки ниже для навигации! 🤗",
        "Выбери нужную функцию из меню! 💫",
        "Нажми на одну из кнопок, чтобы продолжить! ✨"
    ]
    await update.message.reply_text(
        random.choice(responses),
        reply_markup=get_main_keyboard()
    )

async def handle_ai_chat(update: Update, message: str, user_id: int):
    """Обработка сообщений в чате с ИИ"""
    # Показываем "печатает..."
    await update.message.chat.send_action(action="typing")
    
    # Проверяем кризисный уровень
    crisis_level, crisis_desc = crisis_handler.detect_crisis_level(message)
    
    # Если кризис 2 или 3 уровня - показываем помощь
    if crisis_level >= 2:
        crisis_response = crisis_handler.get_crisis_response_by_level(crisis_level, message)
        await update.message.reply_text(crisis_response, parse_mode='Markdown')
        
        # Добавляем запись о кризисе
        if user_id in user_data:
            if "crisis_log" not in user_data[user_id]:
                user_data[user_id]["crisis_log"] = []
            user_data[user_id]["crisis_log"].append({
                "message": message[:100],
                "level": crisis_level,
                "time": datetime.now().isoformat()
            })
    
    # Получаем контекст пользователя
    user_context = {
        'user_id': user_id,
        'name': user_data[user_id].get('name', 'Пользователь'),
        'mood_history': user_data[user_id].get('mood_history', []),
        'is_crisis': crisis_level >= 2
    }
    
    # Получаем ответ от ИИ
    try:
        ai_response = await ai_service.get_ai_response(message, user_context)
        await update.message.reply_text(f"🤖 *Помощник:*\n\n{ai_response}", parse_mode='Markdown')
        
        # Сохраняем историю чата
        if user_id in user_data:
            user_data[user_id]["chat_history"].append({
                "user": message,
                "ai": ai_response,
                "time": datetime.now().isoformat()
            })
            # Ограничиваем историю последними 10 сообщениями
            if len(user_data[user_id]["chat_history"]) > 10:
                user_data[user_id]["chat_history"] = user_data[user_id]["chat_history"][-10:]
                
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        await update.message.reply_text(
            "😔 Извини, произошла ошибка при обработке запроса.\n"
            "Попробуй переформулировать вопрос или нажми '🔄 Новый вопрос'.",
            reply_markup=get_chat_mode_keyboard()
        )

async def save_mood(update: Update, mood_score: int):
    """Сохранение настроения"""
    user_id = update.effective_user.id
    user_data[user_id]["mood_history"].append(mood_score)
    user_data[user_id]["in_chat_mode"] = False
    
    emoji = MOOD_EMOJIS.get(mood_score, "")
    
    response = f"✅ Записал твое настроение: {mood_score}/10 {emoji}"
    
    if mood_score <= 4:
        response += "\n\nВижу, что тяжелый день. Может, попробуешь технику релаксации или пообщаешься с помощником?"
    elif mood_score >= 8:
        response += "\n\nОтлично! Рад, что у тебя хороший день! ✨"
    
    await update.message.reply_text(response, reply_markup=get_main_keyboard())

# ========== WEBHOOK ENDPOINTS ==========
@app.get("/")
async def root():
    status = "MindMate Bot v2.0 is running! 🚀"
    if bot_app:
        status += f" (Active users: {len(user_data)})"
    return {"status": status, "features": ["AI Chat", "Crisis Help", "Mood Tracking"]}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/webhook")
async def webhook(request: dict):
    """Endpoint для вебхука от Telegram"""
    if not bot_app:
        return {"status": "error", "message": "Bot not initialized"}
    
    try:
        # Инициализация обработчиков при первом запросе
        if not bot_app.handlers:
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
            # Получаем URL из окружения (Railway автоматически устанавливает)
            webhook_url = os.getenv('RAILWAY_STATIC_URL', '') + "/webhook"
            
            # Если URL не начинается с http, добавляем https
            if webhook_url and not webhook_url.startswith("http"):
                webhook_url = "https://" + webhook_url
            
            # Устанавливаем вебхук
            if webhook_url and webhook_url.startswith("http"):
                await bot_app.bot.set_webhook(webhook_url)
                logger.info(f"✅ Webhook установлен: {webhook_url}")
            else:
                logger.warning("⚠️ Webhook URL not found or invalid")
                
        except Exception as e:
            logger.error(f"❌ Webhook setup error: {e}")

# Для локального запуска
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
