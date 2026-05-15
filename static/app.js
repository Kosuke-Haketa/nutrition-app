const DEFICIENCY_SUGGESTIONS = {
  calories: {
    foods:  ["ご飯", "パン", "パスタ", "バナナ", "ナッツ類"],
    dishes: ["おにぎり", "カレーライス", "パスタ", "シリアル"],
  },
  protein_g: {
    foods:  ["鶏むね肉", "卵", "豆腐", "納豆", "ツナ缶", "ギリシャヨーグルト"],
    dishes: ["親子丼", "ゆで卵", "冷奴", "納豆ご飯", "豚しゃぶサラダ"],
  },
  fat_g: {
    foods:  ["アボカド", "オリーブオイル", "ナッツ類", "チーズ", "鮭"],
    dishes: ["アボカドサラダ", "ナッツ和え", "鮭のソテー"],
  },
  carbs_g: {
    foods:  ["白米", "さつまいも", "パン", "うどん", "バナナ"],
    dishes: ["おにぎり", "さつまいものスープ", "フルーツ盛り合わせ"],
  },
  fiber_g: {
    foods:  ["ごぼう", "オートミール", "キャベツ", "ブロッコリー", "納豆", "アボカド"],
    dishes: ["きんぴらごぼう", "野菜スープ", "ブロッコリーのごま和え"],
  },
  salt_g: { foods: [], dishes: [] },
  vitamin_a_ug: {
    foods:  ["人参", "レバー", "ほうれん草", "かぼちゃ", "小松菜"],
    dishes: ["人参のきんぴら", "レバニラ炒め", "かぼちゃの煮物"],
  },
  vitamin_d_ug: {
    foods:  ["鮭", "さんま", "いわし", "まいたけ", "しらす干し"],
    dishes: ["焼き鮭", "さんまの塩焼き", "きのこのソテー"],
  },
  vitamin_e_mg: {
    foods:  ["アーモンド", "アボカド", "うなぎ", "かぼちゃ", "ほうれん草"],
    dishes: ["アーモンドサラダ", "うな丼", "かぼちゃのソテー"],
  },
  vitamin_k_ug: {
    foods:  ["ほうれん草", "小松菜", "ブロッコリー", "納豆", "春菊"],
    dishes: ["ほうれん草のおひたし", "小松菜炒め", "納豆ご飯"],
  },
  vitamin_b1_mg: {
    foods:  ["豚肉", "玄米", "枝豆", "そら豆", "ナッツ類"],
    dishes: ["豚肉の生姜焼き", "玄米ご飯", "枝豆"],
  },
  vitamin_b2_mg: {
    foods:  ["レバー", "うなぎ", "卵", "納豆", "アーモンド"],
    dishes: ["レバーの醤油炒め", "玉子焼き", "納豆ご飯"],
  },
  vitamin_b6_mg: {
    foods:  ["鶏むね肉", "かつお", "バナナ", "ピスタチオ", "さつまいも"],
    dishes: ["チキンソテー", "かつおのたたき", "バナナ"],
  },
  vitamin_b12_ug: {
    foods:  ["しじみ", "あさり", "さんま", "レバー", "牡蠣"],
    dishes: ["しじみの味噌汁", "あさりの酒蒸し", "牡蠣の鍋"],
  },
  vitamin_c_mg: {
    foods:  ["ブロッコリー", "パプリカ", "キウイ", "イチゴ", "じゃがいも"],
    dishes: ["ブロッコリーのごま和え", "パプリカサラダ", "フルーツヨーグルト"],
  },
  folate_ug: {
    foods:  ["枝豆", "ほうれん草", "菜の花", "ブロッコリー", "アスパラガス"],
    dishes: ["枝豆の塩茹で", "ほうれん草のソテー", "アスパラの炒め物"],
  },
};

const DAILY_TARGETS = {
  calories:      { label: "カロリー",   unit: "kcal", target: 2000 },
  protein_g:     { label: "タンパク質", unit: "g",    target: 50 },
  fat_g:         { label: "脂質",       unit: "g",    target: 60 },
  carbs_g:       { label: "炭水化物",   unit: "g",    target: 250 },
  fiber_g:       { label: "食物繊維",   unit: "g",    target: 21 },
  salt_g:        { label: "食塩",       unit: "g",    target: 7.5 },
};

