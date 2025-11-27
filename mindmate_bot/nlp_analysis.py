from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

# Загружаем модель для анализа тональности/эмоций (пример для русского языка)
# Модель 'cointegrated/rubert-tiny2-cedr-emotion-detection' определяет эмоции.
emotion_classifier = pipeline(
    "text-classification",
    model="cointegrated/rubert-tiny2-cedr-emotion-detection",
    tokenizer="cointegrated/rubert-tiny2-cedr-emotion-detection",
    return_all_scores=True
)

# Для извлечения тем (ключевых слов) можно использовать простой подход с сопоставлением.
# В будущем можно заменить на модель для NER (распознавание сущностей) или Topic Modeling.
TOPIC_KEYWORDS = {
    'работа': ['работа', 'начальник', 'коллеги', 'проект', 'дедлайн', 'офис', 'зарплата'],
    'семья': ['семья', 'муж', 'жена', 'дети', 'родители', 'мама', 'папа'],
    'друзья': ['друзья', 'друг', 'подруга', 'встреча', 'общение'],
    'здоровье': ['здоровье', 'боль', 'врач', 'усталость', 'болезнь', 'самочувствие'],
    'деньги': ['деньги', 'финансы', 'кредит', 'покупка', 'траты', 'бюджет'],
    'транспорт': ['транспорт', 'пробка', 'машина', 'метро', 'автобус', 'дорога']
}

def analyze_text_sentiment(text: str) -> dict:
    """Анализирует текст и возвращает эмоцию, тональность и темы."""
    result = {
        'sentiment': 0.0, # Упрощенный показатель
        'emotion': 'neutral',
        'topics': []
    }

    # 1. Анализ эмоций
    try:
        emotion_results = emotion_classifier(text)[0]
        # Находим эмоцию с наибольшим скором
        top_emotion = max(emotion_results, key=lambda x: x['score'])
        result['emotion'] = top_emotion['label']
        # Преобразуем эмоцию в числовой скор тональности (очень упрощенно)
        if top_emotion['label'] in ['joy', 'love']:
            result['sentiment'] = 0.9
        elif top_emotion['label'] in ['sadness', 'fear', 'anger']:
            result['sentiment'] = -0.7
        else: # surprise, neutral
            result['sentiment'] = 0.0
    except Exception as e:
        print(f"Error in emotion analysis: {e}")

    # 2. Выявление тем
    text_lower = text.lower()
    detected_topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            detected_topics.append(topic)
    result['topics'] = detected_topics

    return result
