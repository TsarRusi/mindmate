import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from fastapi import FastAPI, Request
import uvicorn

# Импортируем наши модули
from database import SessionLocal, User, MoodEntry
from nlp_analysis import analyze_text_sentiment # Функцию напишем позже
from ai_dialogue import get_ai_response # Функцию напишем позже

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Настраиваем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение для обработки вебхуков
app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

# ========== ОБРАБОТЧИКИ КОМАНД И СООБЩЕНИЙ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start."""
    user = update.effective_user
    db = SessionLocal()

    # Регистрируем пользователя в БД, если его нет
    db_user = db.query(User).filter(User.telegram_id == user.id).first()
    if not db_user:
        db_user = User(telegram_id=user.id, username=user.username, first_name=user.first_name)
        db.add(db_user)
        db.commit()

    db.close()

    welcome_text = (
        f"Привет, {user.first_name}! Я MindMate, твой персональный помощник для заботы о ментальном здоровье.\n\n"
        "Я могу:\n"
        "• Записывать твое настроение и анализировать его\n"
        "• Предлагать техники для снижения тревоги и стресса\n"
        "• Помочь выявить закономерности в твоем состоянии\n\n"
        "Как твое настроение сегодня от 1 до 10?"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения."""
    user_text = update.message.text
    user = update.effective_user

    # Если сообщение - это цифра от 1 до 10, трактуем как оценку настроения
    if user_text.isdigit() and 1 <= int(user_text) <= 10:
        await save_mood_score(update, context, int(user_text))
    else:
        # Иначе это текстовая запись -> анализируем ее
        await analyze_user_text(update, context, user_text)

async def save_mood_score(update: Update, context: CallbackContext, score: int):
    """Сохраняет оценку настроения в БД."""
    db = SessionLocal()
    user = update.effective_user

    mood_entry = MoodEntry(
        user_id=user.id,
        mood_score=score,
        created_at=update.message.date
    )
    db.add(mood_entry)
    db.commit()
    db.close()

    if score <= 4:
        await update.message.reply_text("Спасибо, что поделился. Вижу, что не самый лучший день. Хочешь написать подробнее или сделать короткое упражнение для поднятия настроения?")
    elif score <= 7:
        await update.message.reply_text("Понял, принял. Спасибо за честность! Если хочешь, можешь написать пару слов о своем дне — я проанализирую и помогу найти закономерности.")
    else:
        await update.message.reply_text("Это здорово! Рад за тебя! Поделись, что сегодня было хорошего? Это поможет закрепить позитивный опыт.")

async def analyze_user_text(update: Update, context: CallbackContext, text: str):
    """Анализирует текст пользователя с помощью NLP."""
    user = update.effective_user

    # Вызываем функцию анализа (реализуем ниже)
    analysis_result = analyze_text_sentiment(text)

    # Сохраняем запись и результат анализа в БД
    db = SessionLocal()
    mood_entry = MoodEntry(
        user_id=user.id,
        mood_text=text,
        sentiment_score=analysis_result.get('sentiment'),
        detected_emotion=analysis_result.get('emotion'),
        main_topics=str(analysis_result.get('topics', [])), # Сохраняем как строку
        created_at=update.message.date
    )
    db.add(mood_entry)
    db.commit()
    db.close()

    # Формируем ответ на основе анализа
    response = f"Я проанализировал твое сообщение.\n"
    response += f"**Эмоция:** {analysis_result.get('emotion', 'не определена')}\n"
    response += f"**Основные темы:** {', '.join(analysis_result.get('topics', []))}\n\n"

    if analysis_result['sentiment'] < -0.3:
        response += "Кажется, тебе тяжело. Хочешь, я предложу технику для снижения тревоги? (Напиши 'Упражнение')"
    else:
        response += "Спасибо, что делишься своими мыслями. Это важный шаг!"

    await update.message.reply_text(response)

# ========== WEBHOOK ENDPOINTS (для FastAPI) ==========

@app.post("/webhook")
async def webhook(request: Request):
    """Endpoint, который Telegram будет использовать для отправки обновлений."""
    update_data = await request.json()
    update = Update.de_json(update_data, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    """Устанавливает вебхук при запуске приложения."""
    webhook_url = "https://your-app-name.herokuapp.com/webhook" # ЗАМЕНИТЕ на ваш URL
    await bot_app.bot.set_webhook(webhook_url)
    # Регистрируем обработчики внутри бота
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    # Это для локального тестирования, на продакшене сервер запустит uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
