# Добавьте в файл bot/db.py (в раздел с функциями для фитнес-залов)

async def reset_all_daily_purchases():
    """Сброс статистики покупок для всех игроков"""
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            # Очищаем таблицу с ежедневными покупками
            await cursor.execute("DELETE FROM daily_purchases")
            await conn.commit()
            return True
    except Exception as e:
        print(f"Ошибка сброса ежедневных покупок: {e}")
        return False
    finally:
        conn.close()
