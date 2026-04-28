# /// script
# requires-python = "==3.11.*"
# dependencies = [
#   "codewords-client==0.4.6",
#   "fastapi==0.116.1",
#   "httpx==0.28.1",
#   "openai==1.99.7",
# ]
# [tool.env-checker]
# env_vars = [
#   "PORT=8000",
#   "LOGLEVEL=INFO",
#   "CODEWORDS_API_KEY",
#   "CODEWORDS_RUNTIME_URI",
#   "BZZOIRO_API_KEY",
# ]
# ///

import os
import json
from datetime import datetime, timedelta, timezone
from textwrap import dedent

import httpx
from openai import AsyncOpenAI
from codewords_client import logger, run_service
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="DailyBET API", description="AI-powered daily football accumulator engine", version="1.0.0")

BZZ = "https://sports.bzzoiro.com/api"

# ── Models ────────────────────────────────────────────────────

class PickItem(BaseModel):
    match_id: int = Field(default=0, description="Bzzoiro event ID")
    home_team: str = Field(default="", description="Home team name")
    away_team: str = Field(default="", description="Away team name")
    league: str = Field(default="", description="League name")
    kickoff: str = Field(default="", description="Kickoff datetime ISO")
    market: str = Field(default="", description="Betting market type")
    selection: str = Field(default="", description="Pick selection text")
    odds: float = Field(default=0.0, description="Decimal odds")
    confidence: float = Field(default=0.0, description="ML confidence %")
    ml_prob: float = Field(default=0.0, description="ML probability %")
    value_score: float = Field(default=0.0, description="Value score (ML - implied)")
    reasoning: str = Field(default="", description="Analysis reasoning")
    home_logo: str = Field(default="", description="Home team logo URL")
    away_logo: str = Field(default="", description="Away team logo URL")
    league_logo: str = Field(default="", description="League logo URL")

class AccaResult(BaseModel):
    name: str = Field(default="", description="Acca type name")
    icon: str = Field(default="", description="Icon identifier")
    picks: list[PickItem] = Field(default=[], description="List of picks")
    total_odds: float = Field(default=0.0, description="Combined acca odds")
    combined_confidence: float = Field(default=0.0, description="Average confidence")
    description: str = Field(default="", description="Acca description")

class AccaRequest(BaseModel):
    tz: str = Field(default="UTC", description="Timezone")

class AccaResponse(BaseModel):
    date: str = Field(default="", description="Date of accas")
    accas: list[AccaResult] = Field(default=[], description="All acca results")
    total_matches_analyzed: int = Field(default=0, description="Total matches analyzed")
    generated_at: str = Field(default="", description="Generation timestamp")

# ── Bzzoiro Fetchers ──────────────────────────────────────────

def _hdr() -> dict[str, str]:
    """Build auth headers for Bzzoiro API."""
    return {"Authorization": f"Token {os.environ['BZZOIRO_API_KEY']}"}

def _logo(t: str, i: int) -> str:
    """Build logo URL for team/league."""
    return f"https://sports.bzzoiro.com/img/{t}/{i}/" if i else ""

async def fetch_preds(c: httpx.AsyncClient, tz: str) -> list[dict]:
    out = []
    url = f"{BZZ}/predictions/?upcoming=true&tz={tz}"
    for _ in range(12):
        if not url: break
        r = await c.get(url, headers=_hdr(), timeout=20)
        r.raise_for_status()
        d = r.json()
        out.extend(d.get("results", []))
        url = d.get("next")
    return out

async def fetch_events(c: httpx.AsyncClient, df: str, dt: str, tz: str, status: str = "") -> list[dict]:
    out, p = [], {"date_from": df, "date_to": dt, "tz": tz}
    if status: p["status"] = status
    url = f"{BZZ}/events/"
    for _ in range(12):
        if not url: break
        r = await c.get(url, headers=_hdr(), params=p, timeout=20)
        r.raise_for_status()
        d = r.json()
        out.extend(d.get("results", []))
        url = d.get("next")
        p = {}
    return out

