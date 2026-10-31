"use strict";

const DAY = 86400000;
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"];
const CELLULOID = new Set(["35mm", "70mm", "16mm", "35mm IB Tech", "Nitrate", "8mm", "Super 8"]);
const SPECIAL_EVENTS = new Set(["Q&A", "Intro/guest", "Premiere", "Double feature", "Live music", "Opening night", "Nitrate"]);
const STOPWORDS = new Set(("the a an of and in on to for with at from by is it my me you your i his her " +
  "de la le el los las les du des di il en y o part vol ii iii 2 3 4 & -").split(" "));

let ALL = [];        // every listing
let VENUES = {};     // venue -> chain, from the Venues tab
let today = 0;       // day number (days since 1970-01-01) in Los Angeles
let weeksMode = "films";
const charts = {};

// ---------- parsing ----------

function dayNum(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return Math.round(Date.UTC(y, m - 1, d) / DAY);
}
function fromDay(n) { return new Date(n * DAY); }
function weekday(n) { return fromDay(n).getUTCDay(); }
function fmtDay(n, opts = { weekday: "short", month: "short", day: "numeric" }) {
  return fromDay(n).toLocaleDateString("en-US", { ...opts, timeZone: "UTC" });
}
function fridayOf(n) { return n - ((weekday(n) - 5 + 7) % 7); }

