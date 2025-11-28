import os
import logging
import random
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from fastapi import FastAPI
import uvicorn
import json
from typing import Dict, List

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

# Структура для хранения данных пользователей
user_data: Dict[int, Dict] = {}

# База знаний бота
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
        "description": "Вернись в настоящий момент через органы чувств.",
        "steps": [
            "Назови 5 вещей, которые видишь вокруг",
            "Найди 4 вещи, к которым можешь прикоснуться",
            "Прислушайся к 3 звукам вокруг себя",
            "Найди 2 запаха, которые чувствуешь",
            "Вспомни 1 вкус, который тебе нравится"
        ]
    },
    {
        "name": "🖐️ Прогрессивная релаксация",
        "description": "Поочередно напрягай и расслабляй группы мышц.",
        "steps": [
            "Начни с пальцев ног - напряги на 5 секунд, затем расслабь",
            "Перейди к ступням и икрам",
            "Напряги бедра и ягодицы",
            "Сожми кулаки, затем расслабь руки",
            "Напряги плечи и шею",
            "Заверши лицом - наморщи лоб, затем расслабь"
        ]
    }
]

POSITIVE_AFFIRMATIONS = [
    "Ты справляешься лучше, чем думаешь! 💪",
    "Это временные трудности, ты станешь сильнее! 🌱",
    "Позволь себе чувствовать все эмоции - это нормально! 🎭",
    "Ты не один - я здесь чтобы поддержать! 🤗",
    "Маленькие шаги ведут к большим изменениям! 🐢",
    "Ты заслуживаешь заботы и отдыха! 🌟",
    "Каждый день - новая возможность начать заново! 🌅",
    "Ты сильнее, чем кажешься! 🦁",
    "Забота о себе - это не эгоизм, а необходимость! 💖"
]