const VITAMIN_TARGETS = {
  vitamin_a_ug:   { label: "ビタミンA",  unit: "μg",  target: 900 },
  vitamin_d_ug:   { label: "ビタミンD",  unit: "μg",  target: 8.5 },
  vitamin_e_mg:   { label: "ビタミンE",  unit: "mg",  target: 6 },
  vitamin_k_ug:   { label: "ビタミンK",  unit: "μg",  target: 150 },
  vitamin_b1_mg:  { label: "ビタミンB1", unit: "mg",  target: 1.2 },
  vitamin_b2_mg:  { label: "ビタミンB2", unit: "mg",  target: 1.4 },
  vitamin_b6_mg:  { label: "ビタミンB6", unit: "mg",  target: 1.4 },
  vitamin_b12_ug: { label: "ビタミンB12",unit: "μg",  target: 2.4 },
  vitamin_c_mg:   { label: "ビタミンC",  unit: "mg",  target: 100 },
  folate_ug:      { label: "葉酸",       unit: "μg",  target: 240 },
};

const ALL_TARGETS = { ...DAILY_TARGETS, ...VITAMIN_TARGETS };

let currentFoods = [];
let currentTotal = {};
let imageBase64 = "";
let imageMediaType = "image/jpeg";

// --- 認証 ---

async function boot() {
  try {
    const res = await fetch(window.location.origin + "/api/auth/me");
    const data = await res.json();
    if (data.logged_in) {
      showApp(data.nickname);
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

function showLogin() {
  document.getElementById("loginScreen").style.display = "flex";
  document.getElementById("appScreen").style.display = "none";
}

function showApp(nickname) {
  document.getElementById("loginScreen").style.display = "none";
  document.getElementById("appScreen").style.display = "block";
  document.getElementById("userNickname").textContent = nickname;
  document.getElementById("mealDate").value = todayStr();
}

function loginError(msg) {
  const el = document.getElementById("loginError");
  el.textContent = msg;
  el.style.display = "block";
}

function loginErrorClear() {
  document.getElementById("loginError").style.display = "none";
}

async function registerPasskey() {
  loginErrorClear();
  const nickname = document.getElementById("nicknameInput").value.trim();
  if (!nickname) { loginError("ニックネームを入力してください"); return; }

  if (!window.SimpleWebAuthnBrowser) {
    loginError("このブラウザはパスキーに対応していません");
    return;
  }

  try {
    const optRes = await fetch(window.location.origin + "/api/auth/register/begin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname }),
    });
    const optData = await optRes.json();
    if (!optRes.ok) { loginError(optData.error || "登録を開始できませんでした"); return; }

    const credential = await SimpleWebAuthnBrowser.startRegistration({ optionsJSON: optData });

    const verRes = await fetch(window.location.origin + "/api/auth/register/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credential),
    });
    const verData = await verRes.json();
    if (!verRes.ok || !verData.ok) { loginError(verData.error || "登録に失敗しました"); return; }

    showApp(verData.nickname);
  } catch (err) {
    if (err.name === "InvalidStateError") {
      loginError("このデバイスにはすでにパスキーが登録されています");
    } else if (err.name === "NotAllowedError") {
      loginError("パスキーの登録がキャンセルされました");
    } else {
      loginError(err.message || "登録中にエラーが発生しました");
    }
  }
}

async function loginPasskey() {
  loginErrorClear();
  const nickname = document.getElementById("nicknameInput").value.trim();
  if (!nickname) { loginError("ニックネームを入力してください"); return; }

  if (!window.SimpleWebAuthnBrowser) {
    loginError("このブラウザはパスキーに対応していません");
    return;
  }

  try {
    const optRes = await fetch(window.location.origin + "/api/auth/login/begin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname }),
    });
    const optData = await optRes.json();
    if (!optRes.ok) { loginError(optData.error || "ログインを開始できませんでした"); return; }

    const assertion = await SimpleWebAuthnBrowser.startAuthentication({ optionsJSON: optData });

    const verRes = await fetch(window.location.origin + "/api/auth/login/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(assertion),
    });
    const verData = await verRes.json();
    if (!verRes.ok || !verData.ok) { loginError(verData.error || "ログインに失敗しました"); return; }

    showApp(verData.nickname);
  } catch (err) {
    if (err.name === "NotAllowedError") {
      loginError("パスキーの認証がキャンセルされました");
    } else {
      loginError(err.message || "ログイン中にエラーが発生しました");
    }
  }
}

async function doLogout() {
  await fetch(window.location.origin + "/api/auth/logout", { method: "POST" });
  showLogin();
}

// --- ユーティリティ ---

function todayStr() {
  const d = new Date();
  return d.getFullYear() + "-" +
    String(d.getMonth() + 1).padStart(2, "0") + "-" +
    String(d.getDate()).padStart(2, "0");
}

