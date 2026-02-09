import json
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
        fitness_halls INTEGER DEFAULT 0
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            "magnesia": row[4],
            "last_dumbbell_use": row[5],
            "is_new": row[6],
            "dumbbell_level": row[7],
            "dumbbell_name": row[8],
            "total_lifts": row[9],
            "total_earned": row[10],
            "custom_income": row[11],
            "admin_level": row[12],
            "admin_nickname": row[13],
            "admin_since": row[14],
            "admin_id": row[15],
            "bans_given": row[16],
            "permabans_given": row[17],
            "deletions_given": row[18],
            "dumbbell_sets_given": row[19],
            "nickname_changes_given": row[20],
            "is_banned": row[21],
            "ban_reason": row[22],
            "ban_until": row[23],
            "created_at": row[24],
            "clan_id": row[25],
            "used_promo_codes": json.loads(used_promo_codes),
            "clan_role": row[27],
            "contributions": row[28] or 0,
            "fitness_halls": row[29] or 0,
        }


async def create_player(user_id: int, username: str) -> Optional[Dict[str, Any]]:
    """Create a new player"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO players 
               (user_id, username, dumbbell_level, dumbbell_name) 
               VALUES (?, ?, 1, 'Гантеля 1кг')""",
            (user_id, username),
        )
        await db.commit()
    return await get_player(user_id)


async def update_username(user_id: int, new_username: str) -> bool:
    """Update player username"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET username = ? WHERE user_id = ?", (new_username, user_id)
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
) -> bool:
    """Update player balance and log transaction"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id),
        )

        await db.execute(
            """INSERT INTO transactions (user_id, type, amount, description, admin_id, target_user_id) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, transaction_type, amount, description, admin_id, target_user_id),
        )

        if amount > 0:
            await db.execute(
                "UPDATE players SET total_earned = total_earned + ? WHERE user_id = ?",
                (amount, user_id),
            )

        await db.commit()
    return True


async def set_player_balance(user_id: int, new_balance: int, admin_id: int) -> bool:
    """Set player balance to a specific value"""
    player = await get_player(user_id)
    old_balance = player["balance"] if player else 0

    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET balance = ? WHERE user_id = ?", (new_balance, user_id)
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
            "UPDATE players SET power = power + ? WHERE user_id = ?", (amount, user_id)
        )
        await db.commit()
    return True


async def set_power(user_id: int, new_power: int, admin_id: int) -> bool:
    """Set player power to a specific value"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET power = ? WHERE user_id = ?", (new_power, user_id)
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
            "UPDATE players SET magnesia = magnesia + ? WHERE user_id = ?",
            (amount, user_id),
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
            "UPDATE players SET dumbbell_level = ?, dumbbell_name = ? WHERE user_id = ?",
            (new_level, dumbbell_name, user_id),
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
            "UPDATE players SET dumbbell_level = ?, dumbbell_name = ? WHERE user_id = ?",
            (new_level, dumbbell_info["name"], user_id),
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
            "UPDATE players SET last_dumbbell_use = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id),
        )
        await db.commit()
    return True


async def increment_total_lifts(user_id: int) -> bool:
    """Increment total lifts counter"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET total_lifts = total_lifts + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
    return True


async def set_total_lifts(user_id: int, new_total: int, admin_id: int) -> bool:
    """Set total lifts to a specific value"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE players SET total_lifts = ? WHERE user_id = ?", (new_total, user_id)
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
            "UPDATE players SET custom_income = ? WHERE user_id = ?",
            (custom_income, user_id),
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
               SET admin_level = ?, admin_since = ?, admin_id = ?
               WHERE user_id = ?""",
            (admin_level, datetime.now().isoformat(), str(new_admin_id), user_id),
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
                   dumbbell_sets_given = 0, nickname_changes_given = 0
               WHERE user_id = ?""",
            (user_id,),
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
            "UPDATE players SET admin_nickname = ? WHERE user_id = ?",
            (nickname, user_id),
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
            "UPDATE players SET is_banned = 1, ban_reason = ?, ban_until = ? WHERE user_id = ?",
            (reason, ban_until, user_id),
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
            "UPDATE players SET is_banned = 0, ban_reason = NULL, ban_until = NULL WHERE user_id = ?",
            (user_id,),
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
                f"UPDATE players SET {column} = {column} + 1 WHERE user_id = ?",
                (user_id,),
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


# ==============================
# ФУНКЦИИ ДЛЯ ПРОМОКОДОВ
# ==============================


async def create_promo_code(
    code: str,
    uses_total: int,
    reward_type: str,
    reward_amount: int,
    created_by: int,
    expires_days: Optional[int] = None,
) -> bool:
    """Create a promo code"""
    if expires_days:
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
    else:
        expires_at = None

    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO promo_codes (code, uses_total, uses_left, reward_type, reward_amount, created_by, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    code,
                    uses_total,
                    uses_total,
                    reward_type,
                    reward_amount,
                    created_by,
                    expires_at,
                ),
            )

            await db.execute(
                """
                INSERT INTO admin_actions (admin_id, action_type, target_user_id, details)
                VALUES (?, ?, ?, ?)
            """,
                (
                    created_by,
                    "create_promo",
                    0,
                    f"Создан промокод: {code}, награда: {reward_amount} {reward_type}",
                ),
            )

            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False