MOOD_EMOJIS = {
    1: "😫", 2: "😔", 3: "😟", 4: "😐", 5: "🙂",
    6: "😊", 7: "😄", 8: "🤩", 9: "🥰", 10: "🎉"
}

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    """Основная клавиатура с кнопками"""
    keyboard = [
        [KeyboardButton("📊 Записать настроение"), KeyboardButton("🧘 Техники релаксации")],
        [KeyboardButton("💫 Позитивные аффирмации"), KeyboardButton("📈 Моя статистика")],
        [KeyboardButton("ℹ️ Помощь"), KeyboardButton("🎯 Случайная техника")]
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

def get_relaxation_keyboard():
    """Клавиатура для техник релаксации"""
    keyboard = [
        [KeyboardButton("🧘 Дыхание 4-7-8"), KeyboardButton("👁️ Техника 5-4-3-2-1")],
        [KeyboardButton("🖐️ Прогрессивная релаксация"), KeyboardButton("🎯 Случайная техника")],
        [KeyboardButton("↩️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализируем данные пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            "mood_history": [],
            "name": user.first_name,
            "joined_date": datetime.now().isoformat()
        }
    
    welcome_text = f"""
🤗 Привет, {user.first_name}! 

Я — *MindMate*, твой персональный помощник для заботы о ментальном здоровье.

✨ *Что я умею:*
• 📊 *Отслеживать настроение* — помогу заметить закономерности
• 🧘 *Техники релаксации* — упражнения для снятия стресса
• 💫 *Позитивные аффирмации* — поддержка в трудные моменты
• 📈 *Статистика* — анализ твоего эмоционального состояния

🎯 *Используй кнопки ниже или команды:*
/mood - записать настроение
/relax - техники релаксации  
/affirmation - позитивная аффирмация
/stats - моя статистика
/help - помощь

*Как твое настроение сегодня?* 😊
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    help_text = """
📖 *Помощь по использованию MindMate*

*Основные команды:*
/start - начать работу
/mood - записать настроение (1-10)
/relax - техники для релаксации
/affirmation - случайная аффирмация
/stats - статистика настроения
/help - эта справка

*Как работать с настроением:*
1. Используй кнопку "📊 Записать настроение"
2. Выбери цифру от 1 до 10, где:
   • 1-3 - очень плохо
   • 4-6 - нейтрально  
   • 7-10 - отлично
3. Я запомню твою оценку и покажу статистику

*Регулярное использование поможет:*
• Заметить закономерности в настроении
• Лучше понимать свои эмоции
• Находить эффективные способы самопомощи

Не стесняйся обращаться в трудные моменты! 🤗
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для записи настроения"""
    await update.message.reply_text(
        "📊 *Оцени свое настроение от 1 до 10:*\n\n"
        "1 😫 - Очень плохо\n"
        "2-3 😔 - Плохо\n" 
        "4-5 😐 - Нейтрально\n"
        "6-7 😊 - Хорошо\n"
        "8-10 🎉 - Отлично\n\n"
        "Выбери цифру на клавиатуре:",
        parse_mode='Markdown',
        reply_markup=get_mood_keyboard()
    )

async def relax_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для техник релаксации"""
    await update.message.reply_text(
        "🧘 *Выбери технику для релаксации:*\n\n"
        "• *Дыхание 4-7-8* - для быстрого успокоения\n"
        "• *Техника 5-4-3-2-1* - чтобы вернуться в настоящее\n"
        "• *Прогрессивная релаксация* - для снятия мышечного напряжения\n\n"
        "Или выбери случайную технику:",
        parse_mode='Markdown',
        reply_markup=get_relaxation_keyboard()
    )

async def affirmation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Случайная аффирмация"""
    affirmation = random.choice(POSITIVE_AFFIRMATIONS)
    await update.message.reply_text(f"💫 *Поддержка для тебя:*\n\n{affirmation}", parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика настроения"""
    user_id = update.effective_user.id
    
    if user_id not in user_data or not user_data[user_id]["mood_history"]:
        await update.message.reply_text(
            "📊 *У тебя пока нет записей настроения.*\n\n"
            "Используй кнопку \"📊 Записать настроение\" чтобы начать отслеживать свое состояние!",
            parse_mode='Markdown'
        )
        return
    
    moods = user_data[user_id]["mood_history"]
    avg_mood = sum(moods) / len(moods)
    
    # Анализ настроения
    if avg_mood <= 3:
        analysis = "💔 Сложный период. Помни, что это временно."
        emoji = "😔"
    elif avg_mood <= 6:
        analysis = "💛 Стабильно. Продолжай отслеживать свое состояние."
        emoji = "😐"
    else:
        analysis = "💚 Отлично! Ты хорошо справляешься."
        emoji = "😊"
    
    # Рекомендации
    if avg_mood <= 4:
        recommendation = "🎯 Рекомендую попробовать технику релаксации"
    elif len(moods) < 5:
        recommendation = "📝 Продолжай записывать настроение для более точной статистики"
    else:
        recommendation = "🌟 Продолжай в том же духе!"
    
    stats_text = f"""
📈 *Твоя статистика* {emoji}

• 📊 Всего записей: *{len(moods)}*
• 📅 Среднее настроение: *{avg_mood:.1f}/10*
• 🎯 Последняя запись: *{moods[-1]}/10* {MOOD_EMOJIS.get(moods[-1], '')}

*Анализ:*
{analysis}

*Рекомендация:*
{recommendation}

Продолжай заботиться о себе! 🌟
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения и кнопки"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Инициализация пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            "mood_history": [],
            "name": update.effective_user.first_name,
            "joined_date": datetime.now().isoformat()
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
    elif user_text == "ℹ️ Помощь":
        await help_command(update, context)
        return
    elif user_text == "🎯 Случайная техника":
        technique = random.choice(RELAXATION_TECHNIQUES)
        await send_relaxation_technique(update, technique)
        return
    elif user_text == "↩️ Назад":
        await update.message.reply_text(
            "Возвращаю в главное меню! 🏠",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Обработка кнопок настроения
    if user_text.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")) and "�" in user_text:
        mood_score = int(user_text.split()[0])
        await save_mood(update, mood_score)
        return
    
    # Обработка конкретных техник релаксации
    if user_text in ["🧘 Дыхание 4-7-8", "👁️ Техника 5-4-3-2-1", "🖐️ Прогрессивная релаксация"]:
        technique_name = user_text.split(" ", 1)[1]
        technique = next((t for t in RELAXATION_TECHNIQUES if t["name"].endswith(technique_name)), None)
        if technique:
            await send_relaxation_technique(update, technique)
        return
    
    # Обработка текстовых оценок настроения
    if user_text.isdigit() and 1 <= int(user_text) <= 10:
        await save_mood(update, int(user_text))
        return
    
    # Обычный текст
    responses = [
        "Спасибо, что делишься! 💭 Используй кнопки ниже для работы с ботом.",
        "Понимаю тебя! 🤗 Могу предложить технику релаксации или поддержку.",
        "Спасибо за доверие! Используй меню для навигации.",
        "Записал твои мысли. Хочешь поработать над своим состоянием?"
    ]
    await update.message.reply_text(
        random.choice(responses),
        reply_markup=get_main_keyboard()
    )

async def save_mood(update: Update, mood_score: int):
    """Сохраняет настроение пользователя"""
    user_id = update.effective_user.id
    user_data[user_id]["mood_history"].append(mood_score)
    
    emoji = MOOD_EMOJIS.get(mood_score, "")
    
    # Персонализированный ответ
    if mood_score <= 3:
        response = f"😔 Записал твое настроение: {mood_score}/10 {emoji}\n\nВижу, что тяжелый день. Хочешь попробовать технику релаксации?"
    elif mood_score <= 6:
        response = f"😐 Записал твое настроение: {mood_score}/10 {emoji}\n\nСпасибо за честность! Помни, что все эмоции важны."
    elif mood_score <= 8:
        response = f"😊 Записал твое настроение: {mood_score}/10 {emoji}\n\nХорошо! Рад, что у тебя неплохой день."
    else:
        response = f"🎉 Записал твое настроение: {mood_score}/10 {emoji}\n\nОтлично! Ты сияешь! Поделись энергией с окружающими!"
    
    await update.message.reply_text(response, reply_markup=get_main_keyboard())

async def send_relaxation_technique(update: Update, technique: dict):
    """Отправляет технику релаксации"""
    steps_text = "\n".join([f"• {step}" for step in technique["steps"]])
    
    technique_text = f"""
{technique['name']}

*{technique['description']}*

📝 *Пошагово:*
{steps_text}

⏱️ *Выполняй 5-10 минут*

После выполнения оцени свое состояние! 🌟
"""
    await update.message.reply_text(technique_text, parse_mode='Markdown')

# ========== WEBHOOK ENDPOINTS ==========
@app.get("/")
async def root():
    status = "MindMate Bot is running! 🚀"
    if bot_app:
        status += f" (Active users: {len(user_data)})"
    return {"status": status, "version": "2.0"}

@app.post("/webhook")
async def webhook(request: dict):
    """Endpoint для вебхука от Telegram."""
    if not bot_app:
        return {"status": "error", "message": "Bot not initialized"}
    
    try:
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
    """Настройка при запуске."""
    if bot_app:
        try:
            webhook_url = os.getenv('RENDER_EXTERNAL_URL', '') + "/webhook"
            if webhook_url:
                await bot_app.bot.set_webhook(webhook_url)
                logger.info(f"✅ Webhook установлен: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Startup error: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
