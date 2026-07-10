# The Ledger Autopsy

**Could a detector have caught Enron?** A forensic accounting model, run
point-in-time over the real SEC filings of history's biggest frauds and a set of
healthy control companies, published as an honest scoreboard, the false positive
and the miss included.

**Live:** https://anandvaghasia.com/fraud-detector/

The thesis is maturity, not a victory lap. The tool does **not** claim "AI would
have caught it." It shows what the numbers actually said, what a transparent
red-flag model flags, and where hindsight bias hides. The false positive and the
miss are not bugs. They are the finding.

## The scoreboard

Nine companies, each scored on its last annual report before anyone knew.

| Company                                | Verdict | Reality | Result                                             |
| -------------------------------------- | ------- | ------- | -------------------------------------------------- |
| Enron (FY2000)                         | Flag    | Fraud   | True positive (via footnotes, not ratios)          |
| WorldCom (FY2001)                      | Flag    | Fraud   | True positive                                      |
| Luckin Coffee (FY2019)                 | Flag    | Fraud   | True positive (half catch)                         |
| Wirecard (FY2018)                      | Clear   | Fraud   | **Miss** (the numbers were pristine)               |
| Netflix (FY2019)                       | Flag    | Healthy | **False positive** (cash-poor profit is not fraud) |
| ExxonMobil, Verizon, Starbucks, Costco | Clear   | Healthy | True negatives                                     |

Result: precision and recall both about 75%. The model catches the catchable,
misses the invisible, and false-alarms on the aggressive-but-honest.

## How it works

1. **`pipeline/build.py`** pulls the healthy controls straight from SEC XBRL
   companyfacts (machine-readable filings), merges the hand-curated pre-XBRL
   frauds from `pipeline/cases_seed.py` (Enron and WorldCom predate XBRL, so
   their figures are transcribed from the actual 10-K and every one links to
   it), runs one transparent forensic model over all of them, scores each
   0-100, sets a FLAG / CLEAR verdict at a fixed threshold, and bakes
   `data/cases.json` with the confusion matrix.
2. **The model is a deterministic rubric**, not an opaque number. Every point
   traces to a filing figure: accruals to assets, cash conversion, revenue
   growth implausibility, capital spend versus operating cash, receivables
   growth versus revenue, leverage. You can see exactly what fired.
3. **Where Claude comes in:** the quantitative score is arithmetic. Claude Code
   did the forensic reading around it, pulling and reconciling the filings,
   encoding the signals, and writing the point-in-time memo on each case from
   the footnotes, labelled as the qualitative read it is.
4. The static page (`index.html` / `styles.css` / `app.js`) only renders the
   baked JSON. Zero cost per visitor, nothing runs live.

## Honesty

- Ground truth is known, so the verdict is graded into a real confusion matrix.
- The controls include a company the detector wrongly flags (Netflix), and the
  frauds include one it misses entirely (Wirecard). Both cells are shown.
- Wirecard is a German filer with no SEC financial statements. Its figures are
  shown with that data gap stated out loud, not hidden.
- Thresholds are reasonable, not optimized. On a bigger, blinder universe the
  false-positive rate would be far higher than it looks here.

## Rebuild

```bash
cd pipeline && python3 build.py   # stdlib only, no API key; rate-limited to SEC
```

Then open `index.html`, or deploy with `python3 deploy.py`
(`ANANDVAGHASIA_FTP_*` in `~/.claude/secrets.env`; the script asserts the slug
and never touches anything else).

## Data

SEC EDGAR (free, public): submissions, XBRL companyfacts, and the primary 10-K
documents. Every figure on the site links to the filing it came from.

Built by [Anand Vaghasia](https://anandvaghasia.com). Powered by
[NetRyse](https://netryse.com).
