import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from bot.core.config import settings

# ======================
# ТАБЛИЦЫ ДЛЯ БАЗЫ ДАННЫХ
# ======================

# Основная таблица игроков (убраны бизнес-системы)
SQL_PLAYERS_TABLE = """
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 1,
        power INTEGER DEFAULT 0,
        magnesia INTEGER DEFAULT 0,
        last_dumbbell_use TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_new INTEGER DEFAULT 1,
        dumbbell_level INTEGER DEFAULT 1,
        dumbbell_name TEXT DEFAULT 'Гантеля 1кг',
        total_lifts INTEGER DEFAULT 0,
        total_earned INTEGER DEFAULT 0,
        total_spent INTEGER DEFAULT 0,
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
        fitness_halls INTEGER DEFAULT 0,
        coach_level INTEGER DEFAULT 0,
        last_training TIMESTAMP DEFAULT NULL,
        has_info_access INTEGER DEFAULT 0,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

# Таблица транзакций
SQL_TRANSACTIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount INTEGER,
        description TEXT,
        admin_id INTEGER DEFAULT NULL,
        target_user_id INTEGER DEFAULT NULL,
        clan_id INTEGER DEFAULT NULL,
        other_user_id INTEGER DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица ежедневных покупок залов
SQL_DAILY_HALL_PURCHASES_TABLE = """
    CREATE TABLE IF NOT EXISTS daily_hall_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        purchase_date DATE NOT NULL,
        amount INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES players(user_id)
    )
"""

# Таблица статистики ежедневного дохода
SQL_DAILY_INCOME_STATS_TABLE = """
    CREATE TABLE IF NOT EXISTS daily_income_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        income_date DATE NOT NULL,
        amount_received INTEGER NOT NULL,
        last_received_date TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES players(user_id),
        UNIQUE(user_id, income_date)
    )
"""

# Таблица использований гантелей
SQL_DUMBBELL_USES_TABLE = """
    CREATE TABLE IF NOT EXISTS dumbbell_uses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        dumbbell_level INTEGER,
        income INTEGER,
        power_gained INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица админ действий
SQL_ADMIN_ACTIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS admin_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action_type TEXT,
        target_user_id INTEGER,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

# Таблица промокодов
SQL_PROMO_CODES_TABLE = """
    CREATE TABLE IF NOT EXISTS promo_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        uses_total INTEGER DEFAULT 1,
        uses_left INTEGER DEFAULT 1,
        reward_type TEXT NOT NULL,
        reward_amount INTEGER NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP DEFAULT NULL,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (created_by) REFERENCES players (user_id)
    )
"""

# Таблица использований промокодов
SQL_PROMO_USES_TABLE = """
    CREATE TABLE IF NOT EXISTS promo_uses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        promo_code TEXT NOT NULL,
        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES players (user_id),
        FOREIGN KEY (promo_code) REFERENCES promo_codes (code)
    )
"""

# Таблица кланов (обновленная структура)
SQL_CLANS_TABLE = """
    CREATE TABLE IF NOT EXISTS clans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        level INTEGER DEFAULT 1,
        treasury INTEGER DEFAULT 0,
        member_count INTEGER DEFAULT 1,
        total_income_per_hour INTEGER DEFAULT 0,
        total_lifts INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        settings TEXT DEFAULT '{"requirements": {"min_level": 1}, "greeting": null}',
        banned_players TEXT DEFAULT '[]',
        description TEXT DEFAULT 'Нет описания',
        hall_income INTEGER DEFAULT 0,
        experience INTEGER DEFAULT 0,
        FOREIGN KEY (owner_id) REFERENCES players (user_id)
    )
"""

# Таблица участников кланов
SQL_CLAN_MEMBERS_TABLE = """
    CREATE TABLE IF NOT EXISTS clan_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan_id INTEGER NOT NULL,
        user_id INTEGER UNIQUE NOT NULL,
        role TEXT DEFAULT 'member',
        status TEXT DEFAULT 'active',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        contributions INTEGER DEFAULT 0,
        FOREIGN KEY (clan_id) REFERENCES clans (id),
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица лога казны клана
SQL_CLAN_TREASURY_LOG_TABLE = """
    CREATE TABLE IF NOT EXISTS clan_treasury_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan_id INTEGER NOT NULL,
        user_id INTEGER,
        username TEXT,
        action_type TEXT,
        amount INTEGER,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (clan_id) REFERENCES clans (id),
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица приглашений в кланы
SQL_CLAN_INVITES_TABLE = """
    CREATE TABLE IF NOT EXISTS clan_invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan_id INTEGER NOT NULL,
        inviter_id INTEGER NOT NULL,
        invitee_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY (clan_id) REFERENCES clans (id),
        FOREIGN KEY (inviter_id) REFERENCES players (user_id),
        FOREIGN KEY (invitee_id) REFERENCES players (user_id)
    )
"""

# Таблица логов действий в кланах
SQL_CLAN_LOGS_TABLE = """
    CREATE TABLE IF NOT EXISTS clan_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan_id INTEGER NOT NULL,
        user_id INTEGER,
        action_type TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (clan_id) REFERENCES clans (id),
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица логов администраторов
SQL_ADMIN_LOGS_TABLE = """
    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        admin_name TEXT NOT NULL,
        admin_level TEXT NOT NULL,
        action_type TEXT NOT NULL,
        details TEXT DEFAULT '',
        log_type TEXT DEFAULT 'other',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица заявок администраторов
