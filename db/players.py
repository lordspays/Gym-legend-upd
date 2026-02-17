# bot/db/players.py (новый файл или добавьте в существующий)

async def get_all_players() -> List[Dict[str, Any]]:
    """Получить всех игроков для рассылки"""
    cursor = players_collection.find({}, {"user_id": 1})
    players = await cursor.to_list(length=None)
    return players