// "7:30 pm", "6:30 PM, 10:30 PM", "9.45 pm" -> minutes after midnight; small hours count as the night before.
function parseTimes(text) {
  const out = [];
  for (const m of (text || "").matchAll(/(\d{1,2})(?:[:.](\d{2}))?\s*([ap])\.?\s*m\b/gi)) {
    let h = Number(m[1]) % 12;
    if (m[3].toLowerCase() === "p") h += 12;
    let mins = h * 60 + Number(m[2] || 0);
    if (mins < 5 * 60) mins += 24 * 60;
    out.push(mins);
  }
  return out;
}
function fmtTime(mins) {
  const h24 = Math.floor(mins / 60) % 24, m = mins % 60;
  const h = h24 % 12 || 12;
  return `${h}:${String(m).padStart(2, "0")} ${h24 < 12 ? "am" : "pm"}`;
}
function hourLabel(h) {
  const h24 = h % 24, ap = h24 < 12 ? "a" : "p";
  return `${h24 % 12 || 12}${ap}`;
}
function split(text) { return (text || "").split(";").map(s => s.trim()).filter(Boolean); }
function filmKey(title) { return title.toLowerCase().replace(/[’']/g, "'").replace(/\s+/g, " ").trim(); }

function load(data) {
  const col = Object.fromEntries(data.columns.map((c, i) => [c, i]));
  VENUES = Object.fromEntries((data.venues || []).map(v => [v.venue, v.chain]));
  ALL = data.rows.map(r => {
    const start = dayNum(r[col["Start date"]]);
    const end = Math.max(start, dayNum(r[col["End date"]] || r[col["Start date"]]));
    const venue = r[col["Venue"]];
    const year = parseInt(r[col["Year"]], 10);
    return {
      venue,
      chain: VENUES[venue] || r[col["Chain or group"]] || venue,
      screen: r[col["Screen"]],
      title: r[col["Title"]],
      key: filmKey(r[col["Title"]]),
      year: year > 1880 && year < 2100 ? year : null,
      director: r[col["Director"]],
      start, end,
      listed: r[col["Dates (as listed)"]],
      timesText: r[col["Times"]],
      times: parseTimes(r[col["Times"]]),
      formats: split(r[col["Format"]]),
      events: split(r[col["Events"]]),
      series: r[col["Series"]],
      notes: r[col["Notes"]],
      link: r[col["Link"]],
    };
  });
}

// ---------- filters ----------

function setupFilters() {
  const venueSel = document.getElementById("f-venue");
  const byChain = {};
  for (const r of ALL) (byChain[r.chain] ||= new Set()).add(r.venue);
  for (const chain of Object.keys(byChain).sort()) {
    const venues = [...byChain[chain]].sort();
    if (venues.length === 1) {
      venueSel.add(new Option(venues[0], "v:" + venues[0]));
      continue;
    }
    const group = document.createElement("optgroup");
    group.label = chain;
    group.append(new Option(`All ${chain}`, "c:" + chain));
    for (const v of venues) group.append(new Option(v, "v:" + v));
    venueSel.append(group);
  }

  const whenSel = document.getElementById("f-when");
  whenSel.add(new Option("So far this year", "past"));
  whenSel.add(new Option("Coming up", "future"));
  const months = new Set(ALL.map(r => fromDay(r.start).toISOString().slice(0, 7)));
  for (const m of [...months].sort()) {
    const [y, mo] = m.split("-").map(Number);
    whenSel.add(new Option(`${MONTHS[mo - 1]} ${y}`, "m:" + m));
  }

  const params = new URLSearchParams(location.search);
  if (params.get("venue")) venueSel.value = params.get("venue");
  if (params.get("when")) whenSel.value = params.get("when");
  document.getElementById("f-repertory").checked = params.get("rep") === "1";

  for (const id of ["f-venue", "f-when", "f-repertory"]) {
    document.getElementById(id).addEventListener("change", () => { saveParams(); render(); });
  }
}

function saveParams() {
  const p = new URLSearchParams();
  const v = document.getElementById("f-venue").value, w = document.getElementById("f-when").value;
  if (v) p.set("venue", v);
  if (w !== "all") p.set("when", w);
  if (document.getElementById("f-repertory").checked) p.set("rep", "1");
  history.replaceState(null, "", p.toString() ? "?" + p : location.pathname);
}

function period() {
  const w = document.getElementById("f-when").value;
  if (w === "past") return [-Infinity, today];
  if (w === "future") return [today, Infinity];
  if (w.startsWith("m:")) {
    const [y, m] = w.slice(2).split("-").map(Number);
    return [Math.round(Date.UTC(y, m - 1, 1) / DAY), Math.round(Date.UTC(y, m, 1) / DAY) - 1];
  }
  return [-Infinity, Infinity];
}

function filtered() {
  const v = document.getElementById("f-venue").value;
  const rep = document.getElementById("f-repertory").checked;
  const [a, b] = period();
  return ALL.filter(r =>
    r.start <= b && r.end >= a &&
    (!v || (v.startsWith("v:") ? r.venue === v.slice(2) : r.chain === v.slice(2))) &&
    (!rep || r.chain !== "AMC Theatres"));
}

// ---------- helpers ----------

const fmt = n => n.toLocaleString("en-US");
const pct = (a, b) => b ? Math.round(100 * a / b) : 0;
function countBy(items, keyFn) {
  const m = new Map();
  for (const it of items) {
    const keys = keyFn(it);
    for (const k of Array.isArray(keys) ? keys : [keys]) if (k !== null && k !== undefined && k !== "") m.set(k, (m.get(k) || 0) + 1);
  }
  return m;
}
function topN(map, n) { return [...map.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]))).slice(0, n); }
function displayTitles(rows) {
  // Most common spelling of each title.
  const spell = new Map();
  for (const r of rows) {
    const m = spell.get(r.key) || new Map();
    m.set(r.title, (m.get(r.title) || 0) + 1);
    spell.set(r.key, m);
  }
  return new Map([...spell].map(([k, m]) => [k, topN(m, 1)[0][0]]));
}
function esc(s) { return String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function trunc(s, n = window.innerWidth < 600 ? 18 : 34) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }

// ---------- charts ----------

function baseOptions(horizontal) {
  const grid = css("--grid"), text = css("--text-2");
  const valueAxis = { beginAtZero: true, grid: { color: grid }, border: { display: false }, ticks: { color: text, precision: 0 } };
  const catAxis = { grid: { display: false }, border: { color: grid }, ticks: { color: text, autoSkip: !horizontal } };
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? "y" : "x",
    animation: { duration: 250 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: css("--surface"), titleColor: css("--text"), bodyColor: css("--text-2"),
        borderColor: css("--border"), borderWidth: 1, padding: 10, displayColors: false,
      },
    },
    scales: horizontal ? { x: valueAxis, y: catAxis } : { x: catAxis, y: valueAxis },
  };
}