function fmtDate(str) {
  const d = new Date(str + "T00:00:00");
  return d.toLocaleDateString("ja-JP", { year: "numeric", month: "long", day: "numeric", weekday: "short" });
}

function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
}

// --- タブ ---
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t, i) => {
    t.classList.toggle("active", ["analyze", "history"][i] === name);
  });
  document.getElementById("tab-analyze").style.display = name === "analyze" ? "" : "none";
  document.getElementById("tab-history").style.display  = name === "history"  ? "" : "none";
  if (name === "history") loadHistory();
}

// --- 画像 ---
document.getElementById("fileInput").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) loadFile(file);
});

const uploadArea = document.getElementById("uploadArea");
uploadArea.addEventListener("dragover", (e) => { e.preventDefault(); uploadArea.classList.add("drag-over"); });
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("drag-over"));
uploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadArea.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) loadFile(file);
});

function openFilePicker() {
  const input = document.getElementById("fileInput");
  input.removeAttribute("capture");
  input.click();
}

function openCamera() {
  const input = document.getElementById("fileInput");
  input.setAttribute("capture", "environment");
  input.click();
}

function loadFile(file) {
  imageMediaType = "image/jpeg";
  const reader = new FileReader();
  reader.onload = async (e) => {
    imageBase64 = await compressImage(e.target.result);
    document.getElementById("previewImg").src = imageBase64;
    document.getElementById("uploadArea").style.display = "none";
    document.getElementById("previewArea").style.display = "block";
    document.getElementById("analyzeBtn").disabled = false;
    document.getElementById("result").style.display = "none";
    document.getElementById("errorBox").style.display = "none";
    document.getElementById("saveMsg").style.display = "none";
  };
  reader.readAsDataURL(file);
}

// APIの上限(5MB)を超えないようCanvasでリサイズ
function compressImage(dataUrl, maxBytes = 3.5 * 1024 * 1024) {
  return new Promise((resolve) => {
    const b64 = dataUrl.split(",")[1] || dataUrl;
    // base64→バイト数は約0.75倍
    if (b64.length * 0.75 <= maxBytes) { resolve(dataUrl); return; }

    const img = new window.Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      let w = img.naturalWidth, h = img.naturalHeight;
      if (Math.max(w, h) > 2048) {
        const r = 2048 / Math.max(w, h);
        w = Math.round(w * r); h = Math.round(h * r);
      }
      canvas.width = w; canvas.height = h;
      canvas.getContext("2d").drawImage(img, 0, 0, w, h);

      let quality = 0.85;
      let result;
      do {
        result = canvas.toDataURL("image/jpeg", quality);
        quality -= 0.1;
      } while ((result.split(",")[1].length * 0.75) > maxBytes && quality > 0.3);
      resolve(result);
    };
    img.src = dataUrl;
  });
}

function resetImage() {
  imageBase64 = "";
  document.getElementById("uploadArea").style.display = "block";
  document.getElementById("previewArea").style.display = "none";
  document.getElementById("analyzeBtn").disabled = true;
  document.getElementById("result").style.display = "none";
  document.getElementById("fileInput").value = "";
}

// --- 解析 ---
async function analyze() {
  document.getElementById("loading").style.display = "block";
  document.getElementById("analyzeBtn").disabled = true;
  document.getElementById("errorBox").style.display = "none";
  document.getElementById("result").style.display = "none";
  document.getElementById("saveMsg").style.display = "none";

  try {
    const res = await fetch(window.location.origin + "/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: imageBase64, mediaType: imageMediaType }),
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "解析に失敗しました");
    currentFoods = data.foods;
    currentTotal = data.total;
    renderResult(data);
    document.getElementById("saveBtn").disabled = false;
  } catch (err) {
    const box = document.getElementById("errorBox");
    box.textContent = err.message;
    box.style.display = "block";
  } finally {
    document.getElementById("loading").style.display = "none";
    document.getElementById("analyzeBtn").disabled = false;
  }
}

function recalculate() {
  const inputs = document.querySelectorAll(".food-amount");
  const keys = Object.keys(ALL_TARGETS);
  currentFoods.forEach((food, i) => {
    const newAmount = parseFloat(inputs[i].value) || food.amount_g;
    const ratio = food.amount_g > 0 ? newAmount / food.amount_g : 1;
    food.amount_g = newAmount;
    keys.forEach((k) => { if (food[k] !== undefined) food[k] = parseFloat((food[k] * ratio).toFixed(1)); });
  });
  currentTotal = sumNutrients(currentFoods, keys);
  renderNutrientBars(currentTotal, "macroSection", "vitaminSection");
  renderSuggestions(currentTotal);
}

