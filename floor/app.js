const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
const money = (value) => {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return sign + "$" + Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const price = (value) => {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  const n = Number(value);
  const digits = Math.abs(n) >= 1 ? 4 : Math.abs(n) >= 0.01 ? 6 : 8;
  return "$" + n.toLocaleString("en-US", { maximumFractionDigits: digits });
};
const et = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(date) + " ET";
};
const todayET = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());

let state = null;
let ledger = { days: [] };
let seenFeed = null;
let monthCursor = null;

function tradeCard(trade) {
  const pnlClass = trade.pnl_usd > 0 ? "pos" : trade.pnl_usd < 0 ? "neg" : "";
  return `<article class="trade">
    <div class="trade-top"><strong>${esc(trade.name)} <span class="muted">${esc(trade.symbol)}</span></strong><b class="${pnlClass}">${money(trade.pnl_usd)}</b></div>
    <small>Entry ${esc(et(trade.entry_time))} @ ${esc(price(trade.entry_price))}</small>
    <small>Exit ${esc(et(trade.exit_time))} @ ${esc(price(trade.exit_price))}</small>
    ${teamLine(trade)}
    <div class="row-links">
      <a href="${esc(trade.dex_url)}" target="_blank" rel="noopener">DexScreener</a>
      <a href="${esc(trade.gmgn_url)}" target="_blank" rel="noopener">GMGN</a>
      <span class="tag">PAPER / SIMULATED</span>
    </div>
  </article>`;
}

function teamLine(trade) {
  const team = trade.team;
  if (!team) return `<small class="muted">Logged before the team vote started</small>`;
  const votes = (team.votes || []).map((v) => `<li class="vote-${esc(v.vote)}"><b>${esc(v.agent)}</b> ${esc(v.vote)} — ${esc(v.reason)}</li>`).join("");
  return `<div class="team-line"><small>Proposed by <b>${esc(trade.proposed_by || "—")}</b> · <span class="tag good">TEAM ${esc(team.tally)}</span></small>
    <details class="votes"><summary>Team vote · ${esc(team.rule)}</summary><ul>${votes}</ul></details></div>`;
}

function tokenCard(token, failed) {
  const safety = token.safety || {};
  const zone = token.in_entry_zone == null ? "ATH not measured" : token.in_entry_zone ? "in the 20–45% zone now" : "outside the buy zone now";
  const status = failed ? (token.filter_reason || safety.summary || "not eligible") : (safety.summary || "eligible");
  return `<article class="token">
    <div class="token-top"><strong>${esc(token.symbol || "TOKEN")} <span class="muted">${esc(token.name || "")}</span></strong><span class="tag ${failed ? "bad" : "good"}">${failed ? "NOT ELIGIBLE" : "ELIGIBLE"}</span></div>
    <small>Liq ${token.liquidity_usd == null ? "—" : "$" + Math.round(token.liquidity_usd).toLocaleString()} · MCap ${token.market_cap_usd == null ? "—" : "$" + Math.round(token.market_cap_usd).toLocaleString()} · ${esc(zone)}</small>
    <small>${esc(status)}</small>
    <div class="row-links">
      <a href="${esc(token.dex_url)}" target="_blank" rel="noopener">DexScreener</a>
      <a href="${esc(token.gmgn_url)}" target="_blank" rel="noopener">GMGN</a>
      <a href="${esc(token.bubble_url)}" target="_blank" rel="noopener">Bubblemaps</a>
    </div>
    ${safety.checks ? `<ul class="checks">${safety.checks.map((c) => `<li><b>${esc(c.name)}:</b> ${esc(c.detail || (c.pass ? "pass" : "fail"))}</li>`).join("")}</ul>` : ""}
  </article>`;
}

function renderStrategy(data) {
  const best = data.best;
  const body = $("strategyContent");
  if (!best) {
    body.textContent = "No strategy record yet.";
    return;
  }
  const oos = best.oos;
  body.className = "strategy-body";
  body.innerHTML = `<div class="strategy-title"><div><h3>${esc(best.id || "No champion yet")}</h3><p class="tag">PAPER / SIMULATED · BUY DIPS · NEVER TOP-TICK</p></div><span class="strategy-score">${oos ? money(oos.expectancy_usd) + " / TRADE OOS" : "UNPROVEN"}</span></div>
    <div class="strategy-stats">
      <div><span>OOS TRADES</span><strong>${oos ? oos.trades : "—"}</strong></div>
      <div><span>OOS NET</span><strong>${oos ? money(oos.net_usd) : "—"}</strong></div>
      <div><span>WIN RATE</span><strong>${oos && oos.win_rate != null ? Math.round(oos.win_rate * 100) + "%" : "—"}</strong></div>
    </div>
    <p class="strategy-note">${esc(best.name || "")}</p>
    <p class="strategy-note">${esc(data.strategist_note || "")}</p>
    <div class="risk-note"><strong>RISK · </strong>${esc(data.risk_note || "")}</div>`;
  $("bestLinkText").textContent = best.id ? best.id + " · out-of-sample champion" : "No out-of-sample champion yet";
}

