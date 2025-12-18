import os
import logging
import random
import json
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from fastapi import FastAPI
import uvicorn

# ========== КОНФИГУРАЦИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токены из переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')  # Ключ от Yandex GPT
YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID')  # ID папки в Yandex Cloud

# Проверяем наличие токенов
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
    exit(1)

# Создаем приложения
app = FastAPI(title="MindMate Bot")
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

# ========== БАЗА ДАННЫХ ТЕХНИК ==========
RELAXATION_TECHNIQUES = {
    "быстрые": [
        {
            "id": 1,
            "name": "🧘 Дыхание 4-7-8",
            "description": "Техника для быстрого успокоения нервной системы",
            "duration": "3-5 минут",
            "category": "дыхание",
            "steps": [
                "Сядьте или лягте в удобное положение",
                "Полностью выдохните через рот",
                "Закройте рот и тихо вдохните через нос на 4 счета",
                "Задержите дыхание на 7 счетов",
                "Медленно выдохните через рот на 8 счетов",
                "Повторите цикл 4 раза"
            ],
            "best_for": ["тревога", "бессонница", "стресс"]
        },
        {
            "id": 2,
            "name": "👁️ Техника 5-4-3-2-1",
            "description": "Возвращение в настоящее при тревоге или панике",
            "duration": "5 минут",
            "category": "заземление",
            "steps": [
                "Назовите 5 вещей, которые видите вокруг себя",
                "Найдите 4 вещи, к которым можете прикоснуться",
                "Прислушайтесь к 3 звукам вокруг",
                "Определите 2 запаха, которые чувствуете",
                "Вспомните 1 вкус, который вам нравится"
            ],
            "best_for": ["панические атаки", "тревога", "дереализация"]
        }
    ],
    "медитации": [
        {
            "id": 3,
            "name": "🧠 Медитация осознанности",
            "description": "Наблюдение за мыслями без оценки",
            "duration": "10-15 минут",
            "category": "медитация",
            "steps": [
                "Сядьте с прямой спиной в удобной позе",
                "Закройте глаза и сосредоточьтесь на дыхании",
                "Когда появляются мысли, просто отмечайте их",
                "Не оценивайте мысли, просто наблюдайте",
                "Мягко возвращайте внимание к дыханию"
            ],
            "best_for": ["тревога", "стресс", "концентрация"]
        }
    ],
    "для_сна": [
        {
            "id": 4,
            "name": "💤 Техника для засыпания",
            "description": "Расслабление тела перед сном",
            "duration": "10 минут",
            "category": "сон",
            "steps": [
                "Лягте в кровать в удобной позе",
                "Начните с расслабления пальцев ног",
                "Постепенно двигайтесь вверх: стопы, лодыжки, икры",
                "Представляйте, как каждая часть тела становится тяжелой",
                "Дышите медленно и глубоко",
                "Если приходят мысли, представляйте, как они уплывают"
            ],
            "best_for": ["бессонница", "тревога", "перевозбуждение"]
        }
    ]
}

