import os
import logging

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)

DB_URI = os.getenv("DB_URI")

if not DB_URI:
    raise ValueError("Змінна DB_URI не задана.")

engine = create_engine(DB_URI)

query = text("""
    SELECT
        a.post_id,
        a.title,
        d.domain_name,
        a.score,
        a.comments,
        a.published_at,
        a.is_viral_outlier,
        a.is_policy_tech,
        a.discussion_ratio
    FROM hn_articles a
    LEFT JOIN domains d
        ON a.domain_id = d.domain_id
""")

with engine.connect() as connection:
    df = pd.read_sql(query, connection)

engine.dispose()

if df.empty:
    raise ValueError("Немає публікацій в БД.")

logging.info(f"Завантажено публікацій: {len(df)}")

df["published_at"] = pd.to_datetime(
    df["published_at"], errors="coerce", utc=True
)

numeric_columns = [
    "score",
    "comments",
    "discussion_ratio"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column], errors="coerce"
    )

df["domain_name"] = df["domain_name"].fillna("Unknown")
df["is_viral_outlier"] = df["is_viral_outlier"].fillna(False)

df["category"] = np.where(
    df["is_policy_tech"],
    "Policy / Security / AI",
    "General Tech / Other"
)

df["publication_date"] = df["published_at"].dt.date

total_posts = len(df)
total_domains = df["domain_name"].nunique()

avg_score = df["score"].mean()
median_score = df["score"].median()

avg_comments = df["comments"].mean()

outlier_share = (
    df["is_viral_outlier"].mean() * 100
)

print("\n========== HACKER NEWS ANALYTICS ==========")
print(f"Total publications: {total_posts}")
print(f"Unique domains: {total_domains}")
print(f"Average score: {avg_score:.2f}")
print(f"Median score: {median_score:.2f}")
print(f"Average comments: {avg_comments:.2f}")
print(f"Outlier share: {outlier_share:.2f}%")
print("===========================================\n")

fig, axes = plt.subplots(2, 3, figsize=(19, 12))

fig.suptitle(
    "Hacker News — Content Performance Analysis",
    fontsize=19,
    fontweight="bold"
)

top_domains = (
    df.groupby("domain_name")
    .agg(
        articles_count=("post_id", "count"),
        median_score=("score", "median")
    )
    .sort_values("articles_count", ascending=False)
    .head(10)
    .sort_values("articles_count")
)

top_domains["articles_count"].plot(
    kind="barh",
    ax=axes[0, 0]
)

axes[0, 0].set_title("Top 10 Domains by Publications")
axes[0, 0].set_xlabel("Number of publications")
axes[0, 0].set_ylabel("Domain")

category_scores = (
    df.groupby("category")["score"]
    .median()
    .sort_values()
)

category_scores.plot(
    kind="bar",
    ax=axes[0, 1]
)

axes[0, 1].set_title("Median Score by Category")
axes[0, 1].set_xlabel("Category")
axes[0, 1].set_ylabel("Median score")
axes[0, 1].tick_params(axis="x", rotation=15)

valid_scores = df["score"].dropna()

axes[0, 2].hist(
    np.log1p(valid_scores),
    bins=25,
    edgecolor="black"
)

axes[0, 2].set_title("Distribution of Publication Scores")
axes[0, 2].set_xlabel("Log(Score + 1)")
axes[0, 2].set_ylabel("Number of publications")

for category, group in df.groupby("category"):
    axes[1, 0].scatter(
        group["score"] + 1,
        group["comments"] + 1,
        label=category,
        alpha=0.65
    )

axes[1, 0].set_xscale("log")
axes[1, 0].set_yscale("log")

axes[1, 0].set_title("Score vs Comments")
axes[1, 0].set_xlabel("Score (log scale)")
axes[1, 0].set_ylabel("Comments (log scale)")
axes[1, 0].legend(fontsize=8)

domain_engagement = (
    df.groupby("domain_name")
    .agg(
        articles_count=("post_id", "count"),
        avg_discussion_ratio=("discussion_ratio", "mean")
    )
)

domain_engagement = domain_engagement[
    domain_engagement["articles_count"] >= 3
]

top_engagement = (
    domain_engagement
    .sort_values("avg_discussion_ratio")
    .tail(10)
)

top_engagement["avg_discussion_ratio"].plot(
    kind="barh",
    ax=axes[1, 1]
)

axes[1, 1].set_title("Top Domains by Discussion Ratio")
axes[1, 1].set_xlabel("Average comments / score")
axes[1, 1].set_ylabel("Domain")

daily_posts = (
    df.dropna(subset=["publication_date"])
    .groupby("publication_date")
    .size()
)

axes[1, 2].plot(
    daily_posts.index.astype(str),
    daily_posts.values,
    marker="o"
)

axes[1, 2].set_title("Publication Activity Over Time")
axes[1, 2].set_xlabel("Publication date")
axes[1, 2].set_ylabel("Number of publications")
axes[1, 2].tick_params(axis="x", rotation=45)

plt.tight_layout(rect=[0, 0, 1, 0.95])

plt.savefig(
    "hn_analytics_dashboard.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("Dashboard saved: hn_analytics_dashboard.png")
