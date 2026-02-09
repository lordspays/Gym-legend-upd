from datetime import datetime

from bot.utils import format_number
from vkbottle.bot import BotLabeler, Message

from bot.db import count_promo_uses, get_player, get_promo_info, use_promo_code
from bot.services.users import is_admin

promocode_labeler = BotLabeler()
promocode_labeler.vbml_ignore_case = True


@promocode_labeler.message(text=["промоинфо", "/промоинфо"])
async def promo_info_empty_handler(message: Message, code: str):
    """Информация о промокоде"""
    return "❌ Укажите код промокода!\n📝 Использование: /промоинфо [код]"


@promocode_labeler.message(text=["промоинфо <code>", "/промоинфо <code>"])
async def promo_info_handler(message: Message, code: str):
    """Информация о промокоде"""
    code = code.upper()
    promo_info = await get_promo_info(code)

    if not promo_info:
        return f"❌ Промокод {code} не найден!"

    # Получаем информацию о создателе
    creator = await get_player(promo_info["created_by"])
    creator_id = promo_info["created_by"]
    
    # Форматируем кликабельное имя создателя
    if creator:
        creator_name = f"[id{creator_id}|{creator['username']}]"
    else:
        creator_name = f"[id{creator_id}|ID: {creator_id}]"

    # Форматируем дату создания
    created_at = datetime.fromisoformat(promo_info["created_at"]).strftime(
        "%d.%m.%Y %H:%M"
    )

    status = "✅ Активен" if promo_info["is_active"] == 1 else "❌ Неактивен"

    info_text = (
        f"🎫 Информация о промокоде - {promo_info['code']}\n\n"
        f"📑 Статус: {status}\n\n"
        f"🎯 Использования:\n"
        f"🔹 Всего: {promo_info['uses_total']}\n"
        f"🔹 Осталось: {promo_info['uses_left']}\n"
        f"🔹 Использовано: {promo_info['uses_total'] - promo_info['uses_left']}\n\n"
        f"💲 Награда: {format_number(promo_info['reward_amount'])} {promo_info['reward_type']}\n\n"
        f"👤 Создатель: {creator_name}\n"
        f"📅 Создан: {created_at}\n\n"
        f"💡 Для активации: Промо {promo_info['code']}"
    )

    # Если администратор - показываем дополнительную информацию
    if await is_admin(message.from_id):
        total_uses = await count_promo_uses(code)
        info_text += f"\n\n📊 Статистика (только для админов):\n👥 Всего активаций: {total_uses}"

    return info_text


@promocode_labeler.message(text=["промо", "/промо"])
async def use_promo_empty_handler(message: Message, code: str):
    """Использование промокода"""
    return "❌ Укажите код промокода!\n📝 Использование: /промо [код]"


@promocode_labeler.message(text=["промо <code>", "/промо <code>"])
async def use_promo_handler(message: Message, code: str):
    """Использование промокода"""
    code = code.upper()
    result = await use_promo_code(message.from_id, code)

    if result["success"]:
        player = await get_player(message.from_id)
        new_balance = player["balance"]
        
        return (
            f"🎉 Промокод активирован!\n\n"
            f"🔑 Код: {code}\n"
            f"🎁 Получено: {format_number(result['reward_amount'])} монет\n"
            f"📈 Новый баланс: {format_number(new_balance)} монет\n\n"
            f"✅ Награда успешно зачислена на ваш счет!"
        )
    else:
        return (
            f"❌ Не удалось активировать промокод\n\n"
            f"🔑 Код: {code}\n"
            f"📝 Причина: {result['error']}"
        )
