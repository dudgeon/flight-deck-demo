function e(e){return JSON.stringify(e)}function t(e){return JSON.stringify(e)}var n=`(() => {
  const snapshotId = (crypto && crypto.randomUUID) ? crypto.randomUUID() : ('snap-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10));
  window.__omni_refs__ = new Map();
  window.__omni_snapshot_id__ = snapshotId;
  let nextRef = 0;
  const lines = [];

  const TAG_ROLE = {
    a: 'link', button: 'button', textarea: 'textbox', select: 'combobox',
    nav: 'navigation', main: 'main', header: 'banner', footer: 'contentinfo',
    form: 'form', section: 'region', article: 'article', aside: 'complementary',
    ul: 'list', ol: 'list', li: 'listitem', img: 'image', label: 'label',
    table: 'table', tr: 'row', td: 'cell', th: 'columnheader',
    dialog: 'dialog', summary: 'button', details: 'group',
  };
  const isInteractiveTag = (tag) =>
    tag === 'a' || tag === 'button' || tag === 'input' ||
    tag === 'textarea' || tag === 'select' || tag === 'label' ||
    tag === 'summary';
  const isHeading = (tag) => tag && tag.length === 2 && tag[0] === 'h' && tag[1] >= '1' && tag[1] <= '6';

  function getRole(el) {
    const explicit = el.getAttribute && el.getAttribute('role');
    if (explicit) return explicit;
    const tag = el.tagName && el.tagName.toLowerCase();
    if (!tag) return null;
    if (tag === 'input') {
      const t = (el.type || 'text').toLowerCase();
      if (t === 'submit' || t === 'button' || t === 'reset') return 'button';
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'range') return 'slider';
      if (t === 'hidden') return null;
      return 'textbox';
    }
    if (isHeading(tag)) return 'heading';
    if (TAG_ROLE[tag]) return TAG_ROLE[tag];
    if (el.hasAttribute && (el.hasAttribute('tabindex') || el.hasAttribute('onclick'))) return 'generic';
    return null;
  }

  function getName(el, depth = 0) {
    if (depth > 4) return '';
    if (el.getAttribute) {
      const lbl = el.getAttribute('aria-label');
      if (lbl) return lbl;
      const alt = el.getAttribute('alt');
      if (alt) return alt;
      const ph = el.getAttribute('placeholder');
      if (ph) return ph;
      const ttl = el.getAttribute('title');
      if (ttl) return ttl;
    }
    const tag = el.tagName && el.tagName.toLowerCase();
    if (tag === 'input' && el.value && el.type !== 'password') return String(el.value).slice(0, 80);
    let text = '';
    for (const node of el.childNodes) {
      if (node.nodeType === 3) text += node.textContent;
      else if (node.nodeType === 1) {
        const childTag = node.tagName && node.tagName.toLowerCase();
        if (depth === 0 && isInteractiveTag(childTag)) continue;
        text += getName(node, depth + 1);
      }
      if (text.length > 80) break;
    }
    return text.trim().replace(/\\s+/g, ' ').slice(0, 80);
  }

  function isVisible(el) {
    if (!el.getBoundingClientRect) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    if (style.opacity === '0') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function walk(el, depth) {
    if (!(el instanceof Element)) return;
    if (!isVisible(el)) return;
    const role = getRole(el);
    const picked = role !== null && role !== 'generic';
    let childDepth = depth;
    if (picked) {
      const ref = ++nextRef;
      window.__omni_refs__.set(ref, new WeakRef(el));
      const name = getName(el);
      const indent = '  '.repeat(depth);
      let line = indent + '- ' + role;
      if (name) line += ' ' + JSON.stringify(name);
      line += ' [ref=' + ref + ']';
      lines.push(line);
      childDepth = depth + 1;
    }
    for (const child of el.children) {
      walk(child, childDepth);
    }
  }

  if (document.body) walk(document.body, 0);

  return JSON.stringify({
    snapshot_id: snapshotId,
    url: window.location.href,
    title: document.title,
    tree: lines.join('\\n'),
  });
})()`;function r(n){let r=typeof n.ref==`number`?n.ref:void 0,i=typeof n.snapshot_id==`string`?n.snapshot_id:void 0,a=typeof n.selector==`string`?n.selector:``;return r===void 0?`const el = document.querySelector(${e(a)}); if (!el) throw new Error('selector not found: ' + ${e(a)}); `:(i?`if (window.__omni_snapshot_id__ !== ${e(i)}) throw new Error('snapshot ' + ${e(i)} + ' was superseded by ' + (window.__omni_snapshot_id__ || '(none)') + ' — call browser_snapshot again'); `:``)+`const el = (window.__omni_refs__ && window.__omni_refs__.get(${t(r)}))?.deref(); if (!window.__omni_refs__) throw new Error('no snapshot in this page — call browser_snapshot first'); if (!window.__omni_refs__.has(${t(r)})) throw new Error('ref ' + ${t(r)} + ' not in snapshot — call browser_snapshot again'); if (!el) throw new Error('ref ' + ${t(r)} + ' was garbage-collected — call browser_snapshot again'); `}function i(t,n={},{live:i=!1}={}){if(!n||typeof n!=`object`||Array.isArray(n))throw Error(`Browser action arguments must be an object`);if(![`snapshot`,`click`,`type`].includes(t))throw Error(`Unsupported browser action`);let a=t===`snapshot`?[]:[`ref`,`snapshot_id`,`selector`];if(t===`type`&&a.push(`text`),Object.keys(n).some(e=>!a.includes(e)))throw Error(`Unsupported browser action argument`);if(t===`snapshot`)return`(() => {
  const snapshotId = (crypto && crypto.randomUUID) ? crypto.randomUUID() : ('snap-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10));
  window.__omni_refs__ = new Map();
  window.__omni_snapshot_id__ = snapshotId;
  let nextRef = 0;

  const TAG_ROLE = {
    a: 'link', button: 'button', textarea: 'textbox', select: 'combobox',
    nav: 'navigation', main: 'main', header: 'banner', footer: 'contentinfo',
    form: 'form', section: 'region', article: 'article', aside: 'complementary',
    ul: 'list', ol: 'list', li: 'listitem', img: 'image', label: 'label',
    table: 'table', tr: 'row', td: 'cell', th: 'columnheader',
    dialog: 'dialog', summary: 'button', details: 'group',
  };
  const isInteractiveTag = (tag) =>
    tag === 'a' || tag === 'button' || tag === 'input' ||
    tag === 'textarea' || tag === 'select' || tag === 'label' ||
    tag === 'summary';
  const isHeading = (tag) => tag && tag.length === 2 && tag[0] === 'h' && tag[1] >= '1' && tag[1] <= '6';

  function getRole(el) {
    const explicit = el.getAttribute && el.getAttribute('role');
    if (explicit) return explicit;
    const tag = el.tagName && el.tagName.toLowerCase();
    if (!tag) return null;
    if (tag === 'input') {
      const t = (el.type || 'text').toLowerCase();
      if (t === 'submit' || t === 'button' || t === 'reset') return 'button';
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'range') return 'slider';
      if (t === 'hidden') return null;
      return 'textbox';
    }
    if (isHeading(tag)) return 'heading';
    if (TAG_ROLE[tag]) return TAG_ROLE[tag];
    if (el.hasAttribute && (el.hasAttribute('tabindex') || el.hasAttribute('onclick'))) return 'generic';
    return null;
  }

  // A name is its visible text however deep it sits (not aria-hidden, hidden or script
  // text); the walk stops after this many elements, as names are cut at 80 characters.
  const NAME_NODES = 500;
  const UNREAD = new Set(['script', 'style', 'template', 'noscript']);
  function getName(el, depth = 0, budget = { nodes: NAME_NODES }) {
    if (--budget.nodes < 0) return '';
    if (el.getAttribute) {
      const lbl = el.getAttribute('aria-label');
      if (lbl) return lbl;
      const labelledBy = el.getAttribute('aria-labelledby');
      if (labelledBy && depth === 0) {
        // What each referenced node shows: its rendered text (not hidden descendants'), or an
        // image's alt.
        const named = labelledBy.split(/\\s+/).map((id) => document.getElementById(id))
          .filter(Boolean).map((node) => node.getAttribute('aria-label') || (typeof node.innerText === 'string' ? node.innerText : node.textContent) || node.getAttribute('alt') || '')
          .join(' ').trim().replace(/\\s+/g, ' ');
        if (named) return named.slice(0, 80);
      }
      const alt = el.getAttribute('alt');
      if (alt) return alt;
      const ph = el.getAttribute('placeholder');
      if (ph) return ph;
      const ttl = el.getAttribute('title');
      if (ttl) return ttl;
    }
    const tag = el.tagName && el.tagName.toLowerCase();
    // A button-like input is named by its value; a field's value is its state (below).
    if (tag === 'input' && el.value && /^(submit|button|reset)$/i.test(el.type)) return String(el.value).slice(0, 80);
    let text = '';
    for (const node of el.childNodes) {
      if (node.nodeType === 3) text += node.textContent;
      else if (node.nodeType === 1) {
        const childTag = node.tagName && node.tagName.toLowerCase();
        if (depth === 0 && isInteractiveTag(childTag)) continue;
        if (UNREAD.has(childTag) || node.hidden || node.getAttribute('aria-hidden') === 'true') continue;
        text += getName(node, depth + 1, budget);
      }
      if (text.length > 80) break;
    }
    return text.trim().replace(/\\s+/g, ' ').slice(0, 80);
  }

  // Roles named by their content: where getName finds no text (or stops short), they fall
  // back to what renders.
  const NAMED_BY_CONTENT = new Set(['link', 'button', 'tab', 'menuitem', 'menuitemcheckbox', 'menuitemradio', 'option', 'heading', 'treeitem']);
  // A name cut short where getName stopped going deeper ("Delete" of "Delete account") is
  // the start of what renders: then that is the name.
  function nameOf(el, role) {
    const name = getName(el);
    if (!NAMED_BY_CONTENT.has(role) || typeof el.innerText !== 'string') return name;
    const shown = el.innerText.trim().replace(/\\s+/g, ' ').slice(0, 80);
    return !name || (shown.length > name.length && shown.startsWith(name)) ? shown : name;
  }

  // What a control is set to, so the agent can check what it changed: checked state for
  // checkboxes, radios and switches, and a filled field's value (never a password's).
  function getState(el, role) {
    const tag = el.tagName && el.tagName.toLowerCase();
    if (role === 'checkbox' || role === 'radio' || role === 'switch' || role === 'menuitemcheckbox' || role === 'menuitemradio') {
      const aria = el.getAttribute('aria-checked');
      const native = tag === 'input' && (el.type === 'checkbox' || el.type === 'radio');
      if (native && el.indeterminate) return ' [mixed]';
      if (native) return el.checked ? ' [checked]' : ' [unchecked]';
      if (aria === 'mixed') return ' [mixed]';
      if (aria === 'true' || aria === 'false') return aria === 'true' ? ' [checked]' : ' [unchecked]';
      return '';
    }
    const field = tag === 'textarea' || (tag === 'input' && !/^(submit|button|reset|checkbox|radio|range|file|image|hidden|password)$/i.test(el.type || 'text'));
    // Whole, unlike a name: the agent compares it with what it typed. A very long one (a
    // pasted document) is cut, and says so. Never a secret's: one masked on screen.
    if (field && el.value && !masked(el)) {
      const value = String(el.value);
      return ' [value=' + JSON.stringify(value.length > 2000 ? value.slice(0, 2000) + '…' : value) + ']';
    }
    return '';
  }

  // A field whose text the page hides as a password's: masked characters (text-security),
  // or text drawn clear (a mask's fallback), or one the page marks as a secret's
  // (a password or one-time code, a card's number or security code).
  const SECRET_AUTOCOMPLETE = /(^|\\s)(current-password|new-password|one-time-code|cc-number|cc-csc)(\\s|$)/i;
  function masked(el) {
    if (SECRET_AUTOCOMPLETE.test(el.getAttribute('autocomplete') || '')) return true;
    const style = window.getComputedStyle(el);
    const security = style.getPropertyValue('-webkit-text-security') || style.webkitTextSecurity || '';
    if (security && security !== 'none') return true;
    const clear = (color) => color === 'transparent' || /^rgba\\(.*,\\s*0(\\.0+)?\\)$/.test(color) || /\\/\\s*0(\\.0+)?%?\\)$/.test(color);
    return clear(style.color) || clear(style.getPropertyValue('-webkit-text-fill-color'));
  }

  function isVisible(el, style) {
    if (!el.getBoundingClientRect) return false;
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    if (style.opacity === '0') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  // Roles with no line of their own (their children still have theirs): a plain container,
  // or one the page marks as presentation only (a carousel's track, a layout table).
  const UNLISTED = new Set(['generic', 'presentation', 'none']);
  const IMAGE = new Set(['image', 'img']);
  // The part of the page on screen, by which each line says whether it's out of view.
  const viewWidth = window.innerWidth;
  const viewHeight = window.innerHeight;
  // Which side of the screen an element is off, where it's entirely off it; '' when any
  // of it shows, or it has no box of its own (display: contents).
  function sideOf(el, contents) {
    if (contents) return '';
    const r = el.getBoundingClientRect();
    if (r.bottom <= 0) return 'above';
    if (r.top >= viewHeight) return 'below';
    if (r.right <= 0) return 'left';
    if (r.left >= viewWidth) return 'right';
    return '';
  }

  // Every element with a line, in page order, with the index of the nearest one above it
  // (-1 for none). Lines and refs are given once it's known which fit (see below).
  const entries = [];
  function walk(el, depth, parent, namedAbove) {
    if (!(el instanceof Element)) return;
    const style = window.getComputedStyle(el);
    // A display: contents box has no box of its own (a 0x0 rect); its children still show,
    // and it keeps its role (a link styled so is still a link).
    const contents = style.display === 'contents';
    if (!contents && !isVisible(el, style)) return;
    const role = getRole(el);
    const listed = role !== null && !UNLISTED.has(role);
    const name = listed ? nameOf(el, role) : '';
    // Left out though they have a role: a live region with nothing in it now (pages keep
    // visually hidden ones for screen readers), and an image with no name inside a named
    // control or region, which says what it shows ("Night meal, 12,50 €").
    const picked = listed && !(!name && (role === 'status' || (IMAGE.has(role) && namedAbove)));
    let index = parent;
    if (picked) {
      index = entries.length;
      let line = '  '.repeat(depth) + '- ' + role;
      if (name) line += ' ' + JSON.stringify(name);
      line += getState(el, role);
      const side = sideOf(el, contents);
      if (side) line += ' [' + side + ']';
      entries.push({ el, line, parent, side });
    }
    const childDepth = picked ? depth + 1 : depth;
    const childNamed = picked ? !!name : namedAbove;
    for (const child of el.children) walk(child, childDepth, index, childNamed);
  }

  if (document.body) walk(document.body, 0, -1, false);

  // At most this much tree. On a bigger page, what's on screen goes first, then the rest
  // in page order while it fits, each with the lines above it, so the tree keeps its
  // shape; a last line says how many were left out. Only lines shown get refs.
  const MAX_TREE_CHARS = 24000;
  const kept = new Array(entries.length).fill(false);
  let used = 0;
  // Keep entry i and those above it that aren't kept yet, if they all fit.
  function keep(i) {
    const chain = [];
    let cost = 0;
    for (let at = i; at !== -1 && !kept[at]; at = entries[at].parent) {
      chain.push(at);
      cost += entries[at].line.length + 12;
    }
    if (chain.length === 0 || used + cost > MAX_TREE_CHARS) return;
    used += cost;
    for (const at of chain) kept[at] = true;
  }
  for (let i = 0; i < entries.length; i++) if (!entries[i].side) keep(i);
  for (let i = 0; i < entries.length; i++) keep(i);

  const scrollTop = Math.max(0, Math.round(window.scrollY || 0));
  const pageHeight = Math.max(
    document.documentElement ? document.documentElement.scrollHeight : 0,
    document.body ? document.body.scrollHeight : 0,
    scrollTop + viewHeight,
  );
  const lines = ['viewport: ' + scrollTop + '–' + (scrollTop + viewHeight) + ' of ' + pageHeight + 'px'];
  let left = 0;
  for (let i = 0; i < entries.length; i++) {
    if (!kept[i]) {
      left++;
      continue;
    }
    const ref = ++nextRef;
    window.__omni_refs__.set(ref, new WeakRef(entries[i].el));
    lines.push(entries[i].line + ' [ref=' + ref + ']');
  }
  if (left > 0) lines.push('… ' + left + ' more');

  return JSON.stringify({
    snapshot_id: snapshotId,
    url: window.location.href,
    title: document.title,
    tree: lines.join('\\n'),
  });
})()`;if(n.ref!==void 0&&(!Number.isSafeInteger(n.ref)||n.ref<=0))throw Error(`ref must be a positive integer`);if(n.ref===void 0&&(typeof n.selector!=`string`||!n.selector))throw Error(`A ref or selector is required`);if(n.selector!==void 0&&(typeof n.selector!=`string`||n.selector.length>4096))throw Error(`selector must be a string of at most 4096 characters`);if(n.snapshot_id!==void 0&&(typeof n.snapshot_id!=`string`||n.snapshot_id.length>128))throw Error(`snapshot_id must be a string of at most 128 characters`);if(t===`type`&&(typeof n.text!=`string`||n.text.length>1e5))throw Error(`text must be a string of at most 100000 characters`);if(t===`click`)return`(() => { ${r(n)} el.scrollIntoView({ block: 'center', inline: 'center' }); el.click(); return 'ok'; })()`;let o=n.text,s=i?`omnigentLive(); `:``;return`(() => { ${r(n)} el.focus(); ${s}const setter = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value')?.set; if (setter) setter.call(el, ${e(o)}); else el.value = ${e(o)}; ${s}el.dispatchEvent(new Event('input', { bubbles: true })); ${s}el.dispatchEvent(new Event('change', { bubbles: true })); return 'ok'; })()`}export{n as LEGACY_SNAPSHOT_JS,i as buildBrowserActionScript,r as findElJs,t as jsNumber,e as jsString};