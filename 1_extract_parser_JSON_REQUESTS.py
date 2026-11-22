import requests
import pandas as pd
import time
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BASE_URL = "https://hacker-news.firebaseio.com/v0/"

def scrape_hacker_news(limit=100, output_path='raw_hn_news.csv'):
    records = []

    try:
        response = requests.get(
            BASE_URL + "topstories.json",
            timeout=15
        )
        response.raise_for_status()
        story_ids = response.json()[:limit]

    except requests.RequestException as e:
        logging.error(f"Помилка отримання списку публікацій : {e}")
        return

    for story_id in story_ids:
        try:
            response = requests.get(
                f"{BASE_URL}item/{story_id}.json",
                timeout=15
            )
            response.raise_for_status()
            item = response.json()

            if not item or item.get('type') != 'story':
                continue

            records.append({
                'post_id': item.get('id'),
                'title': item.get('title'),
                'domain': item.get('url', '').split('/')[2]
                          if item.get('url', '').startswith(('http://', 'https://'))
                          else 'news.ycombinator.com',
                'author': item.get('by'),
                'raw_score': str(item.get('score', 0)),
                'raw_comments': str(item.get('descendants', 0)),
                'raw_age': datetime.fromtimestamp(
                    item['time'], tz=timezone.utc
                ).isoformat() if item.get('time') else None,
                'url': item.get('url')
            })

            time.sleep(0.1)

        except (requests.RequestException, ValueError, TypeError) as e:
            logging.warning(f"Помилка публікації {story_id}: {e}")
            continue

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    logging.info(f"Зібрано публікацій: {len(df)}")
    logging.info(f"Файл збережено: {output_path}")


if __name__ == "__main__":
    scrape_hacker_news(limit=500)