async def delete_promo_code(code: str, admin_id: int) -> bool:
    """Delete a promo code"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT code FROM promo_codes WHERE code = ?", (code,)
        ) as cur:
            result = await cur.fetchone()

        if not result:
            return False

        await db.execute("DELETE FROM promo_codes WHERE code = ?", (code,))

        await db.execute(
            """
            INSERT INTO admin_actions (admin_id, action_type, target_user_id, details)
            VALUES (?, ?, ?, ?)
        """,
            (admin_id, "delete_promo", 0, f"Удален промокод: {code}"),
        )

        await db.commit()
    return True


async def get_promo_info(code: str) -> Optional[Dict[str, Any]]:
    """Get promo code information"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT code, uses_total, uses_left, reward_type, reward_amount, 
                   created_by, created_at, expires_at, is_active
            FROM promo_codes WHERE code = ?
        """,
            (code,),
        ) as cur:
            row = await cur.fetchone()

        if row:
            return {
                "code": row[0],
                "uses_total": row[1],
                "uses_left": row[2],
                "reward_type": row[3],
                "reward_amount": row[4],
                "created_by": row[5],
                "created_at": row[6],
                "expires_at": row[7],
                "is_active": row[8],
            }
        return None


async def use_promo_code(user_id: int, code: str) -> Dict[str, Any]:
    """Use a promo code"""
    # Check if promo exists
    promo_info = await get_promo_info(code)
    if not promo_info:
        return {"success": False, "error": "Промокод не найден"}

    # Check if promo is active
    if promo_info["is_active"] == 0:
        return {"success": False, "error": "Промокод неактивен"}

    # Check expiration
    if promo_info["expires_at"]:
        expires_at = datetime.fromisoformat(promo_info["expires_at"])
        if datetime.now() > expires_at:
            return {"success": False, "error": "Срок действия промокода истек"}

    # Check remaining uses
    if promo_info["uses_left"] <= 0:
        return {"success": False, "error": "Лимит использований исчерпан"}

    async with aiosqlite.connect(settings.database_path) as db:
        # Check if player already used this promo
        async with db.execute(
            "SELECT used_promo_codes FROM players WHERE user_id = ?", (user_id,)
        ) as cur:
            result = await cur.fetchone()

        used_codes = json.loads(result[0] if result[0] else "[]")

        if code in used_codes:
            return {"success": False, "error": "Вы уже использовали этот промокод"}

        # Decrease remaining uses
        await db.execute(
            "UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?", (code,)
        )

        # Give reward
        if promo_info["reward_type"] == "монеты":
            await db.execute(
                "UPDATE players SET balance = balance + ? WHERE user_id = ?",
                (promo_info["reward_amount"], user_id),
            )
        elif promo_info["reward_type"] == "магнезия":
            await db.execute(
                "UPDATE players SET magnesia = magnesia + ? WHERE user_id = ?",
                (promo_info["reward_amount"], user_id),
            )

        # Add promo to used codes
        used_codes.append(code)
        await db.execute(
            "UPDATE players SET used_promo_codes = ? WHERE user_id = ?",
            (json.dumps(used_codes), user_id),
        )

        # Log usage
        await db.execute(
            """
            INSERT INTO promo_uses (user_id, promo_code)
            VALUES (?, ?)
        """,
            (user_id, code),
        )

        await db.commit()

    return {
        "success": True,
        "reward_type": promo_info["reward_type"],
        "reward_amount": promo_info["reward_amount"],
    }


async def get_all_promo_codes() -> List[Dict[str, Any]]:
    """Get all promo codes"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute("""
            SELECT code, uses_total, uses_left, reward_type, reward_amount, 
                   created_at, expires_at, is_active
            FROM promo_codes ORDER BY created_at DESC
        """) as cur:
            rows = await cur.fetchall()

    promos = []
    for row in rows:
        promos.append(
            {
                "code": row[0],
                "uses_total": row[1],
                "uses_left": row[2],
                "reward_type": row[3],
                "reward_amount": row[4],
                "created_at": row[5],
                "expires_at": row[6],
                "is_active": row[7],
            }
        )
    return promos


# ==============================
# ФУНКЦИИ ДЛЯ КЛАНОВ (ОБНОВЛЕННЫЕ)
# ==============================


async def create_clan(tag: str, name: str, owner_id: int) -> Dict[str, Any]:
    """Создать новый клан"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            # Проверяем, не существует ли уже такой тег
            async with db.execute(
                "SELECT id FROM clans WHERE tag = ?", (tag.upper(),)
            ) as cur:
                if await cur.fetchone():
                    return {"success": False, "error": f"Клан с тегом [{tag.upper()}] уже существует!"}
            
            # Проверяем, не существует ли клан с таким названием
            async with db.execute(
                "SELECT id FROM clans WHERE name = ?", (name,)
            ) as cur:
                if await cur.fetchone():
                    return {"success": False, "error": f"Клан с названием '{name}' уже существует!"}
            
            # Проверяем, состоит ли игрок уже в клане
            async with db.execute(
                "SELECT clan_id FROM players WHERE user_id = ?", (owner_id,)
            ) as cur:
                player_data = await cur.fetchone()
                if player_data and player_data[0]:
                    return {"success": False, "error": "Вы уже состоите в клане!"}
            
            # Создаем клан
            settings_json = json.dumps({"requirements": {"min_level": 1}, "greeting": None})
            banned_players_json = json.dumps([])
            
            await db.execute(
                """
                INSERT INTO clans (tag, name, owner_id, level, treasury, member_count, 
                                  total_income_per_hour, total_lifts, created_at, updated_at, 
                                  settings, banned_players, description)
                VALUES (?, ?, ?, 1, 0, 1, 0, 0, ?, ?, ?, ?, ?)
                """,
                (tag.upper(), name, owner_id, datetime.now().isoformat(), 
                 datetime.now().isoformat(), settings_json, banned_players_json, "Нет описания")
            )
            
            clan_id = db.lastrowid
            
            # Добавляем владельца в клан
            await db.execute(
                """
                UPDATE players 
                SET clan_id = ?, clan_role = 'owner'
                WHERE user_id = ?
                """,
                (clan_id, owner_id)
            )
            
            # Добавляем в таблицу участников
            await db.execute(
                """
                INSERT INTO clan_members (clan_id, user_id, role, contributions, joined_at)
                VALUES (?, ?, 'owner', 0, ?)
                """,
                (clan_id, owner_id, datetime.now().isoformat())
            )
            
            await db.commit()
            return {"success": True, "clan_id": clan_id}
    except Exception as e:
        return {"success": False, "error": f"Ошибка при создании клана: {str(e)}"}


async def get_clan_by_tag(tag: str) -> Optional[Dict[str, Any]]:
    """Найти клан по тегу"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT id, tag, name, owner_id, level, treasury, member_count, 
                   total_income_per_hour, total_lifts, created_at, updated_at,
                   settings, banned_players, description
            FROM clans WHERE tag = ?
            """,
            (tag.upper(),)
        ) as cur:
            row = await cur.fetchone()

        if row:
            return {
                "id": row[0],
                "tag": row[1],
                "name": row[2],
                "owner_id": row[3],
                "level": row[4],
                "treasury": row[5],
                "member_count": row[6],
                "total_income_per_hour": row[7],
                "total_lifts": row[8],
                "created_at": row[9],
                "updated_at": row[10],
                "settings": json.loads(row[11]) if row[11] else {"requirements": {"min_level": 1}, "greeting": None},
                "banned_players": json.loads(row[12]) if row[12] else [],
                "description": row[13]
            }
        return None


async def get_clan_by_id(clan_id: int) -> Optional[Dict[str, Any]]:
    """Get clan by ID"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT id, tag, name, owner_id, level, treasury, member_count,
                   total_income_per_hour, total_lifts, created_at, updated_at,
                   settings, banned_players, description
            FROM clans WHERE id = ?
            """,
            (clan_id,),
        ) as cur:
            row = await cur.fetchone()

        if row:
            return {
                "id": row[0],
                "tag": row[1],
                "name": row[2],
                "owner_id": row[3],
                "level": row[4],
                "treasury": row[5],
                "member_count": row[6],
                "total_income_per_hour": row[7],
                "total_lifts": row[8],
                "created_at": row[9],
                "updated_at": row[10],
                "settings": json.loads(row[11]) if row[11] else {"requirements": {"min_level": 1}, "greeting": None},
                "banned_players": json.loads(row[12]) if row[12] else [],
                "description": row[13]
            }
        return None