function renderState(data) {
  state = data;
  $("systemState").textContent = data.ok ? (data.health?.stale_agents?.length ? "STALE AGENT" : "FLOOR ONLINE") : "ATTENTION REQUIRED";
  $("healthMetric").textContent = data.health ? (data.health.site_reachable ? "PAGES UP" : "LOCAL") : "—";
  $("lastCycle").textContent = data.last_cycle ? `Last cycle ${et(data.last_cycle)} · ${data.data_status || ""}` : "Waiting for the first cycle";
  const summary = data.summary || {};
  $("discovered").textContent = summary.discovered ?? "—";
  $("eligible").textContent = summary.eligible ?? "—";
  $("pnl").textContent = summary.paper_pnl_usd == null ? "—" : money(summary.paper_pnl_usd);
  $("pnl").className = summary.paper_pnl_usd > 0 ? "pos" : summary.paper_pnl_usd < 0 ? "neg" : "";
  renderStrategy(data);
  const watch = data.watchlist || [];
  $("watchlist").innerHTML = watch.length ? watch.map((t) => tokenCard(t, false)).join("") : `<p class="pad muted">No token passed safety and the lessons this cycle. Filter rejects and failed reviews are listed below. Nothing was invented to fill the board.</p>`;
  const rejected = [...(data.rejected_review || []), ...(data.filter_rejects_sample || [])];
  $("rejected").innerHTML = rejected.length ? `<h3 class="pad" style="margin:0">Checked, not eligible</h3>` + rejected.map((t) => tokenCard(t, true)).join("") : "";
  const trades = data.recent_trades || [];
  $("ledger").innerHTML = trades.length ? trades.map(tradeCard).join("") : `<p class="pad muted">No paper trades yet. The ledger only records simulated fills.</p>`;
  $("tradeCount").textContent = `${summary.paper_trades_total ?? 0} team paper trades`;
  const team = data.team;
  if ($("teamNote")) $("teamNote").textContent = team ? `${team.model} Last cycle: ${team.last_cycle_taken} taken, ${team.last_cycle_rejected} turned down.` : "One team, one shared paper P&L. Every trade needs a team vote.";
  ledger = data.ledger || { days: [] };
  if (!monthCursor) {
    const latest = (ledger.days || []).map((d) => d.date).sort().pop();
    monthCursor = latest ? latest.slice(0, 7) : todayET().slice(0, 7);
  }
  renderCalendar();
  const lessons = data.lessons_preview || {};
  const rules = lessons.rules || [];
  $("lessons").innerHTML = (rules.length ? rules.slice().reverse().map((rule) => `<article class="token"><strong>${esc(rule.rule)}</strong><small>${esc(et(rule.time_et || rule.time))} · ${esc(rule.source)}</small><small>${esc(rule.evidence)}</small></article>`).join("") : `<p class="pad muted">No standing rules yet.</p>`)
    + ((lessons.observations || []).slice(0, 8).map((row) => `<article class="token"><small>${esc(et(row.time_et || row.time))} · ${esc(row.source)}</small><p>${esc(row.text)}</p></article>`).join(""));
  $("agents").innerHTML = (data.agents || []).map((agent) => {
    const stale = Date.now() - new Date(agent.heartbeat || 0).getTime() > 20 * 60 * 1000;
    return `<article class="agent ${agent.status === "error" || stale ? "error" : ""}"><span class="agent-icon" style="color:#${agent.color};border-color:#${agent.color}">${esc(agent.initials)}</span><div><div class="agent-title"><strong>${esc(agent.role)}</strong><span class="agent-status">${esc(stale ? "stale" : agent.status)}</span></div><p>${esc(agent.task)}</p><time>${agent.heartbeat ? et(agent.heartbeat) : "no heartbeat"}${agent.detail ? " · " + esc(agent.detail) : ""}</time></div></article>`;
  }).join("");
  $("agentCount").textContent = `${(data.agents || []).filter((a) => a.status !== "error").length} / 6`;
  const sources = data.sources || {};
  const bits = Object.entries(sources).map(([name, info]) => `${name}: ${info && info.ok ? "ok" : "down"}${info && info.detail ? " — " + (typeof info.detail === "string" ? info.detail : JSON.stringify(info.detail)) : ""}`);
  $("opsText").textContent = (data.health ? `Local ${data.health.local ? "up" : "down"}. Pages ${data.health.site_reachable ? "up" : "not confirmed"} (${data.health.site_error || "checked " + et(data.health.checked_at)}). ` : "") + bits.join(" | ");
  $("sceneStatus").textContent = data.ok ? "AGENTS SEATED" : "CHECK ERRORS";
  if (window.setAgentData) window.setAgentData(data.agents || []);
}