# ── Analysis Helpers ──────────────────────────────────────────

def _imp(odds: float | None) -> float:
    """Convert decimal odds to implied probability."""
    return (1.0 / odds) * 100 if odds and odds > 1 else 0.0

def _val(ml: float, odds: float | None) -> float:
    """Calculate value score: ML prob minus implied prob."""
    i = _imp(odds)
    return ml - i if i else 0.0

def _atk(coach: dict | None) -> float:
    """Calculate attack factor from coach profile."""
    if not coach: return 1.0
    f = 1.0
    pr = coach.get("profile", "balanced")
    if pr == "attacking": f += 0.15
    elif pr == "defensive": f -= 0.1
    pi = coach.get("pressing_intensity") or 0.5
    if pi > 0.6: f += 0.05
    st = coach.get("top_styles", [])
    if any(s in st for s in ["high_press", "tiki_taka", "counter_attack"]): f += 0.05
    return max(f, 0.5)

def enrich(pred: dict) -> dict | None:
    """Enrich a prediction with analysis-ready fields."""
    ev = pred.get("event", {})
    if ev.get("status") not in ("notstarted", "not_started"): return None
    if not ev.get("event_date"): return None
    ho = ev.get("home_team_obj", {})
    ao = ev.get("away_team_obj", {})
    lg = ev.get("league", {})
    af = (_atk(ev.get("home_coach")) + _atk(ev.get("away_coach"))) / 2
    xg = (pred.get("expected_home_goals") or 0) + (pred.get("expected_away_goals") or 0)
    return {
        "ev": ev, "mid": ev.get("id", 0),
        "ht": ev.get("home_team", "?"), "at": ev.get("away_team", "?"),
        "lg": lg.get("name", ""), "ko": ev.get("event_date", ""),
        "ph": pred.get("prob_home_win", 0), "pd": pred.get("prob_draw", 0),
        "pa": pred.get("prob_away_win", 0), "pb": pred.get("prob_btts_yes", 0),
        "po": pred.get("prob_over_25", 0), "xg": xg,
        "conf": pred.get("confidence", 0), "pr": pred.get("predicted_result", ""),
        "ms": pred.get("most_likely_score", ""), "fav": pred.get("favorite", ""),
        "fp": pred.get("favorite_prob", 0), "af": af,
        "oh": ev.get("odds_home"), "od": ev.get("odds_draw"), "oa": ev.get("odds_away"),
        "oo": ev.get("odds_over_25"), "ob": ev.get("odds_btts_yes"),
        "hl": _logo("team", ho.get("id", 0)), "al": _logo("team", ao.get("id", 0)),
        "ll": _logo("league", lg.get("id", 0)),
    }

def _pick(m: dict, mkt: str, sel: str, odds: float | None, prob: float, rsn: str) -> PickItem:
    """Build a PickItem from match data."""
    return PickItem(match_id=m["mid"], home_team=m["ht"], away_team=m["at"],
        league=m["lg"], kickoff=m["ko"], market=mkt, selection=sel,
        odds=round(odds or 1.5, 2), confidence=round(prob, 1), ml_prob=round(prob, 1),
        value_score=round(_val(prob, odds), 1), reasoning=rsn,
        home_logo=m["hl"], away_logo=m["al"], league_logo=m["ll"])

def _total(picks: list[PickItem]) -> float:
    """Calculate total accumulator odds."""
    t = 1.0
    for p in picks: t *= p.odds
    return round(t, 2)

def _avg(picks: list[PickItem]) -> float:
    """Calculate average confidence across picks."""
    return round(sum(p.confidence for p in picks) / len(picks), 1) if picks else 0

# ── Acca Builders ─────────────────────────────────────────────