async def get_player_clan(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить клан игрока"""
    player = await get_player(user_id)
    if not player or not player.get("clan_id"):
        return None
    
    return await get_clan_by_id(player["clan_id"])


async def get_clan_members(clan_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Получить участников клана"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT p.user_id, p.username, cm.role, cm.contributions, cm.joined_at,
                   p.power, p.balance
            FROM players p
            JOIN clan_members cm ON p.user_id = cm.user_id
            WHERE p.clan_id = ? AND cm.clan_id = ?
            ORDER BY 
                CASE cm.role 
                    WHEN 'owner' THEN 1
                    WHEN 'officer' THEN 2
                    ELSE 3 
                END,
                cm.contributions DESC
            LIMIT ?
            """,
            (clan_id, clan_id, limit),
        ) as cur:
            rows = await cur.fetchall()

    members = []
    for row in rows:
        members.append(
            {
                "user_id": row[0],
                "username": row[1],
                "role": row[2],
                "contributions": row[3],
                "joined_at": row[4],
                "power": row[5],
                "balance": row[6],
            }
        )
    return members


async def get_clan_member_count(clan_id: int) -> int:
    """Получить количество участников клана"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM clan_members WHERE clan_id = ?", (clan_id,)
        ) as cur:
            result = await cur.fetchone()
    return result[0] if result else 0


async def deposit_to_clan_treasury(user_id: int, amount: int) -> Dict[str, Any]:
    """Внести деньги в казну клана"""
    try:
        player = await get_player(user_id)
        if not player or not player.get("clan_id"):
            return {"success": False, "error": "Вы не состоите в клане!"}
        
        if player["balance"] < amount:
            return {"success": False, "error": "Недостаточно средств на балансе!"}
        
        async with aiosqlite.connect(settings.database_path) as db:
            # Снимаем деньги с игрока
            await db.execute(
                "UPDATE players SET balance = balance - ? WHERE user_id = ?",
                (amount, user_id),
            )
            
            # Добавляем в казну клана
            await db.execute(
                "UPDATE clans SET treasury = treasury + ? WHERE id = ?",
                (amount, player["clan_id"]),
            )
            
            # Добавляем вклад игрока
            await db.execute(
                "UPDATE clan_members SET contributions = contributions + ? WHERE user_id = ? AND clan_id = ?",
                (amount, user_id, player["clan_id"]),
            )
            
            # Обновляем contributions в таблице players
            await db.execute(
                "UPDATE players SET contributions = contributions + ? WHERE user_id = ?",
                (amount, user_id),
            )
            
            # Логируем операцию
            await log_collection_with_user(
                player["clan_id"],
                user_id,
                "deposit",
                amount,
                f"Внесение в казну"
            )
            
            await db.commit()
            
            # Получаем общий вклад игрока
            updated_player = await get_player(user_id)
            total_contributions = updated_player.get("contributions", 0) if updated_player else 0
            
            return {"success": True, "total_contributions": total_contributions}
    except Exception as e:
        return {"success": False, "error": f"Ошибка при внесении денег: {str(e)}"}


async def subtract_treasury(clan_id: int, amount: int) -> bool:
    """Снять деньги с казны клана"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "UPDATE clans SET treasury = treasury - ? WHERE id = ?",
                (amount, clan_id),
            )
            await db.commit()
            return True
    except:
        return False


async def upgrade_clan(clan_id: int, upgrade_one_level: bool = True, cost: int = None, levels: int = 1) -> Dict[str, Any]:
    """Улучшить уровень клана"""
    try:
        clan = await get_clan_by_id(clan_id)
        if not clan:
            return {"success": False, "error": "Клан не найден!"}
        
        if upgrade_one_level:
            # Улучшаем на 1 уровень
            new_level = clan["level"] + 1
            if new_level > 100:  # Максимальный уровень
                return {"success": False, "error": "Достигнут максимальный уровень клана (100)!"}
            
            async with aiosqlite.connect(settings.database_path) as db:
                await db.execute(
                    "UPDATE clans SET level = level + 1, treasury = treasury - ?, updated_at = ? WHERE id = ?",
                    (cost, datetime.now().isoformat(), clan_id)
                )
                
                # Логируем операцию
                await db.execute(
                    """
                    INSERT INTO clan_treasury_log (clan_id, action_type, amount, description, created_at)
                    VALUES (?, 'upgrade', ?, ?, ?)
                    """,
                    (clan_id, cost, f"Улучшение клана до уровня {new_level}", datetime.now().isoformat())
                )
                
                await db.commit()
            
            return {"success": True, "new_level": new_level, "cost": cost}
        else:
            # Улучшаем на несколько уровней
            new_level = clan["level"] + levels
            if new_level > 100:
                new_level = 100
                levels = 100 - clan["level"]
            
            async with aiosqlite.connect(settings.database_path) as db:
                await db.execute(
                    "UPDATE clans SET level = level + ?, treasury = treasury - ?, updated_at = ? WHERE id = ?",
                    (levels, cost, datetime.now().isoformat(), clan_id)
                )
                
                # Логируем операцию
                await db.execute(
                    """
                    INSERT INTO clan_treasury_log (clan_id, action_type, amount, description, created_at)
                    VALUES (?, 'upgrade', ?, ?, ?)
                    """,
                    (clan_id, cost, f"Улучшение клана на {levels} уровней до {new_level}", datetime.now().isoformat())
                )
                
                await db.commit()
            
            return {"success": True, "new_level": new_level, "total_cost": cost}
    except Exception as e:
        return {"success": False, "error": f"Ошибка при улучшении клана: {str(e)}"}


async def update_clan_name(clan_id: int, new_name: str) -> bool:
    """Обновить название клана"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "UPDATE clans SET name = ?, updated_at = ? WHERE id = ?",
                (new_name, datetime.now().isoformat(), clan_id)
            )
            await db.commit()
            return True
    except:
        return False


async def delete_clan(clan_id: int) -> Dict[str, Any]:
    """Удалить клан"""
    try:
        # Получаем информацию о клане
        clan = await get_clan_by_id(clan_id)
        if not clan:
            return {"success": False, "error": "Клан не найден!"}
        
        async with aiosqlite.connect(settings.database_path) as db:
            # Получаем всех участников клана
            async with db.execute(
                "SELECT user_id FROM clan_members WHERE clan_id = ?", (clan_id,)
            ) as cur:
                members = await cur.fetchall()
            
            # Удаляем участников из клана
            member_ids = [member[0] for member in members]
            if member_ids:
                await db.execute(
                    f"UPDATE players SET clan_id = NULL, clan_role = NULL WHERE user_id IN ({','.join('?' for _ in member_ids)})",
                    member_ids
                )
            
            # Удаляем участников из таблицы clan_members
            await db.execute("DELETE FROM clan_members WHERE clan_id = ?", (clan_id,))
            
            # Удаляем логи казны
            await db.execute("DELETE FROM clan_treasury_log WHERE clan_id = ?", (clan_id,))
            
            # Удаляем логи клана
            await db.execute("DELETE FROM clan_logs WHERE clan_id = ?", (clan_id,))
            
            # Удаляем клан
            await db.execute("DELETE FROM clans WHERE id = ?", (clan_id,))
            
            await db.commit()
            
            return {"success": True, "member_count": len(members)}
    except Exception as e:
        return {"success": False, "error": f"Ошибка при удалении клана: {str(e)}"}


async def update_clan_description(clan_id: int, description: str) -> bool:
    """Обновить описание клана"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "UPDATE clans SET description = ?, updated_at = ? WHERE id = ?",
                (description, datetime.now().isoformat(), clan_id)
            )
            await db.commit()
            return True
    except:
        return False


