# -*- coding: utf-8 -*-
"""Curated case seed for the Ledger Autopsy fraud detector.

Two kinds of company live here:

  1. Historical frauds that PREDATE SEC XBRL (Enron 2001, WorldCom 2002) and a
     foreign fraud with no SEC financials (Wirecard, Luckin). For these, the
     headline financials are transcribed BY HAND from the primary filing and
     every number carries the exact filing URL so a reader can verify the line.
     Each transcribed figure was checked against the fetched primary document.

  2. Healthy controls + one honest false-positive candidate (Netflix) are NOT
     here. They are pulled programmatically from SEC XBRL companyfacts in
     build.py, so their numbers come straight from the machine-readable filing.

`outcome` is the GROUND TRUTH (fraud vs healthy) used to score the detector
against reality. `memo` is the point-in-time forensic read, written by Claude
from the filing footnotes, deliberately kept to what a reader in that year could
have seen. Ratios are currency-invariant, so RMB / EUR cases score the same way
as USD ones; only the display headline is converted.

No em-dashes anywhere (project rule).
"""

# Financials per fiscal year. All values in MILLIONS of the stated currency.
# rev=total revenue, ni=net income, cfo=cash from operating activities,
# assets=total assets, liab=total liabilities, capex=capital expenditures
# (positive number), recv=trade/other receivables (optional).