SQL_ADMIN_REQUESTS_TABLE = """
    CREATE TABLE IF NOT EXISTS admin_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        admin_name TEXT NOT NULL,
        request_type TEXT NOT NULL,
        target_id INTEGER,
        reason TEXT DEFAULT '',
        additional_info TEXT DEFAULT '{}',
        status TEXT DEFAULT 'pending',
        approved_by INTEGER,
        approved_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES players (user_id)
    )
"""

# Таблица статистики использования команд администраторов
SQL_ADMIN_USAGE_STATS_TABLE = """
    CREATE TABLE IF NOT EXISTS admin_usage_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        stat_type TEXT NOT NULL,
        stat_value INTEGER DEFAULT 0,
        period_date DATE NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(admin_id, stat_type, period_date),
        FOREIGN KEY (admin_id) REFERENCES players (user_id)
    )
"""

# Таблица статистики рассылок
SQL_ADMIN_BROADCAST_STATS_TABLE = """
    CREATE TABLE IF NOT EXISTS admin_broadcast_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL UNIQUE,
        usage_count INTEGER DEFAULT 0,
        last_used TIMESTAMP,
        reset_time TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES players (user_id)
    )
"""

# Таблица статистики промокодов модераторов
SQL_MODERATOR_PROMO_STATS_TABLE = """
    CREATE TABLE IF NOT EXISTS moderator_promo_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL UNIQUE,
        coins_used INTEGER DEFAULT 0,
        magnesia_used INTEGER DEFAULT 0,
        power_used INTEGER DEFAULT 0,
        total_created INTEGER DEFAULT 0,
        last_created TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES players (user_id)
    )
"""

# Таблица для системы проверок: инспекторы
SQL_PLAYER_INSPECTORS_TABLE = """
    CREATE TABLE IF NOT EXISTS player_inspectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        level INTEGER NOT NULL,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, level),
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица для системы проверок: защиты
SQL_PLAYER_PROTECTIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS player_protections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        level INTEGER NOT NULL,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, level),
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица для системы проверок: активные защиты
SQL_ACTIVE_PROTECTIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS active_protections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        protection_level INTEGER NOT NULL,
        activated_at TIMESTAMP NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица для системы проверок: статистика проверок
SQL_INSPECTION_STATS_TABLE = """
    CREATE TABLE IF NOT EXISTS inspection_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        total_inspections INTEGER DEFAULT 0,
        successful_inspections INTEGER DEFAULT 0,
        failed_inspections INTEGER DEFAULT 0,
        halls_closed INTEGER DEFAULT 0,
        inspections_today INTEGER DEFAULT 0,
        last_inspection TIMESTAMP,
        last_reset_date DATE,
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица для системы проверок: проверки
SQL_INSPECTIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspector_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        successful INTEGER DEFAULT 0,
        halls_closed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (inspector_id) REFERENCES players(user_id),
        FOREIGN KEY (target_id) REFERENCES players(user_id)
    )
"""

# Таблица для системы проверок: статистика защиты
SQL_PROTECTION_STATS_TABLE = """
    CREATE TABLE IF NOT EXISTS protection_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        total_blocked INTEGER DEFAULT 0,
        total_spent_on_protection INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES players (user_id)
    )
