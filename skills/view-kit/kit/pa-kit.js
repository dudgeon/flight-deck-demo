/* Product Aviator view kit runtime.
   Reads a view spec (#pa-spec) and a dataset (#pa-data) from the page and draws
   one of the standard layouts: tree-table, board, detail, summary, form.
   No dependencies, no network. Works in the Omnigent viewer, in the preview
   harness, and opened as a plain file. See references/spec.md. */
(function () {
  "use strict";

  function readJson(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback;
    try { return JSON.parse(el.textContent || "null") || fallback; } catch (e) { return fallback; }
  }
  var spec = readJson("pa-spec", {});
  var data = readJson("pa-data", { records: [] });
  var root = document.documentElement;
  var host = root.getAttribute("data-host") || spec.host || "canvas";
  root.setAttribute("data-host", host);
  var inHarness = root.hasAttribute("data-harness");
  var app = document.getElementById("pa-app");
  var KEY = "pa:" + (spec.view || spec.title || "view");
  /* Each stage of a flow may keep its own status field, e.g. "explore_status". */
  var SF = spec.status_field || "status";

  /* ---------- state that survives a redraw and, where the host allows, a reload ---------- */
  var state = { detail: [], wide: false, collapsed: {}, filter: null, edits: {}, direct: {}, sent: false, answers: {}, answered: false, asking: null };
  (function load() {
    var saved = null;
    try { saved = window.omnigent && window.omnigent.state && window.omnigent.state[KEY]; } catch (e) {}
    if (!saved) { try { saved = JSON.parse(sessionStorage.getItem(KEY) || "null"); } catch (e) {} }
    if (saved && typeof saved === "object") for (var k in state) if (k in saved) state[k] = saved[k];
    state.asking = null;
  })();
  var saveTimer = null;
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      var snap = JSON.parse(JSON.stringify(state));
      try { if (window.omnigent && window.omnigent.saveState) window.omnigent.saveState(KEY, snap); } catch (e) {}
      try { sessionStorage.setItem(KEY, JSON.stringify(snap)); } catch (e) {}
    }, 60);
  }

  /* ---------- helpers ---------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  var byId = {};
  function index() { byId = {}; recs().forEach(function (r) { byId[r.id] = r; }); }
  function recs() { return Array.isArray(data.records) ? data.records : []; }
  function val(rec, field) {
    if (!rec) return undefined;
    var e = state.edits[rec.id];
    if (e && field in e) return e[field];
    var d = state.direct[rec.id];
    return d && field in d ? d[field].v : rec[field];
  }
  function isEdited(rec, field) {
    var e = state.edits[rec.id];
    return !!e && (field ? field in e : Object.keys(e).length > 0);
  }
  function match(rec, where) {
    if (!where) return true;
    for (var k in where) {
      var want = where[k], got = val(rec, k);
      if (want && typeof want === "object" && !Array.isArray(want)) {
        if ("not" in want && [].concat(want.not).indexOf(got) !== -1) return false;
        if ("exists" in want && (got != null && got !== "" && got !== false) !== !!want.exists) return false;
      } else if ([].concat(want).indexOf(got == null ? null : got) === -1) return false;
    }
    return true;
  }
  function fmt(tpl, rec) {
    return String(tpl == null ? "" : tpl).replace(/\{([\w.\-]+)\}/g, function (_, key) {
      if (key.indexOf("dataset.") === 0) return data[key.slice(8)] == null ? "" : data[key.slice(8)];
      if (key === "dataset") return spec.dataset || "";
      var v = rec ? val(rec, key) : undefined;
      return v == null ? "" : Array.isArray(v) ? v.join(", ") : v;
    });
  }
  function label(field) {
    return String(field).replace(/[_-]+/g, " ").replace(/^\w/, function (c) { return c.toUpperCase(); });
  }
  function collection() { return recs().filter(function (r) { return match(r, spec.records); }); }
  function childrenOf(id, where, link) {
    link = link || "parent";
    return recs().filter(function (r) { return r[link] === id && match(r, where); });
  }
  function detailSpec(rec) {
    if (!rec) return null;
    var d = spec.details || {};
    return d[rec.type] || d["*"] || spec.detail || null;
  }

  /* ---------- status vocabulary ---------- */
  var STATUS = {
    queued: { label: "Queued", tone: "idle", icon: "ring" },
    requested: { label: "Starting", tone: "agent", icon: "ring" },
    working: { label: "Working", tone: "agent", icon: "half" },
    "needs-you": { label: "Needs you", tone: "attn", icon: "bang" },
    ready: { label: "Ready for review", tone: "info", icon: "dot" },
    reviewed: { label: "Reviewed", tone: "ok", icon: "check" },
    returned: { label: "Returned", tone: "you", icon: "back" },
    failed: { label: "Failed", tone: "fail", icon: "x" },
    draft: { label: "Draft", tone: "idle", icon: "ring" }
  };
  if (spec.statuses) for (var sk in spec.statuses) STATUS[sk] = Object.assign({ tone: "idle", icon: "ring" }, STATUS[sk], spec.statuses[sk]);
  function statusOf(v) { return STATUS[v] || { label: v == null || v === "" ? "None" : label(v), tone: "idle", icon: "ring" }; }
  var ICONS = {
    ring: '<circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    half: '<circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6 2a4 4 0 0 1 0 8z" fill="currentColor"/>',
    bang: '<circle cx="6" cy="6" r="5" fill="currentColor"/><path d="M6 3v3.6M6 8.6v.2" stroke="var(--pa-tone-soft)" stroke-width="1.6" stroke-linecap="round"/>',
    dot: '<circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="6" cy="6" r="1.8" fill="currentColor"/>',
    check: '<path d="M2.2 6.4l2.5 2.5 5-5.6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    back: '<path d="M5 2.5L2 5.5l3 3M2.4 5.5h4.4a3 3 0 0 1 0 6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" transform="translate(0 -1)"/>',
    x: '<path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>'
  };
  function icon(name) { return '<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">' + (ICONS[name] || ICONS.ring) + "</svg>"; }
  function pill(v) {
    var s = statusOf(v);
    return '<span class="pa-pill tone-' + s.tone + '">' + icon(s.icon) + esc(s.label) + "</span>";
  }
  /* A link to another project hangs from the record it is about: the chip names
     that project and how it stands, so the news is where the person acts on it. */
  var LINK_WORDS = { "handed-to": "Handed to", "started": "Started", "relies-on": "Relies on" };
  var PROJECT_STATES = {
    "shaping": { label: "Shaping", tone: "idle" }, "in-delivery": { label: "In delivery", tone: "agent" },
    "shipped": { label: "Shipped", tone: "ok" }, "slipped": { label: "Slipped", tone: "attn" },
    "paused": { label: "Paused", tone: "idle" }, "stopped": { label: "Stopped", tone: "idle" }
  };
  function links(rec) {
    return [].concat(rec.links || []).map(function (l) {
      if (!l || !l.project) return "";
      var p = (data.projects || {})[l.project] || {};
      var st = PROJECT_STATES[p.state];
      return '<span class="pa-link tone-' + (st ? st.tone : "idle") + '" title="' + esc(LINK_WORDS[l.type] || "Linked to") + ' another project">' +
        "\u2192 " + esc(l.project) + (p.team ? " \u00b7 " + esc(p.team) : "") + (st ? " \u00b7 " + esc(p.state_note || st.label) : "") + "</span>";
    }).join("");
  }
  function flags(rec) {
    var out = "";
    if (val(rec, "locked")) out += '<span class="pa-flag locked" title="Settled. Changes need your say-so.">Locked</span>';
    if (val(rec, "stale")) out += '<span class="pa-flag stale" title="Something this was built from has changed.">Check again</span>';
    if (isEdited(rec)) out += '<span class="pa-flag edited" title="You changed this. Not saved yet.">Edited</span>';
    return out + links(rec);
  }

  /* ---------- cells ---------- */
  function control(rec, col) {
    var field = col.field, v = val(rec, field), ed = col.edit;
    var changed = isEdited(rec, field) ? " changed" : "";
    var attrs = ' data-edit="' + esc(field) + '" data-id="' + esc(rec.id) + '"';
    if (col.as === "check") return '<input type="checkbox" class="pa-check"' + attrs + (v ? " checked" : "") + ' aria-label="' + esc(col.label || label(field)) + '">';
    if (ed && ed.options) {
      var opts = ed.options.slice();
      if (v != null && opts.indexOf(v) === -1) opts.unshift(v);
      return '<select class="pa-select' + changed + '"' + attrs + ' aria-label="' + esc(col.label || label(field)) + '">' + opts.map(function (o) {
        var text = col.as === "status" ? statusOf(o).label : o;
        return '<option value="' + esc(o) + '"' + (o === v ? " selected" : "") + ">" + esc(text) + "</option>";
      }).join("") + "</select>";
    }
    var type = ed === "number" ? "number" : "text";
    return '<input type="' + type + '" class="pa-input' + changed + '"' + attrs + ' value="' + esc(v == null ? "" : v) + '">';
  }
  function cell(rec, col, allowEdit) {
    var v = val(rec, col.field);
    if (allowEdit && col.edit && !(val(rec, "locked") && col.field !== "locked")) return control(rec, col);
    switch (col.as) {
      case "status": return v == null || v === "" ? "" : pill(v);
      case "chip": return v == null || v === "" ? "" : '<span class="pa-chip">' + esc(v) + "</span>";
      case "tags": return [].concat(v || []).map(function (t) { return '<span class="pa-chip">' + esc(t) + "</span>"; }).join(" ");
      case "check": return v ? icon("check") : "";
      case "meter":
        var max = col.max || 5, n = Math.round(Number(v) || 0), m = "";
        for (var i = 1; i <= max; i++) m += '<i class="' + (i <= n ? "on" : "") + '"></i>';
        return v == null ? "" : '<span class="pa-meter" title="' + esc(v) + " of " + max + '">' + m + "</span>";
      case "count":
        var kids = childrenOf(rec.id, col.of, col.link);
        return kids.length ? String(kids.length) : '<span class="pa-muted">0</span>';
      case "who":
        /* Who made or last touched the record: a participant id from the roster. */
        if (v == null || v === "") return "";
        var who = v === "aviator" ? { name: "Aviator", kind: "agent host", initials: "PA", role: "Your agent" } : v === "you" ? { name: "You", kind: "person", initials: "You", role: "You" } : (data.participants || {})[v] || { name: v, kind: "agent" };
        var ini = who.initials || String(who.name).split(/\s+/).slice(0, 2).map(function (w) { return w.charAt(0); }).join("").toUpperCase();
        return '<span class="pa-who" title="' + esc((who.role || who.kind) + (who.stand_in ? ", stand-in played by an agent" : "")) + '"><i class="pa-mark ' + esc(who.kind) + (who.stand_in ? " standin" : "") + '">' + esc(ini) + "</i>" + esc(who.name) + "</span>";
      case "ref":
        var target = byId[v];
        return target ? '<span class="pa-chip">' + esc(target.title || target.id) + "</span>" : v ? esc(v) : "";
      default:
        /* Short values such as dates stay on one line in a narrow column. */
        var plain = esc(Array.isArray(v) ? v.join(", ") : v == null ? "" : v);
        return typeof v === "string" && v.length <= 12 ? '<span class="pa-short">' + plain + "</span>" : plain;
    }
  }

  /* ---------- actions ---------- */
  function actionsFor(scope, rec) {
    return (spec.actions || []).filter(function (a) {
      return (a.scope || "record") === scope && (!rec || match(rec, a.when)) && (!a.host || a.host === host);
    });
  }
  function actionBtn(a, rec, small) {
    return '<button class="pa-btn ' + (a.tone || "") + (small ? " small" : "") + '" data-act="action" data-a="' + esc(a.id) + '"' + (rec ? ' data-id="' + esc(rec.id) + '"' : "") + ">" + esc(a.label || label(a.id)) + "</button>";
  }
  /* State changes (a status, a lock) can go straight to the agent where the host offers
     omnigent.act. The host accepts state fields only and writes the message itself, so a
     view cannot use this channel to say anything else. Content edits always wait for Send. */
  function isStateField(f) { return f === "status" || f === "locked" || /_status$/.test(f); }
  function isStateValue(v) { return typeof v === "boolean" || (typeof v === "string" && /^[a-z][a-z0-9-]{0,30}$/.test(v)); }
  function canAct() { return !!(window.omnigent && window.omnigent.act && spec.dataset && spec.direct !== false); }
  var actQueue = [], actTimer = null;
  function setDirect(id, field, value) {
    var rec = byId[id];
    if (!rec || rec[field] === value) return;
    (state.direct[id] || (state.direct[id] = {}))[field] = { v: value, from: rec[field] == null ? null : rec[field], t: Date.now() };
    var e = state.edits[id];
    if (e) { delete e[field]; if (!Object.keys(e).length) delete state.edits[id]; }
    actQueue.push({ id: id, field: field, value: value });
    clearTimeout(actTimer);
    actTimer = setTimeout(function () {
      var changes = actQueue.splice(0, 50); actQueue = [];
      try { window.omnigent.act({ dataset: spec.dataset, changes: changes }); } catch (e) {}
    }, 30);
  }
  /* A change from a button or a cell: direct when it is state and the host allows, else an edit. */
  function change(id, field, value) {
    if (canAct() && isStateField(field) && isStateValue(value)) setDirect(id, field, value);
    else setEdit(id, field, value);
  }
  function setEdit(id, field, value) {
    var rec = byId[id];
    if (!rec) return;
    var e = state.edits[id] || (state.edits[id] = {});
    var same = rec[field] === value || (rec[field] == null && (value === "" || value === false));
    if (same) delete e[field]; else e[field] = value;
    if (!Object.keys(e).length) delete state.edits[id];
    state.sent = false;
  }
  function editLines() {
    var lines = [];
    Object.keys(state.edits).forEach(function (id) {
      var rec = byId[id], e = state.edits[id];
      if (!rec) return;
      Object.keys(e).forEach(function (f) {
        var before = rec[f] == null ? "(empty)" : rec[f];
        lines.push("- " + id + " " + f + ": " + JSON.stringify(before) + " -> " + JSON.stringify(e[f]));
      });
    });
    return lines;
  }
  function editCount() { return editLines().length; }
  function send(text, meta) {
    try { if (window.parent && window.parent !== window) window.parent.postMessage({ source: "pa-kit", type: "action", view: spec.view, action: meta || null, text: text }, "*"); } catch (e) {}
    if (window.omnigent && window.omnigent.prompt) window.omnigent.prompt(text);
    else if (!inHarness) toast("Outside Omnigent. This would go to the chat box:\n\n" + text);
  }
  function sendEdits() {
    var lines = editLines();
    if (!lines.length) return;
    send('Save these edits from the "' + (spec.title ? fmt(spec.title) : spec.view) + '" view to ' + (spec.dataset || "the dataset") + ":\n" + lines.join("\n"), { id: "save-edits", edits: JSON.parse(JSON.stringify(state.edits)) });
    state.sent = true;
  }
  function runAction(a, rec, note) {
    if (a.ask && note === undefined) { state.asking = { a: a.id, id: rec ? rec.id : null }; return; }
    state.asking = null;
    /* "direct" actions are pure state changes. With a host that takes them they need no
       sentence; without one they fall back to their prompt and leave the data alone. */
    var direct = a.direct && a.set && !a.ask && canAct();
    var targets = rec ? [rec] : a.direct && a.set && a.records ? collection().filter(function (r) { return match(r, a.records); }) : [];
    if (a.set && !(a.direct && !direct)) targets.forEach(function (r) {
      for (var f in a.set) (a.ask ? setEdit : change)(r.id, f, typeof a.set[f] === "string" ? fmt(a.set[f], r) : a.set[f]);
    });
    if (a.ask && rec && a.ask.field) setEdit(rec.id, a.ask.field, note || "");
    if (a.prompt && !direct) {
      var text = fmt(a.prompt, rec).replace("{note}", note || "");
      var lines = editLines();
      if (lines.length) { text += "\n\nAlso save these edits to " + (spec.dataset || "the dataset") + ":\n" + lines.join("\n"); state.sent = true; }
      send(text, { id: a.id, record: rec ? rec.id : null, note: note || null });
    }
    if (a.next && rec) { var n = neighbour(rec.id, 1, a.when); if (n) state.detail[state.detail.length - 1] = n; else state.detail = []; }
    else if (a.close) state.detail = [];
  }
  function leaves() {
    var d = spec.details || {};
    return collection().filter(function (r) { return !spec.details || d[r.type] || d["*"]; });
  }
  function neighbour(id, dir, where) {
    var list = leaves().filter(function (r) { return r.id === id || !where || match(r, where); });
    var i = list.map(function (r) { return r.id; }).indexOf(id);
    var n = list[i + dir];
    return n ? n.id : null;
  }
  var toastTimer = null, toastText = "";
  function toast(text) {
    toastText = text; render();
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastText = ""; render(); }, 6000);
  }

  /* ---------- shared pieces ---------- */
  var LAYOUT_NAMES = { "tree-table": "Catalog", board: "Board", detail: "Detail", summary: "Summary", form: "Form" };
  function head() {
    var acts = actionsFor("view").map(function (a) { return actionBtn(a); }).join("");
    return '<div class="pa-head"><div class="pa-headmain"><span class="pa-eyebrow">' + esc(spec.eyebrow ? fmt(spec.eyebrow) : "Template · " + (LAYOUT_NAMES[spec.layout] || spec.layout || "View")) + "</span>" +
      "<h1>" + esc(fmt(spec.title || "Untitled view")) + "</h1>" +
      (spec.subtitle ? '<div class="pa-sub">' + esc(fmt(spec.subtitle)) + "</div>" : "") + "</div>" +
      (acts ? '<div class="pa-tools">' + acts + "</div>" : "") + "</div>";
  }
  function strip() {
    var s = spec.summary;
    if (!s) return "";
    var field = s.count_by || SF;
    var list = recs().filter(function (r) { return match(r, s.records || spec.records); });
    var order = s.order || Object.keys(STATUS), counts = {}, seen = [];
    list.forEach(function (r) { var v = val(r, field); if (v == null) return; counts[v] = (counts[v] || 0) + 1; if (seen.indexOf(v) === -1) seen.push(v); });
    var keys = order.filter(function (k) { return counts[k]; }).concat(seen.filter(function (k) { return order.indexOf(k) === -1; }));
    if (!keys.length) return "";
    var pills = keys.map(function (k) {
      var st = statusOf(k);
      return '<button data-act="filter" data-v="' + esc(k) + '" aria-pressed="' + (state.filter === k) + '" title="Show only ' + esc(st.label) + '"><span class="pa-pill tone-' + st.tone + '">' + icon(st.icon) + '<span class="pa-count">' + counts[k] + "</span> " + esc(st.label) + "</span></button>";
    }).join("");
    var bar = keys.map(function (k) { return '<i class="tone-' + statusOf(k).tone + '" style="width:' + (counts[k] / list.length * 100) + '%"></i>'; }).join("");
    return '<div class="pa-strip">' + pills + (state.filter ? '<button class="pa-btn small" data-act="filter" data-v="">Show all</button>' : "") + '</div><div class="pa-progress" role="img" aria-label="Share of items by status">' + bar + "</div>";
  }
  function foot() {
    if (spec.layout === "form") return "";
    var bits = [];
    if (spec.dataset) bits.push(esc(spec.dataset));
    if (data.updated) bits.push("updated " + esc(String(data.updated).replace("T", " ").slice(0, 16)));
    bits.push(recs().length + " records");
    return '<div class="pa-foot">' + bits.map(function (b) { return "<span>" + b + "</span>"; }).join("") + "</div>";
  }
  function pending() {
    var n = editCount(), out = "";
    if (n) {
      out += '<div class="pa-pending" role="status"><span>' + (state.sent ? "Sent " + n + (n === 1 ? " edit" : " edits") + ". Press Send in the chat, then the agent saves them." : n + (n === 1 ? " unsaved edit" : " unsaved edits")) + "</span>" +
        '<button class="pa-btn primary" data-act="send-edits">' + (state.sent ? "Send again" : "Send to agent") + '</button><button class="pa-btn ghost" data-act="discard">Discard</button></div>';
    }
    if (toastText) out += '<div class="pa-toast" role="status">' + esc(toastText) + "</div>";
    return out;
  }

  /* ---------- tree table ---------- */
  function treeTable() {
    var cols = spec.columns && spec.columns.length ? spec.columns : [{ field: "title" }];
    var list = collection(), ids = {};
    list.forEach(function (r) { ids[r.id] = true; });
    var filterField = (spec.summary && spec.summary.count_by) || SF;
    var keep = null;
    if (state.filter) {
      keep = {};
      list.forEach(function (r) {
        if (val(r, filterField) !== state.filter) return;
        for (var p = r; p && !keep[p.id]; p = byId[p.parent]) keep[p.id] = true;
      });
    }
    var inline = (spec.actions || []).some(function (a) { return a.inline; });
    // In a narrow canvas, read-only chips and meters give way to the title, status and edits.
    function narrowHide(c) { return c.narrow === "hide" || (c.narrow !== "keep" && !c.edit && (c.as === "chip" || c.as === "meter" || c.as === "tags")); }
    var rows = "";
    function walk(rec, depth) {
      if (keep && !keep[rec.id]) return;
      var kids = list.filter(function (r) { return r.parent === rec.id; });
      var open = !state.collapsed[rec.id];
      var isOpen = state.detail[state.detail.length - 1] === rec.id;
      var canOpen = !!detailSpec(rec);
      var first = cols[0];
      var rollup = "";
      if (kids.length) {
        var done = kids.filter(function (k) { return val(k, SF) === "reviewed"; }).length;
        rollup = '<span class="pa-rollup">' + kids.length + (done ? " · " + done + " reviewed" : "") + "</span>";
      }
      rows += '<tr class="' + (canOpen ? "pa-row " : "") + (kids.length ? "is-group " : "") + (isOpen ? "is-open" : "") + '"' + (canOpen ? ' data-act="open" data-id="' + esc(rec.id) + '"' : "") + ">" +
        '<td><div class="pa-titlecell" style="--pa-depth:' + depth + '">' +
        (kids.length ? '<button class="pa-twist" data-act="twist" data-id="' + esc(rec.id) + '" aria-expanded="' + open + '" aria-label="' + (open ? "Collapse" : "Expand") + '"><svg width="10" height="10" viewBox="0 0 10 10"><path d="M3 1.5l4 3.5-4 3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></button>' : '<span class="pa-twist"></span>') +
        (spec.show_id === false || kids.length ? "" : '<span class="pa-id">' + esc(rec.id) + "</span>") +
        '<span class="pa-t">' + cell(rec, first, false) + rollup + "</span>" + flags(rec) + "</div></td>" +
        cols.slice(1).map(function (c) {
          var only = c.only && [].concat(c.only).indexOf(rec.type) === -1;
          return '<td class="' + (c.as === "count" || c.as === "number" ? "num" : "") + (narrowHide(c) ? " pa-wide" : "") + '">' + (only ? "" : cell(rec, c, true)) + "</td>";
        }).join("") +
        (inline ? "<td>" + actionsFor("record", rec).filter(function (a) { return a.inline; }).map(function (a) { return actionBtn(a, rec, true); }).join(" ") + "</td>" : "") + "</tr>";
      if (open) kids.forEach(function (k) { walk(k, depth + 1); });
    }
    list.filter(function (r) { return !ids[r.parent]; }).forEach(function (r) { walk(r, 0); });
    if (!rows) return '<div class="pa-empty">' + esc(list.length ? "Nothing matches this filter." : spec.empty || "No records yet. The agent fills this in as it works.") + "</div>";
    return '<div class="pa-tablewrap"><table class="pa-table"><thead><tr>' + cols.map(function (c, i) { return '<th class="' + (i && narrowHide(c) ? "pa-wide" : "") + '">' + esc(c.label || label(c.field)) + "</th>"; }).join("") + (inline ? "<th></th>" : "") + "</tr></thead><tbody>" + rows + "</tbody></table></div>";
  }

  /* ---------- board ---------- */
  function board() {
    var lanes = spec.lanes || { field: SF };
    var field = lanes.field || SF, isStatus = field === SF;
    var list = collection();
    var filterField = (spec.summary && spec.summary.count_by) || SF;
    if (state.filter) list = list.filter(function (r) { return val(r, filterField) === state.filter; });
    var order = (lanes.order || (isStatus ? Object.keys(STATUS) : [])).slice();
    list.forEach(function (r) { var v = val(r, field); if (v != null && order.indexOf(v) === -1) order.push(v); });
    if (!lanes.show_empty) order = order.filter(function (k) { return list.some(function (r) { return val(r, field) === k; }); });
    if (!order.length) return '<div class="pa-empty">' + esc(spec.empty || "No items yet.") + "</div>";
    var tileFields = (spec.tile && spec.tile.fields) || [];
    return '<div class="pa-board">' + order.map(function (k) {
      var items = list.filter(function (r) { return val(r, field) === k; });
      var st = isStatus ? statusOf(k) : null;
      var name = st ? st.label : (lanes.labels && lanes.labels[k]) || (byId[k] && byId[k].title) || k;
      return '<div class="pa-lane"><div class="pa-lanehead' + (st ? " tone-" + st.tone : "") + '">' + esc(name) + "<span>" + items.length + "</span></div>" +
        (items.length ? items.map(function (r) {
          var s = statusOf(val(r, SF)), isOpen = state.detail[state.detail.length - 1] === r.id;
          var acts = actionsFor("record", r).filter(function (a) { return a.inline; });
          return '<div class="pa-tile tone-' + s.tone + (isOpen ? " is-open" : "") + '" role="button" tabindex="0" data-act="open" data-id="' + esc(r.id) + '">' +
            '<div class="pa-id"><span>' + esc(r.id) + "</span>" + (val(r, SF) === "working" ? '<span class="pa-working" title="Working"></span>' : "") + "</div>" +
            '<div class="pa-t">' + esc(val(r, "title")) + "</div>" +
            '<div class="pa-meta">' + (isStatus ? "" : pill(val(r, SF))) + tileFields.map(function (c) { return cell(r, typeof c === "string" ? { field: c, as: "chip" } : c, false); }).join("") + flags(r) + "</div>" +
            (acts.length ? '<div class="pa-meta">' + acts.map(function (a) { return actionBtn(a, r, true); }).join("") + "</div>" : "") + "</div>";
        }).join("") : '<div class="pa-lane-empty">None</div>') + "</div>";
    }).join("") + "</div>";
  }

  /* ---------- detail ---------- */
  function section(rec, s) {
    var v = s.field ? val(rec, s.field) : null, h = s.label ? "<h3>" + esc(s.label) + "</h3>" : "";
    if (s.when && !match(rec, s.when)) return "";
    switch (s.kind) {
      case "fields":
        return '<div class="pa-sec">' + h + '<div class="pa-fields">' + (s.fields || []).map(function (c) {
          if (typeof c === "string") c = { field: c };
          return '<div class="pa-field"><span class="pa-lab">' + esc(c.label || label(c.field)) + "</span><div>" + (cell(rec, c, true) || '<span class="pa-muted">Not set</span>') + "</div></div>";
        }).join("") + "</div></div>";
      case "text":
        if (s.edit) return '<div class="pa-sec">' + h + '<textarea class="pa-input' + (isEdited(rec, s.field) ? " changed" : "") + '" rows="3" data-edit="' + esc(s.field) + '" data-id="' + esc(rec.id) + '">' + esc(v || "") + "</textarea></div>";
        return v ? '<div class="pa-sec">' + h + '<div class="pa-text">' + esc(v) + "</div></div>" : "";
      case "choices":
        /* The record's own options, one to pick. The pick is an edit: it waits with the others for Send. */
        if (!v || !v.length) return "";
        var pickField = s.pick || "choice", picked = val(rec, pickField), rec0 = val(rec, s.recommended || "recommended"), shut = val(rec, "locked");
        return '<div class="pa-sec">' + h + '<div class="pa-choices" role="radiogroup">' + v.map(function (o) {
          if (typeof o === "string") o = { label: o };
          var on = picked === o.label;
          return '<button type="button" role="radio" aria-checked="' + on + '" class="pa-choice' + (on ? " on" : "") + '"' + (shut ? " disabled" : "") + ' data-act="choose" data-id="' + esc(rec.id) + '" data-field="' + esc(pickField) + '" data-v="' + esc(o.label) + '"><b>' + esc(o.label) + (rec0 === o.label ? ' <span class="pa-chip">Recommended</span>' : "") + "</b>" + (o.consequence ? "<span>" + esc(o.consequence) + "</span>" : "") + "</button>";
        }).join("") + "</div></div>";
      case "list":
        return v && v.length ? '<div class="pa-sec">' + h + '<ul class="pa-list">' + v.map(function (x) { return "<li>" + esc(typeof x === "string" ? x : x.text) + "</li>"; }).join("") + "</ul></div>" : "";
      case "evidence":
        return v && v.length ? '<div class="pa-sec">' + h + '<div class="pa-evi">' + v.map(function (x) {
          return "<div>" + (x.quote ? "<q>" + esc(x.quote) + "</q>" : "") + (x.note ? "<span>" + esc(x.note) + "</span>" : "") + '<span class="pa-src">' + esc(x.source || "") + "</span></div>";
        }).join("") + "</div></div>" : "";
      case "callout":
        return v ? '<div class="pa-callout tone-' + (s.tone || "attn") + '"><b>' + esc(s.label || label(s.field)) + '</b><div class="pa-text">' + esc(v) + "</div></div>" : "";
      case "note":
        return '<div class="pa-sec">' + h + '<div class="pa-sub">' + esc(fmt(s.text, rec)) + "</div></div>";
      case "children":
        var kids = childrenOf(rec.id, s.records, s.link);
        if (!kids.length) return s.empty ? '<div class="pa-sec">' + h + '<div class="pa-sub">' + esc(s.empty) + "</div></div>" : "";
        if (s.as === "options") {
          var pickField = s.pick && s.pick.field, picked = pickField ? val(rec, pickField) : null;
          return '<div class="pa-sec">' + h + '<div class="pa-opts">' + kids.map(function (k) {
            var on = picked === k.id;
            return '<div class="pa-opt' + (on ? " is-picked" : "") + '"><div class="pa-t">' + esc(val(k, "title")) + "</div>" +
              (val(k, "summary") ? '<div class="pa-sub">' + esc(val(k, "summary")) + "</div>" : "") +
              '<div class="pa-meta">' + (s.fields || []).map(function (c) {
                if (typeof c === "string") c = { field: c, as: "chip" };
                var body = cell(k, c, false);
                return body ? "<span>" + (c.label ? esc(c.label) + " " : "") + body + "</span>" : "";
              }).join("") + "</div>" +
              '<div class="pa-meta">' + (pickField && !val(rec, "locked") ? '<button class="pa-btn small' + (on ? " primary" : "") + '" data-act="pick" data-id="' + esc(k.id) + '" data-parent="' + esc(rec.id) + '" data-field="' + esc(pickField) + '">' + (on ? "Chosen" : "Choose") + "</button>" : "") +
              (detailSpec(k) ? '<button class="pa-btn small" data-act="open" data-push="1" data-id="' + esc(k.id) + '">Open</button>' : "") + "</div></div>";
          }).join("") + "</div></div>";
        }
        var cols = s.columns || [{ field: "title" }, { field: "status", as: "status" }];
        return '<div class="pa-sec">' + h + '<div class="pa-tablewrap"><table class="pa-table"><thead><tr>' + cols.map(function (c) { return "<th>" + esc(c.label || label(c.field)) + "</th>"; }).join("") + "</tr></thead><tbody>" +
          kids.map(function (k) {
            var can = !!detailSpec(k);
            return "<tr" + (can ? ' class="pa-row" data-act="open" data-push="1" data-id="' + esc(k.id) + '"' : "") + ">" + cols.map(function (c, i) {
              return "<td>" + (i === 0 ? '<div class="pa-titlecell" style="min-width:11em"><span class="pa-id">' + esc(k.id) + '</span><span class="pa-t">' + cell(k, c, false) + "</span>" + flags(k) + "</div>" : cell(k, c, true)) + "</td>";
            }).join("") + "</tr>";
          }).join("") + "</tbody></table></div></div>";
      default: return "";
    }
  }
  function detailBody(rec) {
    var d = detailSpec(rec) || { sections: [] };
    return (d.sections || []).map(function (s) { return section(rec, s); }).join("") || '<div class="pa-sub">Nothing to show for this item yet.</div>';
  }
  function detailFoot(rec) {
    var acts = actionsFor("record", rec);
    if (state.asking && state.asking.id === rec.id) {
      var a = (spec.actions || []).filter(function (x) { return x.id === state.asking.a; })[0];
      if (a) return '<div class="pa-panelfoot" style="flex-direction:column;align-items:stretch"><label for="pa-note" class="pa-lab">' + esc((a.ask && a.ask.label) || "Note") + '</label><textarea id="pa-note" class="pa-input" rows="3" style="width:100%"></textarea><div style="display:flex;gap:8px;justify-content:flex-end"><button class="pa-btn" data-act="ask-cancel">Cancel</button><button class="pa-btn primary" data-act="ask-ok">' + esc(a.label) + "</button></div></div>";
    }
    return acts.length ? '<div class="pa-panelfoot">' + acts.map(function (a) { return actionBtn(a, rec); }).join("") + "</div>" : "";
  }
  function detailHead(rec, inPanel) {
    var d = detailSpec(rec) || {};
    var crumbs = state.detail.slice(0, -1).map(function (id, i) {
      var r = byId[id];
      return '<button data-act="back" data-n="' + i + '">' + esc(r ? r.id : id) + "</button><span>›</span>";
    }).join("");
    var prev = neighbour(rec.id, -1), next = neighbour(rec.id, 1), top = state.detail.length === 1;
    return '<div class="pa-panelhead">' + (inPanel ? '<div class="pa-panelbar"><div class="pa-crumbs">' + crumbs + '<span class="pa-id">' + esc(rec.id) + "</span></div><div class=\"pa-tools\">" +
      (top ? '<button class="pa-btn small" data-act="nav" data-d="-1"' + (prev ? "" : " disabled") + ' aria-label="Previous item">‹</button><button class="pa-btn small" data-act="nav" data-d="1"' + (next ? "" : " disabled") + ' aria-label="Next item">›</button>' : "") +
      '<button class="pa-btn small" data-act="wide">' + (state.wide ? "Side panel" : "Full view") + '</button><button class="pa-btn small" data-act="close" aria-label="Close">Close</button></div></div>' : "") +
      "<h2>" + esc(fmt(d.title || "{title}", rec)) + '</h2><div class="pa-strip">' + (val(rec, SF) ? pill(val(rec, SF)) : "") + flags(rec) + "</div></div>";
  }
  function panel() {
    var id = state.detail[state.detail.length - 1], rec = byId[id];
    if (!rec || spec.layout === "detail" || host === "chat") return "";
    return (state.wide ? "" : '<div class="pa-scrim" data-act="close"></div>') + '<aside class="pa-panel' + (state.wide ? " wide" : "") + '" aria-label="Item detail">' + detailHead(rec, true) + '<div class="pa-panelbody">' + detailBody(rec) + "</div>" + detailFoot(rec) + "</aside>";
  }
  function detailLayout() {
    var rec = byId[spec.record] || collection()[0];
    if (!rec) return '<div class="pa-empty">' + esc(spec.empty || "This item is not in the dataset.") + "</div>";
    state.detail = [rec.id];
    return '<div class="pa-detail-inline">' + detailHead(rec, false) + '<div class="pa-panelbody">' + detailBody(rec) + "</div>" + detailFoot(rec) + "</div>";
  }

  /* ---------- summary ---------- */
  function countBy(list, field) {
    var counts = {}, order = [];
    list.forEach(function (r) { var v = val(r, field); if (v == null || v === "") return; if (!(v in counts)) { counts[v] = 0; order.push(v); } counts[v]++; });
    return { counts: counts, order: order };
  }
  function summary() {
    return (spec.blocks || []).map(function (b) {
      var list = recs().filter(function (r) { return match(r, b.records || spec.records); });
      var h = b.label ? '<span class="pa-eyebrow">' + esc(b.label) + "</span>" : "";
      if (b.kind === "tiles") {
        return '<div class="pa-tiles">' + (b.tiles || []).map(function (t) {
          var n = "value" in t ? fmt(t.value) : recs().filter(function (r) { return match(r, t.where); }).length;
          return '<div class="pa-stat"><b>' + esc(n) + "</b><span>" + esc(t.label) + "</span></div>";
        }).join("") + "</div>";
      }
      if (b.kind === "bars") {
        var c = countBy(list, b.count_by || SF), isStatus = /status$/.test(b.count_by || SF);
        var keys = isStatus ? Object.keys(STATUS).filter(function (k) { return c.counts[k]; }).concat(c.order.filter(function (k) { return !STATUS[k]; })) : c.order;
        var max = Math.max.apply(null, keys.map(function (k) { return c.counts[k]; }).concat([1]));
        return '<div class="pa-card">' + h + '<div class="pa-bars">' + keys.map(function (k) {
          var st = isStatus ? statusOf(k) : null;
          return "<span>" + esc(st ? st.label : (byId[k] && byId[k].title) || k) + '</span><span><div class="pa-bar' + (st ? " tone-" + st.tone : "") + '" style="width:' + (c.counts[k] / max * 100) + '%"></div></span><span class="num">' + c.counts[k] + "</span>";
        }).join("") + "</div></div>";
      }
      if (b.kind === "text") return '<div class="pa-text">' + esc(fmt(b.text)) + "</div>";
      if (b.kind === "list") {
        /* A list about one field only shows the records that have it. */
        if (b.field) list = list.filter(function (r) { var x = val(r, b.field); return x != null && x !== ""; });
        var items = b.limit ? list.slice(0, b.limit) : list;
        if (!items.length) return b.empty ? '<div class="pa-sub">' + esc(b.empty) + "</div>" : "";
        return '<div class="pa-card">' + h + '<div class="pa-tablewrap" style="border:0"><table class="pa-table"><tbody>' + items.map(function (r) {
          var can = host !== "chat" && detailSpec(r);
          return "<tr" + (can ? ' class="pa-row" data-act="open" data-id="' + esc(r.id) + '"' : "") + '><td><div class="pa-titlecell" style="min-width:0"><span class="pa-id">' + esc(r.id) + '</span><span class="pa-t">' + esc(val(r, "title")) + "</span></div></td><td>" + (b.field ? esc(val(r, b.field) || "") : pill(val(r, b.status_field || SF))) + "</td></tr>";
        }).join("") + "</tbody></table></div>" + (list.length > items.length ? '<span class="pa-sub">and ' + (list.length - items.length) + " more</span>" : "") + "</div>";
      }
      return "";
    }).join("");
  }

  /* ---------- form ---------- */
  function form() {
    var fields = spec.fields || [];
    fields.forEach(function (f) { if (!(f.id in state.answers) && "default" in f) state.answers[f.id] = f.default; });
    var body = fields.map(function (f) {
      var a = state.answers[f.id], help = f.help ? '<span class="pa-help">' + esc(f.help) + "</span>" : "";
      if (f.kind === "choice" || f.kind === "multi") {
        var multi = f.kind === "multi";
        return '<fieldset class="pa-q"><legend>' + esc(f.label) + "</legend>" + help + '<div class="pa-choices">' + (f.options || []).map(function (o, i) {
          if (typeof o === "string") o = { value: o };
          var on = multi ? [].concat(a || []).indexOf(o.value) !== -1 : a === o.value;
          return '<label class="pa-choice"><input type="' + (multi ? "checkbox" : "radio") + '" name="q-' + esc(f.id) + '" id="q-' + esc(f.id) + "-" + i + '" data-q="' + esc(f.id) + '" value="' + esc(o.value) + '"' + (on ? " checked" : "") + "><span>" + esc(o.label || o.value) + (o.hint ? "<small>" + esc(o.hint) + "</small>" : "") + "</span></label>";
        }).join("") + "</div></fieldset>";
      }
      if (f.kind === "toggle") return '<div class="pa-q"><label><input type="checkbox" class="pa-check" id="q-' + esc(f.id) + '" data-q="' + esc(f.id) + '"' + (a ? " checked" : "") + "> " + esc(f.label) + "</label>" + help + "</div>";
      var input = f.kind === "number" ? '<input type="number" id="q-' + esc(f.id) + '" data-q="' + esc(f.id) + '" value="' + esc(a == null ? "" : a) + '">' :
        f.kind === "line" ? '<input type="text" id="q-' + esc(f.id) + '" data-q="' + esc(f.id) + '" value="' + esc(a || "") + '" placeholder="' + esc(f.placeholder || "") + '">' :
        '<textarea id="q-' + esc(f.id) + '" data-q="' + esc(f.id) + '" placeholder="' + esc(f.placeholder || "") + '">' + esc(a || "") + "</textarea>";
      return '<div class="pa-q"><label for="q-' + esc(f.id) + '">' + esc(f.label) + "</label>" + help + input + "</div>";
    }).join("");
    var sub = spec.submit || {};
    return '<div class="pa-form' + (state.answered ? " is-answered" : "") + '">' + body + '<div class="pa-formfoot">' +
      (state.answered ? '<span class="pa-answered">' + icon("check") + ' In the chat box. Press Send there.</span><button class="pa-btn small" data-act="form-edit">Change answers</button>' :
        '<button class="pa-btn primary" data-act="form-submit">' + esc(sub.label || "Send answers") + "</button>" + (sub.skip ? '<button class="pa-btn" data-act="form-skip">' + esc(sub.skip) + "</button>" : "")) + "</div></div>";
  }
  function answerLines() {
    return (spec.fields || []).map(function (f) {
      var a = state.answers[f.id];
      if (a == null || a === "" || (Array.isArray(a) && !a.length)) return null;
      return "- " + f.label + " " + (Array.isArray(a) ? a.join(", ") : a === true ? "Yes" : a === false ? "No" : a);
    }).filter(Boolean).join("\n");
  }

  /* ---------- render ---------- */
  function render() {
    index();
    var y = window.scrollY, pb = document.querySelector(".pa-panelbody"), py = pb ? pb.scrollTop : 0;
    var body = spec.layout === "board" ? board() : spec.layout === "detail" ? detailLayout() : spec.layout === "summary" ? summary() : spec.layout === "form" ? form() : treeTable();
    var collectionLayout = spec.layout === "board" || spec.layout === "tree-table" || !spec.layout;
    var inner = head() + (collectionLayout ? strip() : "") + body + foot();
    app.innerHTML = (host === "chat" ? '<div class="pa-shell">' + inner + "</div>" : inner) + panel() + pending();
    window.scrollTo(0, y);
    var pb2 = document.querySelector(".pa-panelbody");
    if (pb2 && spec.layout !== "detail") pb2.scrollTop = py;
    var note = document.getElementById("pa-note");
    if (note) note.focus();
    save();
    /* Inline in a chat, the frame has no height of its own: tell the host. */
    if (host === "chat") {
      try { window.parent.postMessage({ source: "pa-kit", type: "size", view: spec.view, height: Math.ceil(app.getBoundingClientRect().height) }, "*"); } catch (e) {}
    }
  }
  function reconcile() {
    index();
    Object.keys(state.edits).forEach(function (id) {
      var rec = byId[id], e = state.edits[id];
      if (!rec) { delete state.edits[id]; return; }
      Object.keys(e).forEach(function (f) { if (rec[f] === e[f]) delete e[f]; });
      if (!Object.keys(e).length) delete state.edits[id];
    });
    if (!Object.keys(state.edits).length) state.sent = false;
    /* A direct change shows at once and is dropped as soon as the data moves, or after
       three minutes if the agent never applied it. */
    Object.keys(state.direct).forEach(function (id) {
      var rec = byId[id], d = state.direct[id];
      if (!rec) { delete state.direct[id]; return; }
      Object.keys(d).forEach(function (f) {
        var now = rec[f] == null ? null : rec[f];
        if (now !== d[f].from || Date.now() - d[f].t > 180000) delete d[f];
      });
      if (!Object.keys(d).length) delete state.direct[id];
    });
    state.detail = state.detail.filter(function (id) { return byId[id]; });
  }

  /* ---------- events ---------- */
  app.addEventListener("click", function (ev) {
    var t = ev.target;
    if (t.closest("select, input, textarea, label") && !t.closest("[data-act='form-submit']")) return;
    var el = t.closest("[data-act]");
    if (!el) return;
    var act = el.getAttribute("data-act"), id = el.getAttribute("data-id"), rec = byId[id];
    ev.stopPropagation();
    if (act === "open") {
      if (!detailSpec(rec)) return;
      if (el.getAttribute("data-push")) state.detail.push(id); else state.detail = [id];
      state.asking = null;
    } else if (act === "close") { state.detail = []; state.asking = null; }
    else if (act === "back") state.detail = state.detail.slice(0, Number(el.getAttribute("data-n")) + 1);
    else if (act === "wide") state.wide = !state.wide;
    else if (act === "nav") { var n = neighbour(state.detail[0], Number(el.getAttribute("data-d"))); if (n) state.detail = [n]; }
    else if (act === "twist") { if (state.collapsed[id]) delete state.collapsed[id]; else state.collapsed[id] = true; }
    else if (act === "filter") { var v = el.getAttribute("data-v"); state.filter = !v || state.filter === v ? null : v; }
    else if (act === "pick") setEdit(el.getAttribute("data-parent"), el.getAttribute("data-field"), id);
    else if (act === "choose") setEdit(id, el.getAttribute("data-field"), el.getAttribute("data-v"));
    else if (act === "send-edits") sendEdits();
    else if (act === "discard") { state.edits = {}; state.sent = false; }
    else if (act === "ask-cancel") state.asking = null;
    else if (act === "ask-ok" || act === "action") {
      var aid = act === "action" ? el.getAttribute("data-a") : state.asking && state.asking.a;
      var target = act === "action" ? rec : byId[state.asking && state.asking.id];
      var a = (spec.actions || []).filter(function (x) { return x.id === aid; })[0];
      var noteEl = document.getElementById("pa-note");
      if (a) runAction(a, target, act === "ask-ok" ? (noteEl ? noteEl.value : "") : undefined);
    } else if (act === "form-submit" || act === "form-skip") {
      var sub = spec.submit || {};
      var text = act === "form-skip" ? (sub.skip_prompt || "Skip the questions and use sensible defaults.") : fmt(String(sub.prompt || "My answers:\n{answers}").replace("{answers}", "\u0000")).replace("\u0000", answerLines());
      send(text, { id: act === "form-skip" ? "skip" : "submit", answers: JSON.parse(JSON.stringify(state.answers)) });
      state.answered = true;
    } else if (act === "form-edit") state.answered = false;
    render();
  });
  app.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && state.detail.length && spec.layout !== "detail") { state.detail = []; state.asking = null; render(); }
    if ((ev.key === "Enter" || ev.key === " ") && ev.target.matches && ev.target.matches(".pa-tile")) { ev.preventDefault(); ev.target.click(); }
  });
  app.addEventListener("change", function (ev) {
    var t = ev.target, field = t.getAttribute("data-edit"), q = t.getAttribute("data-q");
    if (field) {
      var v = t.type === "checkbox" ? t.checked : t.type === "number" ? (t.value === "" ? null : Number(t.value)) : t.value;
      change(t.getAttribute("data-id"), field, v);
      render();
    } else if (q) {
      if (t.type === "radio") state.answers[q] = t.value;
      else if (t.type === "checkbox" && t.name) {
        var cur = [].concat(state.answers[q] || []), i = cur.indexOf(t.value);
        if (t.checked && i === -1) cur.push(t.value); else if (!t.checked && i !== -1) cur.splice(i, 1);
        state.answers[q] = cur;
      } else if (t.type === "checkbox") state.answers[q] = t.checked;
      else state.answers[q] = t.type === "number" ? (t.value === "" ? null : Number(t.value)) : t.value;
      save();
    }
  });
  app.addEventListener("input", function (ev) {
    var q = ev.target.getAttribute && ev.target.getAttribute("data-q");
    if (q && (ev.target.tagName === "TEXTAREA" || ev.target.type === "text")) { state.answers[q] = ev.target.value; save(); }
  });
  window.addEventListener("message", function (ev) {
    var m = ev.data;
    if (!m || typeof m !== "object") return;
    if (m.type === "pa:data" && m.data) { data = m.data; reconcile(); render(); }
    if (m.type === "pa:open" && m.id) { index(); if (byId[m.id]) { state.detail = [m.id]; render(); } }
  });

  /* ---------- for the agent (canvas_eval) and for tests ---------- */
  window.PA = {
    spec: spec,
    pending: function () { return JSON.parse(JSON.stringify(state.edits)); },
    answers: function () { return JSON.parse(JSON.stringify(state.answers)); },
    state: function () { return JSON.parse(JSON.stringify(state)); },
    setData: function (d) { data = d; reconcile(); render(); },
    open: function (id) { index(); if (byId[id]) { state.detail = [id]; render(); } },
    clearEdits: function () { state.edits = {}; state.sent = false; render(); }
  };
  reconcile();
  render();
})();
