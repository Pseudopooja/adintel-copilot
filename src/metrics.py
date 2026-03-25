import pandas as pd

def load_data(file_path):
    df = pd.read_csv(file_path)
    return df

def calculate_metrics(df):
    df["CTR"] = df["clicks"] / df["impressions"]
    df["CVR"] = df["conversions"] / df["clicks"]
    df["CPA"] = df["spend"] / df["conversions"]
    df["ROI"] = (df["revenue"] - df["spend"]) / df["spend"]
    return df

def aggregate_campaign_level(df):
    agg_df = df.groupby(
        ["campaign_id", "campaign_name", "channel"],
        as_index=False
    ).agg({
        "impressions": "sum",
        "clicks": "sum",
        "conversions": "sum",
        "spend": "sum",
        "revenue": "sum"
    })

    agg_df["CTR"] = agg_df["clicks"] / agg_df["impressions"]
    agg_df["CVR"] = agg_df["conversions"] / agg_df["clicks"]
    agg_df["CPA"] = agg_df["spend"] / agg_df["conversions"]
    agg_df["ROI"] = (agg_df["revenue"] - agg_df["spend"]) / agg_df["spend"]

    return agg_df.round(4)