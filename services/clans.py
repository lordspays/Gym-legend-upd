"""
Сервисы для работы с кланами
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from bot.core.config import settings
from bot.db import (
    get_player,
    get_player_clan,
    get_clan_bonuses as get_clan_bonuses_db,
    get_clan_members,
    update_player_balance,
    log_collection_with_user,
    db,
)
from bot.utils import format_number


def get_clan_bonuses(level: int) -> dict:
    """Получить бонусы клана по уровню"""
    if level < 1:
        level = 1
    if level > 100:
        level = 100
    
    return {
        "lift_bonus_coins": level,  # +1 монета за поднятие за каждый уровень
        "fitness_hall_bonus": level,  # +1 монета с каждого фитнесс-зала за каждый уровень
        "player_lift_bonus": level,  # Бонус игрока: +1 монета к доходу за подход
        "member_limit": 10 + (level * 2),  # Лимит участников увеличивается с уровнем
    }


async def process_dumbbell_lift_with_clan(user_id: int) -> dict:
    """
    Обрабатывает поднятие гантели с учетом бонусов клана
    
    Args:
        user_id: ID игрока
        
    Returns:
        dict: Словарь с информацией о начисленных монетах
    """
    try:
        # Получаем игрока и его клан
        player = await get_player(user_id)
        if not player:
            return {
                "player_income": 1,
                "clan_income": 0,
                "clan_bonus_coins": 0,
                "power_gained": 1,
                "error": "Игрок не найден"
            }
        
        clan = await get_player_clan(user_id)
        
        # Базовый доход от гантели
        base_income = 1  # Значение по умолчанию
        
        if player.get("custom_income") is not None:
            base_income = player["custom_income"]
        else:
            dumbbell_level = player.get("dumbbell_level", 1)
            if dumbbell_level in settings.DUMBBELL_LEVELS:
                dumbbell_info = settings.DUMBBELL_LEVELS[dumbbell_level]
                base_income = dumbbell_info.get("income_per_use", 1)
        
        # Бонус клана
        clan_bonus = 0
        clan_income = 0
        
        if clan:
            bonuses = get_clan_bonuses(clan.get("level", 1))
            clan_bonus = bonuses.get("player_lift_bonus", 0)  # Бонус игроку
            clan_income = bonuses.get("lift_bonus_coins", 0)  # Бонус клану
        
        # Игрок получает базовый доход + бонус
        player_income = base_income + clan_bonus
        
        # Сила за поднятие
        power_gained = 1
        if not player.get("custom_income"):
            dumbbell_level = player.get("dumbbell_level", 1)
            if dumbbell_level in settings.DUMBBELL_LEVELS:
                power_gained = settings.DUMBBELL_LEVELS[dumbbell_level].get("power_per_use", 1)
        
        # Обновляем баланс игрока
        await update_player_balance(
            user_id,
            player_income,
            "dumbbell_lift",
            f"Поднятие гантели с бонусом клана +{clan_bonus}",
            None,
        )
        
        # Начисляем доход клану
        if clan and clan_income > 0:
            clan_id = clan["id"]
            
            # Добавляем деньги в казну клана
            await db.clans.update_one(
                {"_id": clan_id},
                {"$inc": {"treasury": clan_income}}
            )
            
            # Логируем операцию
            await log_collection_with_user(
                clan_id,
                user_id,
                "lift_income",
                clan_income,
                f"Доход от поднятия гантели игроком [id{user_id}] (уровень клана {clan.get('level', 1)})",
            )
            
            # Обновляем общий доход клана
            await db.clans.update_one(
                {"_id": clan_id},
                {"$inc": {"total_income": clan_income}}
            )
        
        # Обновляем статистику игрока
        await db.players.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "total_lifts": 1,
                    "power": power_gained,
                    "total_earned": player_income
                },
                "$set": {"last_dumbbell_use": datetime.now().isoformat()}
            }
        )
        
        return {
            "player_income": player_income,
            "clan_income": clan_income,
            "clan_bonus_coins": clan_bonus,
            "power_gained": power_gained,
            "base_income": base_income,
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Ошибка в process_dumbbell_lift_with_clan: {e}")
        return {
            "player_income": 1,
            "clan_income": 0,
            "clan_bonus_coins": 0,
            "power_gained": 1,
            "error": str(e),
            "success": False
        }


async def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    try:
        player = await get_player(user_id)
        if not player:
            return False
        return player.get("admin_level", 0) > 0
    except Exception:
        return False
