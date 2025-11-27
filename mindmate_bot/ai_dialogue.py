import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Здесь мы будем хранить историю диалога для каждого пользователя (в продакшене нужно сохранять в БД)
user_sessions = {}

def get_ai_response(user_id: int, user_message: str) -> str:
    """Генерирует ответ с помощью GPT, используя контекст диалога."""

    # Инициализируем или получаем историю диалога для пользователя
    if user_id not in user_sessions:
        # Системный промут задает роль боту
        user_sessions[user_id] = [
            {"role": "system", "content": "Ты - добрый и эмпатичный помощник по ментальному здоровью MindMate. Твоя задача - поддерживать пользователя, задавать наводящие вопросы, помогать бросить вызов негативным мыслям. Будь краток, не пиши длинных абзацев. В критических ситуациях (суицидальные мысли) настоятельно рекомендовал обратиться на горячую линию доверия 8-800-2000-122."}
        ]

    # Добавляем сообщение пользователя в историю
    user_sessions[user_id].append({"role": "user", "content": user_message})

    # Ограничиваем длину истории, чтобы не превысить лимит токенов
    if len(user_sessions[user_id]) > 10:
        user_sessions[user_id] = [user_sessions[user_id][0]] + user_sessions[user_id][-9:]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=user_sessions[user_id],
            temperature=0.7,
            max_tokens=300
        )
        ai_reply = response.choices[0].message.content

        # Добавляем ответ ассистента в историю
        user_sessions[user_id].append({"role": "assistant", "content": ai_reply})

        return ai_reply

    except Exception as e:
        print(f"Error with OpenAI: {e}")
        return "Извините, я сейчас не могу обработать ваш запрос. Попробуйте позже."