async def log_clan_action(clan_id: int, user_id: int, action_type: str, details: str) -> bool:
    """Логировать действие в клане"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO clan_logs (clan_id, user_id, action_type, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (clan_id, user_id, action_type, details, datetime.now().isoformat())
            )
            await db.commit()
            return True
    except:
        return False


async def get_clan_log(clan_id: int, limit: int = 15) -> List[Dict[str, Any]]:
    """Получить лог действий клана"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT cl.user_id, p.username, cl.action_type, cl.details, cl.created_at
            FROM clan_logs cl
            LEFT JOIN players p ON cl.user_id = p.user_id
            WHERE cl.clan_id = ?
            ORDER BY cl.created_at DESC
            LIMIT ?
            """,
            (clan_id, limit),
        ) as cur:
            rows = await cur.fetchall()

    logs = []
    for row in rows:
        logs.append(
            {
                "user_id": row[0],
                "username": row[1] or "Неизвестно",
                "action_type": row[2],
                "details": row[3],
                "created_at": row[4],
            }
        )
    return logs


async def get_clan_requirements(clan_id: int) -> Dict[str, Any]:
    """Получить требования клана для вступления"""
    clan = await get_clan_by_id(clan_id)
    if not clan:
        return {"min_level": 1}
    
    return clan.get("settings", {}).get("requirements", {"min_level": 1})


async def get_player_contributions(user_id: int, clan_id: int) -> int:
    """Получить вклады игрока в казну клана"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT contributions FROM clan_members WHERE user_id = ? AND clan_id = ?",
            (user_id, clan_id)
        ) as cur:
            row = await cur.fetchone()
    
    return row[0] if row else 0


async def update_clan_settings(clan_id: int, settings: Dict[str, Any]) -> bool:
    """Обновить настройки клана"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "UPDATE clans SET settings = ?, updated_at = ? WHERE id = ?",
                (json.dumps(settings), datetime.now().isoformat(), clan_id)
            )
            await db.commit()
            return True
    except:
        return False


async def get_all_clans() -> List[Dict[str, Any]]:
    """Получить все кланы"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT id, tag, name, owner_id, level, treasury, member_count,
                   total_income_per_hour, total_lifts, created_at, updated_at,
                   settings, banned_players, description
            FROM clans
            ORDER BY created_at DESC
            LIMIT 1000
            """
        ) as cur:
            rows = await cur.fetchall()

    clans = []
    for row in rows:
        clans.append(
            {
                "id": row[0],
                "tag": row[1],
                "name": row[2],
                "owner_id": row[3],
                "level": row[4],
                "treasury": row[5],
                "member_count": row[6],
                "total_income_per_hour": row[7],
                "total_lifts": row[8],
                "created_at": row[9],
                "updated_at": row[10],
                "settings": json.loads(row[11]) if row[11] else {"requirements": {"min_level": 1}, "greeting": None},
                "banned_players": json.loads(row[12]) if row[12] else [],
                "description": row[13]
            }
        )
    return clans


async def get_top_clans(limit: int = 10) -> List[Dict[str, Any]]:
    """Получить топ кланов по казне"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT c.tag, c.name, c.level, c.treasury, c.total_income_per_hour,
                   COUNT(cm.id) as member_count
            FROM clans c
            LEFT JOIN clan_members cm ON c.id = cm.clan_id
            GROUP BY c.id
            ORDER BY c.total_income_per_hour DESC, c.treasury DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()

    clans = []
    for row in rows:
        clans.append(
            {
                "tag": row[0],
                "name": row[1],
                "level": row[2],
                "treasury": row[3],
                "total_income_per_hour": row[4],
                "member_count": row[5] or 0,
            }
        )
    return clans


async def log_collection_with_user(clan_id: int, user_id: int, action_type: str, amount: int, description: str) -> bool:
    """Логировать операцию с казной"""
    try:
        player = await get_player(user_id)
        username = player["username"] if player else "Неизвестно"
        
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO clan_treasury_log (clan_id, user_id, username, action_type, amount, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (clan_id, user_id, username, action_type, amount, description, datetime.now().isoformat())
            )
            await db.commit()
            return True
    except:
        return False


async def get_clan_treasury_log(clan_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получить лог операций с казной"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT ctl.action_type, ctl.amount, ctl.description, ctl.created_at, ctl.username
            FROM clan_treasury_log ctl
            WHERE ctl.clan_id = ?
            ORDER BY ctl.created_at DESC
            LIMIT ?
            """,
            (clan_id, limit),
        ) as cur:
            rows = await cur.fetchall()

    log = []
    for row in rows:
        log.append(
            {
                "action_type": row[0],
                "amount": row[1],
                "description": row[2],
                "created_at": row[3],
                "username": row[4],
            }
        )
    return log


# ======================
# СИСТЕМА ЕЖЕДНЕВНОГО ДОХОДА КЛАНА
# ======================

async def get_player_fitness_halls(user_id: int) -> int:
    """Получить количество фитнесс-залов игрока"""
    player = await get_player(user_id)
    return player.get("fitness_halls", 0) if player else 0


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
# ФУНКЦИИ ДЛЯ ВАЛИДАЦИИ И ПРАВ
# ======================

async def get_member_clan_role(user_id: int, clan_id: int) -> tuple:
    """Получить роль участника в клане"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT role FROM clan_members WHERE user_id = ? AND clan_id = ?",
            (user_id, clan_id)
        ) as cur:
            result = await cur.fetchone()
    
    return (result[0],) if result and result[0] else ("member",)


async def validate_clan_membership(user_id: int):
    """Проверить состоит ли игрок в клане"""
    clan = await get_player_clan(user_id)
    if not clan:
        return None, "❌ Вы не состоите в клане. Используйте К вступить [ТЕГ]."
    return clan, None


