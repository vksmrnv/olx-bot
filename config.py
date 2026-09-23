# =====================================================
#  НАСТРОЙКИ. Меняйте только этот файл.
# =====================================================

# Ваши поиски: ("Название", "ссылка с OLX").
# Добавить поиск: скопируйте строку целиком, вставьте ниже, поменяйте название и ссылку.
# Удалить: сотрите строку.
SEARCHES = [
    ("Полтавская · до 350 000 грн", "https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/pol/?currency=UAH&min_id=935691472&reason=observed_search&search%5Bfilter_float_price%3Ato%5D=350000&search%5Border%5D=relevance%3Adesc"),
    ("Черкасская · до 350 000 грн", "https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/chk/?currency=UAH&min_id=935689115&reason=observed_search&search%5Bfilter_float_price%3Ato%5D=350000&search%5Border%5D=relevance%3Adesc"),
    ("Кировоградская · до 350 000 грн", "https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/kir/?currency=UAH&min_id=935713499&reason=observed_search&search%5Bfilter_float_price%3Ato%5D=350000&search%5Border%5D=relevance%3Adesc"),
    ("Винницкая · до 350 000 грн", "https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/vin/?currency=UAH&min_id=935576009&reason=observed_search&search%5Bfilter_float_price%3Ato%5D=350000&search%5Border%5D=relevance%3Adesc"),
    ("Полтавская · до 6 500 $", "https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/pol/?currency=USD&min_id=935686583&reason=observed_search&search%5Bfilter_float_price%3Ato%5D=6500&search%5Border%5D=relevance%3Adesc"),
    ("Винницкая · до 6 500 $", "https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/vin/?currency=USD&min_id=935576009&reason=observed_search&search%5Bfilter_float_price%3Ato%5D=6500&search%5Border%5D=relevance%3Adesc"),
    ("Кировоградская · до 6 500 $", "https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/kir/?currency=USD&min_id=935713499&reason=observed_search&search%5Bfilter_float_price%3Ato%5D=6500&search%5Border%5D=relevance%3Adesc"),
    ("Черкасская · до 6 500 $", "https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/chk/?currency=USD&min_id=935689115&reason=observed_search&search%5Bfilter_float_price%3Ato%5D=6500&search%5Border%5D=relevance%3Adesc"),
]

# С какого количества баллов ставить 🔥
HOT_SCORE = 15

# При самом первом запуске: сколько лучших из уже висящих объявлений прислать
FIRST_RUN_TOP = 50

# Максимум сообщений за одну проверку (защита от спама)
MAX_PER_RUN = 30

# Язык вопросов продавцу: "ru" или "uk"
QUESTION_LANG = "ua"
