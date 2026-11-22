import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DB_URI = os.getenv('DB_URI')


def preprocess_and_load(csv_path: str):

    if not DB_URI:
        raise ValueError("Не задано DB_URI.")

    df = pd.read_csv(csv_path)

    logging.info(f"Завантажено рядків : {len(df)}")

    if df.empty:
        logging.warning("CSV-файл пустий.")
        return

    df = df.drop_duplicates(
        subset=['post_id'],
        keep='first'
    ).copy()

    df['title'] = df['title'].fillna('').str.strip()

    df['score'] = (
        df['raw_score'].astype('string')
        .str.extract(r'(\d+)')[0]
        .pipe(pd.to_numeric, errors='coerce')
        .fillna(0)
        .astype(int)
    )

    df['comments'] = (
        df['raw_comments'].astype('string')
        .str.extract(r'(\d+)')[0]
        .pipe(pd.to_numeric, errors='coerce')
        .fillna(0)
        .astype(int)
    )

    df['domain'] = df['domain'].fillna('news.ycombinator.com')
    df['author'] = df['author'].fillna('unknown')

    df['published_at'] = pd.to_datetime(
        df['raw_age'],
        errors='coerce',
        utc=True
    )

    df = df.dropna(subset=['published_at']).copy()

    if df.empty:
        logging.warning("0 записів після обробки.")
        return

    q1 = df['score'].quantile(0.25)
    q3 = df['score'].quantile(0.75)

    iqr = q3 - q1

    upper_bound = q3 + 1.5 * iqr

    df['is_viral_outlier'] = df['score'] > upper_bound

    logging.info(
        f"IQR : {upper_bound:.1f}. "
        f"Кількість аномалій : {df['is_viral_outlier'].sum()}"
    )

    keywords_pattern = (
        r'\b(?:ai|security|cyber|data|government|policy|'
        r'china|russia|eu|nato|privacy)\b'
    )

    df['is_policy_tech'] = (
        df['title']
        .str.lower()
        .str.contains(keywords_pattern, regex=True, na=False)
    )

    df['discussion_ratio'] = np.where(
        df['score'] > 0,
        df['comments'] / df['score'],
        np.nan
    )

    df['discussion_ratio'] = df['discussion_ratio'].round(2)

    df['score_scaled'] = np.nan
    df['comments_scaled'] = np.nan

    scaler = MinMaxScaler()

    normal_mask = ~df['is_viral_outlier']

    if normal_mask.sum() > 0:

        df.loc[
            normal_mask,
            ['score_scaled', 'comments_scaled']
        ] = scaler.fit_transform(
            df.loc[
                normal_mask,
                ['score', 'comments']
            ]
        )

    unique_domains = df['domain'].drop_duplicates().tolist()

    domains_df = pd.DataFrame({
        'domain_id': range(1, len(unique_domains) + 1),
        'domain_name': unique_domains
    })

    df = df.merge(
        domains_df,
        left_on='domain',
        right_on='domain_name',
        how='left'
    )

    clean_articles_df = df[[
        'post_id',
        'domain_id',
        'title',
        'author',
        'score',
        'comments',
        'published_at',
        'is_viral_outlier',
        'is_policy_tech',
        'discussion_ratio',
        'score_scaled',
        'comments_scaled'
    ]].copy()

    engine = create_engine(DB_URI)

    with engine.begin() as conn:

        conn.execute(text(
            "DROP TABLE IF EXISTS hn_articles;"
        ))

        conn.execute(text(
            "DROP TABLE IF EXISTS domains;"
        ))

        domains_df.to_sql(
            'domains',
            con=conn,
            if_exists='fail',
            index=False
        )

        clean_articles_df.to_sql(
            'hn_articles',
            con=conn,
            if_exists='fail',
            index=False
        )

        conn.execute(text(
            "ALTER TABLE domains "
            "ADD PRIMARY KEY (domain_id);"
        ))

        conn.execute(text(
            "ALTER TABLE hn_articles "
            "ADD PRIMARY KEY (post_id);"
        ))

        conn.execute(text("""
            ALTER TABLE hn_articles
            ADD CONSTRAINT fk_domain
            FOREIGN KEY (domain_id)
            REFERENCES domains(domain_id);
        """))

    engine.dispose()

    logging.info(
        "Дані успішно очищено та завантажено до PostgreSQL."
    )

    logging.info(
        f"Завантажено статей : {len(clean_articles_df)}."
    )


if __name__ == "__main__":
    preprocess_and_load('raw_hn_news.csv')
