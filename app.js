/* The Ledger Autopsy — client. Everything is precomputed in data/cases.json by
   the Python model; this file only renders. Scoreboard + case autopsy, hash
   routed (#enron). The signature EKG plots each company's revenue vital sign and
   flatlines at the collapse year for the frauds. */

let DATA = null;
let BYID = {};

const $ = (s, r = document) => r.querySelector(s);
const el = (t, c, h) => {
  const n = document.createElement(t);
  if (c) n.className = c;
  if (h != null) n.innerHTML = h;
  return n;
};
const esc = (s) =>
  (s == null ? "" : String(s)).replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c],
  );

const CUR = { USD: "$", RMB: "¥", EUR: "€" };
function fmtMoney(v, cur) {
  if (v == null) return "n/a";
  const p = CUR[cur] || "$";
  const a = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (a >= 1e6) return `${sign}${p}${(a / 1e6).toFixed(2)}T`;
  if (a >= 1e3) return `${sign}${p}${(a / 1e3).toFixed(1)}B`;
  return `${sign}${p}${a.toFixed(0)}M`;
}
function fmtSig(s) {
  if (s.value == null) return "n/a";
  if (s.format === "pct") return `${(s.value * 100).toFixed(0)}%`;
  if (s.format === "x") return `${s.value.toFixed(2)}x`;
  return s.value.toFixed(2);
}

const RESULT_TXT = {
  TP: ["True positive", "Fraud, flagged"],
  TN: ["True negative", "Healthy, cleared"],
  FP: ["False positive", "Healthy, wrongly flagged"],
  FN: ["Miss", "Fraud, not flagged"],
};

// score -> cold(slate) to hot(blood) heat color
function heat(score) {
  const t = Math.max(0, Math.min(1, score / 100));
  const a = [95, 132, 150],
    b = [217, 164, 65],
    c = [255, 69, 58];
  const mix = (x, y, k) => Math.round(x + (y - x) * k);
  let col;
  if (t < 0.5) {
    const k = t / 0.5;
    col = a.map((x, i) => mix(x, b[i], k));
  } else {
    const k = (t - 0.5) / 0.5;
    col = b.map((x, i) => mix(x, c[i], k));
  }
  return `rgb(${col[0]},${col[1]},${col[2]})`;
}

// ---------- citation chip ----------
function shortCite(line, year) {
  return `${line || "figure"}${year != null ? ` FY${String(year).slice(-2)}` : ""}`;
}
function citeChip(c) {
  const label = esc(shortCite(c.line, c.year));
  const title = esc(
    `${c.line}${c.year ? " · fiscal year " + c.year : ""} — opens the filing`,
  );
  return c.url
    ? `<a class="cite" href="${esc(c.url)}" target="_blank" rel="noopener" title="${title}"><span class="pin">⊕</span>${label}</a>`
    : `<span class="cite" title="${title}"><span class="pin">⊕</span>${label}</span>`;
}

// ---------- board (confusion matrix + stats) ----------
function renderBoard() {
  const m = DATA.matrix,
    met = DATA.metrics;
  const cell = (k, name, desc) =>
    `<div class="mx-cell ${k.toLowerCase()}"><div class="n">${m[k]}</div><div class="k">${name}</div><div class="d">${desc}</div></div>`;
  const pct = (v) => (v == null ? "n/a" : `${Math.round(v * 100)}%`);
  $("#board").innerHTML = `
    <div class="matrix">
      <div class="matrix-cap">Detector verdict vs reality · ${DATA.n} companies · flag threshold ${DATA.threshold}</div>
      <div class="mx">
        <div></div>
        <div class="mx-lbl">Reality: fraud</div>
        <div class="mx-lbl">Reality: healthy</div>
        <div class="mx-lbl side">Said flag</div>
        ${cell("TP", "True positive", "caught")}
        ${cell("FP", "False positive", "wrong alarm")}
        <div class="mx-lbl side">Said clear</div>
        ${cell("FN", "Miss", "slipped through")}
        ${cell("TN", "True negative", "correct pass")}
      </div>
    </div>
    <div class="scorecol">
      <div class="stat"><div class="sv">${pct(met.recall)}</div><div class="sk">Recall</div><div class="sd">Of the frauds, the share the detector flagged.</div></div>
      <div class="stat"><div class="sv">${pct(met.precision)}</div><div class="sk">Precision</div><div class="sd">Of what it flagged, the share that really was fraud.</div></div>
    </div>`;
}

