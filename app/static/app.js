(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const log = $("log"), msg = $("msg"), form = $("form"), sendBtn = $("send");

  const store = window.localStorage;
  let userId = store.getItem("gs_uid");
  if (!userId) { userId = crypto.randomUUID(); store.setItem("gs_uid", userId); }

  const ERRORS = {
    invalid_input: "Please type a shorter message. / कृपया छोटा संदेश लिखें।",
    rate_limited: "Too many requests. Wait a minute. / बहुत ज़्यादा अनुरोध, एक मिनट रुकें।",
    llm_unavailable: "The assistant is busy. Try again soon. / सहायक व्यस्त है, थोड़ी देर बाद कोशिश करें।",
    network: "No connection. Try again. / नेटवर्क नहीं है, फिर कोशिश करें।",
  };
  const EXAMPLES = [
    "Aaj 3 trip mein 850 kamaye, 200 ka petrol",
    "How do I register on e-Shram?",
    "गर्मी में काम करते समय क्या सावधानी रखें?",
    "Driving licence kaise banwayein?",
    "My account was blocked and my payment is pending. Help me write a complaint.",
  ];

  async function loadCities() {
    try {
      const rows = await api("/api/cities");
      rows.forEach((r) => {
        const o = document.createElement("option");
        o.value = r.city; o.textContent = r.city + " (" + r.state + ")";
        $("city").appendChild(o);
      });
      const saved = store.getItem("gs_city");
      if (saved) $("city").value = saved;
    } catch { /* city list is optional */ }
  }
  $("city").addEventListener("change", () => store.setItem("gs_city", $("city").value));
  loadCities();

  const hasDevanagari = (t) => /[\u0900-\u097F]/.test(t);

  function addMessage(kind, text, sources) {
    const div = document.createElement("div");
    div.className = "msg " + kind;
    const p = document.createElement("div");
    p.textContent = text;
    div.appendChild(p);
    if (kind === "bot" && sources && sources.length) {
      const ul = document.createElement("ul");
      sources.forEach((s) => {
        const li = document.createElement("li");
        li.append("Source: ");
        if (s.url.startsWith("https://")) {
          const a = document.createElement("a");
          a.href = s.url; a.target = "_blank"; a.rel = "noopener noreferrer"; a.textContent = s.title;
          li.appendChild(a);
        } else { li.append(s.title); }
        li.append(" (last checked: " + (s.last_verified || "not recorded") + ")");
        if (s.source_type === "secondary") li.append(" - news or legal summary, please confirm with your state Labour Department / राज्य श्रम विभाग से पुष्टि करें");
        ul.appendChild(li);
      });
      div.appendChild(ul);
    }
    if (kind === "bot" && "speechSynthesis" in window) {
      const tools = document.createElement("div");
      tools.className = "tools";
      const b = document.createElement("button");
      b.type = "button"; b.textContent = "🔊 Read aloud / सुनें";
      b.addEventListener("click", () => {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = hasDevanagari(text) ? "hi-IN" : "en-IN";
        window.speechSynthesis.speak(u);
      });
      tools.appendChild(b); div.appendChild(tools);
    }
    log.appendChild(div);
    div.scrollIntoView({ behavior: "smooth", block: "end" });
  }

  async function api(path, options) {
    let res;
    try {
      res = await fetch(path, { ...options, headers: { "Content-Type": "application/json", "X-User-Id": userId } });
    } catch { throw new Error("network"); }
    if (!res.ok) {
      let code = "llm_unavailable";
      try { code = (await res.json()).detail || code; } catch { /* keep default */ }
      throw new Error(code);
    }
    return res.json();
  }

  async function send(text) {
    addMessage("me", text);
    sendBtn.disabled = true; $("status").textContent = "Thinking… / सोच रहा हूँ…";
    try {
      const data = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: text, city: $("city").value || null }) });
      addMessage("bot", data.reply, data.sources);
      if (data.summary) renderSummary(data.summary);
    } catch (e) {
      addMessage("bot", ERRORS[e.message] || ERRORS.llm_unavailable);
    } finally { sendBtn.disabled = false; $("status").textContent = ""; }
  }

  const fmt = (n) => "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
  function renderSummary(s) {
    const dl = $("sum"); dl.replaceChildren();
    const rows = [["Income / कमाई", fmt(s.income)], ["Expenses / खर्च", fmt(s.expense)], ["Net / बचत", fmt(s.net)]];
    if (s.trips) rows.push(["Trips / ट्रिप", s.trips]);
    if (s.hours) rows.push(["Hours / घंटे", s.hours]);
    if (s.income_per_hour != null) rows.push(["Income per hour / प्रति घंटा", fmt(s.income_per_hour)]);
    rows.forEach(([k, v]) => {
      const dt = document.createElement("dt"), dd = document.createElement("dd");
      dt.textContent = k; dd.textContent = v; dl.append(dt, dd);
    });
  }

  async function loadSummary() {
    try { renderSummary(await api("/api/earnings/summary?period=" + $("period").value)); }
    catch (e) { addMessage("bot", ERRORS[e.message] || ERRORS.llm_unavailable); }
  }

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const text = msg.value.trim();
    if (text) { msg.value = ""; send(text); }
  });
  $("refresh").addEventListener("click", loadSummary);

  EXAMPLES.forEach((t) => {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = t;
    b.addEventListener("click", () => send(t));
    $("chips").appendChild(b);
  });

  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Rec) { $("mic").hidden = true; $("voiceLang").hidden = true; }
  else {
    $("mic").addEventListener("click", () => {
      const rec = new Rec();
      rec.lang = $("voiceLang").value; rec.interimResults = false;
      $("status").textContent = "Listening… / सुन रहा हूँ…";
      rec.onresult = (e) => { msg.value = e.results[0][0].transcript; msg.focus(); };
      rec.onend = () => { $("status").textContent = ""; };
      rec.onerror = () => { $("status").textContent = ""; };
      rec.start();
    });
  }
})();
