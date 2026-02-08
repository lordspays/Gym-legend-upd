import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from bot.core.config import settings

# ======================
# ТАБЛИЦЫ ДЛЯ БАЗЫ ДАННЫХ
# ======================

# Основная таблица игроков (добавлена колонка fitness_halls)
SQL_PLAYERS_TABLE = """
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 1,
        power INTEGER DEFAULT 0,
        last_dumbbell_use TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_new INTEGER DEFAULT 1,
        dumbbell_level INTEGER DEFAULT 1,
        dumbbell_name TEXT DEFAULT 'Гантеля 1кг',
        total_lifts INTEGER DEFAULT 0,
        total_earned INTEGER DEFAULT 0,
        custom_income INTEGER DEFAULT NULL,
        admin_level INTEGER DEFAULT 0,
        admin_nickname TEXT DEFAULT NULL,
        admin_since TIMESTAMP DEFAULT NULL,
        admin_id TEXT DEFAULT NULL,
        bans_given INTEGER DEFAULT 0,
        permabans_given INTEGER DEFAULT 0,
        deletions_given INTEGER DEFAULT 0,
        dumbbell_sets_given INTEGER DEFAULT 0,
        nickname_changes_given INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        ban_reason TEXT,
        ban_until TIMESTAMP DEFAULT NULL,
        clan_id INTEGER DEFAULT NULL,
        used_promo_codes TEXT DEFAULT '[]',
        clan_role TEXT DEFAULT NULL,
        contributions INTEGER DEFAULT 0,
        fitness_halls INTEGER DEFAULT 0  -- НОВАЯ КОЛОНКА для фитнесс-залов
    )
"""

# Остальные таблицы остаются без изменений...
# (Все остальные SQL_CREATE_TABLE операторы остаются такими же как во втором файле)

# ======================
# ОСНОВНЫЕ ФУНКЦИИ БАЗЫ ДАННЫХ
# ======================

async def create_tables() -> None:
    """Create all database tables if they don't exist"""
    # Creating database file if it doesn't exist
    with open(settings.database_path, "a"):
        pass

    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(SQL_PLAYERS_TABLE)
        await db.execute(SQL_TRANSACTIONS_TABLE)
        await db.execute(SQL_DUMBBELL_USES_TABLE)
        await db.execute(SQL_ADMIN_ACTIONS_TABLE)
        await db.execute(SQL_PROMO_CODES_TABLE)
        await db.execute(SQL_PROMO_USES_TABLE)
        await db.execute(SQL_CLANS_TABLE)
        await db.execute(SQL_CLAN_MEMBERS_TABLE)
        await db.execute(SQL_CLAN_TREASURY_LOG_TABLE)
        await db.execute(SQL_CLAN_INVITES_TABLE)
        await db.execute(SQL_CLAN_LOGS_TABLE)
        await db.execute(SQL_ADMIN_LOGS_TABLE)
        await db.execute(SQL_ADMIN_REQUESTS_TABLE)
        await db.execute(SQL_ADMIN_USAGE_STATS_TABLE)
        await db.execute(SQL_ADMIN_BROADCAST_STATS_TABLE)
        await db.execute(SQL_MODERATOR_PROMO_STATS_TABLE)
        await db.execute(SQL_PLAYER_INSPECTORS_TABLE)
        await db.execute(SQL_PLAYER_PROTECTIONS_TABLE)
        await db.execute(SQL_ACTIVE_PROTECTIONS_TABLE)
        await db.execute(SQL_INSPECTION_STATS_TABLE)
        await db.execute(SQL_PROTECTION_STATS_TABLE)
        await db.execute(SQL_INSPECTION_TIME_MODE_TABLE)
        await db.execute(SQL_INFO_ACCESS_TABLE)
        
        # Создание индексов
        await db.execute("CREATE INDEX IF NOT EXISTS idx_info_access_expires ON info_access(expires_at)")
        
        await db.commit()


