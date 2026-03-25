def build_compact_text(df):
    lines = []

    for _, row in df.iterrows():
        line = (
            f"{row['campaign_name']} | "
            f"channel={row['channel']} | "
            f"CTR={row['CTR']:.2%} | "
            f"CVR={row['CVR']:.2%} | "
            f"CPA={row['CPA']:.2f} | "
            f"ROI={row['ROI']:.2f}"
        )
        lines.append(line)

    return "\n".join(lines)

def build_prompt(compact_text):
    return f"""
You are AdIntel Copilot.

Below is campaign data:

{compact_text}

Simulate a realistic business discussion between exactly 3 speakers:
Growth Marketer, Finance Analyst, and Risk Analyst.

STRICT RULES:
- Do NOT use "AdIntel Copilot" as a speaker
- Every line must start with:
  Growth Marketer:
  Finance Analyst:
  Risk Analyst:
- No bullets inside debate
- No markdown
- EXACTLY 6 dialogue lines TOTAL (STRICT LIMIT)
- STOP immediately after 6 lines
- Each line must be under 20 words
- If a campaign is selected for scale, it cannot be selected for cut/optimize.
- The scale and cut/optimize campaigns must be different.
- Each speaker MUST reference at least one metric (ROI, CPA, CTR, CVR)
- Each line must introduce a NEW point (no repetition)

DEBATE QUALITY RULES:
- Risk Analyst must highlight uncertainty, downside risk, or long-term impact (not just metrics)
- Each line must directly respond to the previous speaker
- At least 1 line must strongly challenge another persona
- Avoid polite filler phrases ("I agree", "valid point")
- Be direct, decisive, and business-focused
- Each persona should maintain a consistent viewpoint
- Mention budget allocation, scaling strategy, or business impact
- The LAST 2 lines must move toward a decision and must seem natural
- The FINAL line must show convergence

CRITICAL:
- Only discuss campaigns provided in input
- Focus on comparing 2–3 campaigns deeply
- Do NOT discuss any hypothetical campaigns or metrics not in the input
- Do NOT make up any data or metrics that are not in the input


Executive Decision MUST:
- Select EXACTLY 1 campaign to scale
- Select EXACTLY 1 campaign to cut/optimize
- AFTER the debate, you MUST output:

Final Strategic Recommendation:
- Scale: choose exactly 1 campaign name from the input
- Cut/Optimize: choose exactly 1 different campaign name from the input
- Give one short reason for each
- Do not repeat campaign names unnecessarily
- Do not say "not the one to cut"
- Be decisive and metric-driven and give clear recommendation with justification
"""