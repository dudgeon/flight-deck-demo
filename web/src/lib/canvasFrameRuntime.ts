// omnigent-slim: the in-frame half of the canvas tools (canvas_read, canvas_click,
// canvas_type, canvas_set_content, canvas_press_key, canvas_eval).
//
// This source is injected, with the rest of the artifact bridge, into every HTML
// artifact the viewer renders. It answers requests the host page posts into the
// frame (see canvasRelay.ts) and acts on the frame's own DOM, so whatever Claude
// does happens in the canvas the user is looking at. It accepts requests only
// from the parent window and runs inside the same sandbox and CSP as the
// artifact: no network, no access to the Omnigent page.
//
// Kept as a plain ES5 string (no "</script>" inside) because it is inlined into
// the artifact's HTML.

/** Tag on host -> frame canvas requests. */
export const CANVAS_REQUEST_SOURCE = "omnigent-slim-canvas";

export const CANVAS_FRAME_RUNTIME = String.raw`
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
`;
