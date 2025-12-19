import os
import json
import logging
from typing import Optional, Dict, Any
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class AIService:
    """Сервис для работы с нейросетями"""
    
    def __init__(self):
        self.yandex_iam_token = os.getenv('YANDEX_IAM_TOKEN')
        self.yandex_folder_id = os.getenv('YANDEX_FOLDER_ID')
        self.gigachat_token = os.getenv('GIGACHAT_TOKEN')
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        
    async def get_ai_response(self, user_message: str, user_context: Dict = None) -> str:
        """Получает ответ от нейросети"""
        
        # Сначала проверяем кризисные слова
        if self.is_crisis_message(user_message):
            return self.get_crisis_response()
        
        # Выбираем сервис
        if self.yandex_iam_token and self.yandex_folder_id:
            return await self.yandex_gpt(user_message, user_context)
        elif self.gigachat_token:
            return await self.gigachat(user_message, user_context)
        elif self.deepseek_api_key:
            return await self.deepseek(user_message, user_context)
        else:
            return self.get_fallback_response(user_message)
    
    async def yandex_gpt(self, message: str, context: Optional[Dict] = None) -> str:
        """Использует YandexGPT API"""
        try:
            url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
            
            headers = {
                "Authorization": f"Bearer {self.yandex_iam_token}",
                "x-folder-id": self.yandex_folder_id,
                "Content-Type": "application/json"
            }
            
            prompt = self.build_prompt(message, context)
            
            data = {
                "modelUri": f"gpt://{self.yandex_folder_id}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.7,
                    "maxTokens": 1000
                },
                "messages": [
                    {
                        "role": "system",
                        "text": """Ты - добрый и эмпатичный психологический помощник MindMate.
                        Твоя задача - поддерживать пользователя, задавать наводящие вопросы,
                        помогать осознавать эмоции. Будь краток (2-3 предложения).
                        Не давай медицинских рекомендаций.
                        В критических ситуациях направляй к специалистам."""
                    },
                    {
                        "role": "user",
                        "text": prompt
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result['result']['alternatives'][0]['message']['text']
            
        except Exception as e:
            logger.error(f"YandexGPT error: {e}")
            return self.get_fallback_response(message)
    
    async def gigachat(self, message: str, context: Optional[Dict] = None) -> str:
        """Использует GigaChat API"""
        try:
            # Получаем токен доступа
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            auth_headers = {
                "Authorization": f"Bearer {self.gigachat_token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            auth_data = {"scope": "GIGACHAT_API_PERS"}
            
            auth_response = requests.post(auth_url, headers=auth_headers, data=auth_data)
            access_token = auth_response.json().get("access_token")
            
            # Отправляем запрос
            url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            prompt = self.build_prompt(message, context)
            
            data = {
                "model": "GigaChat",
                "messages": [
                    {"role": "system", "content": "Ты психологический помощник."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"GigaChat error: {e}")
            return self.get_fallback_response(message)
    
    async def deepseek(self, message: str, context: Optional[Dict] = None) -> str:
        """Использует DeepSeek API"""
        try:
            url = "https://api.deepseek.com/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = self.build_prompt(message, context)
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Ты психологический помощник."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            return self.get_fallback_response(message)
    
    def build_prompt(self, message: str, context: Optional[Dict] = None) -> str:
        """Создает промпт с контекстом"""
        base_prompt = f"Сообщение пользователя: {message}"
        
        if context:
            if 'mood_history' in context and context['mood_history']:
                avg_mood = sum(context['mood_history']) / len(context['mood_history'])
                base_prompt += f"\nИстория настроений пользователя: среднее {avg_mood}/10"
            if 'recent_topics' in context:
                base_prompt += f"\nНедавние темы: {', '.join(context['recent_topics'])}"
        
        return base_prompt
    
    def is_crisis_message(self, message: str) -> bool:
        """Определяет кризисные сообщения"""
        crisis_keywords = [
            'суицид', 'самоубийство', 'покончить', 'умру', 'не хочу жить',
            'порежу', 'повешусь', 'выброшусь', 'отравлюсь',
            'кризис', 'не выдерживаю', 'больше не могу',
            'помогите', 'спасите', 'экстренно'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in crisis_keywords)
    
    def get_crisis_response(self) -> str:
        """Ответ на кризисное сообщение"""
        return """
🚨 Я вижу, что тебе очень тяжело. 

❗ *Это важно:* я - бот, и не могу оказать экстренную помощь.

📞 *Немедленно обратись:*
• Телефон доверия: 8-800-2000-122 (круглосуточно, бесплатно)
• Экстренная психологическая помощь: 112
• Неотложная помощь: 103

💬 *Также можешь написать:*
• @psyhelpbot - психологическая помощь в Telegram
• Кризисный чат: beztrevoq.ru

Ты не одинок, помощь доступна 24/7. Пожалуйста, обратись к специалисту прямо сейчас! 🤗
"""
    
    def get_fallback_response(self, message: str) -> str:
        """Запасной ответ если нейросеть недоступна"""
        fallback_responses = [
            "Понимаю твои переживания. Хочешь обсудить что-то конкретное?",
            "Спасибо, что делишься. Как я могу поддержать тебя сейчас?",
            "Слышу тебя. Давай попробуем разобраться в твоих чувствах.",
            "Это звучит непросто. Хочешь попробовать технику для снижения тревоги?"
        ]
        import random
        return random.choice(fallback_responses)