async def get_player(user_id: int) -> Optional[Dict[str, Any]]:
    """Get player data by user_id"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT user_id, username, balance, power, last_dumbbell_use, is_new,
                   dumbbell_level, dumbbell_name, total_lifts, total_earned,
                   custom_income, admin_level, admin_nickname, admin_since,
                   admin_id, bans_given, permabans_given, deletions_given,
                   dumbbell_sets_given, nickname_changes_given,
                   is_banned, ban_reason, ban_until, created_at,
                   clan_id, used_promo_codes, clan_role, contributions, fitness_halls
            FROM players WHERE user_id = ?
        """,
            (user_id,),
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return

        used_promo_codes = row[25] if row[25] else "[]"

        return {
            "user_id": row[0],
            "username": row[1],
            "balance": row[2],
            "power": row[3],
            "last_dumbbell_use": row[4],
            "is_new": row[5],
            "dumbbell_level": row[6],
            "dumbbell_name": row[7],
            "total_lifts": row[8],
            "total_earned": row[9],
            "custom_income": row[10],
            "admin_level": row[11],
            "admin_nickname": row[12],
            "admin_since": row[13],
            "admin_id": row[14],
            "bans_given": row[15],
            "permabans_given": row[16],
            "deletions_given": row[17],
            "dumbbell_sets_given": row[18],
            "nickname_changes_given": row[19],
            "is_banned": row[20],
            "ban_reason": row[21],
            "ban_until": row[22],
            "created_at": row[23],
            "clan_id": row[24],
            "used_promo_codes": json.loads(used_promo_codes),
            "clan_role": row[26],
            "contributions": row[27] or 0,
            "fitness_halls": row[28] or 0,  # Добавлено поле fitness_halls
        }

# ======================
# ФУНКЦИИ ДЛЯ ФИТНЕСС-ЗАЛОВ (интегрированы из первого кода)
# ======================

async def get_player_fitness_halls(user_id: int) -> int:
    """Получить количество фитнесс-залов игрока"""
    player = await get_player(user_id)
    return player.get("fitness_halls", 0) if player else 0


async def update_fitness_halls(user_id: int, amount: int, reason: str = None) -> bool:
    """Обновить количество фитнесс-залов игрока"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "UPDATE players SET fitness_halls = fitness_halls + ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()
            return True
    except:
        return False


async def update_clan_daily_income(clan_id: int, income: int) -> bool:
    """Добавить ежедневный доход клану от фитнесс-залов"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "UPDATE clans SET treasury = treasury + ?, updated_at = ? WHERE id = ?",
                (income, datetime.now().isoformat(), clan_id)
            )
            
            # Логируем операцию
            await log_collection_with_user(
                clan_id,
                0,  # system
                "daily_income",
                income,
                f"Ежедневный доход от фитнесс-залов участников"
            )
            
            await db.commit()
            return True
    except:
        return False


# ======================
# СИСТЕМА ЕЖЕДНЕВНОГО ДОХОДА КЛАНА ОТ ФИТНЕСС-ЗАЛОВ
# ======================

async def get_clan_fitness_halls_income(clan_id: int) -> int:
    """Рассчитать ежедневный доход клана от фитнесс-залов участников"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT SUM(p.fitness_halls) as total_halls
            FROM players p
            JOIN clan_members cm ON p.user_id = cm.user_id
            WHERE cm.clan_id = ? AND p.is_banned = 0
            """,
            (clan_id,)
        ) as cur:
            row = await cur.fetchone()
    
    total_halls = row[0] or 0
    # Предположим, что каждый фитнесс-зал приносит 100 монет в день
    daily_income_per_hall = 100
    return total_halls * daily_income_per_hall


# ======================
# ОБНОВЛЕННАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ИГРОКОВ
# ======================

