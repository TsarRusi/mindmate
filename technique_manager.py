"""
Менеджер для работы с техниками релаксации
"""
import random
from datetime import datetime
from typing import Dict, List, Optional

class TechniqueManager:
    def __init__(self):
        self.user_progress = {}  # user_id: {favorites: [], completed: [], ratings: {}}
    
    def get_personalized_technique(self, user_id: int, mood_score: int, tags: List[str] = None):
        """Получить персонализированную технику"""
        from techniques_db import RELAXATION_TECHNIQUES
        
        if mood_score <= 3:
            # Критически низкое настроение - простые техники
            return RELAXATION_TECHNIQUES["быстрые"][1]  # Техника 5-4-3-2-1
        elif mood_score <= 5:
            # Низкое настроение - быстрые техники
            return random.choice(RELAXATION_TECHNIQUES["быстрые"])
        elif mood_score <= 7:
            # Среднее настроение - медитации
            return random.choice(RELAXATION_TECHNIQUES["медитации"])
        else:
            # Хорошее настроение - техники для сна или поддержания
            return random.choice(RELAXATION_TECHNIQUES["для_сна"])
    
    def record_session(self, user_id: int, tech_id: int, duration: int, mood_before: int, mood_after: int):
        """Записать сессию выполнения техники"""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                "favorites": [],
                "completed": [],
                "ratings": {},
                "sessions": []
            }
        
        session = {
            "tech_id": tech_id,
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "mood_before": mood_before,
            "mood_after": mood_after,
            "effectiveness": mood_after - mood_before
        }
        
        self.user_progress[user_id]["sessions"].append(session)
        
        # Добавляем в выполненные, если еще нет
        if tech_id not in self.user_progress[user_id]["completed"]:
            self.user_progress[user_id]["completed"].append(tech_id)
    
    def add_to_favorites(self, user_id: int, tech_id: int):
        """Добавить технику в избранное"""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                "favorites": [],
                "completed": [],
                "ratings": {},
                "sessions": []
            }
        
        if tech_id not in self.user_progress[user_id]["favorites"]:
            self.user_progress[user_id]["favorites"].append(tech_id)
    
    def rate_technique(self, user_id: int, tech_id: int, rating: int):
        """Оценить технику"""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                "favorites": [],
                "completed": [],
                "ratings": {},
                "sessions": []
            }
        
        self.user_progress[user_id]["ratings"][tech_id] = rating
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получить статистику пользователя"""
        if user_id not in self.user_progress:
            return {
                "total_sessions": 0,
                "favorite_techniques": 0,
                "avg_effectiveness": 0,
                "most_effective": None
            }
        
        user_data = self.user_progress[user_id]
        sessions = user_data.get("sessions", [])
        
        if not sessions:
            return {
                "total_sessions": 0,
                "favorite_techniques": len(user_data.get("favorites", [])),
                "avg_effectiveness": 0,
                "most_effective": None
            }
        
        # Находим среднюю эффективность
        effectiveness_sum = sum(s["effectiveness"] for s in sessions)
        avg_effectiveness = effectiveness_sum / len(sessions)
        
        # Находим самую эффективную технику
        tech_effectiveness = {}
        for session in sessions:
            tech_id = session["tech_id"]
            if tech_id not in tech_effectiveness:
                tech_effectiveness[tech_id] = []
            tech_effectiveness[tech_id].append(session["effectiveness"])
        
        most_effective = None
        max_avg = -10
        for tech_id, effects in tech_effectiveness.items():
            avg = sum(effects) / len(effects)
            if avg > max_avg:
                max_avg = avg
                most_effective = tech_id
        
        return {
            "total_sessions": len(sessions),
            "favorite_techniques": len(user_data.get("favorites", [])),
            "avg_effectiveness": avg_effectiveness,
            "most_effective": most_effective
        }