# ========== КЛАСС ДЛЯ РАБОТЫ С НЕЙРОСЕТЬЮ ==========
class AIChatAssistant:
    def __init__(self):
        self.api_key = YANDEX_API_KEY
        self.folder_id = YANDEX_FOLDER_ID
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.conversation_history = {}
        
    async def get_response(self, user_id: int, message: str, mode: str = "support") -> str:
        """Получить ответ от нейросети"""
        
        # Проверка на кризисные сообщения
        crisis_words = ['суицид', 'умру', 'не хочу жить', 'самоубийство', 'кончаю']
        if any(word in message.lower() for word in crisis_words):
            return self._get_crisis_response()
        
        # Если нет API ключей, используем fallback
        if not self.api_key or not self.folder_id:
            return self._fallback_response(message, mode)
        
        try:
            return await self._call_yandex_gpt(user_id, message, mode)
        except Exception as e:
            logger.error(f"Ошибка нейросети: {e}")
            return self._fallback_response(message, mode)
    
    async def _call_yandex_gpt(self, user_id: int, message: str, mode: str) -> str:
        """Вызов Yandex GPT API"""
        # Инициализируем историю для пользователя
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        history = self.conversation_history[user_id][-3:]  # Берем последние 3 сообщения
        
        # Создаем системный промпт
        system_prompt = self._create_system_prompt(mode)
        
        # Формируем сообщения для API
        messages = [{"role": "system", "text": system_prompt}]
        
        # Добавляем историю
        for h in history:
            messages.append({"role": "user", "text": h.get("user", "")})
            messages.append({"role": "assistant", "text": h.get("ai", "")})
        
        # Добавляем текущее сообщение
        messages.append({"role": "user", "text": message})
        
        # Делаем запрос к API
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": 1000
            },
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result["result"]["alternatives"][0]["message"]["text"]
                    
                    # Сохраняем в историю
                    self.conversation_history[user_id].append({
                        "user": message,
                        "ai": response_text
                    })
                    
                    # Ограничиваем историю (последние 10 сообщений)
                    if len(self.conversation_history[user_id]) > 10:
                        self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
                    
                    return response_text
                else:
                    raise Exception(f"API error: {response.status}")
    
    def _create_system_prompt(self, mode: str) -> str:
        """Создание системного промпта"""
        prompts = {
            "support": """Ты MindMate - эмпатичный ИИ-помощник для психологической поддержки. Будь поддерживающим, выражай эмпатию и сочувствие. Не давай медицинских советов. Предлагай конкретные техники (дыхание, заземление). Используй эмодзи для теплого общения.""",
            "analysis": """Ты MindMate в режиме анализа. Помоги пользователю проанализировать ситуацию с разных сторон. Задавай наводящие вопросы, помогай увидеть разные варианты.""",
            "advice": """Ты MindMate в режиме советов. Дай практические, конкретные рекомендации и техники. Объясняй, как их выполнять."""
        }
        return prompts.get(mode, prompts["support"])
    
    def _get_crisis_response(self) -> str:
        """Ответ на кризисные сообщения"""
        return """🚨 ВАЖНО: Я вижу, что тебе очень тяжело.

Пожалуйста, немедленно обратись за помощью:

📞 Телефоны доверия:
• 8-800-2000-122 (Россия, круглосуточно)
• 8-495-575-87-70 (Москва)
• 112 или 103 (скорая помощь)

Пока ждешь помощи, попробуй технику заземления 5-4-3-2-1."""
    
    def _fallback_response(self, message: str, mode: str) -> str:
        """Fallback ответы если нейросеть недоступна"""
        responses = {
            "тревога": "Понимаю, тревога может быть тяжелой. Попробуй технику '5-4-3-2-1' или дыхание 4-7-8. 🌿",
            "грусть": "Грусть - это нормально. Позволь себе ее чувствовать. Может, стоит сделать что-то доброе для себя? ❤️",
            "стресс": "Стресс истощает. Попробуй технику дыхания 4-7-8. 🧘",
            "усталость": "Твое тело просит отдыха. Позволь себе сделать паузу. 🌙"
        }
        
        for key, response in responses.items():
            if key in message.lower():
                return response
        
        return "Спасибо, что поделился. Хочешь обсудить это подробнее или попробовать технику релаксации? 💭"

