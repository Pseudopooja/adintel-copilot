import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

campaigns = [
    {"campaign_id": "CAMP_101", "campaign_name": "Spring Search Boost", "channel": "Search"},
    {"campaign_id": "CAMP_102", "campaign_name": "Brand Display Push", "channel": "Display"},
    {"campaign_id": "CAMP_103", "campaign_name": "Retargeting Revival", "channel": "Social"},
    {"campaign_id": "CAMP_104", "campaign_name": "Prospecting Test", "channel": "Search"},
    {"campaign_id": "CAMP_105", "campaign_name": "Email Lead Funnel", "channel": "Email"},
    {"campaign_id": "CAMP_106", "campaign_name": "Video Awareness Sprint", "channel": "Video"},
]

start_date = datetime(2026, 3, 1)
rows = []

for campaign in campaigns:
    for i in range(4):
        date = start_date + timedelta(days=i * 5)

        impressions = random.randint(4000, 14000)
        ctr_rate = random.uniform(0.015, 0.08)
        clicks = max(1, int(impressions * ctr_rate))

        cvr_rate = random.uniform(0.01, 0.12)
        conversions = max(1, int(clicks * cvr_rate))

        spend = round(random.uniform(150, 1200), 2)
        revenue_per_conversion = random.randint(35, 95)
        revenue = round(conversions * revenue_per_conversion, 2)

        rows.append({
            "date": date.strftime("%Y-%m-%d"),
            "campaign_id": campaign["campaign_id"],
            "campaign_name": campaign["campaign_name"],
            "channel": campaign["channel"],
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "spend": spend,
            "revenue": revenue
        })

df = pd.DataFrame(rows)

df.loc[df["campaign_id"] == "CAMP_101", "revenue"] = (
    df.loc[df["campaign_id"] == "CAMP_101", "revenue"] * 1.35
).round(2)

df.loc[df["campaign_id"] == "CAMP_103", "clicks"] = (
    df.loc[df["campaign_id"] == "CAMP_103", "clicks"] * 1.2
).astype(int)
df.loc[df["campaign_id"] == "CAMP_103", "conversions"] = (
    df.loc[df["campaign_id"] == "CAMP_103", "conversions"] * 0.55
).astype(int).clip(lower=1)

df.loc[df["campaign_id"] == "CAMP_104", "spend"] = (
    df.loc[df["campaign_id"] == "CAMP_104", "spend"] * 1.4
).round(2)

df.loc[df["campaign_id"] == "CAMP_105", "revenue"] = (
    df.loc[df["campaign_id"] == "CAMP_105", "revenue"] * 0.9
).round(2)

output_dir = Path("data")
output_dir.mkdir(exist_ok=True)

output_file = output_dir / "synthetic_campaigns.csv"
df.to_csv(output_file, index=False)

print(f"Dataset created successfully at: {output_file}")
print("\nPreview:")
print(df.head(10))
print(f"\nTotal rows: {len(df)}")