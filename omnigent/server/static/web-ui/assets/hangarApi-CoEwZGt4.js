import{p as e,t}from"./useQuery-C9636CHT.js";import{t as n}from"./useMutation-9bjIesfq.js";import{q as r}from"./streamdown-CKK1KfV6.js";import{L as i}from"./host-CBGPXdh8.js";import{n as a}from"./identity-DrBsj2po.js";import{m as o,n as s,t as c}from"./createLucideIcon-BIFcAuq5.js";import{t as l}from"./utils-6qKQYblA.js";var u=`omnigent-slim-canvas`,d=String.raw`
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
`,f={base:{font:`-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, sans-serif`,mono:`ui-monospace, "SF Mono", Menlo, Consolas, monospace`,r:`6px`,"r-panel":`10px`,gap:`12px`,text:`14px`,"text-sm":`12.5px`,"text-title":`19px`,"weight-title":`650`,"tracking-title":`-0.015em`},light:{bg:`#f4f6f9`,surface:`#ffffff`,sunk:`#eaeef3`,ink:`#0f1e30`,"ink-2":`#475a70`,"ink-3":`#71829a`,line:`#d6dde6`,"line-strong":`#b4c0ce`,navy:`#0a223d`,"navy-hover":`#17385f`,"on-navy":`#f2f6fa`,chrome:`#0a223d`,"chrome-ink":`#f2f6fa`,"chrome-ink-2":`#9fb4cc`,"chrome-hover":`#17385f`,"chrome-active":`#2a5486`,"chrome-line":`#17385f`,you:`#b0237a`,"you-soft":`#f8e1ef`,"on-you":`#ffffff`,ok:`#17794a`,"ok-soft":`#ddf1e6`,info:`#1e6aa6`,"info-soft":`#ddebf7`,warn:`#8d5a00`,"warn-soft":`#f9ebcf`,attn:`#8d5a00`,"attn-soft":`#f9ebcf`,fail:`#b3261e`,"fail-soft":`#f9dedc`,idle:`#71829a`,"idle-soft":`#eaeef3`,agent:`#4f46b8`,"agent-soft":`#e8e6f8`,"author-1":`#1e6aa6`,"author-2":`#8d5a00`,"author-3":`#4d6b1f`,"author-4":`#7a3f8f`,"author-5":`#1f6b66`,"author-6":`#17794a`,"author-7":`#a0462f`,"author-8":`#3d5a99`,comment:`#f5c518`,"comment-strong":`#d29e00`,shadow:`#0a223d`,build:`#0d6e78`,"build-soft":`#d9f0f1`,"on-build":`#ffffff`,"hangar-bg":`#edf4f6`,"hangar-grid":`#d3e3e7`,"hangar-paper":`#fbfdfd`},dark:{bg:`#071526`,surface:`#0c1e33`,sunk:`#091a2d`,ink:`#e6edf5`,"ink-2":`#a6b6c8`,"ink-3":`#71849a`,line:`#1e3550`,"line-strong":`#3a5676`,navy:`#2f64a0`,"navy-hover":`#3a73b3`,"on-navy":`#f2f6fa`,chrome:`#0d2138`,"chrome-ink":`#f2f6fa`,"chrome-ink-2":`#8ea6c2`,"chrome-hover":`#15304f`,"chrome-active":`#1f4470`,"chrome-line":`#17304d`,you:`#f26dc3`,"you-soft":`#3a1530`,"on-you":`#2a0a1f`,ok:`#5bcb93`,"ok-soft":`#0f3123`,info:`#7db7ea`,"info-soft":`#12304d`,warn:`#e9b44c`,"warn-soft":`#362808`,attn:`#e9b44c`,"attn-soft":`#362808`,fail:`#ff8a80`,"fail-soft":`#3d1715`,idle:`#71849a`,"idle-soft":`#12263b`,agent:`#a59cff`,"agent-soft":`#211d47`,"author-1":`#7db7ea`,"author-2":`#e9b44c`,"author-3":`#a9c46a`,"author-4":`#d39be6`,"author-5":`#6fcfc6`,"author-6":`#5bcb93`,"author-7":`#f2967a`,"author-8":`#9fb3ef`,comment:`#f5c518`,"comment-strong":`#d29e00`,shadow:`#000000`,build:`#58c9d3`,"build-soft":`#0c3237`,"on-build":`#04262a`,"hangar-bg":`#081d24`,"hangar-grid":`#12333b`,"hangar-paper":`#0b252d`}},p=`omnigent-slim-artifact`,m=`omnigent-slim:artifact-prompt`,h=`omnigent-slim:artifact-action`,ee=2e4,te=2e5,g=`omnigent-slim:artifact-state:`,_=new Map;function v(e,t){return t?`${e}:${t}`:null}function y(e){if(!e)return{};let t=_.get(e);if(t)return t;let n={};try{let t=window.localStorage.getItem(g+e),r=t?JSON.parse(t):null;typeof r==`object`&&r&&!Array.isArray(r)&&(n=r)}catch{}return _.set(e,n),n}function b(e,t,n){let r;try{r=JSON.parse(n)}catch{return}let i={...y(e),[t]:r},a=JSON.stringify(i);if(!(a.length>te)){_.set(e,i);try{window.localStorage.setItem(g+e,a)}catch{}}}function ne(e){let t=JSON.stringify(e).replace(/</g,`\\u003c`);return`<script data-omnigent-artifact-bridge>(function () {
  if (window.omnigent) return;
  var SOURCE = ${JSON.stringify(p)};
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
    },
    /**
     * Send a decision brief's answers to the agent without the composer:
     * answer({ brief: "id", file: "projects/x/decisions/y.json",
     *          answers: [{ decision: "layout", pick: "page", note: "..." }] }).
     * Ids and picks are checked; notes are quoted as the person's words.
     */
    answer: function (request) {
      try { post("answer", JSON.stringify(request)); } catch (e) {}
    }
  };
${d}
})();<\/script>`}function x(e,t={}){let n=ne(t),r=/^\s*<!doctype[^>]*>/i.exec(e);if(!r)return n+e;let i=r[0].length;return e.slice(0,i)+n+e.slice(i)}function S(e,t){let n={...f.base,...f[t]},r=`<style data-pa-tokens>:root:root:root{${Object.entries(n).map(([e,t])=>`--pa-${e}:${t}`).join(`;`)};color-scheme:${t}}</style><script>document.documentElement.setAttribute("data-theme",${JSON.stringify(t)})<\/script>`,i=/<\/head\s*>/i.exec(e);return i?e.slice(0,i.index)+r+e.slice(i.index):e+r}var C=50,w=400,T=/^[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}$/,E=/^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$/,D=/^(status|locked|[a-z][a-z0-9_]{0,30}_status)$/,O=/^[a-z][a-z0-9-]{0,30}$/,k=0;function A(e){if(typeof e!=`object`||!e)return null;let{dataset:t,changes:n}=e;if(typeof t!=`string`||!T.test(t)||t.includes(`..`)||!Array.isArray(n)||n.length===0||n.length>C)return null;let r=[];for(let e of n){if(typeof e!=`object`||!e)return null;let{id:t,field:n,value:i}=e;if(typeof t!=`string`||!E.test(t)||typeof n!=`string`||!D.test(n)||!(typeof i==`boolean`||typeof i==`string`&&O.test(i)))return null;r.push(`- ${t} ${n} = ${String(i)}`)}return`Canvas action on ${t}:\n${r.join(`
`)}`}var j=20,M=1e3,N=/^[a-z0-9][a-z0-9-]{0,63}$/;function P(e){if(typeof e!=`object`||!e)return null;let{brief:t,file:n,answers:r}=e;if(typeof t!=`string`||!N.test(t)||n!==void 0&&n!==``&&(typeof n!=`string`||!T.test(n)||n.includes(`..`))||!Array.isArray(r)||r.length===0||r.length>j)return null;let i=[];for(let e of r){if(typeof e!=`object`||!e)return null;let{decision:t,pick:n,note:r}=e;if(typeof t!=`string`||!N.test(t)||typeof n!=`string`||n!==``&&!N.test(n)||r!==void 0&&typeof r!=`string`)return null;let a=(r??``).replace(/\s+/g,` `).trim().slice(0,M);if(!n&&!a)return null;i.push(`- ${t} | ${n||`none`}`+(a?` | note: ${JSON.stringify(a)}`:``))}return`Decision brief answers for ${typeof n==`string`&&n?n:t}, sent from the brief by the person (notes are their own words, quoted):\n${i.join(`
`)}`}function F(e,t=null){if(typeof e!=`object`||!e)return!1;let n=e;if(n.source!==`omnigent-slim-artifact`)return!1;if(n.type===`state`)return!t||typeof n.key!=`string`||typeof n.text!=`string`?!1:(b(t,n.key.slice(0,200),n.text),!0);if(n.type===`act`){if(typeof n.text!=`string`)return!1;let e;try{e=JSON.parse(n.text)}catch{return!1}let t=A(e),r=Date.now();if(!t||r-k<w)return!1;k=r;let i={text:t};return window.dispatchEvent(new CustomEvent(h,{detail:i})),!0}if(n.type===`answer`){if(typeof n.text!=`string`)return!1;let e;try{e=JSON.parse(n.text)}catch{return!1}let t=P(e),r=Date.now();if(!t||r-k<w)return!1;k=r;let i={text:t};return window.dispatchEvent(new CustomEvent(h,{detail:i})),!0}if(n.type!==`prompt`||typeof n.text!=`string`||!n.text.trim())return!1;let r={text:n.text.slice(0,ee)};return window.dispatchEvent(new CustomEvent(m,{detail:r})),!0}var I={name:`wrench`,size:24,node:[[`path`,{d:`M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z`,key:`1ngwbx`}]]};I.node;var L=c(I),R=r(),z=`group/hangar`;function B({to:e,label:t,className:n}){let r=o(),a=l(`inline-grid size-5 shrink-0 place-items-center rounded text-muted-foreground`,`opacity-0 transition-opacity duration-150`,`group-hover/hangar:opacity-40 hover:!opacity-100 focus-visible:opacity-100`,`focus-visible:outline-2 focus-visible:outline-[var(--pa-build)]`,n),c=(0,R.jsx)(L,{"aria-hidden":`true`,className:`size-3`,strokeWidth:2});return r?(0,R.jsx)(s,{to:e,className:a,title:t,"aria-label":t,"data-testid":`hangar-wrench`,children:c}):(0,R.jsx)(`a`,{href:i(e),className:a,title:t,"aria-label":t,"data-testid":`hangar-wrench`,children:c})}var V=e=>`/v1/slim/scenarios/${encodeURIComponent(e)}/fly`;function H(e){let t=new URLSearchParams({project:e.project?.name??e.demo.project});return e.prompt&&t.set(`prompt`,e.prompt),`/?${t.toString()}`}function U(){let t=e();return n({mutationFn:({id:e,mode:t,liveTurns:n})=>Z(V(e),`POST`,{...t?{mode:t}:{},...n===void 0?{}:{live_turns:n}}),onSuccess:e=>{e.state!==`exists`&&(t.invalidateQueries({queryKey:[`slim-hangar`]}),t.invalidateQueries({queryKey:[`slim-library`]}),t.invalidateQueries({queryKey:[`projects`]}))}})}function W(){let t=e();return n({mutationFn:e=>Z(`/v1/slim/hangar/repo/send`,`POST`,{summary:e}),onSuccess:()=>t.invalidateQueries({queryKey:[`slim-hangar`]})})}async function G(){let e=await a(`/v1/slim/hangar`);if(!e.ok)throw Error(`The Hangar could not be read (${e.status})`);let t=await e.json();return{...t,drafts:t.drafts.filter(e=>e.kind===`person`),folder_drafts:t.drafts.filter(e=>e.kind!==`person`)}}function K(){return t({queryKey:[`slim-hangar`],queryFn:G,staleTime:5e3})}function q(e){return t({queryKey:[`slim-hangar-page`,e],enabled:e!==null,staleTime:3e4,queryFn:async()=>{let t=await a(e);if(!t.ok)throw Error(`Could not draw this (${t.status})`);return t.text()}})}var J=e=>`/v1/slim/hangar/views/${encodeURIComponent(e.workflow)}/${encodeURIComponent(e.name)}`,re=e=>`/v1/slim/hangar/templates/${encodeURIComponent(e)}`,Y=e=>`/v1/slim/hangar/preview/${encodeURIComponent(e)}`;function X(e){return e.toLowerCase().replace(/[^a-z0-9]+/g,`-`).replace(/^-|-$/g,``)}var ie={home:()=>`/hangar`,shelf:e=>`/hangar/${e}`,person:e=>`/hangar/people/${encodeURIComponent(e)}`,workflow:e=>`/hangar/workflows/${encodeURIComponent(e)}`,view:(e,t)=>`/hangar/views/${encodeURIComponent(e)}/${encodeURIComponent(t)}`,template:e=>`/hangar/views/template/${encodeURIComponent(e)}`,scenario:e=>`/hangar/scenarios/${encodeURIComponent(e)}`,skill:e=>`/hangar/skills/${encodeURIComponent(e)}`,starter:e=>`/hangar/starters/${encodeURIComponent(e)}`,framework:e=>`/hangar/frameworks/${encodeURIComponent(e)}`,draft:e=>`/hangar/drafts/person/${encodeURIComponent(e)}`,folderDraft:(e,t)=>`/hangar/drafts/${e}/${encodeURIComponent(t)}`,history:e=>`/hangar/people/${encodeURIComponent(e)}/history`};async function Z(e,t,n){let r=await a(e,{method:t,headers:n===void 0?void 0:{"Content-Type":`application/json`},body:n===void 0?void 0:JSON.stringify(n)}),i=await r.json().catch(()=>({}));if(!r.ok)throw Error(i.detail??`The Hangar refused (${r.status})`);return i}var Q=e=>`/v1/slim/hangar/drafts/person/${encodeURIComponent(e)}`;function ae(){let t=e(),r=()=>t.invalidateQueries({queryKey:[`slim-hangar`]});return{startDraft:n({mutationFn:({id:e,remove:t})=>Z(Q(e),`POST`,{remove:!!t}),onSuccess:r}),edit:n({mutationFn:({id:e,edit:t})=>Z(Q(e),`PATCH`,t),onSuccess:r}),create:n({mutationFn:({name:e,duplicateOf:t})=>Z(`/v1/slim/hangar/drafts/person`,`POST`,{name:e,duplicate_of:t??null}),onSuccess:r}),discard:n({mutationFn:e=>Z(Q(e),`DELETE`),onSuccess:r}),publish:n({mutationFn:({id:e,summary:t})=>Z(`${Q(e)}/publish`,`POST`,{summary:t}),onSuccess:r}),restore:n({mutationFn:({id:e,version:t})=>Z(`/v1/slim/hangar/history/person/${encodeURIComponent(e)}/${encodeURIComponent(t)}/restore`,`POST`),onSuccess:r})}}var $=(e,t)=>`/v1/slim/hangar/drafts/${e}/${encodeURIComponent(t)}`;function oe(e,n){return t({queryKey:[`slim-hangar`,`folder-draft`,e,n],queryFn:async()=>await Z($(e,n),`GET`)})}var se=(e,t)=>`/v1/slim/hangar/drafts/workflow/${encodeURIComponent(e)}/views/${encodeURIComponent(t)}`,ce=(e,t)=>`${$(e,t)}/preview`;function le(){let t=e(),r=()=>t.invalidateQueries({queryKey:[`slim-hangar`]});return{startDraft:n({mutationFn:({kind:e,id:t,remove:n})=>Z($(e,t),`POST`,{remove:!!n}),onSuccess:r}),create:n({mutationFn:({kind:e,name:t,duplicateOf:n,workflow:r})=>Z(`/v1/slim/hangar/drafts/${e}`,`POST`,{name:t,duplicate_of:n??null,workflow:r??null}),onSuccess:r}),edit:n({mutationFn:({kind:e,id:t,edit:n})=>Z($(e,t),`PATCH`,n),onSuccess:e=>{t.setQueryData([`slim-hangar`,`folder-draft`,e.kind,e.id],e),t.invalidateQueries({queryKey:[`slim-hangar`],exact:!0})}}),discard:n({mutationFn:({kind:e,id:t})=>Z($(e,t),`DELETE`),onSuccess:r}),publish:n({mutationFn:({kind:e,id:t,summary:n})=>Z(`${$(e,t)}/publish`,`POST`,{summary:n}),onSuccess:r}),restore:n({mutationFn:({kind:e,id:t,version:n})=>Z(`/v1/slim/hangar/history/${e}/${encodeURIComponent(t)}/${encodeURIComponent(n)}/restore`,`POST`),onSuccess:r})}}function ue(e,t){return[`I'm editing the ${e.kind} "${t}" in the Hangar, with the scenario-builder skill.`,`The draft is the folder ${e.kind===`scenario`?`.hangar/drafts/scenarios`:`.hangar/drafts/workflows`}/${e.id}/.`,`Change files only inside that draft folder (never the live one), keep each change small,`,`check it with \`pa draft ${e.kind} ${e.id}\`, and tell me in one line what you changed.`,`I can see the page and edit there myself. Nothing is published until I press Publish.`,`Read the draft now and say in two lines what it does. Then wait for me.`].join(` `)}function de(e,t){return[`Play it: run the unpublished scenario draft .hangar/drafts/scenarios/${e}/ as a user would meet it,`,`reading its script.md and fixtures, with the views drawn as the script says. Nothing is published.`,`${t?`Start from or focus on: ${t}`:``}`].join(` `)}var fe=e=>`/v1/slim/hangar/avatars/${encodeURIComponent(e.id)}?draft=1&v=${encodeURIComponent(e.updated??``)}`;function pe(){let t=e(),r=()=>t.invalidateQueries({queryKey:[`slim-hangar`]});return{set:n({mutationFn:async({id:e,file:t})=>{let n=await a(`/v1/slim/hangar/drafts/person/${encodeURIComponent(e)}/avatar`,{method:`PUT`,headers:{"Content-Type":`application/octet-stream`,"X-Filename":t.name},body:t}),r=await n.json().catch(()=>({}));if(!n.ok)throw Error(r.detail??`The picture was refused (${n.status})`);return r},onSuccess:r}),clear:n({mutationFn:e=>Z(`/v1/slim/hangar/drafts/person/${encodeURIComponent(e)}/avatar`,`DELETE`),onSuccess:r})}}function me(){return t({queryKey:[`slim-avatars`],staleTime:6e4,retry:!1,queryFn:async()=>await Z(`/v1/slim/hangar/avatars`,`GET`)})}function he(e,n){return t({queryKey:[`slim-hangar-version`,e,n],enabled:n!==null,queryFn:async()=>await Z(`/v1/slim/hangar/history/person/${encodeURIComponent(e)}/${n}`,`GET`)})}var ge=`Hangar`,_e=[`Who they are`,`How they answer`,`Where they can be called`,`Try them`,`Publish`];function ve(e,t){return[`I'm editing ${e.action===`new`?`a new person`:t} in the Hangar, with the build-person skill.`,`The draft is .hangar/drafts/people/${e.id}.md. I can see the page and edit fields there myself,`,"so keep each change small, make it with `pa draft person` (never edit participants/ yourself),",`and tell me in one line what you changed. Nothing is published until I press Publish.`,`Read the draft now and say in two lines what it says. Then wait for me.`].join(` `)}function ye(e,t,n){return[`Try them (step 4 of build-person): call the unpublished draft ${t} in a background session`,`with \`pa who ${e} --dir .hangar/drafts/people --opening --ask\`, ask them exactly this,`,`and show their answer as their participant turn. Nothing is published. The question: ${n}`].join(` `)}function be(e,t){let n=e.split(`
`),r=t.split(`
`),i=n.length,a=r.length,o=Array.from({length:i+1},()=>Array(a+1).fill(0));for(let e=i-1;e>=0;e--)for(let t=a-1;t>=0;t--)o[e][t]=n[e]===r[t]?o[e+1][t+1]+1:Math.max(o[e+1][t],o[e][t+1]);let s=[],c=0,l=0;for(;c<i&&l<a;)n[c]===r[l]?(s.push({op:`same`,text:n[c]}),c++,l++):o[c+1][l]>=o[c][l+1]?s.push({op:`del`,text:n[c++]}):s.push({op:`add`,text:r[l++]});for(;c<i;)s.push({op:`del`,text:n[c++]});for(;l<a;)s.push({op:`add`,text:r[l++]});return s}function xe(e){let t=/^\s*([-*#>|[]|\d+[.)]\s|\*\*|```|---)/,n=[];for(let r of e.split(`
`)){let e=n.length>0?n[n.length-1]:``;e.trim()&&r.trim()&&!t.test(r)&&!/^\s*(```|---|\|)/.test(e)?n[n.length-1]=`${e.trimEnd()} ${r.trim()}`:n.push(r)}return n.join(`
`)}export{L as A,ae as C,J as D,W as E,F,x as I,S as L,p as M,m as N,z as O,v as P,y as R,K as S,he as T,pe as _,fe as a,le as b,ce as c,X as d,de as f,xe as g,ye as h,H as i,h as j,B as k,ie as l,re as m,ge as n,se as o,Y as p,ve as r,ue as s,_e as t,be as u,me as v,q as w,oe as x,U as y,u as z};