SEED = [
    {
        "id": "enron",
        "name": "Enron Corp.",
        "sector": "Energy",
        "currency": "USD",
        "ticker": "ENE",
        "cik": "1024401",
        "peer": "exxonmobil",
        "collapse_year": 2001,
        "outcome": {
            "truth": "fraud",
            "headline": "Bankrupt Dec 2001. ~$74B in shareholder value erased; ~$63B in assets, the largest US bankruptcy at the time.",
            "what": "Off-balance-sheet partnerships (LJM, the Raptors), mark-to-market revenue, and hidden debt. CEO and CFO convicted; auditor Arthur Andersen dissolved.",
        },
        "source": {
            "label": "Enron FY2000 Form 10-K (filed 2001-04-02, the last annual report before collapse)",
            "url": "https://www.sec.gov/Archives/edgar/data/1024401/000102440101500010/ene10-k.txt",
        },
        "point_in_time_year": 2000,
        # transcribed + verified against ene10-k.txt
        "financials": [
            {"year": 1998, "rev": 31260, "ni": 703, "cfo": 1640, "assets": 29350},
            {"year": 1999, "rev": 40112, "ni": 893, "cfo": 1228, "assets": 33381},
            {"year": 2000, "rev": 100789, "ni": 979, "cfo": 4779, "assets": 65503, "liab": 54033},
        ],
        # qualitative point-in-time flags visible in the filing footnotes / MD&A
        "qual_flags": [
            {"key": "related_party", "weight": 22, "label": "Related-party transactions with officer-run partnerships",
             "note": "The 2000 10-K discloses transactions with limited partnerships (LJM) whose general partner was a senior Enron officer. Related-party deals run by insiders are the single loudest governance red flag in the filing."},
            {"key": "revenue_implausible", "weight": 14, "label": "Revenue up ~151% in one year with flat profit",
             "note": "Total revenues jumped from $40.1B (1999) to $100.8B (2000) while net income barely moved ($893M to $979M). Revenue growing 2.5x on flat earnings points to mark-to-market and trading gross-ups, not real economics."},
            {"key": "mark_to_market", "weight": 12, "label": "Mark-to-market 'price risk management' revenue",
             "note": "A large share of reported revenue came from fair-value gains on energy contracts booked up front, an accounting policy that lets a company report profit it has not yet collected in cash."},
        ],
        "memo": "In 2000 Enron looked, on the ratios, mostly fine. Cash from operations ($4.8B) actually exceeded net income ($979M), so a naive earnings-quality screen would give it a clean bill. The fraud did not live in the ratios. It lived in the footnotes: partnerships run by Enron's own CFO, debt parked off the balance sheet, and revenue that more than doubled in a year with no matching profit. This is the case that teaches the whole lesson. The numbers a screener loves were green, and the company was already dead.",
    },
    {
        "id": "worldcom",
        "name": "WorldCom, Inc.",
        "sector": "Telecom",
        "currency": "USD",
        "ticker": "WCOM",
        "cik": "723527",
        "peer": "verizon",
        "collapse_year": 2002,
        "outcome": {
            "truth": "fraud",
            "headline": "Bankrupt Jul 2002. ~$11B accounting fraud, ~$107B in assets, then the largest US bankruptcy ever.",
            "what": "Ordinary operating 'line costs' were capitalized as assets to inflate profit and hide a collapsing business. CEO Bernard Ebbers sentenced to 25 years.",
        },
        "source": {
            "label": "WorldCom FY2001 Form 10-K405 (filed 2002-03-13, the last annual report before the fraud was disclosed)",
            "url": "https://www.sec.gov/Archives/edgar/data/723527/000100547702001226/d02-36461.txt",
        },
        "point_in_time_year": 2001,
        # transcribed + verified against d02-36461.txt
        "financials": [
            {"year": 1999, "rev": 35908, "ni": 3941, "cfo": 11005, "assets": 91072, "capex": 8716},
            {"year": 2000, "rev": 39090, "ni": 4088, "cfo": 7666, "assets": 98903, "capex": 11484},
            {"year": 2001, "rev": 35179, "ni": 1384, "cfo": 7994, "assets": 103914, "capex": 7886},
        ],
        "qual_flags": [
            {"key": "capex_intensity", "weight": 14, "label": "Capital spending stayed enormous while revenue fell",
             "note": "Revenue dropped from $39.1B (2000) to $35.2B (2001), yet the company kept spending ~$7.9B on capital assets, ~22% of revenue, far above a telecom in a downturn. That is the exact fingerprint of moving operating costs onto the balance sheet."},
            {"key": "margin_implausible", "weight": 12, "label": "Reported a profit while telecom peers posted losses",
             "note": "WorldCom booked $1.4B of net income in 2001 during the telecom depression that pushed most long-distance carriers into losses. Being the one profitable carrier in a sinking sector is a signal, not a strength."},
        ],
        "memo": "WorldCom is the catchable one. You did not need the smoking gun to be suspicious. Revenue was falling, the whole long-distance industry was losing money, and yet WorldCom was still spending like it was 1999 and still reporting a healthy profit. Capital spending that will not fall when revenue does is the classic tell for capitalizing costs that should have been expensed. A screener that watches capex intensity and margin-versus-peers flags this a year before the restatement.",
    },
    {
        "id": "luckin",
        "name": "Luckin Coffee Inc.",
        "sector": "Coffee",
        "currency": "RMB",
        "ticker": "LKNCY",
        "cik": "1767582",
        "peer": "starbucks",
        "collapse_year": 2020,
        "outcome": {
            "truth": "fraud",
            "headline": "Delisted from Nasdaq Jun 2020; ~RMB 2.12B (~$310M) of 2019 sales fabricated. $180M SEC settlement.",
            "what": "A special committee found sales, costs, and expenses had been intentionally inflated from Q2 2019. The decisive proof came from on-the-ground receipt counts, not the filings.",
        },
        "source": {
            "label": "Fabrication figure per Luckin's own restatement disclosed in its FY2020 Form 20-F (filed 2021-06-30); reported 2019 revenue per the Jan 2020 secondary-offering prospectus (424B4)",
            "url": "https://www.sec.gov/Archives/edgar/data/1767582/000104746920000183/a2240425z424b4.htm",
        },
        "point_in_time_year": 2019,
        # reported (fabricated) figures; RMB millions. 2019 revenue as reported;
        # the special committee later found ~RMB 2,119M of it was fabricated.
        "financials": [
            {"year": 2018, "rev": 840.7, "ni": -1618.7, "cfo": -1310, "assets": 4023, "recv": 175},
            {"year": 2019, "rev": 5180.9, "ni": -3136.0, "cfo": -1230, "assets": 11229, "recv": 665},
        ],
        "qual_flags": [
            {"key": "revenue_implausible", "weight": 18, "label": "Revenue up ~516% in one year on a cash-burning store rollout",
             "note": "Reported net revenue leapt from RMB 840.7M (2018) to RMB 5,180.9M (2019). Hyper-growth is not proof of fraud, but revenue this steep, this fast, from a company opening stores at a loss, is exactly the profile a detector should stop on."},
            {"key": "receivables_gap", "weight": 8, "label": "Receivables and prepayments growing faster than a cash business should need",
             "note": "For a coffee chain that collects at the counter, receivables and prepaid balances that swell alongside 'revenue' hint that the sales may not be converting to cash the way real transactions do."},
            {"key": "restatement", "weight": 20, "label": "Later confirmed: ~RMB 2.12B of 2019 sales were fabricated",
             "note": "Luckin's own special committee found roughly RMB 2,119M of 2019 net sales were fabricated. Included so the record is honest about what was eventually proven, though this was not visible in the filing at the time."},
        ],
        "memo": "Luckin is the honest half-catch. The reported growth was absurd, and the receivables did not behave like a cash-only coffee counter should, so a screener would rightly flag it. But the flag alone was not proof, and plenty of real hyper-growth companies look identical on paper. What actually broke Luckin was an anonymous short report backed by thousands of hours of in-store receipt counting. The filings raised the question. Feet on the ground answered it.",
    },
    {
        "id": "wirecard",
        "name": "Wirecard AG",
        "sector": "Payments",
        "currency": "EUR",
        "ticker": "WDI",
        "cik": None,
        "peer": None,
        "collapse_year": 2020,
        "outcome": {
            "truth": "fraud",
            "headline": "Insolvent Jun 2020. EUR 1.9B of cash that did not exist. Former CEO on trial; COO a fugitive.",
            "what": "For years the auditors signed off on cash held in Asian trustee accounts. In 2020 the banks said the accounts, and the money, were never real.",
        },
        "source": {
            "label": "Wirecard AG FY2018 Annual Report (IFRS). Wirecard was a German (Frankfurt) filer with no SEC financial statements, so these figures are outside EDGAR and are shown with that caveat.",
            "url": "https://www.wirecard.com/",
        },
        "point_in_time_year": 2018,
        # IFRS reported figures, EUR millions. These looked pristine. The fraud
        # was in cash that was not there, which does not show up as a bad ratio.
        "financials": [
            {"year": 2017, "rev": 1490, "ni": 260, "cfo": 279, "assets": 4652, "liab": 2418},
            {"year": 2018, "rev": 2016, "ni": 347, "cfo": 210, "assets": 5855, "liab": 3444},
        ],
        "qual_flags": [],
        "memo": "Wirecard is the case that keeps a forensic analyst honest. Read the 2018 numbers cold and you see a fintech growing fast with real profit, positive cash flow, and a strong balance sheet. There is no accrual anomaly to catch, no margin that looks impossible, no leverage spike. The EUR 1.9B at the center of the fraud was reported as cash sitting safely in trust. A detector that scores what is IN the filings scores Wirecard clean, because the lie was an asset that did not exist, not a number that looked wrong. This is why the honest answer to 'could AI have caught it' is sometimes no.",
    },
]

