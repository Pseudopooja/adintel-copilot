from metrics import load_data, calculate_metrics, aggregate_campaign_level
from prompt_builder import build_compact_text, build_prompt
from groq_client import generate_response
# Load and prepare data
df = load_data("../data/synthetic_campaigns.csv")
df = calculate_metrics(df)
agg = aggregate_campaign_level(df)

# Build prompt
compact_text = build_compact_text(agg)
prompt = build_prompt(compact_text)

print("=== PROMPT ===")
print(prompt)

# Call Groq
response = generate_response(prompt)

print("\n=== AI RESPONSE ===")
print(response)