"""

# Таблица для системы проверок: режим "Время проверок"
SQL_INSPECTION_TIME_MODE_TABLE = """
    CREATE TABLE IF NOT EXISTS inspection_time_mode (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        is_active INTEGER DEFAULT 0,
        started_at TIMESTAMP,
        ends_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

# Таблица для доступа к команде /инфа
SQL_INFO_ACCESS_TABLE = """
    CREATE TABLE IF NOT EXISTS info_access (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        admin_id INTEGER NOT NULL,
        granted_at TIMESTAMP NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES players(user_id),
        FOREIGN KEY (admin_id) REFERENCES players(user_id)
    )
"""

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
        await db.execute(SQL_DAILY_HALL_PURCHASES_TABLE)
        await db.execute(SQL_DAILY_INCOME_STATS_TABLE)
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
        await db.execute(SQL_INSPECTIONS_TABLE)
        await db.execute(SQL_PROTECTION_STATS_TABLE)
        await db.execute(SQL_INSPECTION_TIME_MODE_TABLE)
        await db.execute(SQL_INFO_ACCESS_TABLE)
        
        # Создание индексов
        await db.execute("CREATE INDEX IF NOT EXISTS idx_info_access_expires ON info_access(expires_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_players_balance ON players(balance)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_players_total_lifts ON players(total_lifts)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_players_total_earned ON players(total_earned)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_players_fitness_halls ON players(fitness_halls)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_players_power ON players(power)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_clan_members_user_id ON clan_members(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_inspections_inspector_id ON inspections(inspector_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_daily_hall_purchases_user_id ON daily_hall_purchases(user_id)")
        
        # Вставляем дефолтную запись для режима проверок
        await db.execute("INSERT OR IGNORE INTO inspection_time_mode (id, is_active) VALUES (1, 0)")
        
        await db.commit()


async def initialize_admin_ids() -> bool:
    """Initialize admin IDs for existing admins without an ID"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            'SELECT user_id, admin_since FROM players WHERE admin_level > 0 AND (admin_id IS NULL OR admin_id = "") ORDER BY admin_since ASC'
        ) as cur:
            admins = await cur.fetchall()

        current_id = 1000
        for admin in admins:
            user_id = admin[0]
            await db.execute(
                "UPDATE players SET admin_id = ? WHERE user_id = ?",
                (str(current_id), user_id),
            )
            current_id += 1

        await db.commit()
        return True


async def get_player(user_id: int) -> Optional[Dict[str, Any]]:
    """Get player data by user_id"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT user_id, username, balance, power, magnesia, last_dumbbell_use, is_new,
                   dumbbell_level, dumbbell_name, total_lifts, total_earned, total_spent,
                   custom_income, admin_level, admin_nickname, admin_since,
                   admin_id, bans_given, permabans_given, deletions_given,
                   dumbbell_sets_given, nickname_changes_given,
                   is_banned, ban_reason, ban_until, created_at,
                   clan_id, used_promo_codes, clan_role, contributions, fitness_halls,
                   coach_level, last_training, has_info_access, last_active
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
            "magnesia": row[4],
            "last_dumbbell_use": row[5],
            "is_new": row[6],
            "dumbbell_level": row[7],
            "dumbbell_name": row[8],
            "total_lifts": row[9],
            "total_earned": row[10],
            "total_spent": row[11],
            "custom_income": row[12],
            "admin_level": row[13],
            "admin_nickname": row[14],
            "admin_since": row[15],
            "admin_id": row[16],
            "bans_given": row[17],
            "permabans_given": row[18],
            "deletions_given": row[19],
            "dumbbell_sets_given": row[20],
            "nickname_changes_given": row[21],
            "is_banned": row[22],
            "ban_reason": row[23],
            "ban_until": row[24],
            "created_at": row[25],
            "clan_id": row[26],
            "used_promo_codes": json.loads(used_promo_codes),
            "clan_role": row[28],
            "contributions": row[29] or 0,
            "fitness_halls": row[30] or 0,
            "coach_level": row[31] or 0,
            "last_training": row[32],
            "has_info_access": bool(row[33]) if row[33] is not None else False,
            "last_active": row[34]
        }


async def create_player(user_id: int, username: str) -> Optional[Dict[str, Any]]:
    """Create a new player"""
    # Получаем начальные значения из настроек
    start_balance = getattr(settings, 'STARTING_BALANCE', 0)
    start_dumbbell_level = getattr(settings, 'STARTING_DUMBBELL_LEVEL', 1)
    dumbbell_name = "Гантеля 1кг"
    
    if hasattr(settings, 'DUMBBELL_LEVELS') and start_dumbbell_level in settings.DUMBBELL_LEVELS:
        dumbbell_name = settings.DUMBBELL_LEVELS[start_dumbbell_level].get('name', 'Гантеля 1кг')
    
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO players 
               (user_id, username, balance, dumbbell_level, dumbbell_name, last_active) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username, start_balance, start_dumbbell_level, dumbbell_name, datetime.now().isoformat()),
        )
        await db.commit()
    return await get_player(user_id)


async def update_username(user_id: int, new_username: str) -> bool:
    """Update player username"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET username = ?, last_active = ? WHERE user_id = ?", 
            (new_username, datetime.now().isoformat(), user_id)
        )
        await db.commit()
    return True


async def update_player_balance(
    user_id: int,
    amount: int,
    transaction_type: str,
    description: str,
    admin_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    clan_id: Optional[int] = None,
    other_user_id: Optional[int] = None
) -> bool:
    """Update player balance and log transaction"""
    # Рассчитываем заработанное/потраченное
    earned = amount if amount > 0 else 0
    spent = -amount if amount < 0 else 0
    
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET balance = balance + ?, total_earned = total_earned + ?, total_spent = total_spent + ?, last_active = ? WHERE user_id = ?",
            (amount, earned, spent, datetime.now().isoformat(), user_id),
        )

        await db.execute(
            """INSERT INTO transactions (user_id, type, amount, description, admin_id, target_user_id, clan_id, other_user_id) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, transaction_type, amount, description, admin_id, target_user_id, clan_id, other_user_id),
        )

        await db.commit()
    return True


async def set_player_balance(user_id: int, new_balance: int, admin_id: int) -> bool:
    """Set player balance to a specific value"""
    player = await get_player(user_id)
    old_balance = player["balance"] if player else 0

    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET balance = ?, last_active = ? WHERE user_id = ?", 
            (new_balance, datetime.now().isoformat(), user_id)
        )
        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (
                admin_id,
                "set_balance",
                user_id,
                f"Изменение баланса: {old_balance} -> {new_balance}",
            ),
        )
        await db.commit()
    return True


async def add_power(user_id: int, amount: int) -> bool:
    """Add power to player"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET power = power + ?, last_active = ? WHERE user_id = ?", 
            (amount, datetime.now().isoformat(), user_id)
        )
        await db.commit()
    return True


async def set_power(user_id: int, new_power: int, admin_id: int) -> bool:
    """Set player power to a specific value"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET power = ?, last_active = ? WHERE user_id = ?", 
            (new_power, datetime.now().isoformat(), user_id)
        )
        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (admin_id, "set_power", user_id, f"Установлена сила: {new_power}"),
        )
        await db.commit()
    return True


