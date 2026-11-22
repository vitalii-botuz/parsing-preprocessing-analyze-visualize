from bs4 import BeautifulSoup
import pandas as pd

# 1. Имитируем "сырой" HTML-код, который мы скачали с новостного сайта через requests
raw_html = """
<div class="news-feed">
    <article class="post">
        <h2 class="title">Заседание NATO StratCom в Риге</h2>
        <span class="author">Иван Петров</span>
        <span class="views">15400</span>
        <time class="date">2026-11-20</time>
    </article>
    <article class="post">
        <h2 class="title">Новый отчет о дезинформации в соцсетях</h2>
        <span class="author">Анна Коваленко</span>
        <span class="views">8900</span>
        <time class="date">2026-11-21</time>
    </article>
    <article class="post">
        <h2 class="title">Анализ фейков за неделю</h2>
        <!-- Обрати внимание: здесь парсер не нашел автора (будет пропуск!) -->
        <span class="views"></span>
        <time class="date">2026-11-21</time>
    </article>
</div>
"""

soup = BeautifulSoup(raw_html, 'html.parser')

# 3. Создаем пустой список, куда будем складывать собранные данные
parsed_data = []

# Находим все карточки статей на странице и проходим по ним циклом
articles = soup.find_all('article', class_='post')

for article in articles:
    # Безопасно извлекаем данные (если тега нет, ставим None)
    title_tag = article.find('h2', class_='title')
    author_tag = article.find('span', class_='author')
    views_tag = article.find('span', class_='views')
    date_tag = article.find('time', class_='date')

    # Собираем одну статью в аккуратный питоновский словарь
    row = {
        'title': title_tag.text.strip() if title_tag else None,
        'author': author_tag.text.strip() if author_tag else None,
        'views': views_tag.text.strip() if views_tag else None,
        'pub_date': date_tag.text.strip() if date_tag else None,
    }

    # Добавляем словарь в наш общий список
    parsed_data.append(row)

# 4. МАГИЯ КОНВЕРТАЦИИ: Передаем список словарей в Pandas
df = pd.DataFrame(parsed_data)

# Выводим результат и проверяем типы данных
print("--- Итоговый DataFrame ---")
print(df)
print("\n--- Типы данных до очистки ---")
print(df.dtypes)