// ---------- ledger ----------
function learnLinks(c, cls) {
  if (!c.learn) return "";
  const read = c.learn.wiki
    ? `<a class="learn-btn ${cls}" href="${esc(c.learn.wiki)}" target="_blank" rel="noopener">Read the story</a>`
    : "";
  const watch = c.learn.video
    ? `<a class="learn-btn watch ${cls}" href="${esc(c.learn.video)}" target="_blank" rel="noopener">Watch the explainer</a>`
    : "";
  return read + watch;
}
function ledgerItem(c) {
  const item = el("div", "led-item");
  const r = el("button", "row");
  r.setAttribute("aria-label", `Open the ${c.name} case`);
  const truthTag = c.outcome.truth === "fraud" ? "fraud" : "healthy";
  const truthTxt = c.outcome.truth === "fraud" ? "Fraud" : "Healthy";
  const [rtitle] = RESULT_TXT[c.cell];
  r.innerHTML = `
    <div class="r-rank">${String(c._rank).padStart(2, "0")}</div>
    <div class="r-name">${esc(c.name)}<span class="r-sector">${esc(c.sector)} · scored on its FY${c.point_in_time_year} filing</span></div>
    <div class="r-score">
      <div class="r-track"><div class="r-fill" style="width:${c.score}%;background:${heat(c.score)}"></div></div>
      <div class="r-scoreval">${c.score}</div>
    </div>
    <div class="r-detector"><span class="tag ${c.verdict}">${c.verdict === "flag" ? "Flag" : "Clear"}</span></div>
    <div class="r-reality"><span class="tag ${truthTag}">${truthTxt}</span></div>
    <div class="r-result cell-${c.cell.toLowerCase()}"><span class="dot"></span><span>${rtitle}</span></div>
    <div class="r-go">→</div>`;
  r.onclick = () => (location.hash = c.id);
  const more = el("div", "led-more");
  const links = learnLinks(c, "");
  more.innerHTML = `<div class="teaser">${esc(c.teaser || "")}</div>${links ? `<div class="led-links">${links}</div>` : ""}`;
  item.appendChild(r);
  item.appendChild(more);
  return item;
}
function renderLedger() {
  const g = $("#ledger");
  g.innerHTML = "";
  DATA.cases.forEach((c, i) => {
    c._rank = i + 1;
    BYID[c.id] = c;
    g.appendChild(ledgerItem(c));
  });
}

// ---------- EKG (revenue vital sign, flatline at collapse) ----------
function ekg(c) {
  const fins = c.financials
    .filter((f) => typeof f.rev === "number")
    .sort((a, b) => a.year - b.year);
  if (fins.length < 2) return "";
  const fraud = c.outcome.truth === "fraud";
  const collapse = c.collapse_year;
  const W = 640,
    H = 128,
    padL = 8,
    padR = 8,
    padT = 14,
    padB = 22;
  const years = fins.map((f) => f.year);
  const lastY = years[years.length - 1];
  const endYear = fraud && collapse ? collapse : lastY + 1;
  const y0 = years[0];
  const span = Math.max(1, endYear - y0);
  const maxRev = Math.max(...fins.map((f) => f.rev));
  const X = (yr) => padL + ((yr - y0) / span) * (W - padL - padR);
  const Y = (v) => H - padB - (v / maxRev) * (H - padT - padB);
  const baseline = H - padB;

  // build an EKG-style path: rise to each revenue point with a small blip
  let d = `M ${X(y0).toFixed(1)} ${baseline.toFixed(1)}`;
  fins.forEach((f) => {
    const x = X(f.year),
      y = Y(f.rev);
    // little pre-blip then the point (heart-monitor feel)
    d += ` L ${(x - 6).toFixed(1)} ${baseline.toFixed(1)}`;
    d += ` L ${(x - 3).toFixed(1)} ${(y - 6).toFixed(1)}`;
    d += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    d += ` L ${(x + 3).toFixed(1)} ${(baseline - (baseline - y) * 0.55).toFixed(1)}`;
  });
  // tail: fraud flatlines to baseline at collapse; healthy keeps a beat
  const lastX = X(lastY);
  if (fraud && collapse) {
    d += ` L ${(lastX + 8).toFixed(1)} ${baseline.toFixed(1)} L ${X(collapse).toFixed(1)} ${baseline.toFixed(1)}`;
  } else {
    const bx = X(lastY + 1);
    d += ` L ${(lastX + 10).toFixed(1)} ${baseline.toFixed(1)} L ${(bx - 5).toFixed(1)} ${(baseline - 14).toFixed(1)} L ${bx.toFixed(1)} ${baseline.toFixed(1)}`;
  }

  const markX = fraud && collapse ? X(collapse) : X(lastY + 1);
  const marker =
    fraud && collapse
      ? `<circle cx="${markX.toFixed(1)}" cy="${baseline.toFixed(1)}" r="3.5" fill="#ff453a"/><text class="ekg-collapse" x="${markX.toFixed(1)}" y="${(baseline + 15).toFixed(1)}" text-anchor="end">FLATLINE ${collapse}</text>`
      : `<text class="ekg-collapse" style="fill:var(--sage)" x="${markX.toFixed(1)}" y="${(baseline + 15).toFixed(1)}" text-anchor="end">STILL BEATING</text>`;

  const startLbl = `<text class="ekg-axis" x="${padL}" y="${(baseline + 15).toFixed(1)}">${y0}</text>`;
  return `<div class="ekg">
    <div class="ekg-cap"><span>Revenue vital sign · ${esc(c.currency)} · to scale within the company</span><span>${fraud ? "the patient flatlined" : "still operating"}</span></div>
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Revenue over time, ${fraud ? "flatlining at collapse" : "still beating"}">
      <line x1="${padL}" y1="${baseline}" x2="${W - padR}" y2="${baseline}" stroke="var(--line)" stroke-width="1"/>
      <path class="ekg-line ${fraud ? "ekg-flat" : "ekg-live"}" d="${d}"/>
      ${startLbl}${marker}
    </svg>
  </div>`;
}