function sumNutrients(foods, keys) {
  const total = {};
  keys.forEach((k) => { total[k] = parseFloat(foods.reduce((acc, f) => acc + (f[k] || 0), 0).toFixed(1)); });
  return total;
}

// --- 保存 ---
async function saveResult() {
  const date = document.getElementById("mealDate").value || todayStr();
  const btn = document.getElementById("saveBtn");
  btn.disabled = true;
  const box = document.getElementById("errorBox");
  box.style.display = "none";

  let bodyStr;
  try {
    bodyStr = JSON.stringify({ date, foods: currentFoods, total: currentTotal });
  } catch (e) {
    box.textContent = "データ変換エラー: " + e.message;
    box.style.display = "block";
    btn.disabled = false;
    return;
  }

  try {
    const url = window.location.origin + "/save";
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: bodyStr,
    });
    const text = await res.text();
    const data = JSON.parse(text);
    if (!data.ok) throw new Error("サーバーエラー: " + text);
    document.getElementById("saveMsg").style.display = "block";
  } catch (err) {
    box.textContent = "[" + err.name + "] " + err.message;
    box.style.display = "block";
    btn.disabled = false;
  }
}

// --- 履歴 ---
async function loadHistory() {
  const el = document.getElementById("historyList");
  el.innerHTML = "<p style='color:#999;padding:24px 0;text-align:center'>読み込み中...</p>";
  try {
    const res = await fetch(window.location.origin + "/api/history");
    const days = await res.json();
    if (days.length === 0) {
      el.innerHTML = "<p class='history-empty'>まだ記録がありません。<br>食事を解析して保存してみましょう。</p>";
      return;
    }
    el.innerHTML = "";
    days.forEach((day) => el.appendChild(buildDayCard(day)));
  } catch {
    el.innerHTML = "<p class='history-empty'>読み込みに失敗しました。</p>";
  }
}

function buildDayCard(day) {
  const card = document.createElement("div");
  card.className = "day-card";

  const calPct = Math.min(Math.round((day.total.calories || 0) / DAILY_TARGETS.calories.target * 100), 200);
  const calColor = calPct >= 120 ? "#f44336" : calPct >= 80 ? "#ff9800" : "#4caf50";
  const isToday = day.date === todayStr();

  card.innerHTML = `
    <div class="day-header" onclick="toggleDay(this)">
      <span class="day-date">${fmtDate(day.date)}${isToday ? " <span style='color:#4caf50;font-size:12px'>今日</span>" : ""}</span>
      <span class="day-meta">${day.meal_count}食 · ${Math.round(day.total.calories || 0)} kcal</span>
      <span class="day-chevron">▼</span>
    </div>
    <div class="day-calorie-bar">
      <div class="day-calorie-fill" style="width:${Math.min(calPct, 100)}%;background:${calColor}"></div>
    </div>
    <div class="day-body">
      <h3 class="section-label">1日合計 — エネルギー・主要栄養素</h3>
      <div class="macro-bars"></div>
      <h3 class="section-label">1日合計 — ビタミン</h3>
      <div class="vitamin-bars"></div>
      <h3 class="section-label" style="margin-top:18px">食事記録</h3>
      <div class="meal-list"></div>
    </div>
  `;

  const body = card.querySelector(".day-body");
  renderBarsInto(body.querySelector(".macro-bars"), DAILY_TARGETS, day.total);
  renderBarsInto(body.querySelector(".vitamin-bars"), VITAMIN_TARGETS, day.total);

  const mealList = body.querySelector(".meal-list");
  day.meals.forEach((meal) => mealList.appendChild(buildMealBlock(meal, card, day)));

  return card;
}

function buildMealBlock(meal, card, day) {
  const block = document.createElement("div");
  block.className = "meal-block";
  block.dataset.mealId = meal.id;

  const foodNames = meal.foods.map((f) => `${esc(f.name)} ${f.amount_g}g`).join("、");
  block.innerHTML = `
    <div class="meal-block-header">
      <span class="meal-time">${fmtTime(meal.created_at)}</span>
      <span class="meal-kcal">${Math.round(meal.total.calories || 0)} kcal</span>
      <button class="btn-delete" onclick="deleteMeal(${meal.id}, this)">削除</button>
    </div>
    <div class="meal-foods">${foodNames}</div>
  `;
  return block;
}

