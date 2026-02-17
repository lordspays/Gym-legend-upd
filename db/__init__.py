# bot/db/__init__.py
from .inspection import (
    # Базовые функции
    get_player,
    update_player_balance,
    get_all_players,
    
    # Фитнесс-залы
    get_player_fitness_halls,
    update_fitness_halls,
    
    # Инспекторы
    get_player_inspectors,
    buy_inspector_level,
    
    # Защита
    get_player_protections,
    buy_protection_level,
    get_active_protection,
    activate_protection,
    
    # Статистика проверок
    get_inspection_stats,
    update_inspection_stats,
    
    # Статистика защиты
    get_protection_stats,
    update_protection_stats,
    
    # Режимы проверок
    get_inspection_time_mode,
    set_inspection_time_mode,
    extend_inspection_mode,
    
    # Служебные
    cleanup_expired_protections,
    reset_all_daily_inspections
)

__all__ = [
    "get_player",
    "update_player_balance",
    "get_all_players",
    "get_player_fitness_halls",
    "update_fitness_halls",
    "get_player_inspectors",
    "buy_inspector_level",
    "get_player_protections",
    "buy_protection_level",
    "get_active_protection",
    "activate_protection",
    "get_inspection_stats",
    "update_inspection_stats",
    "get_protection_stats",
    "update_protection_stats",
    "get_inspection_time_mode",
    "set_inspection_time_mode",
    "extend_inspection_mode",
    "cleanup_expired_protections",
    "reset_all_daily_inspections"
]
