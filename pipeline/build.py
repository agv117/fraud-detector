#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ledger Autopsy builder.

Pulls the healthy controls + the false-positive candidate straight from SEC
XBRL companyfacts (machine-readable filings), merges the hand-curated historical
frauds from cases_seed.py, runs ONE deterministic forensic model over all of
them, scores each 0-100, sets a FLAG / CLEAR verdict at a fixed threshold, and
bakes data/cases.json with the honest confusion matrix.

The score is a transparent rubric, not an opaque model, so every point traces to
a filing figure and the number can never drift from its citation (the same
guarantee the 990 X-Ray tool holds). Qualitative point-in-time flags (related
parties, off-balance-sheet vehicles) are curated from the filing footnotes and
labelled as such. No live API is hit by visitors; this runs once at build.

Run: python3 build.py   (stdlib only, no API key, rate-limited to SEC's <=10/s)
"""
import json
import time
import urllib.request
from pathlib import Path

from cases_seed import SEED, XBRL_COMPANIES

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "cases.json"
UA = {"User-Agent": "Anand Vaghasia anand@anandvaghasia.com"}
THRESHOLD = 40  # detector flags a company when the red-flag score reaches this

# ---- SEC XBRL ----------------------------------------------------------------
REV_CONCEPTS = ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues", "SalesRevenueNet"]
NI_CONCEPTS = ["NetIncomeLoss", "ProfitLoss"]
CFO_CONCEPTS = ["NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
CAPEX_CONCEPTS = ["PaymentsToAcquirePropertyPlantAndEquipment",
                  "PaymentsToAcquireProductiveAssets"]
ASSET_CONCEPTS = ["Assets"]
LIAB_CONCEPTS = ["Liabilities"]
RECV_CONCEPTS = ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"]


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def fact_by_year(facts, concepts, duration=True):
    """Return {period_year: (value, accn)} for the first concept with data.

    Keyed by the PERIOD END year, not the reporting fy: a 10-K carries prior
    years as comparatives all tagged with the filing's fy, so matching fy would
    grab the wrong period. For duration facts we keep only ~full-year windows
    ending in the target year; for instant (balance) facts, the point at the
    target year end. Prefer the framed / most-recently-filed statement of the
    period so the cited filing actually contains the number.
    """
    usg = facts.get("facts", {}).get("us-gaap", {})
    for c in concepts:
        node = usg.get(c)
        if not node:
            continue
        by = {}
        for u in node.get("units", {}).get("USD", []):
            if not str(u.get("form", "")).startswith("10-K"):
                continue
            e = u.get("end")
            if not e:
                continue
            if duration:
                s = u.get("start")
                if not s:
                    continue
                days = (int(e[:4]) - int(s[:4])) * 365 + (int(e[5:7]) - int(s[5:7])) * 30
                if days < 330:  # full-year only, skip quarters / stubs
                    continue
            year = int(e[:4])
            score = (1 if u.get("frame") else 0, u.get("filed", ""))
            prev = by.get(year)
            if prev is None or score > prev[0]:
                by[year] = (score, u.get("val"), u.get("accn"))
        if by:
            return {yr: (v[1], v[2]) for yr, v in by.items()}
    return {}


def pull_xbrl(company):
    cik10 = company["cik"].zfill(10)
    facts = fetch(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json")
    time.sleep(0.2)
    grids = {
        "rev": fact_by_year(facts, REV_CONCEPTS, True),
        "ni": fact_by_year(facts, NI_CONCEPTS, True),
        "cfo": fact_by_year(facts, CFO_CONCEPTS, True),
        "capex": fact_by_year(facts, CAPEX_CONCEPTS, True),
        "assets": fact_by_year(facts, ASSET_CONCEPTS, False),
        "liab": fact_by_year(facts, LIAB_CONCEPTS, False),
        "recv": fact_by_year(facts, RECV_CONCEPTS, False),
    }
    rows, accns = [], {}
    for y in company["years"]:
        row = {"year": y}
        for k, grid in grids.items():
            if y in grid:
                val, accn = grid[y]
                if val is not None:
                    # capex is reported as a positive cash outflow already
                    row[k] = float(val) / 1e6  # to $millions, consistent w/ seed
                    accns[y] = accn
        rows.append(row)
    cik = str(int(company["cik"]))
    src = None
    for y in reversed(company["years"]):
        if y in accns:
            a = accns[y].replace("-", "")
            src = {"label": f"SEC XBRL companyfacts, FY{y} Form 10-K",
                   "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K"}
            src["filing"] = f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/"
            break
    return rows, (src or {"label": "SEC XBRL companyfacts",
                          "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K"})


# ---- the forensic model ------------------------------------------------------
def g(row, k):
    v = row.get(k)
    return v if isinstance(v, (int, float)) else None


def cite(company, field, year, label):
    src = company["_src"]
    return {"field": field, "line": label, "year": year,
            "url": src.get("filing") or src.get("url")}


def flagof(points):
    return "red" if points >= 18 else "amber" if points >= 8 else "green"


def build_signals(company, fins):
    """One transparent rubric. Each signal: value, points, flag, explain, cites."""
    fins = sorted(fins, key=lambda r: r["year"])
    latest = fins[-1]
    prev = fins[-2] if len(fins) >= 2 else None
    y = latest["year"]
    rev, ni, cfo = g(latest, "rev"), g(latest, "ni"), g(latest, "cfo")
    assets, liab, capex, recv = g(latest, "assets"), g(latest, "liab"), g(latest, "capex"), g(latest, "recv")
    S = []

    # 1. Sloan accruals: earnings not backed by cash
    if ni is not None and cfo is not None and assets:
        val = (ni - cfo) / assets
        pts = 28 if val > 0.12 else 14 if val > 0.06 else 0
        S.append({"key": "accruals", "label": "Accruals to assets", "value": val, "format": "pct",
                  "points": pts, "flag": flagof(pts),
                  "explain": "Net income minus operating cash flow, over assets. A large positive gap means the profit is on paper, not in the bank. Negative is fine: the cash exceeded the reported profit.",
                  "cites": [cite(company, "ni", y, "Net income"), cite(company, "cfo", y, "Cash from operations"), cite(company, "assets", y, "Total assets")]})

    # 2. Cash conversion of profit
    if ni is not None and cfo is not None and ni > 0:
        val = cfo / ni
        pts = 28 if val < 0 else 14 if val < 0.8 else 0
        S.append({"key": "cash_conversion", "label": "Cash conversion (CFO / net income)", "value": val, "format": "x",
                  "points": pts, "flag": flagof(pts),
                  "explain": "How many dollars of operating cash each dollar of reported profit turned into. Below one, and especially below zero, means the earnings are not showing up as cash.",
                  "cites": [cite(company, "cfo", y, "Cash from operations"), cite(company, "ni", y, "Net income")]})

    # 3. Revenue growth implausibility
    if prev and g(prev, "rev") and rev:
        val = rev / g(prev, "rev") - 1
        pts = 28 if val > 1.0 else 22 if val > 0.5 else 12 if val > 0.30 else 0
        S.append({"key": "revenue_growth", "label": "One-year revenue growth", "value": val, "format": "pct",
                  "points": pts, "flag": flagof(pts),
                  "explain": "Year-over-year change in total revenue. Explosive growth is not proof of anything, but revenue that leaps far faster than a real business can is where a detector should stop and look.",
                  "cites": [cite(company, "rev", prev["year"], "Total revenue"), cite(company, "rev", y, "Total revenue")]})

    # 4. Capital spending vs cash generation (the capitalize-your-costs tell)
    if capex is not None and cfo is not None and cfo > 0:
        absorb = capex / cfo
        capex_rev = (capex / rev) if rev else None
        declining = bool(prev and g(prev, "rev") and rev and rev < g(prev, "rev"))
        pts = 24 if absorb > 0.9 else 12 if absorb > 0.7 else 0
        if capex_rev and capex_rev > 0.18 and declining:
            pts += 8
        pts = min(pts, 30)
        extra = " Revenue fell this year while capital spending stayed heavy, the fingerprint of moving operating costs onto the balance sheet." if (capex_rev and capex_rev > 0.18 and declining) else ""
        S.append({"key": "capex_absorption", "label": "Capex as share of operating cash", "value": absorb, "format": "pct",
                  "points": pts, "flag": flagof(pts),
                  "explain": "Capital spending divided by operating cash flow. Near or above one means almost every dollar of 'operating' cash went straight back out as capital spending, which is exactly what capitalizing ordinary expenses looks like." + extra,
                  "cites": [cite(company, "capex", y, "Capital expenditures"), cite(company, "cfo", y, "Cash from operations")]})

    # 5. Receivables outrunning revenue (channel stuffing / fabricated sales)
    if recv is not None and prev and g(prev, "recv") and g(prev, "rev") and rev:
        rg = recv / g(prev, "recv") - 1
        vg = rev / g(prev, "rev") - 1
        val = rg - vg
        pts = 16 if val > 0.3 else 8 if val > 0.1 else 0
        S.append({"key": "receivables_gap", "label": "Receivables growth minus revenue growth", "value": val, "format": "pct",
                  "points": pts, "flag": flagof(pts),
                  "explain": "When money owed grows faster than sales, revenue may be booked before, or without, real collection. Neutral here does not clear a company, it just means this particular tell did not fire.",
                  "cites": [cite(company, "recv", y, "Receivables"), cite(company, "rev", y, "Total revenue")]})

    # 6. Leverage (context)
    if liab is not None and assets:
        val = liab / assets
        pts = 10 if val > 0.9 else 5 if val > 0.8 else 0
        S.append({"key": "leverage", "label": "Liabilities to assets", "value": val, "format": "pct",
                  "points": pts, "flag": "amber" if pts >= 8 else "green" if pts == 0 else "amber",
                  "explain": "Share of the balance sheet financed by debt and other obligations. High and rising leverage is context, not a verdict, but it raises the stakes on everything else.",
                  "cites": [cite(company, "liab", y, "Total liabilities"), cite(company, "assets", y, "Total assets")]})

    return S


def score_company(company, fins, qual_flags):
    company["_src"] = company["source"] if "source" in company else company["_src"]
    signals = build_signals(company, fins)
    quant = sum(s["points"] for s in signals)
    qual = sum(q["weight"] for q in qual_flags)
    total = min(100, quant + qual)
    verdict = "flag" if total >= THRESHOLD else "clear"
    truth = company["outcome"]["truth"]
    if truth == "fraud":
        cell = "TP" if verdict == "flag" else "FN"
    else:
        cell = "FP" if verdict == "flag" else "TN"
    return {
        "signals": signals,
        "qual_flags": qual_flags,
        "quant_points": quant,
        "qual_points": qual,
        "score": round(total),
        "verdict": verdict,
        "cell": cell,
    }


def main():
    cases = []

    # curated frauds
    for s in SEED:
        s["_src"] = s["source"]
        fins = s["financials"]
        r = score_company(s, fins, s.get("qual_flags", []))
        cases.append({
            "id": s["id"], "name": s["name"], "sector": s["sector"], "currency": s["currency"],
            "ticker": s.get("ticker"), "cik": s.get("cik"),
            "point_in_time_year": s["point_in_time_year"], "collapse_year": s.get("collapse_year"),
            "source": s["source"], "outcome": s["outcome"], "memo": s["memo"],
            "financials": fins, "data_note": s.get("data_note"),
            **r,
        })
        print(f"  {s['name']:26} score={r['score']:>3}  {r['verdict']:>5}  truth={s['outcome']['truth']:<7} -> {r['cell']}")

    # XBRL controls + false-positive candidate
    for c in XBRL_COMPANIES:
        try:
            fins, src = pull_xbrl(c)
        except Exception as e:
            print(f"  [skip] {c['name']}: XBRL pull failed: {e}")
            continue
        c["_src"] = src
        r = score_company(c, fins, [])
        cases.append({
            "id": c["id"], "name": c["name"], "sector": c["sector"], "currency": "USD",
            "ticker": None, "cik": c["cik"],
            "point_in_time_year": c["years"][-1], "collapse_year": None,
            "source": src, "outcome": c["outcome"], "memo": c["memo"],
            "financials": fins, "data_note": None,
            **r,
        })
        print(f"  {c['name']:26} score={r['score']:>3}  {r['verdict']:>5}  truth={c['outcome']['truth']:<7} -> {r['cell']}")

    # confusion matrix
    m = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    for c in cases:
        m[c["cell"]] += 1
    tp, fp, fn, tn = m["TP"], m["FP"], m["FN"], m["TN"]
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    accuracy = (tp + tn) / len(cases) if cases else None

    cases.sort(key=lambda c: -c["score"])

    payload = {
        "generated": time.strftime("%Y-%m-%d"),
        "threshold": THRESHOLD,
        "n": len(cases),
        "matrix": m,
        "metrics": {
            "precision": precision, "recall": recall, "accuracy": accuracy,
        },
        "cases": cases,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nConfusion matrix  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"Precision={precision:.0%}  Recall={recall:.0%}  Accuracy={accuracy:.0%}" if precision else "")
    print(f"Wrote {len(cases)} cases to {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