def acca_day(ms: list[dict]) -> AccaResult:
    """Build Acca of the Day: 3-5 mixed market picks with highest confidence."""
    sc = []
    for m in ms:
        bm, bs, bo, bp, br = "", "", 0.0, 0.0, ""
        if m["fav"] == "H" and m["ph"] > 48:
            bm, bs, bo, bp = "1X2", f"{m['ht']} Win", m["oh"] or 1.5, m["ph"]
            br = f"Home fav {m['ph']:.0f}% ML"
        elif m["fav"] == "A" and m["pa"] > 48:
            bm, bs, bo, bp = "1X2", f"{m['at']} Win", m["oa"] or 1.5, m["pa"]
            br = f"Away fav {m['pa']:.0f}% ML"
        if m["po"] > bp and m["po"] > 52:
            bm, bs, bo, bp = "Over/Under", "Over 2.5", m["oo"] or 1.8, m["po"]
            br = f"xG={m['xg']:.1f}"
        if m["pb"] > bp and m["pb"] > 52:
            bm, bs, bo, bp = "BTTS", "BTTS Yes", m["ob"] or 1.7, m["pb"]
            br = f"BTTS {m['pb']:.0f}%"
        if bm:
            s = bp * m["af"] + _val(bp, bo) * 0.3
            sc.append((s, m, bm, bs, bo, bp, br))
    sc.sort(key=lambda x: x[0], reverse=True)
    seen, picks = set(), []
    for s, m, mk, sl, od, pr, rn in sc:
        if m["mid"] in seen: continue
        seen.add(m["mid"])
        picks.append(_pick(m, mk, sl, od, pr, rn))
        if len(picks) >= 5: break
    return AccaResult(name="Acca of the Day", icon="trophy", picks=picks,
        total_odds=_total(picks), combined_confidence=_avg(picks),
        description=f"{len(picks)}-fold mixed accumulator — AI's top picks")

def acca_btts_o25(ms: list[dict]) -> AccaResult:
    """Build BTTS + Over 2.5 acca: top 3 games for goals."""
    sc = []
    for m in ms:
        if m["pb"] < 30 or m["po"] < 30: continue
        cb = (m["pb"] / 100) * (m["po"] / 100) * 100
        s = cb * m["af"] + m["xg"] * 5
        sc.append((s, m, cb))
    sc.sort(key=lambda x: x[0], reverse=True)
    picks = []
    for s, m, cb in sc[:3]:
        co = (m["ob"] or 1.7) * 0.5 + (m["oo"] or 1.8) * 0.5 + 0.5
        picks.append(_pick(m, "BTTS+O2.5", "BTTS Yes & Over 2.5", co, cb,
            f"BTTS {m['pb']:.0f}% + O2.5 {m['po']:.0f}% — xG {m['xg']:.1f}"))
    return AccaResult(name="BTTS + Over 2.5", icon="flame", picks=picks,
        total_odds=_total(picks), combined_confidence=_avg(picks),
        description="Top 3 games for both teams scoring AND 3+ goals")

def acca_win_btts(ms: list[dict]) -> AccaResult:
    """Build WIN + BTTS acca: top 3 games for favorite win plus both scoring."""
    sc = []
    for m in ms:
        fp = max(m["ph"], m["pa"])
        if fp < 38 or m["pb"] < 25: continue
        cb = (fp / 100) * (m["pb"] / 100) * 100
        ft = m["ht"] if m["ph"] >= m["pa"] else m["at"]
        fo = m["oh"] if m["ph"] >= m["pa"] else m["oa"]
        s = cb * m["af"]
        sc.append((s, m, cb, ft, fo))
    sc.sort(key=lambda x: x[0], reverse=True)
    picks = []
    for s, m, cb, ft, fo in sc[:3]:
        co = (fo or 1.5) + (m["ob"] or 1.7) - 1.0 + 0.3
        picks.append(_pick(m, "WIN+BTTS", f"{ft} Win & BTTS", co, cb,
            f"{ft} {max(m['ph'],m['pa']):.0f}% + BTTS {m['pb']:.0f}%"))
    return AccaResult(name="WIN + BTTS", icon="target", picks=picks,
        total_odds=_total(picks), combined_confidence=_avg(picks),
        description="Top 3 games where the favorite wins AND both teams score")