function barChart(id, labels, values, { horizontal = false, colors, tooltip, onClick, boxId, title } = {}) {
  charts[id]?.destroy();
  const box = boxId ? document.getElementById(boxId) : null;
  if (box) {
    box.style.height = horizontal ? `${Math.max(120, labels.length * 24 + 40)}px` : (box.dataset.h || box.style.height);
    box.querySelector(".empty")?.remove();
    box.querySelector("canvas").hidden = false;
  }
  const opts = baseOptions(horizontal);
  if (tooltip) opts.plugins.tooltip.callbacks = tooltip;
  if (title) opts.plugins.tooltip.callbacks = { title, ...(tooltip || {}) };
  if (horizontal) opts.scales.y.ticks.callback = function (v) { return trunc(this.getLabelForValue(v)); };
  if (onClick) {
    opts.onClick = (_, els) => { if (els.length) onClick(els[0].index); };
    opts.onHover = (e, els) => { e.native.target.style.cursor = els.length ? "pointer" : "default"; };
  }
  charts[id] = new Chart(document.getElementById(id), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors || css("--series"),
        hoverBackgroundColor: colors || css("--series"),
        borderRadius: 4,
        borderSkipped: "start",
        borderWidth: 0,
        maxBarThickness: horizontal ? 18 : 40,
        categoryPercentage: 0.85,
        barPercentage: 0.9,
      }],
    },
    options: opts,
  });
}

function emptyState(boxId, chartId, message) {
  charts[chartId]?.destroy();
  delete charts[chartId];
  const box = document.getElementById(boxId);
  if (box.style.height !== "auto") box.dataset.h ||= box.style.height;
  box.style.height = "auto";
  box.querySelector("canvas").hidden = true;
  let el = box.querySelector(".empty");
  if (!el) { el = document.createElement("div"); el.className = "empty"; box.append(el); }
  el.textContent = message;
}

// ---------- sections ----------

function renderTiles(rows, titles) {
  const films = new Set(rows.map(r => r.key));
  const venues = new Set(rows.map(r => r.venue));
  const showtimes = rows.reduce((n, r) => n + r.times.length, 0);
  const celluloid = rows.filter(r => r.formats.some(f => CELLULOID.has(f))).length;
  const guests = rows.filter(r => r.events.some(e => e === "Q&A" || e === "Intro/guest")).length;
  const once = [...countBy(rows, r => r.key).values()].filter(n => n === 1).length;
  const tiles = [
    [fmt(rows.length), "listings", `${fmt(showtimes)} showtimes spelled out`],
    [fmt(films.size), "different films", `${pct(once, films.size)}% played just once`],
    [fmt(venues.size), "theaters", ""],
    [fmt(celluloid), "on film", "35mm, 70mm, 16mm, and nitrate"],
    [fmt(guests), "with Q&As or guests", ""],
  ];
  document.getElementById("tiles").innerHTML = tiles.map(([n, l, h]) =>
    `<div class="tile"><div class="num">${n}</div><div class="label">${l}</div>${h ? `<div class="hint">${h}</div>` : ""}</div>`).join("");
}

function renderSpecials(rows) {
  const card = document.getElementById("specials-card");
  const soon = rows.filter(r => r.end >= today && r.start <= today + 6 &&
    (r.formats.some(f => CELLULOID.has(f)) || r.events.some(e => SPECIAL_EVENTS.has(e))))
    .sort((a, b) => Math.max(a.start, today) - Math.max(b.start, today) || (a.times[0] || 0) - (b.times[0] || 0));
  card.hidden = !soon.length;
  const list = document.getElementById("specials");
  list.classList.remove("open");
  const more = document.getElementById("specials-more");
  more.hidden = soon.length <= 8;
  more.textContent = `Show all ${Math.min(soon.length, 40)}`;
  list.innerHTML = soon.slice(0, 40).map(r => {
    const when = r.start === r.end ? fmtDay(r.start) : `${fmtDay(Math.max(r.start, today))} to ${fmtDay(r.end)}`;
    const badges = [...r.formats.filter(f => CELLULOID.has(f)), ...r.events.filter(e => SPECIAL_EVENTS.has(e))];
    const title = r.link ? `<a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(r.title)}</a>` : esc(r.title);
    return `<li><div class="t">${title}</div><div class="m">${esc(r.venue)} · ${when}${r.times.length ? " · " + r.times.map(fmtTime).join(", ") : ""}</div>` +
      badges.map(b => `<span class="badge">${esc(b)}</span>`).join("") + "</li>";
  }).join("");
}