async def add_magnesia(
    user_id: int, amount: int, admin_id: Optional[int] = None
) -> bool:
    """Add magnesia to player"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET magnesia = magnesia + ?, last_active = ? WHERE user_id = ?",
            (amount, datetime.now().isoformat(), user_id),
        )

        if admin_id:
            await db.execute(
                """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
                   VALUES (?, ?, ?, ?)""",
                (
                    admin_id,
                    "add_magnesia",
                    user_id,
                    f"Добавлено банок магнезии: {amount}",
                ),
            )

        await db.commit()
    return True


async def update_dumbbell_level(
    user_id: int, new_level: int, dumbbell_name: str
) -> bool:
    """Update player dumbbell level"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET dumbbell_level = ?, dumbbell_name = ?, last_active = ? WHERE user_id = ?",
            (new_level, dumbbell_name, datetime.now().isoformat(), user_id),
        )
        await db.commit()
    return True


async def set_dumbbell_level(user_id: int, new_level: int, admin_id: int) -> bool:
    """Set player dumbbell level to a specific value"""
    if new_level not in settings.DUMBBELL_LEVELS:
        return False

    dumbbell_info = settings.DUMBBELL_LEVELS[new_level]

    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET dumbbell_level = ?, dumbbell_name = ?, last_active = ? WHERE user_id = ?",
            (new_level, dumbbell_info["name"], datetime.now().isoformat(), user_id),
        )

        await db.execute(
            "UPDATE players SET dumbbell_sets_given = dumbbell_sets_given + 1 WHERE user_id = ?",
            (admin_id,),
        )

        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (
                admin_id,
                "set_dumbbell_level",
                user_id,
                f"Установлен уровень гантели: {new_level}",
            ),
        )

        await db.commit()
    return True


async def update_dumbbell_use_time(user_id: int) -> bool:
    """Update the last dumbbell use time"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET last_dumbbell_use = ?, last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), datetime.now().isoformat(), user_id),
        )
        await db.commit()
    return True


async def increment_total_lifts(user_id: int) -> bool:
    """Increment total lifts counter"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET total_lifts = total_lifts + 1, last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id),
        )
        await db.commit()
    return True


async def set_total_lifts(user_id: int, new_total: int, admin_id: int) -> bool:
    """Set total lifts to a specific value"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET total_lifts = ?, last_active = ? WHERE user_id = ?", 
            (new_total, datetime.now().isoformat(), user_id)
        )
        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (
                admin_id,
                "set_total_lifts",
                user_id,
                f"Установлено поднятий: {new_total}",
            ),
        )
        await db.commit()
    return True


async def set_custom_income(
    user_id: int, custom_income: Optional[int], admin_id: int
) -> bool:
    """Set custom income for player"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET custom_income = ?, last_active = ? WHERE user_id = ?",
            (custom_income, datetime.now().isoformat(), user_id),
        )
        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (
                admin_id,
                "set_custom_income",
                user_id,
                f"Установлен кастомный доход: {custom_income}",
            ),
        )
        await db.commit()
    return True


async def make_admin(user_id: int, admin_id: int, admin_level: int = 1) -> str:
    """Make a player an admin"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            'SELECT MAX(CAST(admin_id AS INTEGER)) FROM players WHERE admin_id IS NOT NULL AND admin_id != ""'
        ) as cur:
            result = await cur.fetchone()

        if result[0] is None:
            new_admin_id = 1000
        else:
            new_admin_id = int(result[0]) + 1

        await db.execute(
            """UPDATE players 
               SET admin_level = ?, admin_since = ?, admin_id = ?, last_active = ?
               WHERE user_id = ?""",
            (admin_level, datetime.now().isoformat(), str(new_admin_id), datetime.now().isoformat(), user_id),
        )

        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (
                admin_id,
                "make_admin",
                user_id,
                f"Назначение администратора уровня {admin_level} с ID {new_admin_id}",
            ),
        )

        await db.commit()
    return str(new_admin_id)


async def remove_admin(user_id: int, admin_id: int) -> bool:
    """Remove admin status from player"""
    player_data = await get_player(user_id)
    if not player_data:
        return False

    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """UPDATE players 
               SET admin_level = 0, admin_nickname = NULL, admin_since = NULL, admin_id = NULL,
                   bans_given = 0, permabans_given = 0, deletions_given = 0,
                   dumbbell_sets_given = 0, nickname_changes_given = 0, last_active = ?
               WHERE user_id = ?""",
            (datetime.now().isoformat(), user_id),
        )

        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (
                admin_id,
                "remove_admin",
                user_id,
                f"Снятие с должности администратора: {player_data['username']}",
            ),
        )

        await db.commit()
    return True


async def set_admin_nickname(user_id: int, nickname: str) -> bool:
    """Set admin nickname"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET admin_nickname = ?, last_active = ? WHERE user_id = ?",
            (nickname, datetime.now().isoformat(), user_id),
        )
        await db.commit()
    return True