def acca_o25(ms: list[dict]) -> AccaResult:
    """Build Over 2.5 acca: top 3 highest goal-scoring potential."""
    sc = []
    for m in ms:
        if m["po"] < 35: continue
        s = m["po"] * m["af"] + m["xg"] * 8 + _val(m["po"], m["oo"]) * 0.5
        sc.append((s, m))
    sc.sort(key=lambda x: x[0], reverse=True)
    picks = [_pick(m, "Over/Under", "Over 2.5", m["oo"], m["po"],
        f"O2.5 {m['po']:.0f}% — xG {m['xg']:.1f}") for _, m in sc[:3]]
    return AccaResult(name="Over 2.5", icon="bar-chart", picks=picks,
        total_odds=_total(picks), combined_confidence=_avg(picks),
        description="Top 3 games most likely to have 3+ goals")

async def acca_lucky6(ms: list[dict]) -> AccaResult:
    """Build Lucky 6: AI consensus picks for win + BTTS."""
    cands = []
    for m in ms:
        fp = max(m["ph"], m["pa"])
        if fp < 33 or m["pb"] < 22: continue
        cb = (fp / 100) * (m["pb"] / 100) * 100
        ft = m["ht"] if m["ph"] >= m["pa"] else m["at"]
        cands.append({"match": f"{m['ht']} vs {m['at']}", "lg": m["lg"], "ko": m["ko"],
            "fav": ft, "fp": round(fp, 1), "bp": round(m["pb"], 1),
            "cb": round(cb, 1), "xg": round(m["xg"], 2), "af": round(m["af"], 2)})
    cands.sort(key=lambda x: x["cb"], reverse=True)
    top = cands[:20]
    try:
        ai = AsyncOpenAI()
        prompt = dedent("""\
            Pick the 6 BEST football games for "Win + BTTS" from this data.
            Return ONLY a JSON array of 6 objects: {{"match": "...", "fav": "...", "why": "..."}}.

            <data>
            {d}
            </data>

            Consider: cb (combo prob, higher=better), xg (expected goals, >2=good), af (attack factor, >1=attacking).
            Diversify leagues. Pick highest chance of favorite winning + both teams scoring.""").format(d=json.dumps(top[:15], indent=1))
        r = await ai.chat.completions.create(model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}], max_tokens=1200, temperature=0.3)
        ct = r.choices[0].message.content or "[]"
        if "```" in ct:
            ct = ct.split("```json")[-1].split("```")[0] if "```json" in ct else ct.split("```")[1]
        aip = json.loads(ct.strip())
    except Exception as e:
        logger.warning("AI fallback", error=str(e))
        aip = [{"match": c["match"], "fav": c["fav"], "why": f"Combo {c['cb']}%"} for c in top[:6]]
    lu = {m["ht"] + " vs " + m["at"]: m for m in ms}
    picks = []
    for a in aip[:6]:
        m = lu.get(a.get("match", ""))
        if not m:
            for k, v in lu.items():
                if a.get("fav", "") in k: m = v; break
        if not m: continue
        fv = a.get("fav", m["ht"])
        fp = m["ph"] if fv == m["ht"] else m["pa"]
        fo = m["oh"] if fv == m["ht"] else m["oa"]
        co = (fo or 1.5) + (m["ob"] or 1.7) - 1.0 + 0.3
        cb = (fp / 100) * (m["pb"] / 100) * 100
        picks.append(_pick(m, "WIN+BTTS", f"{fv} Win & BTTS", co, cb, a.get("why", "AI pick")))
    return AccaResult(name="Lucky 6", icon="sparkles", picks=picks,
        total_odds=_total(picks), combined_confidence=_avg(picks),
        description="AI consensus — 6 games for straight win + BTTS")

# ── Endpoints ─────────────────────────────────────────────────