function renderWeeks(rows) {
  if (!rows.length) return emptyState("weeks-box", "c-weeks", "Nothing matches these filters.");
  const lo = fridayOf(Math.min(...rows.map(r => r.start)));
  const hi = fridayOf(Math.max(...rows.map(r => weeksMode === "films" ? Math.min(r.end, r.start + 60) : r.start)));
  const weeks = [];
  for (let w = lo; w <= hi; w += 7) weeks.push(w);
  let values;
  if (weeksMode === "films") {
    const sets = weeks.map(() => new Set());
    for (const r of rows) {
      for (let i = 0; i < weeks.length; i++) {
        if (r.start <= weeks[i] + 6 && r.end >= weeks[i]) sets[i].add(r.key);
      }
    }
    values = sets.map(s => s.size);
  } else {
    const counts = countBy(rows, r => fridayOf(r.start));
    values = weeks.map(w => counts.get(w) || 0);
  }
  const thisWeek = fridayOf(today);
  const colors = weeks.map(w => w === thisWeek ? css("--accent") : css("--series"));
  const unit = weeksMode === "films" ? "different films" : "new listings";
  barChart("c-weeks", weeks.map(w => fmtDay(w, { month: "short", day: "numeric" })), values, {
    colors, boxId: "weeks-box",
    tooltip: {
      title: items => `Week of ${fmtDay(weeks[items[0].dataIndex], { month: "long", day: "numeric" })}` +
        (weeks[items[0].dataIndex] === thisWeek ? " (this week)" : ""),
      label: item => `${fmt(item.raw)} ${unit}`,
    },
  });
  const best = values.indexOf(Math.max(...values));
  document.getElementById("weeks-sub").textContent =
    `Weeks run Friday to Thursday, like the tracker. Busiest: the week of ${fmtDay(weeks[best], { month: "long", day: "numeric" })}, with ${fmt(values[best])} ${unit}. This week is in orange.`;
}

function horizontalCounts(id, boxId, entries, unit, opts = {}) {
  if (!entries.length) return emptyState(boxId, id, opts.empty || "Nothing matches these filters.");
  barChart(id, entries.map(e => e[0]), entries.map(e => e[1]), {
    horizontal: true, boxId,
    tooltip: { label: item => `${fmt(item.raw)} ${unit}` + (opts.extra ? opts.extra(item.dataIndex) : "") },
    title: items => entries[items[0].dataIndex][0],
    onClick: opts.onClick,
  });
}

function renderVenues(rows) {
  const entries = topN(countBy(rows, r => r.venue), 40);
  horizontalCounts("c-venues", "venues-box", entries, "listings", {
    onClick: i => { document.getElementById("f-venue").value = "v:" + entries[i][0]; saveParams(); render(); },
  });
}

function renderFilms(rows, titles) {
  const entries = topN(countBy(rows, r => r.key), 20);
  const venuesPer = new Map();
  for (const r of rows) (venuesPer.get(r.key) || venuesPer.set(r.key, new Set()).get(r.key)).add(r.venue);
  horizontalCounts("c-films", "films-box", entries.map(([k, n]) => [titles.get(k), n]), "listings", {
    extra: i => ` at ${venuesPer.get(entries[i][0]).size} theaters`,
    onClick: i => lookup(titles.get(entries[i][0])),
  });
  const spread = topN(new Map([...venuesPer].map(([k, s]) => [k, s.size])), 15);
  horizontalCounts("c-spread", "spread-box", spread.map(([k, n]) => [titles.get(k), n]), "theaters", {
    onClick: i => lookup(titles.get(spread[i][0])),
  });
}