# Ground-truth outcomes and metadata for the XBRL-sourced companies pulled in
# build.py. Controls + the one honest false positive (Netflix). Peer links let
# the margin-implausibility signal compare a suspect to a clean same-sector peer.
XBRL_COMPANIES = [
    {"id": "netflix", "name": "Netflix, Inc.", "cik": "1065280", "sector": "Streaming",
     "years": [2015, 2016, 2017, 2018, 2019], "peer": None,
     "outcome": {"truth": "healthy",
                 "headline": "Not a fraud. A real, audited, still-operating company. Included as an honest false-positive test.",
                 "what": "For years Netflix reported accounting profit while burning billions in cash on content. The gap between profit and cash flow is real and is exactly what an earnings-quality screen flags. It was disclosed, financed, and legitimate."},
     "memo": "Netflix is the trap. From 2015 to 2019 it reported growing profits while free cash flow ran deeply negative, because it paid cash for content long before expensing it. On an accrual or cash-conversion screen this looks alarming, the same shape as an earnings manipulator. But Netflix disclosed all of it, funded it openly with debt, and delivered. A detector that flags cash-poor profit will flag Netflix, and it will be wrong. The false positive is the point: aggressive-looking is not the same as fraudulent."},
    {"id": "exxonmobil", "name": "Exxon Mobil Corp.", "cik": "34088", "sector": "Energy",
     "years": [2013, 2014, 2015, 2016, 2017, 2018, 2019], "peer": None,
     "outcome": {"truth": "healthy", "headline": "Clean control. Enron's sector peer.",
                 "what": "Cash flow that backs earnings, steady leverage, no growth implausibility. What a real energy major looks like next to Enron."},
     "memo": "The energy control. Earnings backed by cash, a balance sheet that moves slowly, revenue that tracks oil prices instead of leaping 150% in a year. Set beside Enron, ExxonMobil is what 'boring and real' reads like on a screen."},
    {"id": "verizon", "name": "Verizon Communications Inc.", "cik": "732712", "sector": "Telecom",
     "years": [2013, 2014, 2015, 2016, 2017, 2018, 2019], "peer": None,
     "outcome": {"truth": "healthy", "headline": "Clean control. WorldCom's sector peer.",
                 "what": "Heavy but stable capital spending that scales with the business, and cash flow that comfortably backs reported profit."},
     "memo": "The telecom control. Verizon spends heavily on its network, like every carrier, but its capital spending scales with the business and its cash flow covers its earnings. It is the honest version of the business WorldCom pretended to be."},
    {"id": "starbucks", "name": "Starbucks Corp.", "cik": "829224", "sector": "Coffee",
     "years": [2013, 2014, 2015, 2016, 2017, 2018, 2019], "peer": None,
     "outcome": {"truth": "healthy", "headline": "Clean control. Luckin's sector peer.",
                 "what": "Mature, cash-generative coffee retail. Growth is single digit and profit converts to cash."},
     "memo": "The coffee control. A mature chain that grows at single digits and turns profit into cash. Luckin claimed to be a faster, hungrier Starbucks. The contrast on the numbers is the whole story."},
    {"id": "costco", "name": "Costco Wholesale Corp.", "cik": "909832", "sector": "Retail",
     "years": [2013, 2014, 2015, 2016, 2017, 2018, 2019], "peer": None,
     "outcome": {"truth": "healthy", "headline": "Clean control. Thin margins, real cash.",
                 "what": "Wafer-thin retail margins that could look weak, but backed by strong, consistent operating cash flow. Low margin is not a red flag when the cash is real."},
     "memo": "The low-margin control. Costco earns almost nothing per dollar of sales, which a lazy screen might dislike, but the cash flow is rock solid and consistent. It is the reminder that a thin margin honestly earned is not a warning sign."},
]