async def check_clan_permissions(user_id: int, clan: Dict[str, Any], required_roles: List[str]) -> tuple:
    """Проверить права игрока в клане"""
    player = await get_player(user_id)
    if not player:
        return False, "❌ Игрок не найден!"
    
    user_role = player.get("clan_role", "member")
    
    # Владелец имеет все права
    if clan["owner_id"] == user_id:
        return True, ""
    
    # Проверяем требуемые роли
    if user_role in required_roles:
        return True, ""
    
    role_names = {
        "owner": "Владелец",
        "officer": "Офицер",
        "member": "Участник"
    }
    
    required_role_names = [role_names.get(role, role) for role in required_roles]
    
    return False, f"❌ Эта команда доступна только: {', '.join(required_role_names)}"


# ======================
# ФУНКЦИИ ДЛЯ СИСТЕМЫ ПРОВЕРОК
# ======================

async def get_player_inspectors(user_id: int) -> List[int]:
    """Получить купленные уровни инспекторов игрока"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT level FROM player_inspectors WHERE user_id = ? ORDER BY level",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
        return [row[0] for row in rows]


async def buy_inspector_level(user_id: int, level: int) -> bool:
    """Купить уровень инспектора"""
    async with aiosqlite.connect(settings.database_path) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO player_inspectors (user_id, level) VALUES (?, ?)",
                (user_id, level)
            )
            await db.commit()
            return True
        except:
            return False


async def get_player_protections(user_id: int) -> List[int]:
    """Получить купленные уровни защиты игрока"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT level FROM player_protections WHERE user_id = ? ORDER BY level",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
        return [row[0] for row in rows]


async def buy_protection_level(user_id: int, level: int) -> bool:
    """Купить уровень защиты"""
    async with aiosqlite.connect(settings.database_path) as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO player_protections (user_id, level) VALUES (?, ?)",
                (user_id, level)
            )
            await db.commit()
            return True
        except:
            return False


async def get_active_protection(user_id: int) -> Optional[Dict]:
    """Получить активную защиту игрока"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT protection_level, activated_at, expires_at FROM active_protections WHERE user_id = ?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if row:
            return {
                "protection_level": row[0],
                "activated_at": row[1],
                "expires_at": row[2]
            }
        return None


async def activate_protection(user_id: int, level: int, duration_minutes: int) -> bool:
    """Активировать защиту"""
    async with aiosqlite.connect(settings.database_path) as db:
        try:
            activated_at = datetime.now()
            expires_at = activated_at + timedelta(minutes=duration_minutes)
            
            await db.execute(
                """INSERT OR REPLACE INTO active_protections 
                   (user_id, protection_level, activated_at, expires_at) 
                   VALUES (?, ?, ?, ?)""",
                (user_id, level, activated_at.isoformat(), expires_at.isoformat())
            )
            await db.commit()
            return True
        except:
            return False


async def get_inspection_stats(user_id: int) -> Dict:
    """Получить статистику проверок игрока"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """SELECT total_inspections, successful_inspections, 
                      failed_inspections, halls_closed, inspections_today,
                      last_inspection, last_reset_date 
               FROM inspection_stats WHERE user_id = ?""",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if row:
            return {
                "total_inspections": row[0],
                "successful_inspections": row[1],
                "failed_inspections": row[2],
                "halls_closed": row[3],
                "inspections_today": row[4],
                "last_inspection": row[5],
                "last_reset_date": row[6]
            }
        
        # Создаем новую запись
        await db.execute(
            """INSERT INTO inspection_stats (user_id) VALUES (?)""",
            (user_id,)
        )
        await db.commit()
        return {
            "total_inspections": 0,
            "successful_inspections": 0,
            "failed_inspections": 0,
            "halls_closed": 0,
            "inspections_today": 0,
            "last_inspection": None,
            "last_reset_date": datetime.now().date().isoformat()
        }


async def update_inspection_stats(
    user_id: int, 
    successful: bool, 
    halls_closed: int = 0
) -> bool:
    """Обновить статистику проверок"""
    async with aiosqlite.connect(settings.database_path) as db:
        try:
            # Сбрасываем дневной счетчик если нужно
            today = datetime.now().date().isoformat()
            await db.execute(
                """UPDATE inspection_stats 
                   SET inspections_today = 0, last_reset_date = ?
                   WHERE user_id = ? AND last_reset_date != ?""",
                (today, user_id, today)
            )
            
            # Обновляем статистику
            if successful:
                await db.execute(
                    """UPDATE inspection_stats 
                       SET total_inspections = total_inspections + 1,
                           successful_inspections = successful_inspections + 1,
                           halls_closed = halls_closed + ?,
                           inspections_today = inspections_today + 1,
                           last_inspection = ?
                       WHERE user_id = ?""",
                    (halls_closed, datetime.now().isoformat(), user_id)
                )
            else:
                await db.execute(
                    """UPDATE inspection_stats 
                       SET total_inspections = total_inspections + 1,
                           failed_inspections = failed_inspections + 1,
                           inspections_today = inspections_today + 1,
                           last_inspection = ?
                       WHERE user_id = ?""",
                    (datetime.now().isoformat(), user_id)
                )
            await db.commit()
            return True
        except Exception as e:
            print(f"Ошибка обновления статистики: {e}")
            return False


async def get_protection_stats(user_id: int) -> Dict:
    """Получить статистику защиты"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT total_blocked, total_spent_on_protection FROM protection_stats WHERE user_id = ?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
        if row:
            return {
                "total_blocked": row[0],
                "total_spent_on_protection": row[1]
            }
        
        # Создаем новую запись
        await db.execute(
            "INSERT INTO protection_stats (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()
        return {
            "total_blocked": 0,
            "total_spent_on_protection": 0
        }


async def update_protection_stats(user_id: int, blocked: bool = False, spent: int = 0) -> bool:
    """Обновить статистику защиты"""
    async with aiosqlite.connect(settings.database_path) as db:
        try:
            if blocked:
                await db.execute(
                    "UPDATE protection_stats SET total_blocked = total_blocked + 1 WHERE user_id = ?",
                    (user_id,)
                )
            if spent > 0:
                await db.execute(
                    "UPDATE protection_stats SET total_spent_on_protection = total_spent_on_protection + ? WHERE user_id = ?",
                    (spent, user_id)
                )
            await db.commit()
            return True
        except:
            return False


async def get_inspection_time_mode() -> Dict:
    """Получить статус режима 'Время проверок'"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT is_active, started_at, ends_at FROM inspection_time_mode ORDER BY id DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
        if row:
            return {
                "is_active": bool(row[0]),
                "started_at": row[1],
                "ends_at": row[2]
            }
        
        # Создаем запись по умолчанию
        await db.execute(
            "INSERT INTO inspection_time_mode (is_active) VALUES (0)"
        )
        await db.commit()
        return {
            "is_active": False,
            "started_at": None,
            "ends_at": None
        }


async def set_inspection_time_mode(is_active: bool, duration_hours: int = 24) -> bool:
    """Установить режим 'Время проверок'"""
    async with aiosqlite.connect(settings.database_path) as db:
        try:
            started_at = datetime.now()
            ends_at = started_at + timedelta(hours=duration_hours)
            
            # Деактивируем все предыдущие записи
            await db.execute("UPDATE inspection_time_mode SET is_active = 0")
            
            # Создаем новую запись
            await db.execute(
                """INSERT INTO inspection_time_mode (is_active, started_at, ends_at) 
                   VALUES (?, ?, ?)""",
                (1 if is_active else 0, started_at.isoformat(), ends_at.isoformat())
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"Ошибка установки режима: {e}")
            return False


async def cleanup_expired_protections():
    """Очистить истекшие защиты"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "DELETE FROM active_protections WHERE expires_at < ?",
            (datetime.now().isoformat(),)
        )
        await db.commit()