function renderHours(rows) {
  const counts = new Map();
  let total = 0;
  for (const r of rows) for (const t of r.times) { const h = Math.floor(t / 60); counts.set(h, (counts.get(h) || 0) + 1); total++; }
  if (!total) {
    document.getElementById("hours-sub").textContent = "Every listed showtime, by the hour it starts.";
    return emptyState("hours-box", "c-hours", "No showtimes listed in this selection.");
  }
  const hours = [...counts.keys()];
  const lo = Math.min(...hours), hi = Math.max(...hours);
  const labels = [], values = [];
  for (let h = lo; h <= hi; h++) { labels.push(hourLabel(h)); values.push(counts.get(h) || 0); }
  barChart("c-hours", labels, values, {
    boxId: "hours-box",
    tooltip: {
      title: items => `${fmtTime((lo + items[0].dataIndex) * 60)} to ${fmtTime((lo + items[0].dataIndex) * 60 + 59)}`,
      label: item => `${fmt(item.raw)} showtimes (${pct(item.raw, total)}%)`,
    },
  });
  const peak = lo + values.indexOf(Math.max(...values));
  const late = rows.reduce((n, r) => n + r.times.filter(t => t >= 23 * 60).length, 0);
  document.getElementById("hours-sub").textContent =
    `${fmt(total)} showtimes, by the hour they start. Peak hour: ${fmtTime(peak * 60)}. ${fmt(late)} start at 11 pm or later.`;
}

function renderHeat(rows) {
  const el = document.getElementById("heat");
  const grid = Array.from({ length: 7 }, () => new Map());
  let lo = Infinity, hi = -Infinity, max = 0;
  for (const r of rows) {
    if (r.start !== r.end) continue;
    const d = (weekday(r.start) + 6) % 7;  // Monday first
    for (const t of r.times) {
      // After-midnight shows belong to the night they started.
      const h = Math.floor(t / 60);
      grid[d].set(h, (grid[d].get(h) || 0) + 1);
      lo = Math.min(lo, h); hi = Math.max(hi, h); max = Math.max(max, grid[d].get(h));
    }
  }
  if (!max) { el.innerHTML = `<div class="empty">No single-date showtimes in this selection.</div>`; return; }
  const steps = 7;
  const level = n => n ? Math.min(steps, 1 + Math.floor((steps - 1) * Math.sqrt(n / max) + 0.0001)) : 0;
  const cols = hi - lo + 1;
  el.style.gridTemplateColumns = `40px repeat(${cols}, minmax(22px, 1fr))`;
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const fullDays = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"];
  let html = "<div></div>";
  for (let h = lo; h <= hi; h++) html += `<div class="cl">${(h - lo) % 2 === 0 ? hourLabel(h) : ""}</div>`;
  days.forEach((name, d) => {
    html += `<div class="rl">${name}</div>`;
    for (let h = lo; h <= hi; h++) {
      const n = grid[d].get(h) || 0;
      html += `<div class="cell" style="background:var(--heat-${level(n)})" data-tip="${fullDays[d]}, ${fmtTime(h * 60)}: ${fmt(n)} showtimes"></div>`;
    }
  });
  el.innerHTML = html;
  const legend = document.createElement("div");
  legend.className = "legend-ramp";
  legend.style.gridColumn = "1 / -1";
  legend.innerHTML = "Fewer " + Array.from({ length: steps + 1 }, (_, i) => `<span class="sw" style="background:var(--heat-${i})"></span>`).join("") + " More";
  el.append(legend);
}

function renderFormats(rows) {
  const entries = topN(countBy(rows, r => r.formats), 16);
  horizontalCounts("c-formats", "formats-box", entries, "listings", { empty: "No formats listed in this selection." });
}

function renderEvents(rows) {
  const entries = topN(countBy(rows, r => r.events.filter(e => e !== "Sold out")), 12);
  horizontalCounts("c-events", "events-box", entries, "listings", { empty: "No special events in this selection." });
}