async def ban_player(user_id: int, days: int, reason: str, admin_id: int) -> bool:
    """Ban a player"""
    if days == 0:
        ban_until = None
    else:
        ban_until = (datetime.now() + timedelta(days=days)).isoformat()

    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET is_banned = 1, ban_reason = ?, ban_until = ?, last_active = ? WHERE user_id = ?",
            (reason, ban_until, datetime.now().isoformat(), user_id),
        )

        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (admin_id, "ban", user_id, f"Бан: {days} дней, причина: {reason}"),
        )

        await db.commit()
    return True


async def unban_player(user_id: int, admin_id: int) -> bool:
    """Unban a player"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET is_banned = 0, ban_reason = NULL, ban_until = NULL, last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id),
        )
        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (admin_id, "unban", user_id, "Разбан игрока"),
        )
        await db.commit()
    return True


async def delete_player(user_id: int, admin_id: int) -> bool:
    """Delete a player"""
    player_data = await get_player(user_id)
    if not player_data:
        return False

    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM dumbbell_uses WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM daily_hall_purchases WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM daily_income_stats WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM inspections WHERE inspector_id = ? OR target_id = ?", (user_id, user_id))
        await db.execute("DELETE FROM player_inspectors WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM player_protections WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM active_protections WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM protection_stats WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM players WHERE user_id = ?", (user_id,))

        await db.execute(
            """INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) 
               VALUES (?, ?, ?, ?)""",
            (
                admin_id,
                "delete_player",
                user_id,
                f"Удален игрок: {player_data['username']}",
            ),
        )

        await db.commit()
    return True


async def log_dumbbell_use(
    user_id: int, dumbbell_level: int, income: int, power_gained: int
) -> bool:
    """Log dumbbell use"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT INTO dumbbell_uses (user_id, dumbbell_level, income, power_gained) 
               VALUES (?, ?, ?, ?)""",
            (user_id, dumbbell_level, income, power_gained),
        )
        await db.commit()
    return True


async def increment_admin_stat(user_id: int, stat_name: str) -> bool:
    """Increment admin statistic"""
    stats_map = {
        "bans": "bans_given",
        "permabans": "permabans_given",
        "deletions": "deletions_given",
        "dumbbell_sets": "dumbbell_sets_given",
        "nickname_changes": "nickname_changes_given",
    }

    if stat_name in stats_map:
        column = stats_map[stat_name]
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                f"UPDATE players SET {column} = {column} + 1, last_active = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id),
            )
            await db.commit()
    return True


async def get_top_balance(limit: int = 10) -> List[Tuple]:
    """Get top players by balance"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT user_id, username, balance, dumbbell_name FROM players WHERE is_banned = 0 ORDER BY balance DESC LIMIT ?",
            (limit,),
        ) as cur:
            return await cur.fetchall()


async def get_top_lifts(limit: int = 10) -> List[Tuple]:
    """Get top players by total lifts"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT user_id, username, total_lifts, dumbbell_name FROM players WHERE is_banned = 0 ORDER BY total_lifts DESC LIMIT ?",
            (limit,),
        ) as cur:
            return await cur.fetchall()


async def get_top_earners(limit: int = 10) -> List[Tuple]:
    """Get top players by total earned"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT user_id, username, dumbbell_name, dumbbell_level, total_earned FROM players WHERE is_banned = 0 ORDER BY total_earned DESC LIMIT ?",
            (limit,),
        ) as cur:
            return await cur.fetchall()


# ======================
# ФУНКЦИИ ДЛЯ ФИТНЕС-ЗАЛОВ
# ======================

async def update_fitness_halls(user_id: int, amount: int, total_price: int = 0) -> int:
    """Обновить количество фитнес-залов у игрока"""
    async with aiosqlite.connect(settings.database_path) as db:
        # Обновляем количество залов
        await db.execute(
            "UPDATE players SET fitness_halls = fitness_halls + ?, last_active = ? WHERE user_id = ?",
            (amount, datetime.now().isoformat(), user_id)
        )
        
        # Обновляем статистику ежедневных покупок
        if amount > 0:
            await update_daily_purchases(user_id, amount)
        
        await db.commit()
        
        # Получаем новое количество залов
        async with db.execute(
            "SELECT fitness_halls FROM players WHERE user_id = ?", 
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_daily_purchases(user_id: int) -> int:
    """Получить количество купленных залов за сегодня"""
    today = datetime.now().date().isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT SUM(amount) as total FROM daily_hall_purchases WHERE user_id = ? AND purchase_date = ?",
            (user_id, today)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row and row[0] else 0


async def update_daily_purchases(user_id: int, amount: int) -> bool:
    """Обновить статистику ежедневных покупок"""
    today = datetime.now().date().isoformat()
    
    async with aiosqlite.connect(settings.database_path) as db:
        # Проверяем, есть ли уже запись на сегодня
        async with db.execute(
            "SELECT id FROM daily_hall_purchases WHERE user_id = ? AND purchase_date = ?",
            (user_id, today)
        ) as cur:
            existing = await cur.fetchone()
        
        if existing:
            # Обновляем существующую запись
            await db.execute(
                "UPDATE daily_hall_purchases SET amount = amount + ? WHERE user_id = ? AND purchase_date = ?",
                (amount, user_id, today)
            )
        else:
            # Создаем новую запись
            await db.execute(
                "INSERT INTO daily_hall_purchases (user_id, purchase_date, amount) VALUES (?, ?, ?)",
                (user_id, today, amount)
            )
        
        await db.commit()
        return True


async def reset_daily_purchases() -> bool:
    """Сбросить счетчики ежедневных покупок"""
    yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "DELETE FROM daily_hall_purchases WHERE purchase_date < ?",
            (yesterday,)
        )
        await db.commit()
        return True