async def reset_daily_inspections():
    """Сбросить дневные счетчики проверок"""
    async with aiosqlite.connect(settings.database_path) as db:
        today = datetime.now().date().isoformat()
        await db.execute(
            """UPDATE inspection_stats 
               SET inspections_today = 0, last_reset_date = ?
               WHERE last_reset_date != ?""",
            (today, today)
        )
        await db.commit()


# ======================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ЛОГАМИ
# ======================

async def add_admin_log(
    user_id: int,
    admin_name: str,
    admin_level: str,
    action_type: str,
    details: str = "",
    log_type: str = "other"
) -> bool:
    """Добавление записи в логи администратора"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO admin_logs 
                (user_id, admin_name, admin_level, action_type, details, log_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, admin_name, admin_level, action_type, details, log_type)
            )
            await db.commit()
            return True
    except:
        return False


async def get_admin_logs(
    log_type: str = None,
    admin_id: int = None,
    limit: int = 50,
    offset: int = 0
) -> list:
    """Получение логов администратора"""
    query = "SELECT * FROM admin_logs WHERE 1=1"
    params = []
    
    if log_type:
        query += " AND log_type = ?"
        params.append(log_type)
    
    if admin_id:
        query += " AND user_id = ?"
        params.append(admin_id)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
    
    logs = []
    for row in rows:
        logs.append({
            "id": row[0],
            "user_id": row[1],
            "admin_name": row[2],
            "admin_level": row[3],
            "action_type": row[4],
            "details": row[5],
            "log_type": row[6],
            "created_at": row[7],
        })
    return logs


async def cleanup_old_logs(days: int = 15) -> int:
    """Очистка старых логов"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "DELETE FROM admin_logs WHERE created_at < ?",
                (cutoff_date,)
            )
            await db.commit()
            
            # Получаем количество удаленных записей
            async with db.execute("SELECT changes()") as cur:
                result = await cur.fetchone()
            return result[0] if result else 0
    except:
        return 0


# ======================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАЯВКАМИ
# ======================

async def create_request(
    request_id: int,
    admin_id: int,
    admin_name: str,
    request_type: str,
    target_id: int = None,
    reason: str = "",
    additional_info: dict = None
) -> dict:
    """Создание заявки"""
    try:
        additional_info_json = json.dumps(additional_info) if additional_info else "{}"
        
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO admin_requests 
                (id, admin_id, admin_name, request_type, target_id, reason, additional_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (request_id, admin_id, admin_name, request_type, target_id, reason, additional_info_json)
            )
            await db.commit()
            return {"success": True, "request_id": request_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_pending_requests() -> list:
    """Получение ожидающих заявок"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT * FROM admin_requests 
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        ) as cur:
            rows = await cur.fetchall()
    
    requests = []
    for row in rows:
        additional_info = {}
        if row[6]:
            try:
                additional_info = json.loads(row[6])
            except:
                additional_info = {}
        
        requests.append({
            "id": row[0],
            "admin_id": row[1],
            "admin_name": row[2],
            "request_type": row[3],
            "target_id": row[4],
            "reason": row[5],
            "additional_info": additional_info,
            "status": row[7],
            "approved_by": row[8],
            "approved_at": row[9],
            "created_at": row[10],
        })
    return requests


async def get_request_by_id(request_id: int) -> dict:
    """Получение заявки по ID"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT * FROM admin_requests WHERE id = ?",
            (request_id,)
        ) as cur:
            row = await cur.fetchone()
    
    if not row:
        return {}
    
    additional_info = {}
    if row[6]:
        try:
            additional_info = json.loads(row[6])
        except:
            additional_info = {}
    
    return {
        "id": row[0],
        "admin_id": row[1],
        "admin_name": row[2],
        "request_type": row[3],
        "target_id": row[4],
        "reason": row[5],
        "additional_info": additional_info,
        "status": row[7],
        "approved_by": row[8],
        "approved_at": row[9],
        "created_at": row[10],
    }


async def approve_request(request_id: int, approved_by: int) -> dict:
    """Подтверждение заявки"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                UPDATE admin_requests 
                SET status = 'approved', approved_by = ?, approved_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (approved_by, datetime.now().isoformat(), request_id)
            )
            await db.commit()
            
            # Проверяем, была ли обновлена запись
            async with db.execute("SELECT changes()") as cur:
                result = await cur.fetchone()
            
            if result and result[0] > 0:
                return {"success": True}
            else:
                return {"success": False, "error": "Заявка не найдена или уже обработана"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def reject_request(request_id: int, rejected_by: int, reason: str = None) -> dict:
    """Отклонение заявки с указанием причины"""
    try:
        # Получаем текущую заявку
        request = await get_request_by_id(request_id)
        if not request:
            return {"success": False, "error": "Заявка не найдена"}
        
        # Обновляем additional_info с причиной отклонения
        additional_info = request.get("additional_info", {})
        additional_info["reject_reason"] = reason or "Отклонено администратором"
        
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                UPDATE admin_requests 
                SET status = 'rejected', 
                    approved_by = ?, 
                    approved_at = ?,
                    additional_info = ?
                WHERE id = ? AND status = 'pending'
                """,
                (rejected_by, datetime.now().isoformat(), json.dumps(additional_info), request_id)
            )
            await db.commit()
            
            # Проверяем, была ли обновлена запись
            async with db.execute("SELECT changes()") as cur:
                result = await cur.fetchone()
            
            if result and result[0] > 0:
                return {"success": True}
            else:
                return {"success": False, "error": "Заявка не найдена или уже обработана"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_request(request_id: int) -> bool:
    """Удаление заявки"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute("DELETE FROM admin_requests WHERE id = ?", (request_id,))
            await db.commit()
            return True
    except:
        return False


async def cleanup_old_requests(days: int = 15) -> int:
    """Очистка старых заявок"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                DELETE FROM admin_requests 
                WHERE created_at < ? AND status != 'pending'
                """,
                (cutoff_date,)
            )
            await db.commit()
            
            # Получаем количество удаленных записей
            async with db.execute("SELECT changes()") as cur:
                result = await cur.fetchone()
            return result[0] if result else 0
    except:
        return 0


async def get_request_stats() -> dict:
    """Получение статистики по заявкам"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT 
                status,
                COUNT(*) as count
            FROM admin_requests 
            GROUP BY status
            """
        ) as cur:
            rows = await cur.fetchall()
    
    stats = {}
    for row in rows:
        stats[row[0]] = row[1]
    
    return stats


async def get_requests_by_admin(admin_id: int, limit: int = 20) -> list:
    """Получение заявок созданных администратором"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT * FROM admin_requests 
            WHERE admin_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (admin_id, limit)
        ) as cur:
            rows = await cur.fetchall()
    
    requests = []
    for row in rows:
        additional_info = {}
        if row[6]:
            try:
                additional_info = json.loads(row[6])
            except:
                additional_info = {}
        
        requests.append({
            "id": row[0],
            "admin_id": row[1],
            "admin_name": row[2],
            "request_type": row[3],
            "target_id": row[4],
            "reason": row[5],
            "additional_info": additional_info,
            "status": row[7],
            "approved_by": row[8],
            "approved_at": row[9],
            "created_at": row[10],
        })
    return requests


