# bot/db/inspection.py
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from motor.motor_asyncio import AsyncIOMotorClient
from bot.core.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URL)
db = client[settings.MONGODB_DB_NAME]

# Коллекции
players_collection = db["players"]
inspectors_collection = db["inspectors"]
protections_collection = db["protections"]
inspection_stats_collection = db["inspection_stats"]
protection_stats_collection = db["protection_stats"]
settings_collection = db["settings"]

# ======================
# БАЗОВЫЕ ФУНКЦИИ ДЛЯ ИГРОКА
# ======================

async def get_player(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить данные игрока"""
    player = await players_collection.find_one({"user_id": user_id})
    if not player:
        # Создаем нового игрока если не найден
        player = {
            "user_id": user_id,
            "username": f"id{user_id}",
            "balance": 0,
            "fitness_halls": 0,
            "created_at": datetime.now()
        }
        await players_collection.insert_one(player)
    return player

async def update_player_balance(
    user_id: int, 
    amount: int, 
    transaction_type: str,
    description: str,
    related_id: Optional[int] = None,
    other_id: Optional[int] = None
) -> bool:
    """Изменить баланс игрока"""
    result = await players_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": amount}}
    )
    return result.modified_count > 0

# ======================
# ФУНКЦИИ ДЛЯ ФИТНЕСС-ЗАЛОВ
# ======================

async def get_player_fitness_halls(user_id: int) -> int:
    """Получить количество фитнесс-залов у игрока"""
    player = await players_collection.find_one({"user_id": user_id})
    return player.get("fitness_halls", 0) if player else 0

async def update_fitness_halls(user_id: int, delta_halls: int, delta_income: int) -> bool:
    """Изменить количество фитнесс-залов"""
    result = await players_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"fitness_halls": delta_halls}}
    )
    return result.modified_count > 0

# ======================
# ФУНКЦИИ ДЛЯ ИНСПЕКТОРОВ
# ======================

async def get_player_inspectors(user_id: int) -> List[int]:
    """Получить список купленных уровней инспекторов"""
    inspector_data = await inspectors_collection.find_one({"user_id": user_id})
    return inspector_data.get("levels", []) if inspector_data else []

async def buy_inspector_level(user_id: int, level: int) -> bool:
    """Купить уровень инспектора"""
    result = await inspectors_collection.update_one(
        {"user_id": user_id},
        {"$addToSet": {"levels": level}},
        upsert=True
    )
    return result.acknowledged

# ======================
# ФУНКЦИИ ДЛЯ ЗАЩИТЫ
# ======================

async def get_player_protections(user_id: int) -> List[int]:
    """Получить список купленных уровней защиты"""
    protection_data = await protections_collection.find_one({"user_id": user_id})
    return protection_data.get("levels", []) if protection_data else []

async def buy_protection_level(user_id: int, level: int) -> bool:
    """Купить уровень защиты"""
    result = await protections_collection.update_one(
        {"user_id": user_id},
        {"$addToSet": {"levels": level}},
        upsert=True
    )
    return result.acknowledged

async def get_active_protection(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить активную защиту игрока"""
    protection = await protections_collection.find_one({
        "user_id": user_id,
        "is_active": True,
        "expires_at": {"$gt": datetime.now()}
    })
    return protection

async def activate_protection(user_id: int, level: int, duration_minutes: int) -> bool:
    """Активировать защиту"""
    expires_at = datetime.now() + timedelta(minutes=duration_minutes)
    
    # Деактивируем старые защиты
    await protections_collection.update_many(
        {"user_id": user_id, "is_active": True},
        {"$set": {"is_active": False}}
    )
    
    # Активируем новую
    result = await protections_collection.update_one(
        {"user_id": user_id, "level": level},
        {
            "$set": {
                "is_active": True,
                "activated_at": datetime.now(),
                "expires_at": expires_at
            }
        },
        upsert=True
    )
    return result.acknowledged

# ======================
# СТАТИСТИКА ПРОВЕРОК
# ======================

async def get_inspection_stats(user_id: int) -> Dict[str, Any]:
    """Получить статистику проверок игрока"""
    stats = await inspection_stats_collection.find_one({"user_id": user_id})
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if not stats:
        return {
            "total_inspections": 0,
            "successful_inspections": 0,
            "failed_inspections": 0,
            "inspections_today": 0,
            "last_inspection": None,
            "halls_closed": 0
        }
    
    # Сбрасываем счетчик за сегодня если это новый день
    last_reset = stats.get("last_reset")
    if not last_reset or last_reset < today:
        stats["inspections_today"] = 0
        stats["last_reset"] = datetime.now()
        await inspection_stats_collection.update_one(
            {"user_id": user_id},
            {"$set": {"inspections_today": 0, "last_reset": datetime.now()}}
        )
    
    return stats

async def update_inspection_stats(
    user_id: int, 
    successful: Optional[bool] = None,
    halls_closed: int = 0
) -> bool:
    """Обновить статистику проверок"""
    update_data = {
        "$inc": {
            "total_inspections": 1,
            "inspections_today": 1,
            "halls_closed": halls_closed
        },
        "$set": {"last_inspection": datetime.now()}
    }
    
    if successful is not None:
        if successful:
            update_data["$inc"]["successful_inspections"] = 1
        else:
            update_data["$inc"]["failed_inspections"] = 1
    
    result = await inspection_stats_collection.update_one(
        {"user_id": user_id},
        update_data,
        upsert=True
    )
    return result.acknowledged

# ======================
# СТАТИСТИКА ЗАЩИТЫ
# ======================

async def get_protection_stats(user_id: int) -> Dict[str, Any]:
    """Получить статистику защиты игрока"""
    stats = await protection_stats_collection.find_one({"user_id": user_id})
    
    if not stats:
        return {
            "total_spent_on_protection": 0,
            "total_blocked": 0
        }
    
    return stats

async def update_protection_stats(
    user_id: int,
    spent: int = 0,
    blocked: bool = False
) -> bool:
    """Обновить статистику защиты"""
    update_data = {}
    
    if spent > 0:
        update_data["$inc"] = {"total_spent_on_protection": spent}
    
    if blocked:
        if "$inc" not in update_data:
            update_data["$inc"] = {}
        update_data["$inc"]["total_blocked"] = 1
    
    if update_data:
        result = await protection_stats_collection.update_one(
            {"user_id": user_id},
            update_data,
            upsert=True
        )
        return result.acknowledged
    
    return True

# ======================
# ФУНКЦИИ ДЛЯ РЕЖИМОВ ПРОВЕРОК (ТОЛЬКО ДЛЯ АДМИНОВ)
# ======================

async def get_inspection_time_mode() -> Dict[str, Any]:
    """
    Получить текущий режим проверок
    Внутренняя функция, используется системой
    """
    mode = await settings_collection.find_one({"key": "inspection_mode"})
    
    if not mode:
        return {"is_active": False, "ends_at": None}
    
    # Проверяем не истек ли режим
    if mode.get("ends_at"):
        try:
            ends_at = datetime.fromisoformat(mode["ends_at"])
            if ends_at < datetime.now():
                await settings_collection.update_one(
                    {"key": "inspection_mode"},
                    {"$set": {"is_active": False}}
                )
                return {"is_active": False, "ends_at": None}
        except (ValueError, TypeError):
            pass
    
    return mode

async def set_inspection_time_mode(is_active: bool, duration_hours: int = 0) -> bool:
    """
    Установить режим проверок
    ТОЛЬКО ДЛЯ АДМИНИСТРАТОРОВ!
    
    Args:
        is_active: True - включить режим, False - выключить
        duration_hours: количество часов действия (если is_active=True)
    """
    ends_at = None
    if is_active and duration_hours > 0:
        ends_at = (datetime.now() + timedelta(hours=duration_hours)).isoformat()
    
    result = await settings_collection.update_one(
        {"key": "inspection_mode"},
        {
            "$set": {
                "is_active": is_active,
                "ends_at": ends_at,
                "updated_at": datetime.now()
            }
        },
        upsert=True
    )
    return result.acknowledged

# ======================
# ОЧИСТКА ПРОСРОЧЕННЫХ ЗАЩИТ
# ======================

async def cleanup_expired_protections() -> int:
    """Очистить просроченные защиты"""
    result = await protections_collection.update_many(
        {
            "is_active": True,
            "expires_at": {"$lte": datetime.now()}
        },
        {"$set": {"is_active": False}}
    )
    return result.modified_count

# ======================
# СБРОС ДНЕВНЫХ ПРОВЕРОК
# ======================

async def reset_all_daily_inspections() -> int:
    """Сбросить счетчики дневных проверок для всех игроков"""
    result = await inspection_stats_collection.update_many(
        {},
        {"$set": {"inspections_today": 0, "last_reset": datetime.now()}}
    )
    return result.modified_count
