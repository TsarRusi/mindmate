from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    created_at = Column(DateTime)

class MoodEntry(Base):
    __tablename__ = 'mood_entries'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    mood_score = Column(Integer) # Оценка от 1 до 10
    mood_text = Column(Text, nullable=True) # Текстовая запись пользователя
    sentiment_score = Column(Float, nullable=True) # Результат анализа NLP (например, от -1 до 1)
    detected_emotion = Column(String, nullable=True) # Обнаруженная эмоция (гнев, грусть и т.д.)
    main_topics = Column(Text, nullable=True) # Ключевые темы (в виде JSON строки)
    created_at = Column(DateTime)

# Создаем таблицы в БД
Base.metadata.create_all(bind=engine)
