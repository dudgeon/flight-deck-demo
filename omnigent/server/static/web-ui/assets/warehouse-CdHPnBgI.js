import{t as e}from"./createLucideIcon-DX_i9hk4.js";var t=`omnigent-slim-canvas`,n=String.raw`
  var CANVAS_SOURCE = "omnigent-slim-canvas";
  var canvasHandled = {};
  var MAX_DOM = 400000;
  var MAX_TEXT = 4000;
  var MAX_PIXELS = 6000000;

  function canvasReply(id, result) {
    window.parent.postMessage({ source: SOURCE, type: "canvas-result", id: id, result: result }, "*");
  }
  function describe(el) {
    if (!el || el.nodeType !== 1) return null;
    var d = { tag: el.tagName.toLowerCase() };
    if (el.id) d.id = el.id;
    if (el.className && typeof el.className === "string") d.class = el.className;
    var t = (el.innerText || el.value || "").trim();
    if (t) d.text = t.slice(0, 80);
    return d;
  }
  function pageText() {
    var t = (document.body && document.body.innerText) || "";
    return t.length > MAX_TEXT ? t.slice(0, MAX_TEXT) + "\n[truncated]" : t;
  }
  // A timer, not requestAnimationFrame: a hidden canvas gets no animation frames.
  function settle() {
    return new Promise(function (resolve) { setTimeout(resolve, 80); });
  }
  function bySelector(selector, index) {
    var list;
    try { list = document.querySelectorAll(selector); }
    catch (e) { throw new Error("invalid selector: " + selector); }
    if (!list.length) throw new Error("no element matches " + selector);
    var i = index || 0;
    if (i >= list.length) throw new Error(list.length + " elements match " + selector + "; index " + i + " is out of range");
    return list[i];
  }
  function ownText(el) {
    return ((el.innerText != null ? el.innerText : el.textContent) || el.value || el.getAttribute("aria-label") || "").trim();
  }
  function byText(text, index) {
    var want = String(text).trim();
    var clickable = "button, a, [role=button], input[type=button], input[type=submit], input[type=reset], summary, label, [onclick], [tabindex]";
    var hits = Array.prototype.filter.call(document.querySelectorAll(clickable), function (el) {
      return ownText(el) === want;
    });
    if (!hits.length) {
      hits = Array.prototype.filter.call(document.body.querySelectorAll("*"), function (el) {
        if (ownText(el) !== want) return false;
        // Deepest match only: skip an element whose child also matches.
        return !Array.prototype.some.call(el.children, function (c) { return ownText(c) === want; });
      });
    }
    if (!hits.length) throw new Error("no element has the text " + JSON.stringify(want));
    var i = index || 0;
    if (i >= hits.length) throw new Error(hits.length + " elements have that text; index " + i + " is out of range");
    return hits[i];
  }
  function target(args) {
    if (args.selector) return bySelector(args.selector, args.index);
    if (args.text != null) return byText(args.text, args.index);
    throw new Error("give a selector or text");
  }
  function isField(el) {
    return el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT";
  }
  function setFieldValue(el, value) {
    var proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype
      : el.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    var setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
  function mouse(el, type) {
    var r = el.getBoundingClientRect();
    var init = { bubbles: true, cancelable: true, view: window, button: 0,
      clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
    var Ctor = type.indexOf("pointer") === 0 && window.PointerEvent ? PointerEvent : MouseEvent;
    el.dispatchEvent(new Ctor(type, init));
  }
  function keyEvents(el, key) {
    var code = key.length === 1 ? (/[0-9]/.test(key) ? "Digit" + key : /[a-z]/i.test(key) ? "Key" + key.toUpperCase() : "") : key;
    var init = { key: key, code: code, bubbles: true, cancelable: true, view: window };
    var down = el.dispatchEvent(new KeyboardEvent("keydown", init));
    if (key.length === 1 || key === "Enter") el.dispatchEvent(new KeyboardEvent("keypress", init));
    el.dispatchEvent(new KeyboardEvent("keyup", init));
    return down;
  }
  // Copy live state (field values, canvases) from the page into a deep clone.
  function syncState(orig, clone) {
    var a = orig.querySelectorAll("input, textarea, select, canvas");
    var b = clone.querySelectorAll("input, textarea, select, canvas");
    for (var i = 0; i < a.length && i < b.length; i++) {
      var o = a[i], c = b[i];
      if (o.tagName === "TEXTAREA") c.textContent = o.value;
      else if (o.tagName === "SELECT") {
        for (var j = 0; j < o.options.length; j++) {
          if (o.options[j].selected) c.options[j].setAttribute("selected", "");
          else c.options[j].removeAttribute("selected");
        }
      } else if (o.tagName === "CANVAS") {
        try {
          var img = document.createElement("img");
          img.setAttribute("src", o.toDataURL());
          img.setAttribute("width", o.width);
          img.setAttribute("height", o.height);
          c._snapshot = img;
        } catch (e) {}
      } else {
        c.setAttribute("value", o.value);
        if (o.checked) c.setAttribute("checked", ""); else c.removeAttribute("checked");
      }
    }
  }
  function stripViewer(clone) {
    var extras = clone.querySelectorAll("script[data-omnigent-artifact-bridge], script[data-omni-nonce], style[data-omni-restore-hide]");
    for (var i = 0; i < extras.length; i++) extras[i].remove();
  }
  function domOf(args) {
    var root = args.selector ? bySelector(args.selector, args.index) : document.documentElement;
    var clone = root.cloneNode(true);
    syncState(root, clone);
    stripViewer(clone);
    var html = (root === document.documentElement ? "<!DOCTYPE html>\n" : "") + clone.outerHTML;
    if (html.length > MAX_DOM) return { dom: html.slice(0, MAX_DOM), dom_truncated: true, dom_chars: html.length };
    return { dom: html };
  }
  function inlineStyles(orig, clone) {
    var cs = getComputedStyle(orig);
    var css = "";
    for (var i = 0; i < cs.length; i++) {
      var name = cs[i];
      css += name + ":" + cs.getPropertyValue(name) + ";";
    }
    clone.setAttribute("style", css);
    var oc = orig.children, cc = clone.children;
    for (var j = 0; j < oc.length && j < cc.length; j++) inlineStyles(oc[j], cc[j]);
  }
  function screenshot() {
    var de = document.documentElement;
    var width = Math.max(de.clientWidth, 1);
    var height = Math.max(de.scrollHeight, document.body ? document.body.scrollHeight : 0, de.clientHeight, 1);
    var clone = de.cloneNode(true);
    syncState(de, clone);
    inlineStyles(de, clone);
    var scripts = clone.querySelectorAll("script, noscript");
    for (var i = 0; i < scripts.length; i++) scripts[i].remove();
    var canvases = clone.querySelectorAll("canvas");
    for (var k = 0; k < canvases.length; k++) {
      if (canvases[k]._snapshot) {
        canvases[k]._snapshot.setAttribute("style", canvases[k].getAttribute("style") || "");
        canvases[k].replaceWith(canvases[k]._snapshot);
      }
    }
    clone.style.height = height + "px";
    clone.style.width = width + "px";
    var xhtml = new XMLSerializer().serializeToString(clone);
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '">' +
      '<foreignObject x="0" y="0" width="100%" height="100%">' + xhtml + "</foreignObject></svg>";
    var scale = Math.min(window.devicePixelRatio || 1, 2);
    if (width * height * scale * scale > MAX_PIXELS) scale = Math.sqrt(MAX_PIXELS / (width * height));
    return new Promise(function (resolve, reject) {
      var img = new Image();
      img.onload = function () {
        try {
          var c = document.createElement("canvas");
          c.width = Math.max(1, Math.round(width * scale));
          c.height = Math.max(1, Math.round(height * scale));
          var ctx = c.getContext("2d");
          ctx.scale(scale, scale);
          ctx.drawImage(img, 0, 0);
          resolve({ data_url: c.toDataURL("image/png"), width: width, height: height });
        } catch (e) {
          reject(new Error("this browser would not render a screenshot of the canvas (" + e.message + "); read the DOM instead"));
        }
      };
      img.onerror = function () { reject(new Error("the screenshot image failed to render")); };
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    });
  }
  function jsonSafe(value) {
    var seen = [];
    var text = JSON.stringify(value, function (k, v) {
      if (v && typeof v === "object") {
        if (v.nodeType === 1) return describe(v);
        if (v === window || v === document) return "[" + (v === window ? "window" : "document") + "]";
        if (seen.indexOf(v) >= 0) return "[circular]";
        seen.push(v);
      }
      if (typeof v === "function") return "[function]";
      if (v === undefined) return null;
      return v;
    });
    if (text === undefined) text = "null";
    return text.length > 20000 ? text.slice(0, 20000) + "...[truncated]" : text;
  }
  var canvasActions = {
    canvas_read: function (args) {
      var data = {
        title: document.title,
        viewport: { width: document.documentElement.clientWidth, height: document.documentElement.clientHeight },
        page_height: document.documentElement.scrollHeight,
        focused: describe(document.activeElement)
      };
      if (args.dom !== false) {
        var d = domOf(args);
        for (var key in d) data[key] = d[key];
      }
      if (args.screenshot === false) return Promise.resolve({ ok: true, data: data });
      return screenshot().then(function (shot) {
        return { ok: true, data: data, data_url: shot.data_url };
      }, function (err) {
        data.screenshot_error = err.message;
        return { ok: true, data: data };
      });
    },
    canvas_click: function (args) {
      var el = target(args);
      if (el.scrollIntoView) el.scrollIntoView({ block: "nearest", inline: "nearest" });
      mouse(el, "pointerdown");
      mouse(el, "mousedown");
      if (el.focus) el.focus();
      mouse(el, "pointerup");
      mouse(el, "mouseup");
      el.click();
      return settle().then(function () { return { ok: true, data: { clicked: describe(el), text: pageText() } }; });
    },
    canvas_type: function (args) {
      var el = bySelector(args.selector, args.index);
      if (el.focus) el.focus();
      var text = String(args.text == null ? "" : args.text);
      if (isField(el)) {
        setFieldValue(el, args.clear === false ? el.value + text : text);
      } else if (el.isContentEditable) {
        if (args.clear === false) el.textContent += text; else el.textContent = text;
        el.dispatchEvent(new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }));
      } else {
        throw new Error("element is not an input, textarea, select or contenteditable; use canvas_set_content");
      }
      if (args.press_enter) {
        var go = keyEvents(el, "Enter");
        if (go && el.form && el.tagName === "INPUT" && el.form.requestSubmit) el.form.requestSubmit();
      }
      return settle().then(function () { return { ok: true, data: { typed_into: describe(el), text: pageText() } }; });
    },
    canvas_set_content: function (args) {
      var els = args.all ? Array.prototype.slice.call(document.querySelectorAll(args.selector)) : [bySelector(args.selector, args.index)];
      if (!els.length) throw new Error("no element matches " + args.selector);
      els.forEach(function (el) {
        if (isField(el)) setFieldValue(el, String(args.text != null ? args.text : args.html || ""));
        else if (args.html != null) el.innerHTML = String(args.html);
        else el.textContent = String(args.text == null ? "" : args.text);
      });
      return settle().then(function () { return { ok: true, data: { changed: els.length, text: pageText() } }; });
    },
    canvas_press_key: function (args) {
      var el = args.selector ? bySelector(args.selector, args.index) : (document.activeElement || document.body);
      if (args.selector && el.focus) el.focus();
      keyEvents(el, String(args.key));
      return settle().then(function () { return { ok: true, data: { target: describe(el), text: pageText() } }; });
    },
    canvas_eval: function (args) {
      var value = (0, eval)(String(args.script || ""));
      return Promise.resolve(value).then(function (v) {
        return { ok: true, data: { result: jsonSafe(v) } };
      });
    }
  };
  window.addEventListener("message", function (event) {
    if (event.source !== window.parent) return;
    var m = event.data;
    if (!m || m.source !== CANVAS_SOURCE || m.type !== "canvas-request") return;
    // Acknowledge every copy, so the host stops re-sending; run each id once.
    window.parent.postMessage({ source: SOURCE, type: "canvas-ack", id: m.id }, "*");
    if (canvasHandled[m.id]) return;
    canvasHandled[m.id] = true;
    var run = canvasActions[m.action];
    if (!run) { canvasReply(m.id, { ok: false, error: "unknown canvas action " + m.action }); return; }
    var result;
    try { result = run(m.args || {}); }
    catch (e) { canvasReply(m.id, { ok: false, error: String(e && e.message || e) }); return; }
    Promise.resolve(result).then(function (r) { canvasReply(m.id, r); },
      function (e) { canvasReply(m.id, { ok: false, error: String(e && e.message || e) }); });
  });
`,r={base:{font:`-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, sans-serif`,mono:`ui-monospace, "SF Mono", Menlo, Consolas, monospace`,r:`6px`,"r-panel":`10px`,gap:`12px`,text:`14px`,"text-sm":`12.5px`,"text-title":`19px`,"weight-title":`650`,"tracking-title":`-0.015em`},light:{bg:`#f4f6f9`,surface:`#ffffff`,sunk:`#eaeef3`,ink:`#0f1e30`,"ink-2":`#475a70`,"ink-3":`#71829a`,line:`#d6dde6`,"line-strong":`#b4c0ce`,navy:`#0a223d`,"navy-hover":`#17385f`,"on-navy":`#f2f6fa`,chrome:`#0a223d`,"chrome-ink":`#f2f6fa`,"chrome-ink-2":`#9fb4cc`,"chrome-hover":`#17385f`,"chrome-active":`#2a5486`,"chrome-line":`#17385f`,you:`#b0237a`,"you-soft":`#f8e1ef`,"on-you":`#ffffff`,ok:`#17794a`,"ok-soft":`#ddf1e6`,info:`#1e6aa6`,"info-soft":`#ddebf7`,warn:`#8d5a00`,"warn-soft":`#f9ebcf`,attn:`#8d5a00`,"attn-soft":`#f9ebcf`,fail:`#b3261e`,"fail-soft":`#f9dedc`,idle:`#71829a`,"idle-soft":`#eaeef3`,agent:`#4f46b8`,"agent-soft":`#e8e6f8`,"author-1":`#1e6aa6`,"author-2":`#8d5a00`,"author-3":`#4d6b1f`,"author-4":`#7a3f8f`,"author-5":`#1f6b66`,"author-6":`#17794a`,"author-7":`#a0462f`,"author-8":`#3d5a99`,comment:`#f5c518`,"comment-strong":`#d29e00`,shadow:`#0a223d`,build:`#0d6e78`,"build-soft":`#d9f0f1`,"on-build":`#ffffff`,"hangar-bg":`#edf4f6`,"hangar-grid":`#d3e3e7`,"hangar-paper":`#fbfdfd`},dark:{bg:`#071526`,surface:`#0c1e33`,sunk:`#091a2d`,ink:`#e6edf5`,"ink-2":`#a6b6c8`,"ink-3":`#71849a`,line:`#1e3550`,"line-strong":`#3a5676`,navy:`#2f64a0`,"navy-hover":`#3a73b3`,"on-navy":`#f2f6fa`,chrome:`#0d2138`,"chrome-ink":`#f2f6fa`,"chrome-ink-2":`#8ea6c2`,"chrome-hover":`#15304f`,"chrome-active":`#1f4470`,"chrome-line":`#17304d`,you:`#f26dc3`,"you-soft":`#3a1530`,"on-you":`#2a0a1f`,ok:`#5bcb93`,"ok-soft":`#0f3123`,info:`#7db7ea`,"info-soft":`#12304d`,warn:`#e9b44c`,"warn-soft":`#362808`,attn:`#e9b44c`,"attn-soft":`#362808`,fail:`#ff8a80`,"fail-soft":`#3d1715`,idle:`#71849a`,"idle-soft":`#12263b`,agent:`#a59cff`,"agent-soft":`#211d47`,"author-1":`#7db7ea`,"author-2":`#e9b44c`,"author-3":`#a9c46a`,"author-4":`#d39be6`,"author-5":`#6fcfc6`,"author-6":`#5bcb93`,"author-7":`#f2967a`,"author-8":`#9fb3ef`,comment:`#f5c518`,"comment-strong":`#d29e00`,shadow:`#000000`,build:`#58c9d3`,"build-soft":`#0c3237`,"on-build":`#04262a`,"hangar-bg":`#081d24`,"hangar-grid":`#12333b`,"hangar-paper":`#0b252d`}},i=`omnigent-slim-artifact`,a=`omnigent-slim:artifact-prompt`,o=`omnigent-slim:artifact-action`,s=2e4,c=2e5,l=`omnigent-slim:artifact-state:`,u=new Map;function d(e,t){return t?`${e}:${t}`:null}function f(e){if(!e)return{};let t=u.get(e);if(t)return t;let n={};try{let t=window.localStorage.getItem(l+e),r=t?JSON.parse(t):null;typeof r==`object`&&r&&!Array.isArray(r)&&(n=r)}catch{}return u.set(e,n),n}function p(e,t,n){let r;try{r=JSON.parse(n)}catch{return}let i={...f(e),[t]:r},a=JSON.stringify(i);if(!(a.length>c)){u.set(e,i);try{window.localStorage.setItem(l+e,a)}catch{}}}function m(e){let t=JSON.stringify(e).replace(/</g,`\\u003c`);return`<script data-omnigent-artifact-bridge>(function () {
  if (window.omnigent) return;
  var SOURCE = ${JSON.stringify(i)};
  function post(type, text, key) {
    window.parent.postMessage(
      { source: SOURCE, type: type, text: String(text == null ? "" : text), key: key },
      "*"
    );
  }
  window.omnigent = {
    /** Put text in the session composer for the user to review and send. */
    prompt: function (text) { post("prompt", text); },
    /** What this artifact saved before it was last reloaded: { key: value }. */
    state: ${t},
    /** Keep a small JSON value across reloads of this artifact. */
    saveState: function (key, value) {
      try { post("state", JSON.stringify(value === undefined ? null : value), String(key)); } catch (e) {}
    },
    /**
     * Send state changes to the agent without the composer:
     * act({ dataset: "data/x.json", changes: [{ id: "R-01", field: "status", value: "reviewed" }] }).
     * Only state fields and plain status words are accepted; the host writes the message.
     */
    act: function (request) {
      try { post("act", JSON.stringify(request)); } catch (e) {}
    }
  };
${n}
})();<\/script>`}function h(e,t={}){let n=m(t),r=/^\s*<!doctype[^>]*>/i.exec(e);if(!r)return n+e;let i=r[0].length;return e.slice(0,i)+n+e.slice(i)}function g(e,t){let n={...r.base,...r[t]},i=`<style data-pa-tokens>:root:root:root{${Object.entries(n).map(([e,t])=>`--pa-${e}:${t}`).join(`;`)};color-scheme:${t}}</style><script>document.documentElement.setAttribute("data-theme",${JSON.stringify(t)})<\/script>`,a=/<\/head\s*>/i.exec(e);return a?e.slice(0,a.index)+i+e.slice(a.index):e+i}var _=50,v=400,y=/^[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}$/,b=/^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$/,x=/^(status|locked|[a-z][a-z0-9_]{0,30}_status)$/,S=/^[a-z][a-z0-9-]{0,30}$/,C=0;function w(e){if(typeof e!=`object`||!e)return null;let{dataset:t,changes:n}=e;if(typeof t!=`string`||!y.test(t)||t.includes(`..`)||!Array.isArray(n)||n.length===0||n.length>_)return null;let r=[];for(let e of n){if(typeof e!=`object`||!e)return null;let{id:t,field:n,value:i}=e;if(typeof t!=`string`||!b.test(t)||typeof n!=`string`||!x.test(n)||!(typeof i==`boolean`||typeof i==`string`&&S.test(i)))return null;r.push(`- ${t} ${n} = ${String(i)}`)}return`Canvas action on ${t}:\n${r.join(`
`)}`}function T(e,t=null){if(typeof e!=`object`||!e)return!1;let n=e;if(n.source!==`omnigent-slim-artifact`)return!1;if(n.type===`state`)return!t||typeof n.key!=`string`||typeof n.text!=`string`?!1:(p(t,n.key.slice(0,200),n.text),!0);if(n.type===`act`){if(typeof n.text!=`string`)return!1;let e;try{e=JSON.parse(n.text)}catch{return!1}let t=w(e),r=Date.now();if(!t||r-C<v)return!1;C=r;let i={text:t};return window.dispatchEvent(new CustomEvent(o,{detail:i})),!0}if(n.type!==`prompt`||typeof n.text!=`string`||!n.text.trim())return!1;let r={text:n.text.slice(0,s)};return window.dispatchEvent(new CustomEvent(a,{detail:r})),!0}var E={name:`book-open`,size:24,node:[[`path`,{d:`M12 5v16`,key:`1f6ucr`}],[`path`,{d:`M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z`,key:`1fyvmf`}]]};E.node;var D=e(E),O={name:`compass`,size:24,node:[[`circle`,{cx:`12`,cy:`12`,r:`10`,key:`1mglay`}],[`path`,{d:`m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z`,key:`9ktpf1`}]]};O.node;var k=e(O),A={name:`warehouse`,size:24,node:[[`path`,{d:`M18 21V10a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1v11`,key:`pb2vm6`}],[`path`,{d:`M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 1.132-1.803l7.95-3.974a2 2 0 0 1 1.837 0l7.948 3.974A2 2 0 0 1 22 8z`,key:`doq5xv`}],[`path`,{d:`M6 13h12`,key:`yf64js`}],[`path`,{d:`M6 17h12`,key:`1jwigz`}]]};A.node;var j=e(A);export{i as a,T as c,f as d,t as f,o as i,h as l,k as n,a as o,D as r,d as s,j as t,g as u};