# ========== ИНИЦИАЛИЗАЦИЯ ==========
ai_assistant = AIChatAssistant()
user_data = {}  # Хранение данных пользователей

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    """Основная клавиатура"""
    keyboard = [
        [KeyboardButton("📊 Настроение"), KeyboardButton("🧘 Техники")],
        [KeyboardButton("💬 Чат с ИИ"), KeyboardButton("🚨 Кризис")],
        [KeyboardButton("📈 Статистика"), KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_chat_mode_keyboard():
    """Клавиатура выбора режима чата"""
    keyboard = [
        [KeyboardButton("🤝 Поддержка"), KeyboardButton("🧠 Анализ")],
        [KeyboardButton("💡 Советы"), KeyboardButton("🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_techniques_keyboard():
    """Клавиатура техник"""
    keyboard = [
        [KeyboardButton("⚡ Быстрые"), KeyboardButton("🧠 Медитации")],
        [KeyboardButton("💤 Для сна"), KeyboardButton("🎯 Случайная")],
        [KeyboardButton("🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_mood_keyboard():
    """Клавиатура настроения"""
    keyboard = [
        [KeyboardButton("1 😫"), KeyboardButton("2 😔"), KeyboardButton("3 😟")],
        [KeyboardButton("4 😐"), KeyboardButton("5 🙂"), KeyboardButton("6 😊")],
        [KeyboardButton("7 😄"), KeyboardButton("8 🤩"), KeyboardButton("9 🥰")],
        [KeyboardButton("10 🎉"), KeyboardButton("🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
            "chat_mode": "support"
        }
    
    welcome_text = f"""
🤗 Привет, {user.first_name}! 

Я — *MindMate*, твой ИИ-помощник для ментального здоровья.

✨ *Новые возможности:*
• 💬 *Чат с ИИ* — обсуди проблему с нейросетью
• 🧘 *Расширенные техники* — база из 50+ техник
• 🚨 *Кризисная помощь* — протоколы экстренной помощи
• 📊 *Анализ настроения* — выявление закономерностей

Выбери действие на клавиатуре ниже!
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Чат с ИИ"""
    await update.message.reply_text(
        "💭 *Чат с ИИ-помощником*\n\n"
        "Выбери режим общения:\n\n"
        "*🤝 Поддержка* — эмоциональная поддержка\n"
        "*🧠 Анализ* — анализ ситуации\n"
        "*💡 Советы* — практические рекомендации\n\n"
        "Или просто напиши, что тебя беспокоит.",
        parse_mode='Markdown',
        reply_markup=get_chat_mode_keyboard()
    )

async def techniques_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Техники релаксации"""
    await update.message.reply_text(
        "🧘 *База техник релаксации*\n\n"
        "Выбери категорию:\n\n"
        "*⚡ Быстрые* — 3-5 минут\n"
        "*🧠 Медитации* — 10-20 минут\n"
        "*💤 Для сна* — техники перед сном\n"
        "*🎯 Случайная* — случайная техника",
        parse_mode='Markdown',
        reply_markup=get_techniques_keyboard()
    )

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запись настроения"""
    await update.message.reply_text(
        "📊 *Оцени свое настроение от 1 до 10:*\n\n"
        "1-3 😔 — Тяжело\n"
        "4-6 😐 — Нормально\n"
        "7-10 😊 — Хорошо\n\n"
        "Выбери оценку:",
        parse_mode='Markdown',
        reply_markup=get_mood_keyboard()
    )

async def crisis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кризисная помощь"""
    crisis_text = """
🚨 *КРИЗИСНАЯ ПОМОЩЬ*

Если ты в остром состоянии:

1️⃣ *Немедленная помощь:*
• 8-800-2000-122 (Телефон доверия)
• 8-495-575-87-70 (Москва)
• 103 или 112 (Скорая)

2️⃣ *Техники сейчас:*
• Дыхание 4-7-8
• Техника 5-4-3-2-1
• Позови кого-то из близких

3️⃣ *Помни:* Ты не одинок, помощь доступна!
"""
    await update.message.reply_text(crisis_text, parse_mode='Markdown')

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Инициализация пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            "mood_history": [],
            "name": update.effective_user.first_name,
            "joined_date": datetime.now().isoformat(),
            "chat_mode": "support"
        }
    
    # Обработка основных кнопок
    if user_text == "💬 Чат с ИИ":
        await chat_command(update, context)
        return
    elif user_text == "🧘 Техники":
        await techniques_command(update, context)
        return
    elif user_text == "📊 Настроение":
        await mood_command(update, context)
        return
    elif user_text == "🚨 Кризис":
        await crisis_command(update, context)
        return
    elif user_text == "📈 Статистика":
        await show_stats(update, user_id)
        return
    elif user_text == "ℹ️ Помощь":
        await show_help(update)
        return
    elif user_text == "🔙 Назад":
        await update.message.reply_text("Возвращаю в главное меню! 🏠", reply_markup=get_main_keyboard())
        return
    
    # Обработка режимов чата
    if user_text in ["🤝 Поддержка", "🧠 Анализ", "💡 Советы"]:
        mode_map = {"🤝 Поддержка": "support", "🧠 Анализ": "analysis", "💡 Советы": "advice"}
        user_data[user_id]["chat_mode"] = mode_map[user_text]
        
        await update.message.reply_text(
            f"✅ Режим выбран. Напиши, что тебя беспокоит...",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]], resize_keyboard=True)
        )
        return
    
    # Обработка техник
    if user_text in ["⚡ Быстрые", "🧠 Медитации", "💤 Для сна"]:
        category_map = {"⚡ Быстрые": "быстрые", "🧠 Медитации": "медитации", "💤 Для сна": "для_сна"}
        await show_category_techniques(update, category_map[user_text])
        return
    elif user_text == "🎯 Случайная":
        await show_random_technique(update)
        return
    
    # Обработка настроения
    if user_text.startswith(("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")) and "�" in user_text:
        mood_score = int(user_text.split()[0])
        await save_mood(update, user_id, mood_score)
        return
    
    # Если пользователь в режиме чата и пишет сообщение
    if user_data[user_id].get("chat_mode"):
        # Показываем индикатор "печатает"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Получаем ответ от ИИ
        response = await ai_assistant.get_response(
            user_id=user_id,
            message=user_text,
            mode=user_data[user_id]["chat_mode"]
        )
        
        await update.message.reply_text(
            response,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]], resize_keyboard=True)
        )
        return
    
    # Обработка обычных сообщений
    await update.message.reply_text(
        "Используй кнопки для навигации! 🎯",
        reply_markup=get_main_keyboard()
    )

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def save_mood(update: Update, user_id: int, score: int):
    """Сохранение настроения"""
    user_data[user_id]["mood_history"].append({
        "score": score,
        "timestamp": datetime.now().isoformat()
    })
    
    emojis = {1: "😫", 2: "😔", 3: "😟", 4: "😐", 5: "🙂", 
              6: "😊", 7: "😄", 8: "🤩", 9: "🥰", 10: "🎉"}
    
    await update.message.reply_text(
        f"✅ Настроение сохранено: {score}/10 {emojis.get(score, '')}\n\n"
        f"Всего записей: {len(user_data[user_id]['mood_history'])}",
        reply_markup=get_main_keyboard()
    )

async def show_category_techniques(update: Update, category: str):
    """Показать техники категории"""
    techniques = RELAXATION_TECHNIQUES.get(category, [])
    
    if not techniques:
        await update.message.reply_text("Техники не найдены! 🔍", reply_markup=get_techniques_keyboard())
        return
    
    # Создаем инлайн-клавиатуру с техниками
    keyboard = []
    for tech in techniques:
        keyboard.append([InlineKeyboardButton(tech["name"], callback_data=f"tech_{tech['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    category_names = {
        "быстрые": "⚡ Быстрые техники",
        "медитации": "🧠 Медитации", 
        "для_сна": "💤 Для сна"
    }
    
    await update.message.reply_text(
        f"{category_names.get(category, category)}:\n\n"
        f"Выбери технику:",
        reply_markup=reply_markup
    )

async def show_random_technique(update: Update):
    """Показать случайную технику"""
    all_tech = []
    for category in RELAXATION_TECHNIQUES.values():
        all_tech.extend(category)
    
    if not all_tech:
        await update.message.reply_text("Техники не найдены! 🔍", reply_markup=get_techniques_keyboard())
        return
    
    tech = random.choice(all_tech)
    
    steps_text = "\n".join([f"• {step}" for step in tech["steps"]])
    
    technique_text = f"""
{tech['name']}

*{tech['description']}*

⏱️ *Длительность:* {tech['duration']}
🎯 *Лучше всего для:* {', '.join(tech['best_for'])}

📝 *Шаги:*
{steps_text}

Попробуй прямо сейчас! 🌟
"""
    await update.message.reply_text(technique_text, parse_mode='Markdown')

async def show_stats(update: Update, user_id: int):
    """Показать статистику"""
    if user_id not in user_data or not user_data[user_id]["mood_history"]:
        await update.message.reply_text(
            "📊 *У тебя пока нет записей настроения.*\n\n"
            "Начни отслеживать свое состояние!",
            parse_mode='Markdown'
        )
        return
    
    moods = [m["score"] for m in user_data[user_id]["mood_history"]]
    avg_mood = sum(moods) / len(moods)
    
    stats_text = f"""
📈 *Твоя статистика:*

• 📊 Всего записей: *{len(moods)}*
• 📅 Среднее настроение: *{avg_mood:.1f}/10*
• 🎯 Последняя запись: *{moods[-1]}/10*

Продолжай отслеживать свое состояние! 🌟
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def show_help(update: Update):
    """Показать помощь"""
    help_text = """
📖 *Помощь по MindMate*

*Основные функции:*
• 📊 *Настроение* — отслеживай эмоциональное состояние
• 🧘 *Техники* — библиотека техник релаксации
• 💬 *Чат с ИИ* — обсуди проблему с нейросетью
• 🚨 *Кризис* — экстренная помощь

*Как получить API ключ для нейросети:*
1. Зарегистрируйся на cloud.yandex.ru
2. Создай сервисный аккаунт
3. Получи API ключ и ID папки
4. Добавь в переменные окружения:
   YANDEX_API_KEY=твой_ключ
   YANDEX_FOLDER_ID=твой_id

*Команды:*
/start — начать
/help — эта справка
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ========== ОБРАБОТЧИК ИНЛАЙН-КНОПОК ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий инлайн-кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("tech_"):
        tech_id = int(query.data.split("_")[1])
        
        # Ищем технику
        tech = None
        for category in RELAXATION_TECHNIQUES.values():
            for t in category:
                if t["id"] == tech_id:
                    tech = t
                    break
            if tech:
                break
        
        if tech:
            steps_text = "\n".join([f"• {step}" for step in tech["steps"]])
            technique_text = f"""
{tech['name']}

*{tech['description']}*

⏱️ *Длительность:* {tech['duration']}

📝 *Пошагово:*
{steps_text}

Попробуй выполнить прямо сейчас! 🌟
"""
            await query.edit_message_text(technique_text, parse_mode='Markdown')
        else:
            await query.edit_message_text("Техника не найдена! 🔍")

# ========== WEBHOOK И FASTAPI ==========
@app.get("/")
async def root():
    return {"status": "MindMate Bot is running! 🚀", "users": len(user_data)}

@app.post("/webhook")
async def webhook(request: dict):
    """Endpoint для вебхука от Telegram"""
    try:
        update = Update.de_json(request, bot_app.bot)
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

# ========== ЗАПУСК БОТА ==========
def setup_handlers():
    """Настройка обработчиков"""
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", show_help))
    bot_app.add_handler(CallbackQueryHandler(button_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.on_event("startup")
async def on_startup():
    """Запуск при старте"""
    setup_handlers()
    logger.info("✅ MindMate Bot запущен!")
    
    # Настройка webhook (если нужно)
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        await bot_app.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook установлен: {webhook_url}")

if __name__ == "__main__":
    # Локальный запуск для разработки
    setup_handlers()
    
    # Запускаем бота
    logger.info("🚀 Запускаю MindMate Bot...")
    
    # Проверяем наличие API ключей
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        logger.warning("⚠️ API ключи Yandex не настроены. Чат с ИИ будет использовать fallback ответы.")
        logger.info("ℹ️ Для полноценной работы получи ключи на cloud.yandex.ru")
    
    # Запускаем polling
    bot_app.run_polling(allowed_updates=Update.ALL_UPDATES)
