# bot/utils/clan_helpers.py

from bot.db import (
    get_player_clan,
    get_member_clan_role,
    format_number,  # из bot.utils
)

async def check_clan_permissions(user_id: int, clan: dict, required_roles: list) -> tuple:
    """
    Проверяет права пользователя в клане
    
    Args:
        user_id: ID пользователя
        clan: данные клана
        required_roles: список допустимых ролей (["owner"], ["owner", "officer"] и т.д.)
    
    Returns:
        tuple: (has_permission, error_message)
    """
    # Проверяем, является ли пользователь владельцем
    if clan["owner_id"] == user_id:
        return True, ""
    
    # Получаем роль пользователя в клане
    member_role = await get_member_clan_role(user_id, clan["id"])
    
    # member_role возвращает (role, error) или подобное, берем первый элемент
    role = member_role[0] if isinstance(member_role, tuple) else member_role
    
    if role in required_roles:
        return True, ""
    
    return False, "❌ У вас недостаточно прав для выполнения этой команды!"


async def validate_clan_membership(user_id: int, clan: dict = None) -> tuple:
    """
    Проверяет членство пользователя в клане
    
    Args:
        user_id: ID пользователя
        clan: данные клана (опционально)
    
    Returns:
        tuple: (is_member, error_message, clan_data)
    """
    if not clan:
        clan = await get_player_clan(user_id)
        
    if not clan:
        return False, "❌ Вы не состоите в клане. Используйте К вступить [ТЕГ].", None
        
    return True, "", clan


async def format_clan_members(members: list, detailed: bool = False) -> str:
    """
    Форматирует список участников клана для вывода
    
    Args:
        members: список участников
        detailed: подробный вывод с ролями
    
    Returns:
        str: отформатированный список
    """
    if not members:
        return "❌ В клане нет участников"
    
    if not detailed:
        # Краткий список
        text = "👥 Участники клана:\n\n"
        for i, member in enumerate(members[:15], 1):
            role_emoji = (
                "👑" if member["role"] == "owner"
                else ("⭐" if member["role"] == "officer" else "👤")
            )
            text += f"{i}. {role_emoji} [id{member['user_id']}|{member['username']}]\n"
        
        if len(members) > 15:
            text += f"\n...и еще {len(members) - 15} участников"
        
        return text
    
    else:
        # Подробный список с группировкой по ролям
        owners = [m for m in members if m["role"] == "owner"]
        officers = [m for m in members if m["role"] == "officer"]
        regular_members = [m for m in members if m["role"] == "member"]
        
        text = f"📊 ПОДРОБНЫЙ СОСТАВ КЛАНА\n\n"
        
        if owners:
            text += "👑 ВЛАДЕЛЬЦЫ:\n"
            for member in owners:
                contributions = member.get("contributions", 0)
                text += f"• [id{member['user_id']}|{member['username']}]"
                if contributions > 0:
                    text += f" - {format_number(contributions)} монет"
                text += "\n"
            text += "\n"
        
        if officers:
            text += "⭐ ОФИЦЕРЫ:\n"
            for member in officers:
                contributions = member.get("contributions", 0)
                text += f"• [id{member['user_id']}|{member['username']}]"
                if contributions > 0:
                    text += f" - {format_number(contributions)} монет"
                text += "\n"
            text += "\n"
        
        if regular_members:
            text += f"👤 УЧАСТНИКИ ({len(regular_members)}):\n"
            for i, member in enumerate(regular_members[:10], 1):
                contributions = member.get("contributions", 0)
                text += f"{i}. [id{member['user_id']}|{member['username']}]"
                if contributions > 0:
                    text += f" - {format_number(contributions)} монет"
                text += "\n"
            
            if len(regular_members) > 10:
                text += f"...и ещё {len(regular_members) - 10} участников\n"
        
        text += f"\n📈 Всего участников: {len(members)}"
        return text


async def get_clan_leaderboard_position(clan_id: int, clans_list: list) -> int:
    """
    Получить позицию клана в рейтинге
    
    Args:
        clan_id: ID клана
        clans_list: отсортированный список кланов
    
    Returns:
        int: позиция в рейтинге (начиная с 1) или 0 если не найден
    """
    for i, clan in enumerate(clans_list, 1):
        if clan["id"] == clan_id:
            return i
    return 0


def format_clan_short_info(clan: dict, position: int = None) -> str:
    """
    Форматирует краткую информацию о клане
    
    Args:
        clan: данные клана
        position: позиция в рейтинге (опционально)
    
    Returns:
        str: отформатированная информация
    """
    position_text = f"#{position} " if position else ""
    
    return (
        f"{position_text}[{clan['tag']}] {clan['name']}\n"
        f"   ⭐ Уровень: {clan['level']} | 👥 {clan.get('member_count', '?')} участников\n"
        f"   🏦 Казна: {format_number(clan['treasury'])} монет"
    )


def parse_user_mention(text: str) -> int or None:
    """
    Парсит упоминание пользователя или ID
    
    Args:
        text: текст с упоминанием ([id123|Name] или 123)
    
    Returns:
        int: ID пользователя или None если не удалось распарсить
    """
    import re
    
    # Паттерн для [id123|Name]
    mention_pattern = r'\[id(\d+)\|.*?\]'
    match = re.search(mention_pattern, text)
    
    if match:
        return int(match.group(1))
    
    # Если просто число
    if text.isdigit():
        return int(text)
    
    return None
