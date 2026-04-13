# ==========================================================
# 🧠 AI-LIKE WEIGHTED SCORING ENGINE v6.1
# ==========================================================

def calculate_score(context):

    score = 0
    details = []

    # ======================================================
    # 🔥 TREND HTF (BOBOT 8)
    # ======================================================
    trend = context.get("htf_trend")

    if trend in ["BULLISH", "BEARISH"]:
        score += 8
        details.append("Trend")

    # ======================================================
    # 🔥 LIQUIDITY SWEEP (BOBOT 7)
    # ======================================================
    if context.get("liquidity_sweep"):
        score += 7
        details.append("Liquidity")

    # ======================================================
    # 🔥 PREMIUM / DISCOUNT (BOBOT 5)
    # ======================================================
    pd_zone = context.get("pd_zone")

    if pd_zone in ["PREMIUM", "DISCOUNT"]:
        score += 5
        details.append("PD")

    # ======================================================
    # 🔥 STRUCTURE CHANGE (BOBOT 5)
    # ======================================================
    if context.get("structure_break"):
        score += 5
        details.append("Structure")

    return {
        "score": score,
        "max_score": 25,
        "probability": (score / 25) * 100,
        "details": details
    }