async function deleteMeal(id, btn) {
  if (!confirm("この食事記録を削除しますか？")) return;
  btn.disabled = true;
  try {
    await fetch(window.location.origin + `/api/meals/${id}`, { method: "DELETE" });
    loadHistory();
  } catch {
    alert("削除に失敗しました");
    btn.disabled = false;
  }
}

function toggleDay(header) {
  header.closest(".day-card").classList.toggle("open");
}

// --- 描画共通 ---
function renderResult(data) {
  renderFoodList(data.foods);
  renderNutrientBars(data.total, "macroSection", "vitaminSection");
  renderSuggestions(data.total);
  document.getElementById("result").style.display = "block";
}

function renderFoodList(foods) {
  const el = document.getElementById("foodList");
  el.innerHTML = "";
  foods.forEach((food, i) => {
    const row = document.createElement("div");
    row.className = "food-item";
    row.innerHTML = `
      <span class="food-name">${esc(food.name)}</span>
      <input class="food-amount" type="number" value="${food.amount_g}" min="0" data-index="${i}">
      <span class="food-unit">g &nbsp; ${food.calories} kcal</span>
    `;
    el.appendChild(row);
  });
}

function renderNutrientBars(total, macroId, vitaminId) {
  renderBarsInto(document.getElementById(macroId), DAILY_TARGETS, total);
  renderBarsInto(document.getElementById(vitaminId), VITAMIN_TARGETS, total);
}

function renderBarsInto(container, targets, total) {
  container.innerHTML = "";
  Object.entries(targets).forEach(([key, meta]) => {
    const value = total[key] || 0;
    const pct = meta.target > 0 ? Math.min((value / meta.target) * 100, 200) : 0;
    const displayPct = Math.round((value / meta.target) * 100);
    const cls = displayPct >= 120 ? "red" : displayPct >= 80 ? "yellow" : "green";
    const color = cls === "red" ? "#f44336" : cls === "yellow" ? "#ff9800" : "#4caf50";

    const row = document.createElement("div");
    row.className = "nutrient-row";
    row.innerHTML = `
      <span class="nutrient-label">${esc(meta.label)}</span>
      <div class="bar-wrap"><div class="bar-fill ${cls}" style="width:${Math.min(pct, 100)}%"></div></div>
      <span class="nutrient-pct" style="color:${color}">${displayPct}%</span>
      <span class="nutrient-val">${r1(value)} ${esc(meta.unit)} / ${meta.target}</span>
    `;
    container.appendChild(row);
  });
}

function r1(v) { return Math.round(v * 10) / 10; }
function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

function detectDeficientNutrients(total) {
  const deficient = [];
  Object.entries(ALL_TARGETS).forEach(([key, meta]) => {
    const suggestion = DEFICIENCY_SUGGESTIONS[key];
    if (!suggestion || (suggestion.foods.length === 0 && suggestion.dishes.length === 0)) return;
    const value = total[key] || 0;
    const pct = meta.target > 0 ? (value / meta.target) * 100 : 100;
    if (pct < 80) {
      deficient.push({ key, label: meta.label, pct: Math.round(pct), suggestion });
    }
  });
  deficient.sort((a, b) => a.pct - b.pct);
  return deficient.slice(0, 3);
}

function renderSuggestions(total) {
  const container = document.getElementById("suggestionSection");
  if (!container) return;
  const deficient = detectDeficientNutrients(total);
  container.innerHTML = "";
  if (deficient.length === 0) {
    container.innerHTML = '<p class="suggestion-ok">全ての栄養素が適正または十分です！</p>';
    return;
  }
  deficient.forEach(({ label, pct, suggestion }) => {
    const card = document.createElement("div");
    card.className = "suggestion-item";
    const foodTags = suggestion.foods.map(f => `<span class="suggestion-tag suggestion-tag--food">${esc(f)}</span>`).join("");
    const dishTags = suggestion.dishes.map(d => `<span class="suggestion-tag suggestion-tag--dish">${esc(d)}</span>`).join("");
    card.innerHTML = `
      <div class="suggestion-header">
        <span class="suggestion-nutrient">${esc(label)}</span>
        <span class="suggestion-pct">${pct}%</span>
      </div>
      <div class="suggestion-body">
        ${foodTags ? `<div class="suggestion-group"><span class="suggestion-group-label">食材</span>${foodTags}</div>` : ""}
        ${dishTags ? `<div class="suggestion-group"><span class="suggestion-group-label">料理</span>${dishTags}</div>` : ""}
      </div>
    `;
    container.appendChild(card);
  });
}

// 起動
boot();