# ======================
# ФУНКЦИИ ДЛЯ ЕЖЕДНЕВНЫХ ВЫПЛАТ
# ======================

async def get_all_players_with_halls() -> List[Dict[str, Any]]:
    """Получить всех игроков, у которых есть фитнес-залы"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT user_id, username, fitness_halls FROM players WHERE fitness_halls > 0 AND is_banned = 0"
        ) as cur:
            rows = await cur.fetchall()
    
    players = []
    for row in rows:
        players.append({
            "user_id": row[0],
            "username": row[1],
            "fitness_halls": row[2]
        })
    return players


async def add_daily_fitness_hall_income(user_id: int, amount: int, description: str) -> bool:
    """Добавить ежедневный доход с фитнес-залов"""
    async with aiosqlite.connect(settings.database_path) as db:
        # Обновляем баланс игрока
        await db.execute(
            "UPDATE players SET balance = balance + ?, total_earned = total_earned + ?, last_active = ? WHERE user_id = ?",
            (amount, amount, datetime.now().isoformat(), user_id)
        )
        
        # Записываем транзакцию
        await db.execute(
            "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'daily_hall_income', ?, ?)",
            (user_id, amount, description)
        )
        
        # Обновляем статистику ежедневных выплат
        today = datetime.now().date().isoformat()
        await db.execute(
            """INSERT OR REPLACE INTO daily_income_stats 
               (user_id, income_date, amount_received, last_received_date) 
               VALUES (?, ?, ?, ?)""",
            (user_id, today, amount, datetime.now().isoformat())
        )
        
        await db.commit()
        return True


async def get_daily_income_stats(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить статистику ежедневного дохода игрока"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """SELECT 
                COALESCE(SUM(amount_received), 0) as total_received,
                MAX(last_received_date) as last_received_date
               FROM daily_income_stats 
               WHERE user_id = ?
               GROUP BY user_id""",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
    
    if row:
        return {
            "total_received": row[0],
            "last_received_date": row[1]
        }
    return None


async def reset_daily_income_stats() -> bool:
    """Сбросить старые записи статистики ежедневного дохода"""
    month_ago = (datetime.now() - timedelta(days=30)).date().isoformat()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "DELETE FROM daily_income_stats WHERE income_date < ?",
            (month_ago,)
        )
        await db.commit()
        return True


# ======================
# ФУНКЦИИ ДЛЯ ТРЕНЕРСКОЙ ДЕЯТЕЛЬНОСТИ
# ======================

async def get_coach_level(user_id: int) -> int:
    """Получить уровень тренерской деятельности игрока"""
    player = await get_player(user_id)
    return player.get("coach_level", 0) if player else 0


async def update_coach_level(user_id: int, new_level: int) -> bool:
    """Обновить уровень тренерской деятельности"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET coach_level = ?, last_active = ? WHERE user_id = ?",
            (new_level, datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


async def get_last_training_time(user_id: int) -> Optional[str]:
    """Получить время последней тренировки"""
    player = await get_player(user_id)
    return player.get("last_training") if player else None


async def set_last_training_time(user_id: int, timestamp: str = None) -> bool:
    """Установить время последней тренировки"""
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET last_training = ?, last_active = ? WHERE user_id = ?",
            (timestamp, datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


async def get_coach_stats(user_id: int) -> Dict[str, Any]:
    """Получить статистику тренерской деятельности"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """SELECT 
                COALESCE(SUM(CASE WHEN type = 'training_income' THEN amount ELSE 0 END), 0) as total_earned,
                COUNT(CASE WHEN type = 'training_income' THEN 1 END) as total_trainings
               FROM transactions 
               WHERE user_id = ?""",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
    
    if row:
        return {
            "total_earned": row[0],
            "total_trainings": row[1]
        }
    return {"total_earned": 0, "total_trainings": 0}


# ======================
# ФУНКЦИИ ДЛЯ ДОСТУПА К КОМАНДЕ /ИНФА
# ======================

async def set_info_access(user_id: int) -> bool:
    """Выдать доступ к команде инфа"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET has_info_access = 1, last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


async def get_info_access_status(user_id: int) -> bool:
    """Получить статус доступа к команде инфа"""
    player = await get_player(user_id)
    return player.get("has_info_access", False) if player else False


async def remove_info_access(user_id: int) -> bool:
    """Забрать доступ к команде инфа"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET has_info_access = 0, last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


# ======================
# ФУНКЦИИ ДЛЯ ТОПОВ И РЕЙТИНГОВ
# ======================

async def get_top_players_by_power(limit: int = 10) -> List[Dict[str, Any]]:
    """Получить топ игроков по силе"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT user_id, username, power FROM players WHERE is_banned = 0 ORDER BY power DESC LIMIT ?",
            (limit,)
        ) as cur:
            rows = await cur.fetchall()
    
    players = []
    for row in rows:
        players.append({
            "user_id": row[0],
            "username": row[1],
            "power": row[2]
        })
    return players


async def get_top_players_by_halls(limit: int = 10) -> List[Dict[str, Any]]:
    """Получить топ игроков по фитнес-залам"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT user_id, username, fitness_halls FROM players WHERE is_banned = 0 ORDER BY fitness_halls DESC LIMIT ?",
            (limit,)
        ) as cur:
            rows = await cur.fetchall()
    
    players = []
    for row in rows:
        players.append({
            "user_id": row[0],
            "username": row[1],
            "fitness_halls": row[2]
        })
    return players


# ======================
# ФУНКЦИИ ДЛЯ АДМИНИСТРИРОВАНИЯ
# ======================

async def update_player_admin_level(user_id: int, admin_level: int) -> bool:
    """Обновить уровень админа игрока"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET admin_level = ?, last_active = ? WHERE user_id = ?",
            (admin_level, datetime.now().isoformat(), user_id)
        )
        await db.commit()
        return True