function renderDecades(rows) {
  const films = new Map();
  for (const r of rows) if (!films.has(r.key) || r.year) films.set(r.key, r.year);
  const dated = [...films.values()].filter(Boolean);
  const sub = document.getElementById("decades-sub");
  if (dated.length < 5) {
    sub.textContent = "Films by release decade.";
    return emptyState("decades-box", "c-decades",
      `Release years aren't filled in yet (${fmt(dated.length)} of ${fmt(films.size)} films have one). ` +
      "This chart fills in as years are added to the sheet's Films tab.");
  }
  const counts = countBy(dated, y => Math.floor(y / 10) * 10);
  const decades = [...counts.keys()].sort((a, b) => a - b);
  const all = [];
  for (let d = decades[0]; d <= decades[decades.length - 1]; d += 10) all.push(d);
  barChart("c-decades", all.map(d => `${d}s`), all.map(d => counts.get(d) || 0), {
    boxId: "decades-box",
    tooltip: { label: item => `${fmt(item.raw)} films` },
  });
  const oldest = Math.min(...dated);
  sub.textContent = `Films by release decade (${fmt(dated.length)} of ${fmt(films.size)} films have a year). Oldest: ${oldest}.`;
}

function renderDirectors(rows) {
  const withDir = rows.filter(r => r.director);
  const entries = topN(countBy(withDir, r => r.director.split(/\s*[,;&]\s*|\s+and\s+/).filter(Boolean)), 15);
  const sub = document.getElementById("directors-sub");
  if (entries.length < 3) {
    sub.textContent = "Directors with the most listings.";
    return emptyState("directors-box", "c-directors",
      `Directors aren't filled in yet (${fmt(withDir.length)} listings have one). ` +
      "This chart fills in as directors are added to the sheet.");
  }
  sub.textContent = `Directors with the most listings (${pct(withDir.length, rows.length)}% of listings name a director).`;
  horizontalCounts("c-directors", "directors-box", entries, "listings", { onClick: i => lookup(entries[i][0]) });
}

function renderSeries(rows) {
  const entries = topN(countBy(rows, r => r.series), 15);
  horizontalCounts("c-series", "series-box", entries, "listings", {
    empty: "No series or festivals in this selection.",
    onClick: i => lookup(entries[i][0]),
  });
}

// ---------- fun facts ----------

