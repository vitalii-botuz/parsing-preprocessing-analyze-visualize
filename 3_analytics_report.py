import os
import pandas as pd
from sqlalchemy import create_engine

DB_URI = os.getenv('DB_URI')


def run_analysis():

    if not DB_URI:
        raise ValueError("Не задано змінну оточення DB_URI.")

    engine = create_engine(DB_URI)

    try:

        print("=== 1 ТОП ДЖЕРЕЛ ===")

        sql_query = """
        SELECT
            d.domain_name,
            COUNT(a.post_id) AS articles_count,
            SUM(a.score) AS total_score,
            ROUND(AVG(a.discussion_ratio)::numeric, 2)
                AS avg_discussion_ratio
        FROM domains d
        LEFT JOIN hn_articles a
            ON d.domain_id = a.domain_id
            AND a.is_viral_outlier = FALSE
        GROUP BY d.domain_name
        HAVING COUNT(a.post_id) >= 2
        ORDER BY total_score DESC
        LIMIT 10;
        """

        top_domains = pd.read_sql(sql_query, con=engine)

        print(top_domains.to_string(index=False))


        print("\n=== 2 СЕРЕДНЄ ТА МЕДІАНА ===")

        df = pd.read_sql(
            "SELECT * FROM hn_articles",
            con=engine
        )

        if df.empty:
            print("Намає відповідних даних.")
            return

        mean_score = df['score'].mean()
        median_score = df['score'].median()

        print(f"Всього статей проаналізовано : {len(df)}")
        print(f"Середній рейтинг (Mean) : {mean_score:.1f}")
        print(f"Медіанний рейтинг (Median) : {median_score:.1f}")

        if mean_score > median_score:
            print(
                "Середнє більше медіани."
                "Це може вказувати на правосторонню асиметрію."
            )
        elif mean_score < median_score:
            print(
                "Медіана більша середнього."
                "Це може вказувати на лівосторонню асиметрію."
            )
        else:
            print("Середнє та медіана співпадають.")

        print("\n=== 3. POLICY & TECH ПРОТИВ ІНШИХ ===")

        topic_summary = df.groupby('is_policy_tech').agg(
            posts_count=('post_id', 'count'),
            median_score=('score', 'median'),
            median_comments=('comments', 'median'),
            avg_discussion_ratio=('discussion_ratio', 'mean')
        ).reset_index()

        topic_summary['category'] = topic_summary['is_policy_tech'].map({
            True: 'Policy / Security / AI',
            False: 'General Tech / Other'
        })

        print(
            topic_summary[
                [
                    'category',
                    'posts_count',
                    'median_score',
                    'median_comments',
                    'avg_discussion_ratio'
                ]
            ].to_string(index=False)
        )

        print("\n=== 4 САМІ ОБГОВОРЮВАНІ СТАТТІ ===")

        controversial = df[
            (df['discussion_ratio'] > 1.0) &
            (df['score'] > 20)
        ].sort_values(
            by='discussion_ratio',
            ascending=False
        )

        print(
            controversial[
                ['title', 'score', 'comments', 'discussion_ratio']
            ].head(5).to_string(index=False)
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    run_analysis()