async def add_daily_income(user_id: int, amount: int, description: str) -> bool:
    """Добавить ежедневный доход (устаревшая функция, используйте add_daily_fitness_hall_income)"""
    return await add_daily_fitness_hall_income(user_id, amount, description)


# ======================
# ФУНКЦИИ ДЛЯ КЛАНОВ (НОВЫЕ)
# ======================

async def update_clan_hall_income(clan_id: int, amount: int) -> bool:
    """Обновить доход клана от залов"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE clans SET hall_income = hall_income + ? WHERE id = ?",
            (amount, clan_id)
        )
        await db.commit()
        return True


# ======================
# ФУНКЦИИ ДЛЯ СИСТЕМЫ ПРОВЕРОК (НОВЫЕ)
# ======================

async def get_inspections_by_inspector(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Получить проверки инспектора"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """SELECT i.*, p.username as target_name 
               FROM inspections i 
               LEFT JOIN players p ON i.target_id = p.user_id 
               WHERE inspector_id = ? 
               ORDER BY created_at DESC 
               LIMIT ?""",
            (user_id, limit)
        ) as cur:
            rows = await cur.fetchall()
    
    inspections = []
    for row in rows:
        inspections.append({
            "id": row[0],
            "inspector_id": row[1],
            "target_id": row[2],
            "successful": bool(row[3]),
            "halls_closed": row[4],
            "created_at": row[5],
            "target_name": row[6]
        })
    return inspections


async def add_inspection(
    inspector_id: int, 
    target_id: int, 
    successful: bool, 
    halls_closed: int = 0
) -> bool:
    """Добавить запись о проверке"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO inspections (inspector_id, target_id, successful, halls_closed) VALUES (?, ?, ?, ?)",
            (inspector_id, target_id, 1 if successful else 0, halls_closed)
        )
        await db.commit()
        return True


# ======================
# НОВЫЕ АДМИН КОМАНДЫ
# ======================

async def admin_reset_daily_stats(admin_id: int) -> Dict[str, Any]:
    """Сбросить ежедневную статистику (админ команда)"""
    try:
        # Сбрасываем статистику ежедневных покупок
        await reset_daily_purchases()
        
        # Сбрасываем статистику проверок
        await reset_daily_inspections()
        
        # Обновляем статистику админа
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)",
                (admin_id, "reset_daily_stats", 0, "Сброс ежедневной статистики")
            )
            await db.commit()
        
        return {"success": True, "message": "✅ Ежедневная статистика сброшена"}
    except Exception as e:
        return {"success": False, "error": f"Ошибка при сбросе статистики: {str(e)}"}


