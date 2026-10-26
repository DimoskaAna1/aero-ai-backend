/**
 * Ana | Support Specialist
 * <script src="http://127.0.0.1:8000/sdk.js" data-tenant="health-clinic" defer></script>
 */
(function () {
  if (window.__b2bAiWidgetLoaded) return;
  window.__b2bAiWidgetLoaded = true;

  var script = document.currentScript;
  var HESITATION_MS = 15000;
  var EXIT_TOP_PX = 24;
  var WELCOME = "Hey, I am Ana. How can I help?";

  function attribute(name) {
    return script && script.getAttribute(name);
  }

  function positiveNumber(value, fallback) {
    var parsed = Number(value);
    return isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  function defaultApiBase() {
    var explicit = attribute("data-api-base");
    if (explicit) return explicit.replace(/\/$/, "");
    if (script && script.src) {
      try {
        return new URL(script.src).origin;
      } catch (error) {
        return "http://127.0.0.1:8000";
      }
    }
    return "http://127.0.0.1:8000";
  }

  var config = {
    tenantId: (attribute("data-tenant") || attribute("data-tenant-id") || "").trim(),
    tenantKey: (attribute("data-key") || "").trim(),
    apiBase: defaultApiBase(),
    productName: (attribute("data-product-name") || "").trim(),
    hesitationMs: positiveNumber(attribute("data-hesitation-ms"), HESITATION_MS),
    launcherLabel: (attribute("data-launcher-label") || "Ask Ana").trim(),
    launcherSub: (attribute("data-launcher-sub") || "We reply right away").trim(),
  };

  function sessionId() {
    var key = "b2b_ai_session_" + config.tenantId;
    try {
      var existing = window.sessionStorage.getItem(key);
      if (existing) return existing;
      var id = "sess_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      window.sessionStorage.setItem(key, id);
      return id;
    } catch (error) {
      return "sess_" + Date.now().toString(36);
    }
  }

  function whenReady(callback) {
    if (document.body) callback();
    else document.addEventListener("DOMContentLoaded", callback);
  }

  whenReady(mount);

  function mount() {
    if (document.getElementById("b2b-ai-widget")) return;

    var host = document.createElement("div");
    host.id = "b2b-ai-widget";
    host.style.cssText = "position:fixed;inset:0;z-index:2147483000;pointer-events:none;";
    if (attribute("data-theme-color")) host.style.setProperty("--theme-color", attribute("data-theme-color"));
    document.body.appendChild(host);

    var shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = template();

    var launcher = shadow.querySelector(".launcher");
    var panel = shadow.querySelector(".panel");
    var offer = shadow.querySelector(".offer");
    var thread = shadow.querySelector(".thread");
    var list = shadow.querySelector(".messages");
    var typing = shadow.querySelector(".typing");
    var form = shadow.querySelector(".composer");
    var field = shadow.querySelector(".field");
    var send = shadow.querySelector(".send");
    var status = shadow.querySelector(".status");
    var product = config.productName;
    var messages = [];
    var panelOpen = false;
    var sending = false;
    var userSpoke = false;
    var commerceOffer = false;
    var exitFired = false;
    var hesitationFired = false;
    var exitMessage =
      "Before you go — I can take 10% off " +
      product +
      " today, or split the payment into installments.";
    var hesitationMessage =
      "Still looking at " +
      product +
      "? I can check installment plans or hold it while you decide.";
    var hesitationTimer = 0;
    var lastPointerY = null;
    var greeted = shadow.querySelector(".greet-copy");
    var title = shadow.querySelector(".header h2");
    var subtitle = shadow.querySelector(".header .role");
    var launcherLine1 = shadow.querySelector(".launcher-line-1");
    var launcherLine2 = shadow.querySelector(".launcher-line-2");
    var chipList = shadow.querySelector(".chips");
    var welcomeText = WELCOME;
    var configReady = false;
    var welcomed = false;

    greeted.textContent = "";
    if (launcherLine1) launcherLine1.textContent = config.launcherLabel;
    if (launcherLine2) launcherLine2.textContent = config.launcherSub;

    function speakOnce() {
      welcomed = true;
    }

    function reducedMotion() {
      return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function typeText(el, text, done) {
      var full = text || "";
      if (reducedMotion() || !full) {
        el.textContent = full;
        el.classList.remove("is-typing");
        if (done) done();
        return;
      }
      var index = 0;
      var step = full.length > 220 ? 4 : full.length > 110 ? 3 : full.length > 48 ? 2 : 1;
      var delay = full.length > 220 ? 7 : full.length > 110 ? 10 : 16;
      el.textContent = "";
      el.classList.add("is-typing");
      function tick() {
        index += step;
        el.textContent = full.slice(0, index);
        if (el !== greeted) thread.scrollTop = thread.scrollHeight;
        if (index < full.length) {
          window.setTimeout(tick, delay);
          return;
        }
        el.classList.remove("is-typing");
        if (done) done();
      }
      tick();
    }

    function popChips(root) {
      var buttons = root.querySelectorAll(".chip");
      var i;
      for (i = 0; i < buttons.length; i += 1) {
        buttons[i].classList.add("is-pop");
        buttons[i].style.animationDelay = (0.04 + i * 0.05) + "s";
      }
    }

    function formatMoney(amount) {
      if (!amount) return "";
      return String(amount).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " MKD";
    }

    function attachCard(item, card, inRail) {
      if (!card || !card.title) return;
      var shots = (card.images && card.images.length) ? card.images.slice(0, 4) : [];
      if (!shots.length && card.image_url) shots = [card.image_url];
      var box = document.createElement("article");
      box.className = "product-card is-reveal" + (inRail ? " is-tile" : " is-sheet");
      if (!inRail) item.classList.add("has-sheet");
      if (shots.length) {
        var gallery = document.createElement("div");
        gallery.className = "product-gallery" + (shots.length === 1 ? " is-one" : "");
        shots.forEach(function (src, index) {
          var photo = document.createElement("img");
          photo.src = src;
          photo.alt = card.title;
          if (index === 0) photo.className = "is-lead";
          gallery.appendChild(photo);
        });
        box.appendChild(gallery);
      }
      var copy = document.createElement("div");
      copy.className = "product-card-copy";
      var title = document.createElement("strong");
      title.textContent = card.title;
      var price = document.createElement("span");
      price.className = "product-card-price";
      if (card.old_price_mkd && card.old_price_mkd > card.price_mkd) {
        var was = document.createElement("s");
        was.textContent = formatMoney(card.old_price_mkd);
        price.appendChild(was);
        price.appendChild(document.createTextNode(" " + formatMoney(card.price_mkd)));
      } else {
        price.textContent = formatMoney(card.price_mkd);
      }
      copy.appendChild(title);
      if (price.textContent || price.childNodes.length) copy.appendChild(price);
      if (!inRail && card.detail) {
        var detail = document.createElement("p");
        detail.className = "product-card-detail";
        detail.textContent = card.detail;
        copy.appendChild(detail);
      }
      if (inRail) {
        var open = document.createElement("button");
        open.className = "product-card-buy";
        open.type = "button";
        open.textContent = "Otvori";
        open.addEventListener("click", function (event) {
          event.stopPropagation();
          sendMessage(card.title);
        });
        copy.appendChild(open);
        box.addEventListener("click", function () {
          sendMessage(card.title);
        });
      } else {
        var buy = document.createElement("button");
        buy.className = "product-card-buy";
        buy.type = "button";
        buy.textContent = "U kosnicka";
        buy.addEventListener("click", function () {
          sendMessage("u kosnicka");
        });
        copy.appendChild(buy);
      }
      box.appendChild(copy);
      item.appendChild(box);
    }

    function attachRail(item, cards) {
      var rail = document.createElement("div");
      rail.className = "catalog-rail";
      item.classList.add("has-rail");
      (cards || []).forEach(function (card) {
        attachCard(rail, card, true);
      });
      item.appendChild(rail);
    }

    function attachExtras(item, message) {
      if (message.cards && message.cards.length) {
        attachRail(item, message.cards);
      } else if (message.card) {
        attachCard(item, message.card);
      } else if (message.imageUrl) {
        var photo = document.createElement("img");
        photo.src = message.imageUrl;
        photo.alt = message.text;
        photo.className = "is-reveal";
        item.appendChild(photo);
      }
      if (message.suggestions && message.suggestions.length) {
        var choices = document.createElement("div");
        choices.className = "chips";
        message.suggestions.forEach(function (choice) {
          var button = document.createElement("button");
          button.className = "chip aero-chip";
          button.type = "button";
          button.textContent = choice.label;
          button.addEventListener("click", function () {
            sendMessage(choice.message || choice.label);
          });
          choices.appendChild(button);
        });
        item.appendChild(choices);
        popChips(choices);
      }
    }

    function typeGreeting() {
      if (greeted.dataset.typed === welcomeText) return;
      greeted.dataset.typed = welcomeText;
      typeText(greeted, welcomeText, function () {
        popChips(chipList);
      });
    }

    function renderChips(chips) {
      chipList.textContent = "";
      (chips || []).forEach(function (chip) {
        var label = typeof chip === "string" ? chip : chip && (chip.label || chip.text);
        var message = typeof chip === "string" ? chip : chip && (chip.message || chip.prompt || label);
        if (!label || !message) return;
        var button = document.createElement("button");
        button.className = "chip aero-chip";
        button.type = "button";
        button.textContent = label;
        button.addEventListener("click", function () {
          sendMessage(message);
        });
        chipList.appendChild(button);
      });
      if (greeted.dataset.typed === welcomeText) popChips(chipList);
    }

    function applyTenant(record) {
      var nextGreeting = (record.greeting_message || WELCOME).trim() || WELCOME;
      var nextName = (record.agent_name || "Ana | Support Specialist").trim();
      if (nextGreeting !== welcomeText) welcomed = false;
      welcomeText = nextGreeting;
      greeted.dataset.typed = "";
      if (panelOpen) typeGreeting();
      else greeted.textContent = "";
      title.textContent = nextName;
      if (subtitle) subtitle.textContent = "AI support assistant";
      panel.setAttribute("aria-label", nextName);
      if (record.quick_chips && record.quick_chips.length) renderChips(record.quick_chips);
      var industry = String(record.industry || "").toLowerCase();
      commerceOffer = industry === "ecommerce" || industry === "e-commerce";
      configReady = true;
      if (panelOpen) speakOnce();
      if (offersAllowed()) armHesitation();
      else window.clearTimeout(hesitationTimer);
    }

    function loadTenantConfig() {
      fetch(config.apiBase + "/api/v1/tenant-config/" + encodeURIComponent(config.tenantId))
        .then(function (response) {
          if (!response.ok) throw new Error("config");
          return response.json();
        })
        .then(applyTenant)
        .catch(function () {
          configReady = true;
          if (panelOpen) speakOnce();
        });
    }

    function appendMessage(message) {
      var item = document.createElement("div");
      item.className = "message is-enter " + (message.role === "user" ? "is-user" : "is-assistant");
      if (message.proactive) {
        var label = document.createElement("span");
        label.className = "eyebrow";
        label.textContent = "Proactive";
        item.appendChild(label);
      }
      var body = document.createElement("p");
      item.appendChild(body);
      list.appendChild(item);
      thread.scrollTop = thread.scrollHeight;
      if (message.role === "assistant") {
        typeText(body, message.text, function () {
          attachExtras(item, message);
          thread.scrollTop = thread.scrollHeight;
        });
        return;
      }
      body.textContent = message.text;
      attachExtras(item, message);
      thread.scrollTop = thread.scrollHeight;
    }

    function pushMessage(role, text, proactive, imageUrl, suggestions, card, cards) {
      var message = {
        role: role,
        text: text,
        proactive: !!proactive,
        imageUrl: imageUrl || "",
        suggestions: suggestions || [],
        card: card || null,
        cards: cards || [],
      };
      messages.push(message);
      appendMessage(message);
    }

    function showTyping(on) {
      typing.classList.toggle("is-on", on);
      status.textContent = on ? "Ana is replying" : "";
      thread.scrollTop = thread.scrollHeight;
    }

    function setOpen(next) {
      panelOpen = next;
      panel.classList.toggle("is-open", next);
      launcher.classList.toggle("is-open", next);
      launcher.setAttribute("aria-expanded", next ? "true" : "false");
      launcher.setAttribute("aria-label", next ? "Close assistant" : "Open assistant");
      if (next) {
        offer.classList.remove("is-open");
        typeGreeting();
        speakOnce();
        window.setTimeout(function () {
          field.focus();
        }, 280);
      }
    }

    function offersAllowed() {
      return commerceOffer && !!product && !userSpoke;
    }

    function showExitOffer() {
      if (!offersAllowed() || exitFired) return;
      exitFired = true;
      if (panelOpen) {
        pushMessage("assistant", exitMessage, true);
        return;
      }
      offer.classList.add("is-open");
    }

    function showHesitation() {
      if (!offersAllowed() || hesitationFired) return;
      hesitationFired = true;
      window.clearTimeout(hesitationTimer);
      pushMessage("assistant", hesitationMessage, true);
      setOpen(true);
    }

    function armHesitation() {
      if (!offersAllowed() || hesitationFired) return;
      window.clearTimeout(hesitationTimer);
      hesitationTimer = window.setTimeout(showHesitation, config.hesitationMs);
    }

    function errorText(body) {
      if (!body || body.detail == null) return "The assistant is unavailable right now.";
      if (typeof body.detail === "string") return body.detail;
      return "That message could not be sent.";
    }

    function publishCart(item) {
      if (!item || !item.title) return;
      try {
        window.dispatchEvent(new CustomEvent("b2b-ai:cart", { detail: item }));
      } catch (error) {}
      var cartUrl = attribute("data-cart-url");
      if (cartUrl) window.location.assign(cartUrl);
    }

    function sendMessage(text) {
      var trimmed = text.trim();
      if (!trimmed || sending) return;
      if (!config.tenantId) {
        status.textContent = "This widget is missing data-tenant.";
        return;
      }
      userSpoke = true;
      window.clearTimeout(hesitationTimer);
      pushMessage("user", trimmed);
      field.value = "";
      sending = true;
      send.disabled = true;
      showTyping(true);

      var controller = new AbortController();
      var timeout = window.setTimeout(function () {
        controller.abort();
      }, 35000);

      fetch(config.apiBase + "/api/v1/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Id": config.tenantId,
          "X-Tenant-Key": config.tenantKey,
        },
        body: JSON.stringify({
          tenant_id: config.tenantId,
          user_message: trimmed,
          session_id: sessionId(),
        }),
        signal: controller.signal,
      })
        .then(function (response) {
          return response.text().then(function (raw) {
            var body = {};
            if (raw) {
              try {
                body = JSON.parse(raw);
              } catch (error) {
                body = {};
              }
            }
            if (!response.ok) throw new Error(errorText(body));
            if (!body.assistant_message) throw new Error("The assistant returned an empty reply.");
            publishCart(body.cart);
            pushMessage("assistant", body.assistant_message, false, body.image_url, body.suggestions, body.card, body.cards);
          });
        })
        .catch(function (error) {
          var message =
            error && error.name === "AbortError"
              ? "The assistant took too long to reply."
              : (error && error.message) || "The assistant is unavailable right now.";
          pushMessage("assistant", message, false);
        })
        .then(function () {
          window.clearTimeout(timeout);
          sending = false;
          send.disabled = false;
          showTyping(false);
          field.focus();
        });
    }

    launcher.addEventListener("click", function () {
      setOpen(!panelOpen);
    });

    shadow.querySelector(".close").addEventListener("click", function () {
      setOpen(false);
    });

    var micButton = shadow.querySelector(".mic");
    var SpeechApi = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechApi) {
      micButton.hidden = true;
    } else {
      var recognition = new SpeechApi();
      recognition.lang = "mk-MK";
      recognition.interimResults = false;
      recognition.continuous = false;
      recognition.onresult = function (event) {
        var said = event.results[0][0].transcript || "";
        micButton.classList.remove("is-listening");
        micButton.setAttribute("aria-pressed", "false");
        if (said.trim()) sendMessage(said.trim());
      };
      recognition.onerror = function () {
        micButton.classList.remove("is-listening");
        micButton.setAttribute("aria-pressed", "false");
        status.textContent = "Voice input is unavailable in this browser.";
      };
      recognition.onend = function () {
        micButton.classList.remove("is-listening");
        micButton.setAttribute("aria-pressed", "false");
      };
      micButton.addEventListener("click", function () {
        if (micButton.classList.contains("is-listening")) {
          recognition.stop();
          return;
        }
        micButton.classList.add("is-listening");
        micButton.setAttribute("aria-pressed", "true");
        recognition.start();
      });
    }

    shadow.querySelectorAll(".chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        sendMessage(chip.getAttribute("data-message") || "");
      });
    });

    shadow.querySelector(".claim").addEventListener("click", function () {
      offer.classList.remove("is-open");
      pushMessage("assistant", exitMessage, true);
      setOpen(true);
    });

    shadow.querySelector(".dismiss").addEventListener("click", function () {
      offer.classList.remove("is-open");
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      sendMessage(field.value);
    });

    field.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage(field.value);
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && panelOpen) setOpen(false);
    });

    // Clicks and typing count as interactions. Scrolling the product page does not.
    ["pointerdown", "keydown"].forEach(function (type) {
      document.addEventListener(type, armHesitation, true);
    });

    document.addEventListener("mousemove", function (event) {
      var movingUp = lastPointerY != null && event.clientY < lastPointerY;
      if (movingUp && event.clientY <= EXIT_TOP_PX) showExitOffer();
      lastPointerY = event.clientY;
    });

    document.addEventListener("mouseout", function (event) {
      if (event.relatedTarget || event.toElement) return;
      if (event.clientY <= 0) showExitOffer();
    });

    function askFromPage(text) {
      setOpen(true);
      sendMessage(String(text || ""));
    }

    window.B2BAI = {
      send: askFromPage,
    };
    window.addEventListener("b2b-ai:ask", function (event) {
      askFromPage(event.detail);
    });

    loadTenantConfig();
  }

  function headsetIcon(className) {
    return (
      '<svg class="' +
      className +
      '" viewBox="0 0 32 32" fill="none" aria-hidden="true">' +
      '<circle class="face" cx="16" cy="14.1" r="5.1" fill="currentColor"/>' +
      '<path class="face" d="M8 28c1.1-4.6 3.9-7 8-7s6.9 2.4 8 7" fill="currentColor"/>' +
      '<path class="rig" d="M6.8 15.4a9.2 9.2 0 0 1 18.4 0" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>' +
      '<rect class="rig" x="4.2" y="13.6" width="5" height="8.4" rx="2.5" fill="currentColor"/>' +
      '<rect class="rig" x="22.8" y="13.6" width="5" height="8.4" rx="2.5" fill="currentColor"/>' +
      '<path class="rig" d="M26.8 21.4c2.4.6 3.4 2.2 2.8 4.1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>' +
      '<circle class="rig" cx="29.2" cy="26.4" r="1.55" fill="currentColor"/>' +
      "</svg>"
    );
  }

  function template() {
    return [
      "<style>",
      ":host{all:initial;--background-blur:0;--glass-bg:#fff;--glass-border:#dcdcd6;--text-color:#111114;--shadow:0 10px 30px rgba(150,150,150,.2);--ink:#111114;--rule:#dcdcd6;}",
      ".launcher,.panel,.offer,.chip,.close,.send,.field,.mic,.claim,.dismiss{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:var(--text-color,#111114);}",
      ".launcher{position:fixed;right:20px;bottom:20px;border:0;color:#fff;cursor:pointer;pointer-events:auto;",
      "background:#111114;box-shadow:var(--shadow);",
      "transition:transform .3s cubic-bezier(0,1.2,1,1),border-radius .3s ease,width .2s ease;}",
      ".launcher.is-pill{display:flex;align-items:center;gap:10px;width:auto;height:auto;min-height:56px;padding:8px 16px 8px 8px;border-radius:999px;}",
      ".launcher.is-pill .launcher-icon{width:40px;height:40px;border-radius:999px;display:grid;place-items:center;background:#1c1c22;flex:none;position:relative;}",
      ".launcher-copy{display:flex;flex-direction:column;align-items:flex-start;line-height:1.15;text-align:left;}",
      ".launcher-line-1{font-size:14px;font-weight:700;color:#fff;}",
      ".launcher-line-2{font-size:12px;color:rgba(255,255,255,.72);}",
      ".launcher:hover{transform:translateY(-2px);}",
      ".launcher.is-open{width:56px;height:56px;min-height:56px;padding:0;border-radius:999px;justify-content:center;}",
      ".launcher.is-open .launcher-copy,.launcher.is-open .launcher-icon{display:none;}",
      ".launcher svg{width:22px;height:22px;transition:opacity .28s ease,transform .45s cubic-bezier(.16,1,.3,1);}",
      ".launcher .icon-close{position:absolute;opacity:0;transform:rotate(-80deg) scale(.6);color:#fff;}",
      ".launcher.is-open .icon-chat{opacity:0;}",
      ".launcher.is-open .icon-close{opacity:1;transform:none;position:static;}",
      ".panel.aero-ai-assistant{position:fixed;right:20px;bottom:88px;width:min(400px,calc(100vw - 24px));height:min(640px,calc(100vh - 120px));min-height:min(480px,calc(100vh - 112px));",
      "display:flex;flex-direction:column;pointer-events:auto;color:var(--ink,#111114);overflow:hidden;",
      "background:#fff;border:1px solid rgba(150,150,150,.2);border-radius:12px;",
      "box-shadow:0 10px 30px rgba(150,150,150,.2),0 0 0 1px rgba(150,150,150,.2);",
      "transform-origin:100% 100%;opacity:0;transform:translateY(16px) scale(.96);visibility:hidden;",
      "transition:opacity .2s ease,transform .3s cubic-bezier(0,1.2,1,1),visibility 0s linear .3s;}",
      ".panel.is-open{opacity:1;transform:none;visibility:visible;transition:opacity .35s ease,transform .55s cubic-bezier(.16,1,.3,1),border-radius .55s cubic-bezier(.16,1,.3,1),visibility 0s;}",
      ".header{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 14px 12px;background:#fff;border-bottom:1px solid var(--rule,#dcdcd6);}",
      ".identity{display:flex;align-items:center;gap:10px;}",
      ".orb{position:relative;width:40px;height:40px;border-radius:999px;display:grid;place-items:center;background:#f3f3f0;border:1px solid var(--rule,#dcdcd6);overflow:hidden;}",
      ".orb svg{width:26px;height:26px;display:block;color:#111114;}",
      ".orb .rig{color:#111114;}",
      ".launcher .icon-chat{width:26px;height:26px;color:#fff;}",
      ".launcher .icon-chat .rig{color:#fff;}",
      ".header h2{margin:0;font-size:15px;font-weight:700;letter-spacing:-.02em;color:var(--ink,#111114);}",
      ".role{margin:2px 0 0;font-size:12px;color:#6b6b70;}",
      ".presence{display:flex;align-items:center;gap:6px;margin-top:3px;color:#6b6b70;font-size:11px;}",
      ".dot{width:7px;height:7px;border-radius:99px;background:var(--theme-color,#00e676);box-shadow:0 0 12px var(--theme-color,#00e676);animation:blink 1.8s ease-in-out infinite;}",
      ".close{width:32px;height:32px;border:0;border-radius:999px;background:transparent;color:#111114;cursor:pointer;font-size:20px;}",
      ".thread{position:relative;z-index:1;display:flex;flex:1;overflow:auto;padding:8px 14px 14px;flex-direction:column;gap:12px;background:#fff;}",
      ".greeting{display:flex;flex-direction:column;gap:10px;align-items:flex-start;}",
      ".welcome{display:flex;align-items:flex-end;gap:8px;max-width:100%;animation:unveil .6s cubic-bezier(.16,1,.3,1) both;}",
      ".greet-copy{margin:0;font-size:14px;line-height:1.5;color:var(--ink,#111114);}",
      ".greet-copy.is-typing::after{content:'';display:inline-block;width:7px;height:.95em;margin-left:3px;vertical-align:text-bottom;background:#111114;animation:caret .7s steps(1) infinite;}",
      ".voice{display:none;}",
      ".voice i{display:block;width:3px;height:6px;border-radius:99px;background:currentColor;}",
      ".voice i:nth-child(2){height:10px;}",
      ".voice i:nth-child(3){height:14px;}",
      ".voice i:nth-child(4){height:8px;}",
      ".voice.is-speaking i{animation:wave .8s ease-in-out infinite;}",
      ".voice.is-speaking i:nth-child(2){animation-delay:.1s;}",
      ".voice.is-speaking i:nth-child(3){animation-delay:.2s;}",
      ".voice.is-speaking i:nth-child(4){animation-delay:.3s;}",
      ".chips{display:flex;flex-wrap:wrap;gap:8px;}",
      ".greeting .chips .chip{opacity:0;}",
      ".chip.aero-chip{background:#fff;border:1px solid var(--rule,#dcdcd6);color:var(--ink,#111114);border-radius:999px;padding:8px 12px;font-size:13px;cursor:pointer;transition:all .2s ease;}",
      ".chip.aero-chip:hover{background:#111114;color:#fff;}",
      ".chip.is-pop{animation:unveil .42s cubic-bezier(.16,1,.3,1) both;}",
      ".messages{display:flex;flex-direction:column;gap:10px;}",
      ".message{max-width:86%;padding:10px 12px;border-radius:16px;font-size:14px;line-height:1.45;}",
      ".message.has-rail,.message.has-sheet{max-width:100%;}",
      ".message p{margin:0;}",
      ".message p.is-typing::after{content:'';display:inline-block;width:7px;height:.95em;margin-left:3px;vertical-align:text-bottom;background:#111114;animation:caret .7s steps(1) infinite;}",
      ".message img{display:block;width:100%;max-height:180px;object-fit:cover;border-radius:12px;margin-top:8px;}",
      ".message img.is-reveal{animation:unveil .5s cubic-bezier(.16,1,.3,1) both;}",
      ".message .chips{margin-top:8px;}",
      ".message.is-enter{animation:unveil .52s cubic-bezier(.16,1,.3,1) both;}",
      ".message.is-assistant{align-self:flex-start;background:#f6f6f2;border:1px solid var(--rule,#dcdcd6);color:var(--ink,#111114);}",
      ".message.is-user{align-self:flex-end;background:#111114;border:1px solid #111114;color:#fff;}",
      ".product-card{display:grid;grid-template-columns:88px 1fr;gap:10px;margin-top:10px;border:1px solid var(--rule,#dcdcd6);border-radius:8px;overflow:hidden;background:#fff;}",
      ".product-card-copy{display:flex;flex-direction:column;justify-content:center;gap:4px;padding:8px 10px 8px 0;}",
      ".product-card-copy strong{font-size:13px;}",
      ".product-card-price{font-size:13px;font-weight:700;}",
      ".product-card-price s{color:#8a8a90;font-weight:500;margin-right:4px;}",
      ".product-card-detail{margin:2px 0 0;font-size:12px;line-height:1.45;font-weight:400;color:#3f3f46;white-space:pre-line;}",
      ".product-card-buy{align-self:flex-start;border:0;border-radius:999px;padding:6px 10px;background:#111114;color:#fff;font-size:12px;font-weight:700;cursor:pointer;}",
      ".product-gallery{display:grid;grid-template-columns:1.45fr 1fr;gap:4px;background:#f3f3f3;}",
      ".product-gallery img{display:block;width:100%;height:118px;max-height:none;margin:0;border-radius:0;object-fit:cover;}",
      ".product-gallery img.is-lead{grid-row:1 / span 2;height:240px;}",
      ".product-gallery.is-one{grid-template-columns:1fr;}",
      ".product-gallery.is-one img{height:250px;}",
      ".product-card.is-sheet{display:flex;flex-direction:column;grid-template-columns:none;}",
      ".product-card.is-sheet .product-card-copy{padding:10px 12px 12px;}",
      ".catalog-rail{display:flex;gap:10px;overflow-x:auto;margin-top:10px;padding:2px 2px 10px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;}",
      ".catalog-rail::-webkit-scrollbar{height:6px;}",
      ".catalog-rail::-webkit-scrollbar-thumb{background:#dcdcd6;border-radius:99px;}",
      ".product-card.is-tile{flex:0 0 176px;width:176px;display:flex;flex-direction:column;grid-template-columns:none;margin-top:0;scroll-snap-align:start;cursor:pointer;}",
      ".product-card.is-tile .product-gallery{display:block;}",
      ".product-card.is-tile .product-gallery img{width:100%;height:220px;max-height:none;}",
      ".product-card.is-tile .product-card-copy{padding:8px;}",
      ".eyebrow{display:block;margin-bottom:4px;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#7dd3fc;}",
      ".typing{display:none;align-self:flex-start;gap:5px;padding:12px 14px;border-radius:16px;background:rgba(255,255,255,.06);border:1px solid rgba(148,197,255,.18);}",
      ".typing.is-on{display:flex;}",
      ".typing span{width:7px;height:7px;border-radius:99px;background:var(--theme-color,#00e676);opacity:.35;animation:dot 1.05s cubic-bezier(.22,1,.36,1) infinite;}",
      ".typing span:nth-child(2){animation-delay:.15s;}",
      ".typing span:nth-child(3){animation-delay:.3s;}",
      ".composer{position:relative;z-index:1;display:flex;gap:8px;padding:12px;border-top:1px solid var(--rule,#dcdcd6);background:#fff;}",
      ".field{flex:1;resize:none;min-height:44px;max-height:96px;border:1px solid var(--rule,#dcdcd6);border-radius:10px;padding:10px 12px;",
      "font:14px/1.4 Inter,ui-sans-serif,system-ui,sans-serif;color:var(--ink,#111114);background:#fff;}",
      ".field::placeholder{color:#8a8a90;}",
      ".field:focus{outline:2px solid #111114;border-color:transparent;}",
      ".mic{width:44px;flex:none;border:1px solid var(--rule,#dcdcd6);border-radius:10px;color:#111114;background:#fff;cursor:pointer;}",
      ".mic.is-listening{background:#111114;color:#fff;}",
      ".send{border:0;border-radius:10px;padding:0 14px;color:#fff;cursor:pointer;font-weight:700;font-size:13px;background:#111114;}",
      ".send:disabled{opacity:.55;cursor:progress;}",
      ".status{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);}",
      ".offer{position:fixed;right:24px;bottom:104px;width:min(320px,calc(100vw - 32px));padding:16px;pointer-events:auto;color:var(--text-color,#fff);",
      "background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:20px;",
      "backdrop-filter:blur(var(--background-blur));-webkit-backdrop-filter:blur(var(--background-blur));",
      "box-shadow:var(--shadow);",
      "opacity:0;transform:translateY(16px) scale(.94);visibility:hidden;",
      "transition:opacity .35s ease,transform .5s cubic-bezier(.16,1,.3,1),visibility 0s linear .5s;}",
      ".offer.is-open{opacity:1;transform:none;visibility:visible;transition:opacity .35s ease,transform .5s cubic-bezier(.16,1,.3,1),visibility 0s;}",
      ".offer strong{display:block;font-size:18px;font-weight:640;letter-spacing:-.03em;}",
      ".offer p{margin:6px 0 14px;font-size:13px;line-height:1.45;color:#b7c8e4;}",
      ".offer-actions{display:flex;gap:8px;}",
      ".claim,.dismiss{border-radius:999px;padding:8px 12px;font:600 12px/1 ui-sans-serif,system-ui,sans-serif;cursor:pointer;}",
      ".claim{border:0;color:#000;background:var(--theme-color,#00e676);box-shadow:0 0 15px var(--theme-color,#00e676);}",
      ".dismiss{border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.08);color:var(--text-color,#fff);}",
      "@keyframes ring{0%{transform:scale(.92);opacity:.8;}70%{transform:scale(1.18);opacity:0;}100%{opacity:0;}}",
      "@keyframes blink{0%,100%{opacity:1;}50%{opacity:.35;}}",
      "@keyframes dot{0%,80%,100%{transform:translateY(0);opacity:.35;}40%{transform:translateY(-4px);opacity:1;}}",
      "@keyframes wave{0%,100%{transform:scaleY(.45);}50%{transform:scaleY(1);}}",
      "@keyframes unveil{from{opacity:0;transform:translateX(-28px);filter:blur(5px);}to{opacity:1;transform:none;filter:none;}}",
      "@keyframes scan{0%{transform:translateY(0);opacity:0;}12%{opacity:.7;}100%{transform:translateY(640px);opacity:0;}}",
      "@keyframes caret{0%,49%{opacity:1;}50%,100%{opacity:0;}}",
      "@media (prefers-reduced-motion: reduce){.launcher,.launcher::before,.orb::after,.panel,.panel::after,.offer,.dot,.typing span,.voice i,.message.is-enter,.chip.is-pop,.welcome,.message img.is-reveal{animation:none;transition:none;filter:none;}}",
      "</style>",
      '<button class="launcher is-pill" type="button" aria-expanded="false" aria-label="Open assistant">',
      '<span class="launcher-icon">',
      headsetIcon("icon-chat"),
      "</span>",
      '<span class="launcher-copy"><span class="launcher-line-1">Ask Ana</span><span class="launcher-line-2">We reply right away</span></span>',
      '<svg class="icon-close" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 7l10 10M17 7 7 17" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
      "</button>",
      '<section class="offer" role="dialog" aria-label="Checkout offer">',
      "<strong>10% off before you go</strong>",
      "<p>Ask Ana about the discount or an installment plan and I’ll apply it to this order.</p>",
      '<div class="offer-actions"><button class="claim" type="button">Claim offer</button><button class="dismiss" type="button">No thanks</button></div>',
      "</section>",
      '<section class="panel aero-ai-assistant" role="dialog" aria-label="Ana, Support Specialist">',
      '<header class="header"><div class="identity"><span class="orb" aria-hidden="true">',
      headsetIcon("orb-face"),
      "</span><div>",
      "<h2>Ana</h2>",
      '<p class="role">AI support assistant</p>',
      '<p class="presence"><span class="dot" aria-hidden="true"></span>Online</p>',
      '</div></div><button class="close" type="button" aria-label="Close assistant">×</button></header>',
      '<div class="thread">',
      '<div class="greeting"><div class="message is-assistant welcome"><p class="greet-copy"></p></div><div class="chips">',
      '<button class="chip aero-chip" type="button" data-message="Is shipping free for this order?">Free Shipping?</button>',
      '<button class="chip aero-chip" type="button" data-message="What installment plans can I use?">Installment Plans</button>',
      '<button class="chip aero-chip" type="button" data-message="Can I get 10% off today?">10% Discount</button>',
      "</div></div>",
      '<div class="messages" role="log" aria-live="polite"></div>',
      '<div class="typing" aria-hidden="true"><span></span><span></span><span></span></div>',
      "</div>",
      '<form class="composer"><textarea class="field" rows="1" maxlength="4000" placeholder="Message Ana" aria-label="Message"></textarea><button class="mic" type="button" aria-label="Speak" aria-pressed="false"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3" stroke="currentColor" stroke-width="1.7"/><path d="M6 11a6 6 0 0 0 12 0M12 17v3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg></button><button class="send" type="submit">Send</button></form>',
      '<span class="status" role="status"></span>',
      "</section>",
    ].join("");
  }
})();