function renderCalendar() {
  const [year, month] = monthCursor.split("-").map(Number);
  $("monthLabel").textContent = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(year, month - 1, 1)));
  const byDate = {};
  (ledger.days || []).forEach((day) => { byDate[day.date] = day; });
  const first = new Date(Date.UTC(year, month - 1, 1, 12)).getUTCDay();
  const count = new Date(Date.UTC(year, month, 0, 12)).getUTCDate();
  const cells = [];
  for (let i = 0; i < first; i += 1) cells.push(`<button class="cal-day empty" tabindex="-1" type="button"></button>`);
  const today = todayET();
  for (let day = 1; day <= count; day += 1) {
    const date = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const row = byDate[date];
    const klass = !row || !row.trade_count ? "flat" : row.pnl_usd > 0 ? "pos" : row.pnl_usd < 0 ? "neg" : "flat";
    cells.push(`<button type="button" class="cal-day ${klass} ${date === today ? "today" : ""}" data-date="${date}"><b>${day}</b><span>${row && row.trade_count ? money(row.pnl_usd) : ""}</span></button>`);
  }
  $("calendar").innerHTML = cells.join("");
  $("calendar").querySelectorAll("[data-date]").forEach((button) => {
    button.onclick = () => openDay(button.dataset.date);
  });
}

async function openDay(date) {
  const host = $("dayDetail");
  host.classList.remove("hidden");
  host.innerHTML = `<p class="pad muted">Loading ${esc(date)}…</p>`;
  try {
    const res = await fetch(`data/ledger/${date}.json?` + Date.now());
    if (res.status === 404) {
      host.innerHTML = `<div class="pad"><strong>${esc(date)} ET</strong><p class="muted">No simulated trades closed this day.</p></div>`;
      return;
    }
    if (!res.ok) throw new Error("HTTP " + res.status);
    const doc = await res.json();
    const total = doc.pnl_usd || 0;
    host.innerHTML = `<div class="pad"><strong>${esc(doc.date)} ET</strong> · ${doc.trade_count || 0} paper trades · <b class="${total > 0 ? "pos" : total < 0 ? "neg" : ""}">${money(total)}</b><div class="tag">PAPER / SIMULATED</div></div>`
      + ((doc.trades || []).map(tradeCard).join("") || `<p class="pad muted">No simulated trades closed this day.</p>`);
  } catch (err) {
    host.innerHTML = `<p class="pad">Could not load ${esc(date)}: ${esc(err.message)}. No trades were invented.</p>`;
  }
}

function renderFeed(feed) {
  const events = feed.events || [];
  const first = seenFeed == null;
  if (first) seenFeed = new Set(events.map((event) => event.id));
  $("feed").innerHTML = events.length ? events.map((event) => {
    const fresh = !first && !seenFeed.has(event.id);
    return `<article class="feed-item ${event.type === "error" ? "error" : ""} ${fresh ? "is-new" : ""}"><span class="feed-dot"></span><div><div class="feed-head"><strong>${esc(event.agent)}</strong><time>${esc(et(event.time))}</time></div>${event.trade ? tradeCard(event.trade) : `<p>${esc(event.text)}</p>`}</div></article>`;
  }).join("") : `<p class="pad muted">Waiting for the first transmission.</p>`;
  events.forEach((event) => seenFeed.add(event.id));
  $("feedUpdated").textContent = feed.updated ? et(feed.updated) : "WAITING";
}

async function loadJSON(path) {
  const res = await fetch(path + "?" + Date.now());
  if (!res.ok) throw new Error(path + " HTTP " + res.status);
  return res.json();
}

async function loadState() {
  try {
    renderState(await loadJSON("data/research.json"));
  } catch (err) {
    $("systemState").textContent = "DATA UNREADABLE";
    $("strategyContent").textContent = err.message + ". Retrying. No simulated numbers were substituted.";
  }
}

async function loadFeed() {
  try {
    renderFeed(await loadJSON("data/feed.json"));
  } catch (err) {
    $("feed").innerHTML = `<p class="pad">Feed unavailable: ${esc(err.message)}</p>`;
  }
}

function tick() {
  if (!state?.next_cycle) return;
  const left = Math.max(0, Math.floor((new Date(state.next_cycle) - Date.now()) / 1000));
  $("countdown").textContent = `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
}

$("prevMonth").onclick = () => { shiftMonth(-1); };
$("nextMonth").onclick = () => { shiftMonth(1); };
function shiftMonth(delta) {
  if (!monthCursor) monthCursor = todayET().slice(0, 7);
  const [year, month] = monthCursor.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1 + delta, 1));
  monthCursor = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
  renderCalendar();
}

loadState();
loadFeed();
setInterval(loadState, 20000);
setInterval(loadFeed, 12000);
setInterval(tick, 1000);
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