async def admin_get_system_stats(admin_id: int) -> Dict[str, Any]:
    """Получить статистику системы (админ команда)"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            # Получаем общую статистику
            stats = {}
            
            # Количество игроков
            async with db.execute("SELECT COUNT(*) FROM players") as cur:
                stats["total_players"] = (await cur.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM players WHERE is_banned = 1") as cur:
                stats["banned_players"] = (await cur.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM players WHERE admin_level > 0") as cur:
                stats["admins"] = (await cur.fetchone())[0]
            
            # Статистика фитнес-залов
            async with db.execute("SELECT SUM(fitness_halls) FROM players") as cur:
                stats["total_halls"] = (await cur.fetchone())[0] or 0
            
            async with db.execute("SELECT COUNT(*) FROM players WHERE fitness_halls > 0") as cur:
                stats["players_with_halls"] = (await cur.fetchone())[0]
            
            # Статистика проверок
            async with db.execute("SELECT COUNT(*) FROM inspections") as cur:
                stats["total_inspections"] = (await cur.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM inspections WHERE successful = 1") as cur:
                stats["successful_inspections"] = (await cur.fetchone())[0]
            
            # Статистика транзакций
            async with db.execute("SELECT SUM(balance) FROM players") as cur:
                stats["total_balance"] = (await cur.fetchone())[0] or 0
            
            async with db.execute("SELECT SUM(total_earned) FROM players") as cur:
                stats["total_earned"] = (await cur.fetchone())[0] or 0
            
            # Ежедневные покупки
            today = datetime.now().date().isoformat()
            async with db.execute("SELECT SUM(amount) FROM daily_hall_purchases WHERE purchase_date = ?", (today,)) as cur:
                stats["daily_hall_purchases"] = (await cur.fetchone())[0] or 0
            
            return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": f"Ошибка при получении статистики: {str(e)}"}


async def admin_manage_fitness_halls(
    admin_id: int, 
    target_user_id: int, 
    action: str, 
    amount: int
) -> Dict[str, Any]:
    """Управление фитнес-залами игрока (админ команда)"""
    try:
        player = await get_player(target_user_id)
        if not player:
            return {"success": False, "error": "Игрок не найден"}
        
        old_halls = player.get("fitness_halls", 0)
        new_halls = old_halls
        
        if action == "add":
            new_halls = old_halls + amount
            await update_fitness_halls(target_user_id, amount, 0)
        elif action == "remove":
            new_halls = max(0, old_halls - amount)
            await update_fitness_halls(target_user_id, -amount, 0)
        elif action == "set":
            if amount < 0:
                return {"success": False, "error": "Количество залов не может быть отрицательным"}
            difference = amount - old_halls
            new_halls = amount
            await update_fitness_halls(target_user_id, difference, 0)
        else:
            return {"success": False, "error": "Неизвестное действие"}
        
        # Логируем действие
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "INSERT INTO admin_actions (admin_id, action_type, target_user_id, details) VALUES (?, ?, ?, ?)",
                (admin_id, "manage_fitness_halls", target_user_id, f"{action.capitalize()} фитнес-залов: {old_halls} -> {new_halls} ({amount})")
            )
            await db.commit()
        
        return {
            "success": True, 
            "message": f"✅ Количество фитнес-залов изменено: {old_halls} → {new_halls}",
            "old_halls": old_halls,
            "new_halls": new_halls,
            "difference": new_halls - old_halls
        }
    except Exception as e:
        return {"success": False, "error": f"Ошибка при управлении фитнес-залами: {str(e)}"}


# ======================
# УТИЛИТНЫЕ ФУНКЦИИ
# ======================

async def cleanup_old_data() -> Dict[str, int]:
    """Очистка старых данных"""
    try:
        deleted_counts = {}
        
        # Очищаем старые логи (старше 30 дней)
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        async with aiosqlite.connect(settings.database_path) as db:
            # Удаляем старые логи
            await db.execute("DELETE FROM admin_logs WHERE created_at < ?", (month_ago,))
            async with db.execute("SELECT changes()") as cur:
                deleted_counts["admin_logs"] = (await cur.fetchone())[0]
            
            # Удаляем старые запросы
            await db.execute(
                "DELETE FROM admin_requests WHERE created_at < ? AND status != 'pending'",
                (month_ago,)
            )
            async with db.execute("SELECT changes()") as cur:
                deleted_counts["admin_requests"] = (await cur.fetchone())[0]
            
            # Удаляем старые транзакции (старше 90 дней)
            three_months_ago = (datetime.now() - timedelta(days=90)).isoformat()
            await db.execute("DELETE FROM transactions WHERE created_at < ?", (three_months_ago,))
            async with db.execute("SELECT changes()") as cur:
                deleted_counts["transactions"] = (await cur.fetchone())[0]
            
            # Удаляем старые проверки (старше 60 дней)
            two_months_ago = (datetime.now() - timedelta(days=60)).isoformat()
            await db.execute("DELETE FROM inspections WHERE created_at < ?", (two_months_ago,))
            async with db.execute("SELECT changes()") as cur:
                deleted_counts["inspections"] = (await cur.fetchone())[0]
            
            await db.commit()
        
        # Сбрасываем ежедневные статистики
        await reset_daily_purchases()
        await reset_daily_income_stats()
        await cleanup_expired_protections()
        await cleanup_expired_info_access()
        
        return {"success": True, "deleted_counts": deleted_counts}
    except Exception as e:
        return {"success": False, "error": f"Ошибка при очистке данных: {str(e)}"}


async def get_player_stats(user_id: int) -> Dict[str, Any]:
    """Получить полную статистику игрока"""
    try:
        player = await get_player(user_id)
        if not player:
            return {"success": False, "error": "Игрок не найден"}
        
        stats = {
            "player_info": {
                "username": player["username"],
                "balance": player["balance"],
                "power": player["power"],
                "magnesia": player["magnesia"],
                "fitness_halls": player.get("fitness_halls", 0),
                "coach_level": player.get("coach_level", 0),
                "total_lifts": player["total_lifts"],
                "total_earned": player["total_earned"],
                "total_spent": player.get("total_spent", 0),
                "clan_contributions": player.get("contributions", 0),
                "created_at": player["created_at"],
                "last_active": player.get("last_active", player["created_at"])
            },
            "inspections": {
                "stats": await get_inspection_stats(user_id),
                "inspectors": await get_player_inspectors(user_id),
                "recent": await get_inspections_by_inspector(user_id, 10)
            },
            "protection": {
                "active": await get_active_protection(user_id),
                "protections": await get_player_protections(user_id),
                "stats": await get_protection_stats(user_id)
            },
            "coach_stats": await get_coach_stats(user_id),
            "daily_stats": {
                "purchases": await get_daily_purchases(user_id),
                "income": await get_daily_income_stats(user_id)
            }
        }
        
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": f"Ошибка при получении статистики: {str(e)}"}


# ======================
# ОБНОВЛЕННЫЕ ФУНКЦИИ
# ======================

# Остальные функции из исходного кода остаются без изменений
# ... (здесь продолжается код из первой части)
