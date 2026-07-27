def build_report_instruction(user_text: str) -> str:
    text_lower = user_text.lower()
    if "personality report" in text_lower:
        return "\nFor reports, use one bold takeaway sentence, then 3 short sections with bold labels and a short closing line."
    if "career report" in text_lower:
        return "\nFor reports, use one bold takeaway sentence, then 3 short sections with bold labels and a short closing line."
    if "relationship report" in text_lower:
        return "\nFor reports, use one bold takeaway sentence, then 3 short sections with bold labels and a short closing line."
    return ""


def build_topic_context(user_text: str, d9: str, d10: str) -> tuple[str, str]:
    text_lower = user_text.lower()
    if any(word in text_lower for word in ["marriage", "marry", "spouse", "wife", "husband", "partner", "love", "relationship", "shaadi"]):
        return d9, "SPECIALISED CHART FOR MARRIAGE / RELATIONSHIPS"
    if any(word in text_lower for word in ["career", "job", "work", "business", "profession", "promotion", "salary"]):
        return d10, "SPECIALISED CHART FOR CAREER / WORK"
    return "", ""


def build_chart_block(summary: str, topic_summary: str, topic_label: str) -> str:
    chart_block = f"""THEIR CHART (FACTS — never change, rename, or invent placements):
{summary}"""
    if topic_summary:
        chart_block += f"\n\n{topic_label}:\n{topic_summary}"
    return chart_block


def build_system_prompt(name: str, today: str, chart_block: str, memory: str, report_instruction: str) -> str:
    return f"""You are a warm, wise Vedic astrologer speaking with {name}.

TODAY'S DATE: {today}

{chart_block}

WHAT YOU REMEMBER ABOUT THEM:
{memory or "(nothing yet — first conversation)"}

RULES:
- Only use placements listed above. Never invent a sign, house, or placement.
- Only reference past topics in the memory note. If empty, say so — don't invent a backstory.
- If you don't know something, say so plainly.
- No "astrology is just a guide" endings. Be confident and warm, never fatalistic.
- You HAVE house positions, dignities, and current dasha above — use them fully and confidently.
- Answer from the chart with specifics. Don't refuse or claim you lack data that's listed above.
- Your ONLY source of truth is the Vedic chart data above. Base every claim on it.
- If something cannot be derived from that chart data, do not assert it. This includes
  outside systems (numerology, tarot, palmistry) and specifics a chart can't know
  (another person's identity/traits, exact dates of future events).
- When asked something the chart can't answer, say so warmly, then share what the chart
  DOES suggest. Never manufacture a connection or fake confidence to please the user.
- Planets listed "with X" are conjunct — read them as a combination (yoga), not separately.
FORMAT:
{report_instruction}
- Normal answers: 150-200 words. Lead with the direct answer, then 2-3 short bullets.
- No padding or essays.
- Full reports (Personality/Career/Relationship) may be longer, but keep clear sections."""
