import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from vkbottle.bot import BotLabeler, Message
from vkbottle import API

from bot.core.config import settings
from bot.db import (
    get_player,
    get_player_fitness_halls,
    get_all_players_with_halls,
    add_daily_fitness_hall_income,
    get_daily_income_stats,
    reset_daily_income_stats,
)
from bot.utils import format_number

daily_income_labeler = BotLabeler()
daily_income_labeler.vbml_ignore_case = True

# Константы для ежедневных выплат
DAILY_HALL_INCOME = 10  # 10 монет за каждый фитнес-зал в день


# ======================
# ЕЖЕДНЕВНЫЕ ВЫПЛАТЫ С ФИТНЕС-ЗАЛОВ
# ======================

async def daily_income_task():
    """Фоновая задача для начисления ежедневного дохода с фитнес-залов в 00:01"""
    while True:
        now = datetime.now()
        
        # Рассчитываем время до следующего дня 00:01
        next_day = now.replace(hour=0, minute=1, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (next_day - now).total_seconds()
        
        print(f"[DAILY INCOME] Ждем до {next_day.strftime('%d.%m.%Y %H:%M:%S')} ({wait_seconds:.0f} секунд)")
        
        # Ждем до 00:01 следующего дня
        await asyncio.sleep(wait_seconds)
        
        try:
            print(f"[DAILY INCOME] Начинаем начисление дохода...")
            
            # Получаем всех игроков, у которых есть фитнес-залы
            players_with_halls = await get_all_players_with_halls()
            
            total_income_distributed = 0
            total_players_received = 0
            
            for player in players_with_halls:
                user_id = player["user_id"]
                fitness_halls = player["fitness_halls"]
                
                if fitness_halls > 0:
                    # Рассчитываем доход
                    daily_income = fitness_halls * DAILY_HALL_INCOME
                    
                    # Начисляем доход
                    success = await add_daily_fitness_hall_income(
                        user_id, 
                        daily_income, 
                        f"Ежедневный доход с {fitness_halls} фитнес-залов"
                    )
                    
                    if success:
                        total_income_distributed += daily_income
                        total_players_received += 1
                        
                        # Отправляем уведомление игроку о полученном доходе
                        try:
                            await send_daily_income_notification(user_id, fitness_halls, daily_income)
                        except Exception as e:
                            print(f"[DAILY INCOME] Ошибка отправки уведомления игроку {user_id}: {e}")
            
            print(f"[DAILY INCOME] Начисление завершено!")
            print(f"[DAILY INCOME] Получили доход: {total_players_received} игроков")
            print(f"[DAILY INCOME] Распределено: {format_number(total_income_distributed)} монет")
            
        except Exception as e:
            print(f"[DAILY INCOME] Критическая ошибка при начислении дохода: {e}")


async def send_daily_income_notification(user_id: int, halls_count: int, income: int):
    """Отправить уведомление игроку о полученном доходе"""
    try:
        api = API(token=settings.VK_TOKEN)
        
        message = (
            f"💰 ЕЖЕДНЕВНЫЙ ДОХОД С ФИТНЕС-ЗАЛОВ\n\n"
            f"Вам начислен ежедневный доход с ваших фитнес-залов!\n\n"
            f"🏦 Количество залов: {format_number(halls_count)}\n"
            f"💵 Доход за день: {format_number(income)} монет\n"
            f"📊 (по {DAILY_HALL_INCOME} монет за каждый зал)\n\n"
            f"🕐 Следующее начисление: завтра в 00:01\n\n"
            f"💡 Хотите больше дохода?\n"
            f"Покупайте больше фитнес-залов командой:\n"
            f"Купить зал [количество]"
        )
        
        await api.messages.send(
            peer_id=user_id,
            message=message,
            random_id=0
        )
    except Exception as e:
        print(f"[NOTIFICATION] Ошибка отправки уведомления игроку {user_id}: {e}")


@daily_income_labeler.message(text=["доход залы", "/доход залы", "статистика дохода", "/статистика дохода"])
async def daily_income_stats_handler(message: Message):
    """Показать статистику ежедневного дохода с фитнес-залов"""
    user_id = message.from_id
    player = await get_player(user_id)
    
    if not player:
        return "❌ Игрок не найден"
    
    fitness_halls = await get_player_fitness_halls(user_id)
    daily_income = fitness_halls * DAILY_HALL_INCOME
    
    # Получаем статистику из БД
    stats = await get_daily_income_stats(user_id)
    
    total_received = stats.get("total_received", 0) if stats else 0
    last_received = stats.get("last_received_date", None) if stats else None
    
    if last_received:
        last_date = datetime.fromisoformat(last_received).strftime("%d.%m.%Y %H:%M")
        last_received_text = f"📅 Последнее начисление: {last_date}"
    else:
        last_received_text = "📅 Вы еще не получали ежедневный доход"
    
    income_text = (
        f"💰 ЕЖЕДНЕВНЫЙ ДОХОД С ФИТНЕС-ЗАЛОВ\n\n"
        f"🏦 У вас фитнес-залов: {format_number(fitness_halls)}\n"
        f"💵 Доход в день: {format_number(daily_income)} монет\n"
        f"📊 (по {DAILY_HALL_INCOME} монет за зал)\n\n"
        f"⏰ Время начисления: каждый день в 00:01\n\n"
        f"📈 Ваша статистика:\n"
        f"💸 Всего получено: {format_number(total_received)} монет\n"
        f"{last_received_text}\n\n"
        f"💡 Увеличьте доход:\n"
        f"Покупайте больше залов командой:\n"
        f"Купить зал [количество]"
    )
    
    await message.answer(income_text)


# ======================
# ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ
# ======================

async def init_daily_income_system():
    """Инициализировать систему ежедневных выплат"""
    # Запускаем фоновую задачу для ежедневных выплат
    asyncio.create_task(daily_income_task())
    print("✅ Система ежедневных выплат инициализирована")
    
    # Проверяем время до следующего начисления
    now = datetime.now()
    next_day = now.replace(hour=0, minute=1, second=0, microsecond=0) + timedelta(days=1)
    wait_hours = (next_day - now).total_seconds() / 3600
    print(f"[DAILY INCOME] Следующее начисление через: {wait_hours:.1f} часов")