@app.post("/", response_model=AccaResponse)
async def get_accas(request: AccaRequest):
    logger.info("Generating accas", tz=request.tz)
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    tmrw = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    async with httpx.AsyncClient() as c:
        preds = await fetch_preds(c, request.tz)
    logger.info("Fetched predictions", count=len(preds))
    ms = []
    for p in preds:
        e = enrich(p)
        if e and e["ko"][:10] in (today, tmrw): ms.append(e)
    if not ms:
        for p in preds:
            e = enrich(p)
            if e: ms.append(e)
        ms = ms[:30]
    logger.info("Analyzing matches", count=len(ms))
    a1 = acca_day(ms)
    a2 = acca_btts_o25(ms)
    a3 = acca_win_btts(ms)
    a4 = acca_o25(ms)
    a5 = await acca_lucky6(ms)
    return AccaResponse(date=today, accas=[a1, a2, a3, a4, a5],
        total_matches_analyzed=len(ms), generated_at=now.isoformat())

class StatsReq(BaseModel):
    tz: str = Field(default="UTC")
    days: int = Field(default=7)

class MatchRes(BaseModel):
    home_team: str = Field(default="", description="Home team")
    away_team: str = Field(default="", description="Away team")
    league: str = Field(default="", description="League name")
    score: str = Field(default="", description="Final score")
    date: str = Field(default="", description="Match date")
    btts: bool = Field(default=False, description="Both teams scored")
    over25: bool = Field(default=False, description="Over 2.5 goals")
    home_win: bool = Field(default=False, description="Home team won")
    away_win: bool = Field(default=False, description="Away team won")
    draw: bool = Field(default=False, description="Match was a draw")

class StatsResp(BaseModel):
    period_days: int = Field(default=7, description="Stats period in days")
    total_matches: int = Field(default=0, description="Total finished matches")
    btts_rate: float = Field(default=0.0, description="BTTS rate %")
    over25_rate: float = Field(default=0.0, description="Over 2.5 rate %")
    home_win_rate: float = Field(default=0.0, description="Home win rate %")
    away_win_rate: float = Field(default=0.0, description="Away win rate %")
    draw_rate: float = Field(default=0.0, description="Draw rate %")
    avg_goals: float = Field(default=0.0, description="Average goals per match")
    recent_results: list[MatchRes] = Field(default=[], description="Recent match results")

@app.post("/stats", response_model=StatsResp)
async def get_stats(request: StatsReq):
    logger.info("Stats", days=request.days)
    now = datetime.now(timezone.utc)
    df = (now - timedelta(days=request.days)).strftime("%Y-%m-%d")
    dt = now.strftime("%Y-%m-%d")
    async with httpx.AsyncClient() as c:
        evs = await fetch_events(c, df, dt, request.tz, status="finished")
    res, tg, bc, oc, hc, ac, dc = [], 0, 0, 0, 0, 0, 0
    for ev in evs:
        hs, aws = ev.get("home_score"), ev.get("away_score")
        if hs is None or aws is None: continue
        hs, aws = int(hs), int(aws)
        tot = hs + aws; tg += tot
        b = hs > 0 and aws > 0; o = tot > 2; h = hs > aws; a = aws > hs; d = hs == aws
        if b: bc += 1
        if o: oc += 1
        if h: hc += 1
        if a: ac += 1
        if d: dc += 1
        res.append(MatchRes(home_team=ev.get("home_team",""), away_team=ev.get("away_team",""),
            league=ev.get("league",{}).get("name",""), score=f"{hs}-{aws}",
            date=ev.get("event_date","")[:10], btts=b, over25=o, home_win=h, away_win=a, draw=d))
    n = len(res) or 1
    return StatsResp(period_days=request.days, total_matches=len(res),
        btts_rate=round(bc/n*100,1), over25_rate=round(oc/n*100,1),
        home_win_rate=round(hc/n*100,1), away_win_rate=round(ac/n*100,1),
        draw_rate=round(dc/n*100,1), avg_goals=round(tg/n,2), recent_results=res[:20])

if __name__ == "__main__":
    run_service(app)