function renderFacts(rows, titles) {
  const facts = [];
  const add = (k, v, d) => facts.push(`<div class="fact"><div class="k">${k}</div><div class="v">${v}</div><div class="d">${d}</div></div>`);
  if (!rows.length) { document.getElementById("facts").innerHTML = ""; return; }

  // Most-traveled film
  const venuesPer = new Map();
  for (const r of rows) (venuesPer.get(r.key) || venuesPer.set(r.key, new Set()).get(r.key)).add(r.venue);
  const [travKey, travSet] = [...venuesPer].sort((a, b) => b[1].size - a[1].size)[0];
  add("Most-traveled film", esc(titles.get(travKey)), `Played ${travSet.size} different theaters.`);

  // Repeat champion at a single theater (repertory only, so a two-week AMC run doesn't win).
  const pair = countBy(rows.filter(r => r.start === r.end), r => r.venue + "\u0000" + r.key);
  if (pair.size) {
    const [[pk, pn]] = topN(pair, 1);
    const [pv, pf] = pk.split("\u0000");
    if (pn > 1) add("Can't get enough", esc(titles.get(pf)), `${pn} separate dates at ${esc(pv)}.`);
  }

  // Longest stay on LA screens
  const span = new Map();
  for (const r of rows) {
    const s = span.get(r.key) || [Infinity, -Infinity];
    span.set(r.key, [Math.min(s[0], r.start), Math.max(s[1], r.end)]);
  }
  const [lk, [la, lb]] = [...span].sort((a, b) => (b[1][1] - b[1][0]) - (a[1][1] - a[1][0]))[0];
  if (lb > la) add("Staying power", esc(titles.get(lk)), `First listed ${fmtDay(la, { month: "short", day: "numeric" })}, last listed ${fmtDay(lb, { month: "short", day: "numeric" })}: ${fmt(Math.round((lb - la) / 7))} weeks apart.`);

  // One and done
  const perFilm = countBy(rows, r => r.key);
  const once = [...perFilm.values()].filter(n => n === 1).length;
  add("One and done", `${pct(once, perFilm.size)}%`, `of films got exactly one listing: ${fmt(once)} of ${fmt(perFilm.size)}.`);

  // Busiest single day
  const daily = new Map();
  for (const r of rows) if (r.start === r.end) daily.set(r.start, (daily.get(r.start) || 0) + Math.max(1, r.times.length));
  if (daily.size) {
    const [[bd, bn]] = topN(daily, 1);
    add("Busiest night out", fmtDay(bd, { weekday: "long", month: "long", day: "numeric" }), `${fmt(bn)} one-day screenings across town.`);
  }

  // Night owls and early birds
  const timed = rows.flatMap(r => r.times.map(t => [t, r]));
  if (timed.length) {
    const late = timed.reduce((a, b) => b[0] > a[0] ? b : a);
    const early = timed.reduce((a, b) => b[0] < a[0] ? b : a);
    add("Night owl special", esc(late[1].title), `Starts at ${fmtTime(late[0])} at ${esc(late[1].venue)}.`);
    add("Early bird special", esc(early[1].title), `Starts at ${fmtTime(early[0])} at ${esc(early[1].venue)}.`);
    const midnight = countBy(timed.filter(([t]) => t >= 23 * 60 + 30), ([, r]) => r.venue);
    if (midnight.size) {
      const [[mv, mn]] = topN(midnight, 1);
      add("Midnight movie capital", esc(mv), `${fmt(mn)} shows starting 11:30 pm or later.`);
    }
  }

  // Most adventurous programmer: the most different films per listing (at least 30 listings).
  const vl = countBy(rows, r => r.venue);
  const vf = new Map();
  for (const r of rows) (vf.get(r.venue) || vf.set(r.venue, new Set()).get(r.venue)).add(r.key);
  const adventurous = [...vl].filter(([, n]) => n >= 30).map(([v, n]) => [v, vf.get(v).size, n])
    .sort((a, b) => b[1] / b[2] - a[1] / a[2] || b[1] - a[1])[0];
  if (adventurous) add("Most adventurous programming", esc(adventurous[0]), `${fmt(adventurous[1])} different films in ${fmt(adventurous[2])} listings.`);
  const most = [...vf].sort((a, b) => b[1].size - a[1].size)[0];
  if (most) add("Biggest menu", esc(most[0]), `${fmt(most[1].size)} different films.`);

  // Celluloid champion
  const film = countBy(rows.filter(r => r.formats.some(f => CELLULOID.has(f))), r => r.venue);
  if (film.size) {
    const [[cv, cn]] = topN(film, 1);
    add("Celluloid champion", esc(cv), `${fmt(cn)} listings projected on film.`);
  }

  // Double features
  const dfs = rows.filter(r => r.events.includes("Double feature"));
  if (dfs.length) {
    const dfv = topN(countBy(dfs, r => r.venue), 1)[0];
    add("Double the fun", `${fmt(Math.round(dfs.length / 2))} double bills`, `${esc(dfv[0])} ran the most.`);
  }

  // Titles
  const uniq = [...titles.values()];
  const longest = uniq.reduce((a, b) => b.length > a.length ? b : a);
  const shortest = uniq.filter(t => t.trim().length > 0).reduce((a, b) => b.length < a.length ? b : a);
  add("Longest title", esc(longest), `${longest.length} characters.`);
  add("Shortest title", esc(shortest), `${shortest.length} character${shortest.length === 1 ? "" : "s"}.`);
  const words = countBy(uniq, t => [...new Set(t.toLowerCase().replace(/[^a-z0-9' ]/g, " ").split(/\s+/))]
    .filter(w => w.length > 2 && !STOPWORDS.has(w)));
  if (words.size) {
    const [[w, n]] = topN(words, 1);
    add("Favorite word", `“${esc(w[0].toUpperCase() + w.slice(1))}”`, `Appears in ${fmt(n)} film titles.`);
  }

  // Sequels
  const sequels = uniq.filter(t => /\b(2|3|4|5|II|III|IV|Part \w+)\b/.test(t)).length;
  if (sequels) add("Sequel watch", fmt(sequels), `titles with a number in them (looking at you, ${esc(uniq.find(t => /\b(2|II)\b/.test(t)) || "sequels")}).`);

  // Oldest film, once years are in
  const dated = rows.filter(r => r.year);
  if (dated.length) {
    const old = dated.reduce((a, b) => b.year < a.year ? b : a);
    add("Oldest film", esc(old.title), `From ${old.year}, at ${esc(old.venue)}.`);
  }

  document.getElementById("facts").innerHTML = facts.join("");
}

// ---------- lookup ----------

let lookupRows = [];
function lookup(text) {
  const q = document.getElementById("q");
  q.value = text;
  renderLookup();
  document.getElementById("lookup").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderLookup() {
  const q = document.getElementById("q").value.trim().toLowerCase();
  const body = document.getElementById("q-rows"), count = document.getElementById("q-count");
  if (!q) {
    body.innerHTML = "";
    count.textContent = `${fmt(lookupRows.length)} listings in the current filter.`;
    return;
  }
  const hits = lookupRows.filter(r =>
    r.key.includes(q) || (r.director || "").toLowerCase().includes(q) || (r.series || "").toLowerCase().includes(q) ||
    (r.notes || "").toLowerCase().includes(q) || r.formats.some(f => f.toLowerCase() === q) || r.venue.toLowerCase().includes(q))
    .sort((a, b) => a.start - b.start);
  count.textContent = `${fmt(hits.length)} listing${hits.length === 1 ? "" : "s"}${hits.length > 300 ? ", showing the first 300" : ""}.`;
  body.innerHTML = hits.slice(0, 300).map(r => {
    const dates = r.start === r.end ? fmtDay(r.start) : `${fmtDay(r.start)} to ${fmtDay(r.end)}`;
    const extras = [...r.formats, ...r.events, r.series].filter(Boolean).map(esc).join(" · ");
    const title = r.link ? `<a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(r.title)}</a>` : esc(r.title);
    const meta = [r.year, r.director].filter(Boolean).join(", ");
    return `<tr><td class="film">${title}${meta ? ` <span class="dir">(${esc(meta)})</span>` : ""}</td><td>${esc(r.venue)}${r.screen ? `<br><span class="dir">${esc(r.screen)}</span>` : ""}</td>` +
      `<td>${dates}</td><td>${esc(r.timesText)}</td><td>${extras}</td></tr>`;
  }).join("");
}

// ---------- heatmap tooltip ----------

function setupTip() {
  const tip = document.getElementById("tip");
  const heat = document.getElementById("heat");
  heat.addEventListener("mousemove", e => {
    const t = e.target.closest("[data-tip]");
    if (!t) { tip.hidden = true; return; }
    tip.textContent = t.dataset.tip;
    tip.hidden = false;
    const x = Math.min(e.clientX + 12, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = x + "px";
    tip.style.top = (e.clientY + 14) + "px";
  });
  heat.addEventListener("mouseleave", () => { tip.hidden = true; });
}

// ---------- main ----------

function render() {
  const rows = filtered();
  const titles = displayTitles(rows);
  lookupRows = rows;
  renderTiles(rows, titles);
  renderSpecials(rows);
  renderWeeks(rows);
  renderVenues(rows);
  renderFilms(rows, titles);
  renderHours(rows);
  renderHeat(rows);
  renderFormats(rows);
  renderEvents(rows);
  renderDecades(rows);
  renderDirectors(rows);
  renderSeries(rows);
  renderFacts(rows, titles);
  renderLookup();
}

async function main() {
  today = dayNum(new Intl.DateTimeFormat("en-CA", { timeZone: "America/Los_Angeles" }).format(new Date()));
  const updated = document.getElementById("updated");
  let data;
  try {
    const res = await fetch("data/tinseltown.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(res.status);
    data = await res.json();
  } catch (err) {
    updated.textContent = "Couldn't load the tracker data. Try reloading in a minute.";
    return;
  }
  load(data);
  const when = new Date(data.updated);
  updated.textContent = `${fmt(ALL.length)} listings · updated ${when.toLocaleString("en-US", {
    timeZone: "America/Los_Angeles", month: "long", day: "numeric", hour: "numeric", minute: "2-digit" })} Pacific`;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  setupFilters();
  setupTip();
  document.querySelectorAll("[data-weeks]").forEach(b => b.addEventListener("click", () => {
    weeksMode = b.dataset.weeks;
    document.querySelectorAll("[data-weeks]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    renderWeeks(filtered());
  }));
  document.getElementById("q").addEventListener("input", renderLookup);
  document.getElementById("specials-more").addEventListener("click", e => {
    document.getElementById("specials").classList.add("open");
    e.target.hidden = true;
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
  render();
}

main();
