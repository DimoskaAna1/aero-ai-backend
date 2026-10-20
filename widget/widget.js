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
    var voiceButton = shadow.querySelector(".voice");
    var greeted = shadow.querySelector(".greet-copy");
    var title = shadow.querySelector(".header h2");
    var chipList = shadow.querySelector(".chips");
    var welcomeText = WELCOME;
    var configReady = false;
    var welcomed = false;

    greeted.textContent = welcomeText;

    function preferredVoice() {
      var voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
      var english = [];
      var index;
      for (index = 0; index < voices.length; index += 1) {
        if ((voices[index].lang || "").toLowerCase().indexOf("en") === 0) english.push(voices[index]);
      }
      for (index = 0; index < english.length; index += 1) {
        if (/samantha|aria|jenny|google uk english female|female|zira/i.test(english[index].name || "")) {
          return english[index];
        }
      }
      return english[0] || null;
    }

    function speakWelcome() {
      if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
        status.textContent = "Voice playback is unavailable in this browser.";
        return;
      }
      window.speechSynthesis.cancel();
      var utterance = new SpeechSynthesisUtterance(welcomeText);
      utterance.lang = "en-US";
      utterance.rate = 1;
      utterance.pitch = 1.05;
      var voice = preferredVoice();
      if (voice) utterance.voice = voice;
      utterance.onstart = function () {
        voiceButton.classList.add("is-speaking");
        voiceButton.setAttribute("aria-pressed", "true");
      };
      utterance.onend = utterance.onerror = function () {
        voiceButton.classList.remove("is-speaking");
        voiceButton.setAttribute("aria-pressed", "false");
      };
      window.speechSynthesis.speak(utterance);
    }

    function speakOnce() {
      if (!configReady || welcomed) return;
      welcomed = true;
      speakWelcome();
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
    }

    function applyTenant(record) {
      var nextGreeting = (record.greeting_message || WELCOME).trim() || WELCOME;
      var nextName = (record.agent_name || "Ana | Support Specialist").trim();
      if (nextGreeting !== welcomeText) welcomed = false;
      welcomeText = nextGreeting;
      greeted.textContent = welcomeText;
      title.textContent = nextName;
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

    function render() {
      list.textContent = "";
      messages.forEach(function (message) {
        var item = document.createElement("div");
        item.className = "message " + (message.role === "user" ? "is-user" : "is-assistant");
        if (message.proactive) {
          var label = document.createElement("span");
          label.className = "eyebrow";
          label.textContent = "Proactive";
          item.appendChild(label);
        }
        var body = document.createElement("p");
        body.textContent = message.text;
        item.appendChild(body);
        if (message.imageUrl) {
          var photo = document.createElement("img");
          photo.src = message.imageUrl;
          photo.alt = message.text;
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
        }
        list.appendChild(item);
      });
      thread.scrollTop = thread.scrollHeight;
    }

    function pushMessage(role, text, proactive, imageUrl, suggestions) {
      messages.push({
        role: role,
        text: text,
        proactive: !!proactive,
        imageUrl: imageUrl || "",
        suggestions: suggestions || [],
      });
      render();
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
            pushMessage("assistant", body.assistant_message, false, body.image_url, body.suggestions);
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

    voiceButton.addEventListener("click", function () {
      speakWelcome();
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

    loadTenantConfig();
  }

  function headsetIcon(className) {
    return (
      '<svg class="' +
      className +
      '" viewBox="0 0 32 32" fill="none" aria-hidden="true">' +
      '<path d="M8 16.2a8 8 0 0 0 16 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>' +
      '<rect x="5.2" y="15.2" width="3.5" height="6.2" rx="1.5" fill="currentColor"/>' +
      '<rect x="23.3" y="15.2" width="3.5" height="6.2" rx="1.5" fill="currentColor"/>' +
      '<circle cx="16" cy="15.4" r="4" fill="currentColor"/>' +
      '<path d="M8.8 27.2c1.1-3.2 3.6-4.8 7.2-4.8s6.1 1.6 7.2 4.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>' +
      '<path d="M23.4 21.2c1.8.3 2.5 1.6 2.1 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
      '<circle cx="25.2" cy="24.8" r="1.05" fill="currentColor"/>' +
      "</svg>"
    );
  }

  function template() {
    return [
      "<style>",
      ":host{all:initial;--background-blur:16px;--glass-bg:rgba(25,25,35,.45);--glass-border:rgba(255,255,255,.12);--text-color:#fff;--shadow:0 8px 32px 0 rgba(0,0,0,.37);}",
      ".launcher,.panel,.offer,.chip,.close,.send,.field{font-family:ui-sans-serif,system-ui,sans-serif;color:var(--text-color,#fff);}",
      ".launcher{position:fixed;right:24px;bottom:24px;width:68px;height:68px;border:1px solid var(--glass-border);border-radius:999px;color:#fff;cursor:pointer;pointer-events:auto;display:grid;place-items:center;",
      "background:var(--glass-bg);backdrop-filter:blur(var(--background-blur));-webkit-backdrop-filter:blur(var(--background-blur));",
      "box-shadow:var(--shadow),0 0 22px var(--theme-color,#00e676);",
      "transition:transform .45s cubic-bezier(.16,1,.3,1),box-shadow .45s ease,border-radius .45s ease;}",
      ".launcher::before{content:'';position:absolute;inset:-7px;border-radius:inherit;border:1px solid var(--theme-color,#00e676);box-shadow:0 0 18px var(--theme-color,#00e676);animation:ring 2.6s cubic-bezier(.22,1,.36,1) infinite;}",
      ".launcher:hover{transform:translateY(-3px) scale(1.04);}",
      ".launcher.is-open{border-radius:18px;box-shadow:var(--shadow),0 0 28px var(--theme-color,#00e676);}",
      ".launcher.is-open::before{animation:none;opacity:.45;}",
      ".launcher svg{width:26px;height:26px;position:absolute;transition:opacity .28s ease,transform .45s cubic-bezier(.16,1,.3,1);}",
      ".launcher .icon-close{opacity:0;transform:rotate(-80deg) scale(.6);}",
      ".launcher.is-open .icon-chat{opacity:0;transform:rotate(80deg) scale(.6);}",
      ".launcher.is-open .icon-close{opacity:1;transform:none;}",
      ".panel.aero-ai-assistant{position:fixed;right:24px;bottom:104px;width:min(390px,calc(100vw - 32px));height:min(640px,calc(100vh - 140px));",
      "display:flex;flex-direction:column;pointer-events:auto;color:var(--text-color,#fff);overflow:hidden;",
      "background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:20px;",
      "backdrop-filter:blur(var(--background-blur));-webkit-backdrop-filter:blur(var(--background-blur));box-shadow:var(--shadow);",
      "transform-origin:100% 100%;opacity:0;transform:translateY(28px) scale(.78);visibility:hidden;",
      "transition:opacity .35s ease,transform .55s cubic-bezier(.16,1,.3,1),border-radius .55s cubic-bezier(.16,1,.3,1),visibility 0s linear .55s;}",
      ".panel.is-open{opacity:1;transform:none;visibility:visible;transition:opacity .35s ease,transform .55s cubic-bezier(.16,1,.3,1),border-radius .55s cubic-bezier(.16,1,.3,1),visibility 0s;}",
      ".header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 16px 8px;background:transparent;}",
      ".identity{display:flex;align-items:center;gap:10px;}",
      ".orb{width:36px;height:36px;border-radius:999px;display:grid;place-items:center;background:rgba(255,255,255,.08);border:1px solid var(--glass-border);box-shadow:0 0 16px var(--theme-color,#00e676);}",
      ".orb svg{width:24px;height:24px;display:block;}",
      ".launcher .icon-chat{width:32px;height:32px;}",
      ".header h2{margin:0;font-size:15px;font-weight:650;letter-spacing:-.02em;color:var(--text-color,#fff);}",
      ".presence{display:flex;align-items:center;gap:6px;margin-top:3px;color:rgba(255,255,255,.72);font-size:11px;letter-spacing:.04em;}",
      ".dot{width:7px;height:7px;border-radius:99px;background:var(--theme-color,#00e676);box-shadow:0 0 12px var(--theme-color,#00e676);animation:blink 1.8s ease-in-out infinite;}",
      ".close{width:32px;height:32px;border:1px solid var(--glass-border);border-radius:999px;background:rgba(255,255,255,.08);color:var(--text-color,#fff);cursor:pointer;}",
      ".thread{display:flex;flex:1;overflow:auto;padding:8px 14px 14px;flex-direction:column;gap:12px;background:transparent;}",
      ".greeting{display:flex;flex-direction:column;gap:10px;align-items:flex-start;}",
      ".welcome{display:flex;align-items:flex-end;gap:8px;max-width:100%;}",
      ".greet-copy{margin:0;font-size:14px;line-height:1.5;color:var(--text-color,#fff);}",
      ".voice{display:inline-flex;align-items:flex-end;gap:2px;height:28px;padding:0 8px;border-radius:999px;border:1px solid rgba(125,211,252,.4);background:rgba(14,165,233,.1);color:#7dd3fc;cursor:pointer;}",
      ".voice i{display:block;width:3px;height:6px;border-radius:99px;background:currentColor;}",
      ".voice i:nth-child(2){height:10px;}",
      ".voice i:nth-child(3){height:14px;}",
      ".voice i:nth-child(4){height:8px;}",
      ".voice.is-speaking i{animation:wave .8s ease-in-out infinite;}",
      ".voice.is-speaking i:nth-child(2){animation-delay:.1s;}",
      ".voice.is-speaking i:nth-child(3){animation-delay:.2s;}",
      ".voice.is-speaking i:nth-child(4){animation-delay:.3s;}",
      ".chips{display:flex;flex-wrap:wrap;gap:8px;}",
      ".chip.aero-chip{backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.1);color:var(--text-color,#fff);border-radius:999px;padding:8px 12px;font-size:13px;cursor:pointer;transition:all .3s ease;}",
      ".chip.aero-chip:hover{background:var(--theme-color,#00e676);color:#000;box-shadow:0 0 15px var(--theme-color,#00e676);transform:translateY(-1px);}",
      ".messages{display:flex;flex-direction:column;gap:10px;}",
      ".message{max-width:86%;padding:10px 12px;border-radius:16px;font-size:14px;line-height:1.45;}",
      ".message p{margin:0;}",
      ".message img{display:block;width:100%;max-height:180px;object-fit:cover;border-radius:12px;margin-top:8px;}",
      ".message .chips{margin-top:8px;}",
      ".message.is-assistant{align-self:flex-start;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.1);color:var(--text-color,#fff);}",
      ".message.is-user{align-self:flex-end;background:color-mix(in srgb,var(--theme-color,#00e676) 22%,transparent);border:1px solid color-mix(in srgb,var(--theme-color,#00e676) 45%,transparent);color:#fff;}",
      ".eyebrow{display:block;margin-bottom:4px;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#7dd3fc;}",
      ".typing{display:none;align-self:flex-start;gap:5px;padding:12px 14px;border-radius:16px;background:rgba(255,255,255,.06);border:1px solid rgba(148,197,255,.18);}",
      ".typing.is-on{display:flex;}",
      ".typing span{width:7px;height:7px;border-radius:99px;background:var(--theme-color,#00e676);opacity:.35;animation:dot 1.05s cubic-bezier(.22,1,.36,1) infinite;}",
      ".typing span:nth-child(2){animation-delay:.15s;}",
      ".typing span:nth-child(3){animation-delay:.3s;}",
      ".composer{display:flex;gap:8px;padding:12px;border-top:1px solid var(--glass-border);background:transparent;}",
      ".field{flex:1;resize:none;min-height:44px;max-height:96px;border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:10px 12px;",
      "font:14px/1.4 ui-sans-serif,system-ui,sans-serif;color:var(--text-color,#fff);background:rgba(255,255,255,.08);}",
      ".field::placeholder{color:rgba(255,255,255,.55);}",
      ".field:focus{outline:2px solid var(--theme-color,#00e676);border-color:transparent;}",
      ".mic{width:44px;flex:none;border:1px solid rgba(255,255,255,.1);border-radius:14px;color:#fff;background:rgba(255,255,255,.08);cursor:pointer;}",
      ".mic.is-listening{background:var(--theme-color,#00e676);color:#000;}",
      ".send{border:0;border-radius:14px;padding:0 14px;color:#000;cursor:pointer;font-weight:700;font-size:13px;background:var(--theme-color,#00e676);box-shadow:0 0 15px var(--theme-color,#00e676);}",
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
      "@media (prefers-reduced-motion: reduce){.launcher,.launcher::before,.panel,.offer,.dot,.typing span,.voice i{animation:none;transition:none;}}",
      "</style>",
      '<button class="launcher" type="button" aria-expanded="false" aria-label="Open assistant">',
      headsetIcon("icon-chat"),
      '<svg class="icon-close" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 7l10 10M17 7 7 17" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
      "</button>",
      '<section class="offer" role="dialog" aria-label="Checkout offer">',
      "<strong>10% off before you go</strong>",
      "<p>Ask Ana about the discount or an installment plan and I’ll apply it to this order.</p>",
      '<div class="offer-actions"><button class="claim" type="button">Claim offer</button><button class="dismiss" type="button">No thanks</button></div>',
      "</section>",
      '<section class="panel aero-ai-assistant" role="dialog" aria-label="Ana, Support Specialist">',
      '<header class="header"><div class="identity"><span class="orb" aria-hidden="true"></span><div>',
      "<h2>Ana | Support Specialist</h2>",
      '<p class="presence"><span class="dot" aria-hidden="true"></span>Online &amp; Active</p>',
      '</div></div><button class="close" type="button" aria-label="Close assistant">×</button></header>',
      '<div class="thread">',
      '<div class="greeting"><div class="message is-assistant welcome"><p class="greet-copy"></p><button class="voice" type="button" aria-label="Hear Ana\'s greeting" aria-pressed="false"><i></i><i></i><i></i><i></i></button></div><div class="chips">',
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
