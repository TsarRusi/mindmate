"""
MindMate Bot - Упрощенная версия с нейросетью
"""
import os
import logging
import random
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Optional

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackQueryHandler
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI
import uvicorn

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
    exit(1)

# Создаем бота
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
web_app = FastAPI(title="MindMate Bot")

# ========== БАЗА ДАННЫХ В ПАМЯТИ ==========
user_data: Dict[int, Dict] = {}
technique_manager = {}
ai_conversations: Dict[int, List] = {}

# ========== СЕРВИС НЕЙРОСЕТИ ==========
class AIService:
    """Упрощенный сервис нейросети с fallback"""
    
    def __init__(self):
        self.api_key = os.getenv('YANDEX_API_KEY')
        self.folder_id = os.getenv('YANDEX_FOLDER_ID')
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
    def is_yandex_available(self) -> bool:
        return bool(self.api_key and self.folder_id)
    
    async def get_response(self, user_id: int, message: str, mode: str = "support") -> str:
        """Получить ответ от нейросети"""
        
        # Проверка кризисных слов
        crisis_words = ['суицид', 'умру', 'не хочу жить', 'самоубийство']
        if any(word in message.lower() for word in crisis_words):
            return self._crisis_response()
        
        # Пробуем Yandex GPT
        if self.is_yandex_available():
            try:
                return await self._call_yandex_gpt(user_id, message, mode)
            except Exception as e:
                logger.error(f"Yandex GPT error: {e}")
        
        # Fallback на локальные ответы
        return self._fallback_response(message, mode)
    
    async def _call_yandex_gpt(self, user_id: int, message: str, mode: str) -> str:
        """Вызов Yandex GPT"""
        
        # Инициализируем историю
        if user_id not in ai_conversations:
            ai_conversations[user_id] = []
        
        history = ai_conversations[user_id][-3:]  # Последние 3 сообщения
        
        # Создаем промпт
        system_prompt = self._create_prompt(mode)
        
        # Формируем сообщения
        messages = [{"role": "system", "text": system_prompt}]
        
        # Добавляем историю
        for h in history:
            messages.append({"role": "user", "text": h.get("user", "")})
            messages.append({"role": "assistant", "text": h.get("ai", "")})
        
        # Добавляем текущее сообщение
        messages.append({"role": "user", "text": message})
        
        # Делаем запрос
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": 500
            },
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result["result"]["alternatives"][0]["message"]["text"]
                    
                    # Сохраняем в историю
                    ai_conversations[user_id].append({
                        "user": message,
                        "ai": response_text,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Ограничиваем историю
                    if len(ai_conversations[user_id]) > 10:
                        ai_conversations[user_id] = ai_conversations[user_id][-10:]
                    
                    return response_text
                else:
                    raise Exception(f"API error: {response.status}")
    
    def _create_prompt(self, mode: str) -> str:
        """Создание промпта"""
        prompts = {
            "support": "Ты MindMate - эмпатичный помощник для психологической поддержки. Будь поддерживающим, предлагай техники релаксации. Отвечай кратко с эмодзи.",
            "analysis": "Ты помогаешь анализировать ситуации. Задавай вопросы, помогай увидеть разные стороны.",
            "advice": "Ты даешь практические советы и техники для улучшения состояния."
        }
        return prompts.get(mode, prompts["support"])
    
    def _crisis_response(self) -> str:
        """Ответ на кризис"""
        return """🚨 ВАЖНО: Немедленно обратись за помощью!

📞 Телефоны:
• 8-800-2000-122 (Россия)
• 112 или 103 (Скорая)

🎯 Пока ждешь помощи:
1. Техника 5-4-3-2-1
2. Дыхание 4-7-8
3. Позови кого-то"""
    
    def _fallback_response(self, message: str, mode: str) -> str:
        """Простой ответ если нейросеть недоступна"""
        responses = {
            "тревога": [
                "Понимаю, тревога тяжела. Попробуй технику 5-4-3-2-1 🌿",
                "Сделай 4 глубоких вдоха. Ты сильнее, чем кажется 💪"
            ],
            "грусть": [
                "Грусть - это нормально. Позволь себе ее чувствовать ❤️",
                "Сделай что-то доброе для себя сегодня 🌟"
            ],
            "стресс": [
                "Стресс истощает. Попробуй дыхание 4-7-8 🧘",
                "Разбей задачи на маленькие шаги 🎯"
            ]
        }
        
        # Ищем ключевые слова
        msg_lower = message.lower()
        for key, answers in responses.items():
            if key in msg_lower:
                return random.choice(answers)
        
        # Общие ответы
        general = [
            "Спасибо, что поделился. Хочешь обсудить подробнее? 💭",
            "Я слышу тебя. Твои чувства важны 🤗",
            "Что обычно помогает тебе в таких ситуациях? 🤔"
        ]
        return random.choice(general)

# Инициализация AI сервиса
ai_service = AIService()

# ========== БАЗА ТЕХНИК РЕЛАКСАЦИИ ==========
TECHNIQUES = {
    "быстрые": [
        {
            "id": 1,
            "name": "🧘 Дыхание 4-7-8",
            "description": "Быстрое успокоение нервной системы",
            "duration": "3-5 минут",
            "steps": [
                "Сядьте удобно",
                "Выдохните через рот",
                "Вдохните через нос на 4 счета",
                "Задержите на 7",
                "Выдохните на 8",
                "Повторите 4 раза"
            ]
        },
        {
            "id": 2,
            "name": "👁️ Техника 5-4-3-2-1",
            "description": "Возвращение в настоящее",
            "duration": "5 минут",
            "steps": [
                "Назовите 5 вещей вокруг",
                "Найдите 4 вещи для прикосновения",
                "Услышьте 3 звука",
                "Почувствуйте 2 запаха",
                "Вспомните 1 вкус"
            ]
        }
    ],
    "медитации": [
        {
            "id": 3,
            "name": "🧠 Медитация осознанности",
            "description": "Наблюдение за мыслями",
            "duration": "10-15 минут",
            "steps": [
                "Сядьте с прямой спиной",
                "Закройте глаза",
                "Сосредоточьтесь на дыхании",
                "Отмечайте мысли без оценки",
                "Возвращайтесь к дыханию"
            ]
        }
    ],
    "для сна": [
        {
            "id": 4,
            "name": "💤 Техника для засыпания",
            "description": "Расслабление перед сном",
            "duration": "10 минут",
            "steps": [
                "Лягте в кровать",
                "Расслабьте пальцы ног",
                "Двигайтесь вверх по телу",
                "Представляйте тяжесть",
                "Дышите глубоко"
            ]
        }
    ]
}

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    """Главное меню"""
    keyboard = [
        [KeyboardButton("📊 Настроение"), KeyboardButton("🧘 Техники")],
        [KeyboardButton("💬 Чат с ИИ"), KeyboardButton("🚨 Кризис")],
        [KeyboardButton("📈 Статистика"), KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def chat_menu():
    """Меню чата"""
    keyboard = [
        [KeyboardButton("🤝 Поддержка"), KeyboardButton("🧠 Анализ")],
        [KeyboardButton("💡 Советы"), KeyboardButton("🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def techniques_menu():
    """Меню техник"""
    keyboard = [
        [KeyboardButton("⚡ Быстрые"), KeyboardButton("🧠 Медитации")],
        [KeyboardButton("💤 Для сна"), KeyboardButton("🎯 Случайная")],
        [KeyboardButton("🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def mood_menu():
    """Меню настроения"""
    keyboard = [
        [KeyboardButton("1 😫"), KeyboardButton("2 😔"), KeyboardButton("3 😟")],
        [KeyboardButton("4 😐"), KeyboardButton("5 🙂"), KeyboardButton("6 😊")],
        [KeyboardButton("7 😄"), KeyboardButton("8 🤩"), KeyboardButton("9 🥰")],
        [KeyboardButton("10 🎉"), KeyboardButton("🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализация пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            "name": user.first_name,
            "moods": [],
            "joined": datetime.now().isoformat(),
            "chat_mode": "support"
        }
    
    welcome = f"""
🤗 Привет, {user.first_name}!

Я — MindMate, твой помощник для ментального здоровья.

✨ Что я умею:
• 💬 Чат с ИИ (нейросеть)
• 🧘 Техники релаксации
• 📊 Отслеживание настроения
• 🚨 Кризисная помощь

Выбери действие ниже:
"""
    await update.message.reply_text(welcome, reply_markup=main_menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📖 Помощь по MindMate

Основные функции:
• /start - Начать
• /chat - Чат с ИИ
• /techniques - Техники
• /mood - Настроение
• /crisis - Экстренная помощь

Или используй кнопки в меню!
"""
    await update.message.reply_text(help_text, reply_markup=main_menu())

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Чат с ИИ"""
    ai_status = "✅ Доступен" if ai_service.is_yandex_available() else "⚠️ Локальный режим"
    
    text = f"""
💭 Чат с ИИ-помощником

Статус нейросети: {ai_status}

Выбери режим:
• 🤝 Поддержка - эмоциональная поддержка
• 🧠 Анализ - анализ ситуации
• 💡 Советы - практические рекомендации

Или просто напиши, что беспокоит.
"""
    await update.message.reply_text(text, reply_markup=chat_menu())

async def techniques_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Техники релаксации"""
    text = """
🧘 Техники релаксации

Выбери категорию:
• ⚡ Быстрые (3-5 мин)
• 🧠 Медитации (10-15 мин)
• 💤 Для сна
• 🎯 Случайная техника
"""
    await update.message.reply_text(text, reply_markup=techniques_menu())

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запись настроения"""
    text = """
📊 Отслеживание настроения

Оцени от 1 до 10:
1-3 😔 - Тяжело
4-6 😐 - Нормально
7-10 😊 - Хорошо

Выбери цифру:
"""
    await update.message.reply_text(text, reply_markup=mood_menu())

async def crisis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кризисная помощь"""
    crisis_text = """
🚨 КРИЗИСНАЯ ПОМОЩЬ

Если тебе очень тяжело:

📞 Телефоны:
• 8-800-2000-122 (Россия)
• 8-495-575-87-70 (Москва)
• 103 или 112 (Скорая)

🎯 Техники сейчас:
1. Дыхание 4-7-8
2. Техника 5-4-3-2-1
3. Позови близких

Ты не одинок! Помощь доступна.
"""
    await update.message.reply_text(crisis_text, reply_markup=main_menu())

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Инициализация
    if user_id not in user_data:
        user_data[user_id] = {
            "name": update.effective_user.first_name,
            "moods": [],
            "joined": datetime.now().isoformat(),
            "chat_mode": "support",
            "in_ai_chat": False
        }
    
    # Навигация по меню
    if text == "🔙 Назад":
        await update.message.reply_text("🏠 Главное меню", reply_markup=main_menu())
        user_data[user_id]["in_ai_chat"] = False
        return
    
    # Главное меню
    elif text == "💬 Чат с ИИ":
        await chat_command(update, context)
        return
    elif text == "🧘 Техники":
        await techniques_command(update, context)
        return
    elif text == "📊 Настроение":
        await mood_command(update, context)
        return
    elif text == "🚨 Кризис":
        await crisis_command(update, context)
        return
    elif text == "📈 Статистика":
        await show_stats(update, user_id)
        return
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
        return
    
    # Режимы чата
    elif text in ["🤝 Поддержка", "🧠 Анализ", "💡 Советы"]:
        mode_map = {
            "🤝 Поддержка": "support",
            "🧠 Анализ": "analysis",
            "💡 Советы": "advice"
        }
        user_data[user_id]["chat_mode"] = mode_map[text]
        user_data[user_id]["in_ai_chat"] = True
        
        await update.message.reply_text(
            f"✅ Режим выбран. Пиши свое сообщение...",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]], resize_keyboard=True)
        )
        return
    
    # Если в AI-чате
    elif user_data[user_id].get("in_ai_chat", False):
        # Показываем "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        try:
            mode = user_data[user_id].get("chat_mode", "support")
            response = await ai_service.get_response(user_id, text, mode)
            
            await update.message.reply_text(
                response,
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]], resize_keyboard=True)
            )
            
        except Exception as e:
            await update.message.reply_text(
                "😔 Ошибка. Попробуй еще раз.",
                reply_markup=main_menu()
            )
            user_data[user_id]["in_ai_chat"] = False
        
        return
    
    # Техники
    elif text in ["⚡ Быстрые", "🧠 Медитации", "💤 Для сна"]:
        category = text.split(" ")[1].lower()
        await show_category_techniques(update, category)
        return
    
    elif text == "🎯 Случайная":
        await show_random_technique(update)
        return
    
    # Настроение
    elif any(text.startswith(str(i)) for i in range(1, 11)) and "�" in text:
        mood = int(text.split()[0])
        await save_mood(update, user_id, mood)
        return
    
    # Обычные сообщения
    else:
        await update.message.reply_text(
            "Используй кнопки для навигации! 🎯",
            reply_markup=main_menu()
        )

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def save_mood(update: Update, user_id: int, score: int):
    """Сохранить настроение"""
    user_data[user_id]["moods"].append({
        "score": score,
        "time": datetime.now().isoformat()
    })
    
    emojis = {1: "😫", 2: "😔", 3: "😟", 4: "😐", 5: "🙂", 
              6: "😊", 7: "😄", 8: "🤩", 9: "🥰", 10: "🎉"}
    
    await update.message.reply_text(
        f"✅ Сохранено: {score}/10 {emojis.get(score, '')}\n"
        f"Всего записей: {len(user_data[user_id]['moods'])}",
        reply_markup=main_menu()
    )

async def show_category_techniques(update: Update, category: str):
    """Показать техники категории"""
    techniques = TECHNIQUES.get(category, [])
    
    if not techniques:
        await update.message.reply_text("Техники не найдены", reply_markup=techniques_menu())
        return
    
    # Создаем инлайн-кнопки
    keyboard = []
    for tech in techniques:
        keyboard.append([InlineKeyboardButton(tech["name"], callback_data=f"tech_{tech['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    category_names = {
        "быстрые": "⚡ Быстрые техники",
        "медитации": "🧠 Медитации",
        "для сна": "💤 Для сна"
    }
    
    await update.message.reply_text(
        f"{category_names.get(category, category)}:",
        reply_markup=reply_markup
    )

async def show_random_technique(update: Update):
    """Показать случайную технику"""
    all_tech = []
    for category in TECHNIQUES.values():
        all_tech.extend(category)
    
    if not all_tech:
        await update.message.reply_text("Техники не найдены", reply_markup=techniques_menu())
        return
    
    tech = random.choice(all_tech)
    steps = "\n".join([f"• {step}" for step in tech["steps"]])
    
    text = f"""
{tech['name']}

{tech['description']}

⏱️ {tech['duration']}

📝 Шаги:
{steps}

Попробуй прямо сейчас! 🌟
"""
    await update.message.reply_text(text, reply_markup=techniques_menu())

async def show_stats(update: Update, user_id: int):
    """Показать статистику"""
    if user_id not in user_data or not user_data[user_id]["moods"]:
        await update.message.reply_text(
            "📊 У тебя пока нет записей настроения.",
            reply_markup=main_menu()
        )
        return
    
    moods = [m["score"] for m in user_data[user_id]["moods"]]
    avg = sum(moods) / len(moods)
    
    text = f"""
📈 Твоя статистика:

• 📊 Записей: {len(moods)}
• 📅 Среднее: {avg:.1f}/10
• 🎯 Последняя: {moods[-1]}/10

Продолжай отслеживать! 🌟
"""
    await update.message.reply_text(text, reply_markup=main_menu())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка инлайн-кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("tech_"):
        tech_id = int(query.data.split("_")[1])
        
        # Ищем технику
        tech = None
        for category in TECHNIQUES.values():
            for t in category:
                if t["id"] == tech_id:
                    tech = t
                    break
            if tech:
                break
        
        if tech:
            steps = "\n".join([f"• {step}" for step in tech["steps"]])
            text = f"""
{tech['name']}

{tech['description']}

⏱️ {tech['duration']}

📝 Шаги:
{steps}

Попробуй выполнить! 🌟
"""
            await query.edit_message_text(text)
        else:
            await query.edit_message_text("Техника не найдена")

# ========== FASTAPI ENDPOINTS ==========
@web_app.get("/")
async def root():
    return {"status": "MindMate Bot is running!", "users": len(user_data)}

@web_app.get("/health")
async def health():
    return {"status": "healthy"}

# ========== НАСТРОЙКА И ЗАПУСК ==========
def setup_handlers():
    """Настройка обработчиков"""
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("chat", chat_command))
    bot_app.add_handler(CommandHandler("techniques", techniques_command))
    bot_app.add_handler(CommandHandler("mood", mood_command))
    bot_app.add_handler(CommandHandler("crisis", crisis_command))
    
    bot_app.add_handler(CallbackQueryHandler(button_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def startup():
    """Запуск приложения"""
    setup_handlers()
    logger.info("🚀 MindMate Bot запущен!")
    
    # Проверка AI
    if ai_service.is_yandex_available():
        logger.info("✅ Yandex GPT доступен")
    else:
        logger.info("⚠️ Yandex GPT не настроен, используется локальный режим")

# ========== ТОЧКА ВХОДА ==========
if __name__ == "__main__":
    import asyncio
    
    # Настраиваем обработчики
    setup_handlers()
    
    # Запускаем
    logger.info("🤖 Запускаю MindMate Bot...")
    
    # Проверяем токены
    if not TELEGRAM_TOKEN:
        logger.error("❌ Токен бота не найден!")
        exit(1)
    
    # Запускаем polling
    bot_app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_UPDATES
    )