# ======================
# ФУНКЦИИ ДЛЯ СТАТИСТИКИ ИСПОЛЬЗОВАНИЯ
# ======================

async def get_admin_usage_stats(admin_id: int) -> dict:
    """Получение статистики использования команд администратором"""
    async with aiosqlite.connect(settings.database_path) as db:
        # Получаем дату 30 дней назад
        thirty_days_ago = (datetime.now() - timedelta(days=30)).date().isoformat()
        
        async with db.execute(
            """
            SELECT stat_type, SUM(stat_value) as total
            FROM admin_usage_stats 
            WHERE admin_id = ? 
            AND period_date >= ?
            GROUP BY stat_type
            """,
            (admin_id, thirty_days_ago)
        ) as cur:
            rows = await cur.fetchall()
    
    stats = {}
    for row in rows:
        stats[row[0]] = row[1]
    
    return stats


async def update_admin_usage_stats(admin_id: int, stat_type: str, value: int = 1) -> bool:
    """Обновление статистики использования команд"""
    try:
        today = datetime.now().date().isoformat()
        
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO admin_usage_stats (admin_id, stat_type, stat_value, period_date)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(admin_id, stat_type, period_date) 
                DO UPDATE SET 
                stat_value = stat_value + ?,
                updated_at = CURRENT_TIMESTAMP
                """,
                (admin_id, stat_type, value, today, value)
            )
            await db.commit()
            return True
    except:
        return False


# ======================
# ФУНКЦИИ ДЛЯ СТАТИСТИКИ РАССЫЛОК
# ======================

async def get_broadcast_usage(admin_id: int) -> dict:
    """Получение статистики рассылок"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT * FROM admin_broadcast_stats WHERE admin_id = ?",
            (admin_id,)
        ) as cur:
            row = await cur.fetchone()
    
    if not row:
        # Создаем запись если нет
        await reset_broadcast_usage(admin_id)
        return {
            "usage_count": 0,
            "last_used": datetime.now().isoformat(),
            "reset_time": (datetime.now() + timedelta(days=1)).isoformat()
        }
    
    # Проверяем нужно ли сбросить счетчик (прошло 24 часа)
    reset_time = row[3]
    if isinstance(reset_time, str):
        try:
            reset_time = datetime.fromisoformat(reset_time.replace('Z', '+00:00'))
        except:
            reset_time = datetime.now()
    
    if datetime.now() > reset_time:
        await reset_broadcast_usage(admin_id)
        return {
            "usage_count": 0,
            "last_used": datetime.now().isoformat(),
            "reset_time": (datetime.now() + timedelta(days=1)).isoformat()
        }
    
    return {
        "usage_count": row[2],
        "last_used": row[3],
        "reset_time": row[4],
    }


async def increment_broadcast_usage(admin_id: int) -> bool:
    """Увеличение счетчика рассылок"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO admin_broadcast_stats (admin_id, usage_count, last_used)
                VALUES (?, 1, ?)
                ON CONFLICT(admin_id) 
                DO UPDATE SET 
                usage_count = usage_count + 1,
                last_used = ?,
                updated_at = CURRENT_TIMESTAMP
                """,
                (admin_id, datetime.now().isoformat(), datetime.now().isoformat())
            )
            await db.commit()
            return True
    except:
        return False


async def reset_broadcast_usage(admin_id: int) -> bool:
    """Сброс счетчика рассылок"""
    try:
        next_reset = datetime.now() + timedelta(days=1)
        
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO admin_broadcast_stats (admin_id, usage_count, reset_time)
                VALUES (?, 0, ?)
                ON CONFLICT(admin_id) 
                DO UPDATE SET 
                usage_count = 0,
                reset_time = ?,
                updated_at = CURRENT_TIMESTAMP
                """,
                (admin_id, next_reset.isoformat(), next_reset.isoformat())
            )
            await db.commit()
            return True
    except:
        return False


async def check_broadcast_limit(admin_id: int) -> tuple:
    """Проверка лимита рассылок"""
    stats = await get_broadcast_usage(admin_id)
    
    if stats["usage_count"] >= 5:
        return False, stats
    
    return True, stats


# ======================
# ФУНКЦИИ ДЛЯ СТАТИСТИКИ ПРОМОКОДОВ МОДЕРАТОРОВ
# ======================

async def get_moderator_promo_stats(admin_id: int) -> dict:
    """Получение статистики промокодов модератора"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT * FROM moderator_promo_stats WHERE admin_id = ?",
            (admin_id,)
        ) as cur:
            row = await cur.fetchone()
    
    if not row:
        return {
            "coins_used": 0,
            "magnesia_used": 0,
            "power_used": 0,
            "total_created": 0,
            "last_created": None
        }
    
    return {
        "coins_used": row[2],
        "magnesia_used": row[3],
        "power_used": row[4],
        "total_created": row[5],
        "last_created": row[6],
    }


