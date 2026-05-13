import base64
import io
import json
import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
DB_PATH = os.path.join(os.path.dirname(__file__), "nutrition.db")

# Render は DATABASE_URL を "postgres://" で渡すが psycopg2 は "postgresql://" が必要
_DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
USE_PG = bool(_DATABASE_URL)

ANALYZE_PROMPT = """この食事の画像を分析し、以下のJSON形式のみで返答してください。説明文・コードブロック記法は不要です。

{
  "foods": [
    {
      "name": "食品名（日本語）",
      "amount_g": 推定グラム数,
      "calories": カロリー(kcal),
      "protein_g": タンパク質(g),
      "fat_g": 脂質(g),
      "carbs_g": 炭水化物(g),
      "fiber_g": 食物繊維(g),
      "salt_g": 食塩相当量(g),
      "vitamin_a_ug": ビタミンA(μg RAE),
      "vitamin_d_ug": ビタミンD(μg),
      "vitamin_e_mg": ビタミンE(mg),
      "vitamin_k_ug": ビタミンK(μg),
      "vitamin_b1_mg": ビタミンB1(mg),
      "vitamin_b2_mg": ビタミンB2(mg),
      "vitamin_b6_mg": ビタミンB6(mg),
      "vitamin_b12_ug": ビタミンB12(μg),
      "vitamin_c_mg": ビタミンC(mg),
      "folate_ug": 葉酸(μg)
    }
  ],
  "total": {
    "calories": 合計, "protein_g": 合計, "fat_g": 合計, "carbs_g": 合計,
    "fiber_g": 合計, "salt_g": 合計, "vitamin_a_ug": 合計, "vitamin_d_ug": 合計,
    "vitamin_e_mg": 合計, "vitamin_k_ug": 合計, "vitamin_b1_mg": 合計,
    "vitamin_b2_mg": 合計, "vitamin_b6_mg": 合計, "vitamin_b12_ug": 合計,
    "vitamin_c_mg": 合計, "folate_ug": 合計
  }
}

すべての数値は小数点以下1桁の数値で返してください。"""


# --- DB ヘルパー ---

def _connect():
    if USE_PG:
        import psycopg2
        return psycopg2.connect(_DATABASE_URL)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# SQLプレースホルダー: PostgreSQL=%s / SQLite=?
PH = "%s" if USE_PG else "?"

def _rows(sql, params=()):
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        if USE_PG:
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def _run(sql, params=()):
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()

def init_db():
    id_col = "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    _run(f"""CREATE TABLE IF NOT EXISTS meals (
        id         {id_col},
        date       TEXT NOT NULL,
        foods      TEXT NOT NULL,
        total      TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")

def aggregate_totals(totals_list):
    keys = {k for t in totals_list for k in t}
    return {k: round(sum(t.get(k, 0) for t in totals_list), 1) for k in keys}


# --- 画像圧縮 ---

def compress_image(b64_data, media_type):
    MAX_BYTES = 4 * 1024 * 1024
    raw = base64.b64decode(b64_data)
    if len(raw) <= MAX_BYTES:
        return b64_data, media_type
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if max(img.size) > 2048:
        img.thumbnail((2048, 2048), Image.LANCZOS)
    quality = 85
    buf = io.BytesIO()
    while quality >= 40:
        buf.seek(0); buf.truncate()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= MAX_BYTES:
            break
        quality -= 15
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"


# --- Routes ---

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    image_data = data.get("image")
    media_type = data.get("mediaType", "image/jpeg")
    if not image_data:
        return jsonify({"error": "画像データがありません"}), 400
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    image_data, media_type = compress_image(image_data, media_type)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                {"type": "text", "text": ANALYZE_PROMPT},
            ]}],
        )
        text = response.content[0].text.strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            text = match.group(0)
        return jsonify(json.loads(text))
    except json.JSONDecodeError:
        return jsonify({"error": "解析結果のパースに失敗しました"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/save", methods=["POST"])
def save():
    data = request.get_json()
    date = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    _run(
        f"INSERT INTO meals (date, foods, total, created_at) VALUES ({PH},{PH},{PH},{PH})",
        (date,
         json.dumps(data.get("foods", []), ensure_ascii=False),
         json.dumps(data.get("total", {}), ensure_ascii=False),
         datetime.now().isoformat()),
    )
    return jsonify({"ok": True})


@app.route("/api/history")
def history():
    rows = _rows("SELECT id, date, foods, total, created_at FROM meals ORDER BY date DESC, created_at ASC")
    days = defaultdict(list)
    for row in rows:
        days[row["date"]].append({
            "id": row["id"],
            "foods": json.loads(row["foods"]),
            "total": json.loads(row["total"]),
            "created_at": row["created_at"],
        })
    result = []
    for date in sorted(days.keys(), reverse=True):
        meals = days[date]
        result.append({
            "date": date,
            "meal_count": len(meals),
            "total": aggregate_totals([m["total"] for m in meals]),
            "meals": meals,
        })
    return jsonify(result)


@app.route("/api/meals/<int:meal_id>", methods=["DELETE"])
def delete_meal(meal_id):
    _run(f"DELETE FROM meals WHERE id = {PH}", (meal_id,))
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)

# Gunicorn エントリポイント（Render用）
init_db()
