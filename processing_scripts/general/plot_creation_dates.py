# uv run -m general.plot_creation_dates

import pandas as pd
import matplotlib.pyplot as plt
from interact_with_neo4j import load_artifact_creation_dates


# Load data
df = load_artifact_creation_dates()

df["artifact_creation_date"] = pd.to_datetime(
    df["artifact_creation_date"]
)

df["year_month"] = df["artifact_creation_date"].dt.to_period("M")
monthly_counts = (
    df.groupby("year_month")
    .size()
    .sort_index()
)
monthly_counts.index = monthly_counts.index.to_timestamp() # type: ignore

# Plot Bar chart of artifact creation by month

plt.figure(figsize=(10, 5))

labels = monthly_counts.index.astype(str)
plt.bar(labels, monthly_counts.values) # type: ignore

plt.title("Artifact Creation by Month")
plt.xlabel("Month")
plt.ylabel("Number of Artifacts")
plt.xticks(rotation=45)
plt.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.savefig("./general/artifact_creation_by_month.png")

# Plot distribution of artifact ages (boxplot)

df["artifact_creation_date"] = pd.to_datetime(
    df["artifact_creation_date"]
)

today = pd.Timestamp.now()

# Compute age in days
df["artifact_age_days"] = (
    today - df["artifact_creation_date"]
).dt.days

ages = df["artifact_age_days"]

plt.figure(figsize=(6, 6))
plt.boxplot(ages, vert=True)

plt.title("Distribution of Artifact Age")
plt.ylabel("Age (days) as of " + today.strftime("%Y-%m-%d"))
plt.grid(axis="y", alpha=0.3)


plt.tight_layout()
plt.savefig("./general/artifact_age_distribution.png")