async def update_moderator_promo_stats(admin_id: int, reward_type: str, amount: int) -> bool:
    """Обновление статистики промокодов"""
    try:
        # Сначала получаем текущую статистику
        current_stats = await get_moderator_promo_stats(admin_id)
        
        # Обновляем соответствующие поля
        if reward_type == "монеты":
            coins_used = current_stats["coins_used"] + amount
            magnesia_used = current_stats["magnesia_used"]
            power_used = current_stats["power_used"]
        elif reward_type == "магнезия":
            coins_used = current_stats["coins_used"]
            magnesia_used = current_stats["magnesia_used"] + amount
            power_used = current_stats["power_used"]
        elif reward_type == "сила":
            coins_used = current_stats["coins_used"]
            magnesia_used = current_stats["magnesia_used"]
            power_used = current_stats["power_used"] + amount
        else:
            coins_used = current_stats["coins_used"]
            magnesia_used = current_stats["magnesia_used"]
            power_used = current_stats["power_used"]
        
        total_created = current_stats["total_created"] + 1
        
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT INTO moderator_promo_stats 
                (admin_id, coins_used, magnesia_used, power_used, total_created, last_created)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(admin_id) 
                DO UPDATE SET 
                coins_used = ?,
                magnesia_used = ?,
                power_used = ?,
                total_created = ?,
                last_created = ?,
                updated_at = CURRENT_TIMESTAMP
                """,
                (admin_id, coins_used, magnesia_used, power_used, total_created, 
                 datetime.now().isoformat(), coins_used, magnesia_used, power_used, 
                 total_created, datetime.now().isoformat())
            )
            await db.commit()
            return True
    except:
        return False


async def get_promo_usage_stats(admin_id: int) -> dict:
    """Получение статистики использования промокодов администратором"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT 
                SUM(CASE WHEN reward_type = 'монеты' THEN reward_amount ELSE 0 END) as total_coins,
                SUM(CASE WHEN reward_type = 'магнезия' THEN reward_amount ELSE 0 END) as total_magnesia,
                SUM(CASE WHEN reward_type = 'сила' THEN reward_amount ELSE 0 END) as total_power,
                COUNT(*) as total_created
            FROM promo_codes 
            WHERE created_by = ?
            """,
            (admin_id,)
        ) as cur:
            row = await cur.fetchone()
    
    return {
        "total_coins": row[0] or 0,
        "total_magnesia": row[1] or 0,
        "total_power": row[2] or 0,
        "total_created": row[3] or 0
    }


async def update_promo_usage_stats(admin_id: int, reward_type: str, amount: int) -> bool:
    """Обновление статистики использования промокодов"""
    # Эта функция вызывает update_moderator_promo_stats
    return await update_moderator_promo_stats(admin_id, reward_type, amount)


# ======================
# ФУНКЦИИ ДЛЯ РАБОТЫ С АДМИНИСТРАТОРАМИ
# ======================

async def get_admin_level(user_id: int) -> int:
    """Получение уровня администратора"""
    player = await get_player(user_id)
    if player:
        return player.get("admin_level", 0)
    return 0


# ======================
# ФУНКЦИИ ДЛЯ ДОСТУПА К КОМАНДЕ /ИНФА
# ======================

async def grant_info_access(user_id: int, admin_id: int, hours: int) -> bool:
    """Предоставить доступ к команде /инфа"""
    try:
        granted_at = datetime.now()
        expires_at = granted_at + timedelta(hours=hours)
        
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO info_access (user_id, admin_id, granted_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, admin_id, granted_at.isoformat(), expires_at.isoformat())
            )
            await db.commit()
            return True
    except:
        return False


async def revoke_info_access(user_id: int) -> bool:
    """Отозвать доступ к команде /инфа"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "DELETE FROM info_access WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            return True
    except:
        return False


async def check_info_access(user_id: int) -> tuple[bool, Optional[str]]:
    """Проверить доступ к команде /инфа"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            async with db.execute(
                "SELECT expires_at FROM info_access WHERE user_id = ?",
                (user_id,)
            ) as cur:
                row = await cur.fetchone()
            
            if not row:
                return False, "У вас нет доступа к команде /инфа"
            
            expires_at = datetime.fromisoformat(row[0])
            if datetime.now() > expires_at:
                # Удаляем истекший доступ
                await db.execute(
                    "DELETE FROM info_access WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
                return False, "Срок действия доступа к команде /инфа истек"
            
            time_left = expires_at - datetime.now()
            hours_left = int(time_left.total_seconds() // 3600)
            minutes_left = int((time_left.total_seconds() % 3600) // 60)
            
            return True, f"Доступ активен еще {hours_left}ч {minutes_left}мин"
    except:
        return False, "Ошибка при проверке доступа"


async def cleanup_expired_info_access():
    """Очистить истекшие доступы к команде /инфа"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute(
                "DELETE FROM info_access WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            await db.commit()
    except:
        pass


# ======================
# ДРУГИЕ ФУНКЦИИ
# ======================

async def count_players(regular_only: bool = True, unbanned_only: bool = False) -> int:
    """Посчитать количество игроков"""
    query = "SELECT COUNT(*) FROM players"
    params = []
    
    if regular_only or unbanned_only:
        query += " WHERE "
        conditions = []
        
        if regular_only:
            conditions.append("admin_level = 0")
        
        if unbanned_only:
            conditions.append("is_banned = 0")
        
        query += " AND ".join(conditions)

    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(query, params) as cur:
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


async def count_banned_players() -> int:
    """Посчитать количество забаненных игроков"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM players WHERE is_banned = 1"
        ) as cur:
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


async def count_admins() -> int:
    """Посчитать количество администраторов"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM players WHERE admin_level > 0"
        ) as cur:
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


async def count_clans() -> int:
    """Посчитать количество кланов"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute("SELECT COUNT(*) FROM clans") as cur:
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


async def count_total_balance() -> int:
    """Посчитать общий баланс всех игроков"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT SUM(balance) FROM players WHERE admin_level = 0"
        ) as cur:
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


async def count_promo_uses(code: str, limit: int = 0):
    """Посчитать количество использований промокода"""
    query = "SELECT COUNT(*) FROM promo_uses WHERE promo_code = ?"
    params = [code]
    
    if limit > 0:
        query += f" LIMIT {limit}"

    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(query, params) as cur:
            if limit > 0:
                result = await cur.fetchall()
                return result
            
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


async def sum_promo_uses() -> int:
    """Суммировать использованные промокоды"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT SUM(uses_total - uses_left) FROM promo_codes"
        ) as cur:
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


async def get_recent_players(limit: int = 5):
    """Получить последних зарегистрированных игроков"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            "SELECT username, created_at FROM players ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ) as cur:
            return await cur.fetchall()


async def sum_column(table: str, column: str) -> int:
    """Суммировать значения в колонке"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(f"SELECT SUM({column}) FROM {table}") as cur:
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


async def count_table_rows(table: str) -> int:
    """Посчитать количество строк в таблице"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(f"SELECT COUNT(*) FROM {table}") as cur:
            result = await cur.fetchone()
            return 0 if not result else 0 if not result[0] else result[0]


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


async def get_all_players(limit: int = 100) -> List[Dict[str, Any]]:
    """Получить всех игроков"""
    async with aiosqlite.connect(settings.database_path) as db:
        async with db.execute(
            """
            SELECT user_id, username, balance, power, magnesia, 
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
            "magnesia": row[4],
            "dumbbell_level": row[5],
            "dumbbell_name": row[6],
            "total_lifts": row[7],
            "total_earned": row[8],
            "admin_level": row[9],
            "is_banned": row[10],
            "clan_id": row[11],
            "fitness_halls": row[12],
            "created_at": row[13],
        })
    return players
