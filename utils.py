import re

def format_number(number):
    """Форматирует число с разделителями тысяч"""
    return f"{number:,}".replace(",", ".")


def pointer_to_screen_name(user_pointer: str) -> str | None:
    # Remove leading 'vk.com/' from the URL
    if user_pointer.startswith('vk.com/'):
        user_pointer = user_pointer[6:]

    # Match VK links in the format https://vk.com/idXXX or vk.com/idXXX
    vk_link_match = re.match(r'https?:\/\/(?:www\.)?vk\.com\/(.*?)(?:\/|$)', user_pointer)

    # If it's a VK link, extract the ID
    if vk_link_match:
        return vk_link_match.group(1)

    try:
        # Match mentions in the format [idXXX|@mention]
        mention_match = user_pointer.split("|")[0][1:].replace("id", "")
        return mention_match
    except Exception:
        return


def parse_amount_string(amount_str: str) -> int:
    """
    Парсит строку с суммой в различных форматах
    Поддерживает: обычные числа, K (тысячи), KK (миллионы), KKK (миллиарды)
    """
    amount_str = amount_str.strip().lower()
    
    # Убираем лишние символы
    amount_str = re.sub(r'[^\d\.\,кk]', '', amount_str)
    
    # Если строка пустая после очистки
    if not amount_str:
        raise ValueError("Пустая сумма")
    
    # Заменяем запятые на точки
    amount_str = amount_str.replace(',', '.')
    
    # Определяем множитель
    multiplier = 1
    
    if 'ккк' in amount_str or 'kkk' in amount_str:
        multiplier = 1000000000  # миллиарды
        amount_str = amount_str.replace('ккк', '').replace('kkk', '')
    elif 'кк' in amount_str or 'kk' in amount_str:
        multiplier = 1000000  # миллионы
        amount_str = amount_str.replace('кк', '').replace('kk', '')
    elif 'к' in amount_str or 'k' in amount_str:
        multiplier = 1000  # тысячи
        amount_str = amount_str.replace('к', '').replace('k', '')
    
    # Парсим числовую часть
    try:
        if amount_str == '':
            number = 1  # Если просто "к" без числа, считаем как 1к
        else:
            number = float(amount_str)
    except ValueError:
        raise ValueError(f"Не удалось распознать числовую часть: {amount_str}")
    
    # Применяем множитель и возвращаем целое число
    result = int(number * multiplier)
    
    # Проверяем на разумные пределы
    if result <= 0:
        raise ValueError("Сумма должна быть положительной")
    
    return result


# Для обратной совместимости
def convert_kkk_to_number(amount_str: str) -> int:
    """Алиас для parse_amount_string"""
    return parse_amount_string(amount_str)