async def get_all_players(limit: int = 100) -> List[Dict[str, Any]]:
    """Получить всех игроков (с фитнесс-залами)"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT user_id, username, balance, power, 
                   dumbbell_level, dumbbell_name, total_lifts, total_earned,
                   admin_level, is_banned, clan_id, fitness_halls,
                   created_at
            FROM players 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (limit,)
        ) as cur:
            rows = await cur.fetchall()
    
    players = []
    for row in rows:
        players.append({
            "user_id": row[0],
            "username": row[1],
            "balance": row[2],
            "power": row[3],
            "dumbbell_level": row[4],
            "dumbbell_name": row[5],
            "total_lifts": row[6],
            "total_earned": row[7],
            "admin_level": row[8],
            "is_banned": row[9],
            "clan_id": row[10],
            "fitness_halls": row[11] or 0,  # Добавлено поле fitness_halls
            "created_at": row[12],
        })
    return players


# ======================
# ОБНОВЛЕННАЯ ФУНКЦИЯ ДЛЯ СОЗДАНИЯ ИГРОКА
# ======================

async def create_player(user_id: int, username: str) -> Optional[Dict[str, Any]]:
    """Create a new player"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO players 
               (user_id, username, dumbbell_level, dumbbell_name, fitness_halls) 
               VALUES (?, ?, 1, 'Гантеля 1кг', 0)""",
            (user_id, username),
        )
        await db.commit()
    return await get_player(user_id)


# ======================
# ОБНОВЛЕННАЯ ФУНКЦИЯ ДЛЯ СБРОСА ВСЕХ ДАННЫХ
# ======================

async def reset_all() -> None:
    """Сбросить все данные (только для тестов)"""
    async with aiosqlite.connect(settings.database_path) as db:
        # Удаляем обычных игроков
        await db.execute("DELETE FROM players WHERE admin_level = 0")

        # Удаляем кланы
        await db.execute("DELETE FROM clans")

        # Очищаем связанные таблицы
        await db.execute("DELETE FROM transactions")
        await db.execute("DELETE FROM dumbbell_uses")
        await db.execute("DELETE FROM promo_uses")
        await db.execute("DELETE FROM clan_members")
        await db.execute("DELETE FROM clan_treasury_log")
        await db.execute("DELETE FROM clan_invites")
        await db.execute("DELETE FROM clan_logs")
        await db.execute("DELETE FROM admin_logs")
        await db.execute("DELETE FROM admin_requests")
        await db.execute("DELETE FROM admin_usage_stats")
        await db.execute("DELETE FROM admin_broadcast_stats")
        await db.execute("DELETE FROM moderator_promo_stats")
        await db.execute("DELETE FROM player_inspectors")
        await db.execute("DELETE FROM player_protections")
        await db.execute("DELETE FROM active_protections")
        await db.execute("DELETE FROM inspection_stats")
        await db.execute("DELETE FROM protection_stats")
        await db.execute("DELETE FROM inspection_time_mode")
        await db.execute("DELETE FROM info_access")

        await db.commit()

# ======================
# НОВАЯ ФУНКЦИЯ ДЛЯ ТОПА ПО ФИТНЕСС-ЗАЛАМ
# ======================

async def get_top_fitness_halls(limit: int = 10) -> List[Tuple]:
    """Get top players by fitness halls"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT user_id, username, fitness_halls, balance FROM players WHERE is_banned = 0 ORDER BY fitness_halls DESC LIMIT ?",
            (limit,),
        ) as cur:
            return await cur.fetchall()

# ======================
# ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ ФИТНЕСС-ЗАЛОВ АДМИНИСТРАТОРОМ
# ======================

async def set_fitness_halls(user_id: int, new_amount: int, admin_id: int) -> bool:
    """Установить количество фитнесс-залов игрока"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            # Получаем текущее количество залов
            async with db.execute(
                "SELECT fitness_halls FROM players WHERE user_id = ?",
                (user_id,)
            ) as cur:
                row = await cur.fetchone()
                old_amount = row[0] if row else 0
            
            await db.execute(
                "UPDATE players SET fitness_halls = ? WHERE user_id = ?",
                (new_amount, user_id)
            )
            
            # Логируем действие администратора
            await db.execute(
                """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
                   VALUES (?, ?, ?, ?)""",
                (
                    admin_id,
                    "set_fitness_halls",
                    user_id,
                    f"Изменение фитнесс-залов: {old_amount} -> {new_amount}",
                ),
            )
            
            await db.commit()
            return True
    except Exception as e:
        print(f"Ошибка при обновлении фитнесс-залов: {e}")
        return False

# Все остальные функции из второго файла остаются без изменений...
# (Копируем все остальные функции из второго файла, они остаются без изменений)
# ... [все остальные функции остаются такими же, как во втором файле]