// ---------- case autopsy ----------
function renderCase(c) {
  const [rtitle, rdesc] = RESULT_TXT[c.cell];
  const detTxt = c.verdict === "flag" ? "Flag" : "Clear";
  const truthTxt = c.outcome.truth === "fraud" ? "Fraud" : "Healthy";

  const signals = c.signals
    .map(
      (s) => `
    <div class="sig ${s.flag}">
      <div class="sig-top">
        <div class="sig-label">${esc(s.label)}</div>
        <div class="sig-right"><div class="sig-val">${fmtSig(s)}</div><div class="sig-pts">+${s.points} pts</div></div>
      </div>
      <div class="sig-explain">${esc(s.explain)}</div>
      <div class="sig-cites">${(s.cites || []).map(citeChip).join("")}</div>
    </div>`,
    )
    .join("");

  const qual = (c.qual_flags || []).length
    ? `<div class="c-label">Qualitative point-in-time flags · read from the filing footnotes</div>
       <div class="qual">${c.qual_flags
         .map(
           (q) => `<div class="qflag">
             <div class="qw">+${q.weight}<small>PTS</small></div>
             <div><div class="ql">${esc(q.label)}</div><div class="qn">${esc(q.note)} ${citeChip({ line: c.source.label.split("(")[0].trim(), year: c.point_in_time_year, url: c.source.url })}</div></div>
           </div>`,
         )
         .join("")}</div>`
    : "";

  // financials table
  const fins = c.financials.slice().sort((a, b) => a.year - b.year);
  const rowsDef = [
    ["rev", "Revenue"],
    ["ni", "Net income"],
    ["cfo", "Cash from operations"],
    ["capex", "Capital expenditures"],
    ["recv", "Receivables"],
    ["assets", "Total assets"],
    ["liab", "Total liabilities"],
  ];
  const present = rowsDef.filter(([k]) =>
    fins.some((f) => typeof f[k] === "number"),
  );
  const finTable = `<div class="fin"><table>
    <thead><tr><th>${esc(c.currency)} millions</th>${fins.map((f) => `<th>FY${f.year}</th>`).join("")}</tr></thead>
    <tbody>${present
      .map(
        ([k, label]) =>
          `<tr><td>${label}</td>${fins.map((f) => `<td>${typeof f[k] === "number" ? fmtMoney(f[k], c.currency) : "—"}</td>`).join("")}</tr>`,
      )
      .join("")}</tbody>
  </table></div>
  <div class="fin-note">Figures as reported in the primary filing. <a href="${esc(c.source.filing || c.source.url)}" target="_blank" rel="noopener">${esc(c.source.label)}</a></div>`;

  const honesty =
    c.cell === "FN"
      ? "This is the miss the whole project exists to show. The reported statements were internally consistent and healthy, so a model that scores what is in the filing scores it clean. Reading numbers cannot catch a number that was never real."
      : c.cell === "FP"
        ? "This is the false alarm the project exists to show. The signals that fired are real and are exactly what an earnings-quality screen looks for, and here they are attached to an honest, well-run company. A flag is a question, not a conviction."
        : c.cell === "TP"
          ? "A hit, but read the signals before celebrating. In at least one of these the ratios were mostly green, and the flag came from growth implausibility and the footnotes. The detector helps you ask the right question; it did not by itself prove the fraud."
          : "Correctly cleared. Real cash backing real earnings, growth that a real business can produce, leverage that is not spiralling. This is what the honest version of the suspect's business looks like on the same instruments.";

  const s = $("#case");
  s.innerHTML = `
    <button class="back" onclick="goBack()">← Back to the scoreboard</button>
    <div class="dossier">
      <div class="c-head">
        <div class="c-eyebrow"><span>${esc(c.sector)}</span><span class="muted">Point in time · last annual before collapse · FY${c.point_in_time_year}</span>${c.ticker ? `<span class="muted">${esc(c.ticker)}</span>` : ""}</div>
        <h1 class="c-name">${esc(c.name)}</h1>
      </div>

      ${
        c.teaser
          ? `<div class="case-story">
        <div class="cs-tag">The story in one line</div>
        <div class="cs-line">${esc(c.teaser)}</div>
        ${learnLinks(c, "") ? `<div class="cs-links">${learnLinks(c, "")}</div>` : ""}
      </div>`
          : ""
      }

      <div class="verdict">
        <div class="v-box"><div class="vk">The detector said</div><div class="vv v-${c.verdict}">${detTxt}</div><div class="vs">red-flag score ${c.score} / 100 · threshold ${DATA.threshold}</div></div>
        <div class="v-box"><div class="vk">Reality was</div><div class="vv v-${c.outcome.truth}">${truthTxt}</div><div class="vs">${esc(c.outcome.truth === "fraud" ? "collapsed / charged" : "still operating")}</div></div>
        <div class="v-box result-cell v-${c.cell.toLowerCase()}"><div class="vk">Result</div><div class="vv">${rtitle}</div><div class="vs">${esc(rdesc)}</div></div>
      </div>

      ${ekg(c)}

      <div class="c-label">The point-in-time read</div>
      <div class="memo">${esc(c.memo)}<div class="memo-sign">Forensic memo, written by Claude Code from the ${esc(c.point_in_time_year)} filing.</div></div>

      <div class="c-label">The quantitative signals · every point traced to a filing figure</div>
      <div class="signals">${signals}</div>

      ${qual}

      <div class="c-label">What actually happened</div>
      <div class="outcome">
        <h3>The outcome</h3>
        <div class="redact" onclick="this.classList.add('open')">
          <div class="under">${esc(c.outcome.headline).replace(/(\$[\d.]+ ?[BMT]|RMB [\d.]+B|EUR [\d.]+B|~?\$?[\d.]+B)/g, '<span class="accent">$1</span>')}</div>
          <div class="bar"><span>Redacted · click to unseal</span></div>
        </div>
        <div class="what">${esc(c.outcome.what)}</div>
      </div>

      <div class="c-label">The filed numbers</div>
      ${finTable}

      <div class="c-honesty"><h4>What this case is really telling you</h4><p>${esc(honesty)}</p></div>
    </div>`;

  $("#ledger-sec").classList.add("hidden");
  $(".hero").classList.add("hidden");
  s.classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "instant" });

  // auto-unseal the redaction shortly after load for accessibility
  setTimeout(() => {
    const r = s.querySelector(".redact");
    if (r) r.classList.add("open");
  }, 1400);
}

// ---------- routing ----------
let cameFromBoard = false;
function showBoard() {
  $("#case").classList.add("hidden");
  $("#ledger-sec").classList.remove("hidden");
  $(".hero").classList.remove("hidden");
  cameFromBoard = true;
}
function route() {
  const h = location.hash.replace("#", "");
  if (h && BYID[h]) renderCase(BYID[h]);
  else showBoard();
}
function goBack() {
  if (cameFromBoard && history.length > 1) history.back();
  else location.hash = "";
}
window.goBack = goBack;

// ---------- boot ----------
async function boot() {
  try {
    DATA = await (await fetch("data/cases.json", { cache: "no-store" })).json();
  } catch (e) {
    $("#board").innerHTML =
      `<div class="board-load">Could not load the case ledger. ${esc(String(e))}</div>`;
    return;
  }
  renderBoard();
  renderLedger();
  document.querySelectorAll('[data-nav="top"]').forEach((a) =>
    a.addEventListener("click", (e) => {
      e.preventDefault();
      location.hash = "";
      window.scrollTo({ top: 0, behavior: "smooth" });
    }),
  );
  route();
  window.addEventListener("hashchange", route);
}
boot();
