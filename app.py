import base64
import io
import json
import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime

import requests as http_requests

import webauthn
from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from PIL import Image
from webauthn import base64url_to_bytes
from webauthn.helpers import parse_authentication_credential_json, parse_registration_credential_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
DB_PATH = os.path.join(os.path.dirname(__file__), "nutrition.db")

_DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
USE_PG = bool(_DATABASE_URL)

RP_ID      = os.environ.get("RP_ID", "localhost")
RP_NAME    = "栄養記録アプリ"
APP_ORIGIN = os.environ.get("APP_ORIGIN", "http://localhost:8080")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

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
        url = _DATABASE_URL
        if "sslmode" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        return psycopg2.connect(url)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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

def _fetchone(sql, params=()):
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            return None
        if USE_PG:
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
        return dict(row)
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
    _run(f"""CREATE TABLE IF NOT EXISTS users (
        id          {id_col},
        nickname    TEXT NOT NULL UNIQUE,
        user_handle TEXT NOT NULL UNIQUE,
        created_at  TEXT NOT NULL
    )""")
    _run(f"""CREATE TABLE IF NOT EXISTS credentials (
        id            {id_col},
        user_id       INTEGER NOT NULL,
        credential_id TEXT NOT NULL UNIQUE,
        public_key    TEXT NOT NULL,
        sign_count    INTEGER NOT NULL DEFAULT 0,
        transports    TEXT,
        created_at    TEXT NOT NULL
    )""")
    # user_id カラムを meals に追加（既存DBとの互換）
    if USE_PG:
        _run("ALTER TABLE meals ADD COLUMN IF NOT EXISTS user_id INTEGER")
        _run("ALTER TABLE meals ADD COLUMN IF NOT EXISTS image TEXT")
        _run("ALTER TABLE meals ADD COLUMN IF NOT EXISTS variance REAL")
    else:
        for col_sql in [
            "ALTER TABLE meals ADD COLUMN user_id INTEGER",
            "ALTER TABLE meals ADD COLUMN image TEXT",
            "ALTER TABLE meals ADD COLUMN variance REAL",
        ]:
            try:
                _run(col_sql)
            except Exception:
                pass

def aggregate_totals(totals_list):
    keys = {k for t in totals_list for k in t}
    return {k: round(sum(t.get(k, 0) for t in totals_list), 1) for k in keys}

def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return {"id": uid, "nickname": session.get("nickname", "")}


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


# --- 認証ルート ---

@app.route("/api/auth/me")
def auth_me():
    user = get_current_user()
    if user:
        return jsonify({"logged_in": True, "nickname": user["nickname"]})
    return jsonify({"logged_in": False, "nickname": None})


@app.route("/api/auth/register/begin", methods=["POST"])
def register_begin():
    try:
        init_db()
        data = request.get_json()
        nickname = (data.get("nickname") or "").strip()
        if not nickname:
            return jsonify({"error": "ニックネームを入力してください"}), 400

        existing = _fetchone(f"SELECT id FROM users WHERE nickname = {PH}", (nickname,))
        if existing:
            return jsonify({"error": "このニックネームはすでに使われています"}), 409

        user_handle = os.urandom(64)
        options = webauthn.generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=user_handle,
            user_name=nickname,
            user_display_name=nickname,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        session["reg_challenge"]    = base64.b64encode(options.challenge).decode()
        session["reg_nickname"]     = nickname
        session["reg_user_handle"]  = user_handle.hex()
        return jsonify(json.loads(webauthn.options_to_json(options)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/register/complete", methods=["POST"])
def register_complete():
    try:
        init_db()
        challenge_b64  = session.get("reg_challenge")
        nickname       = session.get("reg_nickname")
        user_handle_hex = session.get("reg_user_handle")
        if not challenge_b64 or not nickname:
            return jsonify({"error": "セッションが無効です。もう一度登録してください"}), 400

        raw_body = request.get_data(as_text=True)
        req_data = json.loads(raw_body)
        credential = parse_registration_credential_json(raw_body)
        verification = webauthn.verify_registration_response(
            credential=credential,
            expected_challenge=base64.b64decode(challenge_b64),
            expected_rp_id=RP_ID,
            expected_origin=APP_ORIGIN,
            require_user_verification=True,
        )

        _run(
            f"INSERT INTO users (nickname, user_handle, created_at) VALUES ({PH},{PH},{PH})",
            (nickname, user_handle_hex, datetime.now().isoformat()),
        )
        user = _fetchone(f"SELECT id FROM users WHERE nickname = {PH}", (nickname,))
        user_id = user["id"]

        cred_id_b64 = base64.urlsafe_b64encode(verification.credential_id).decode().rstrip("=")
        pub_key_b64 = base64.b64encode(verification.credential_public_key).decode()
        transports  = json.dumps(req_data.get("response", {}).get("transports", []))
        _run(
            f"INSERT INTO credentials (user_id, credential_id, public_key, sign_count, transports, created_at) VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
            (user_id, cred_id_b64, pub_key_b64, verification.sign_count, transports, datetime.now().isoformat()),
        )

        session.pop("reg_challenge", None)
        session.pop("reg_nickname", None)
        session.pop("reg_user_handle", None)
        session["user_id"]  = user_id
        session["nickname"] = nickname
        return jsonify({"ok": True, "nickname": nickname})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/login/begin", methods=["POST"])
def login_begin():
    try:
        init_db()
        data = request.get_json()
        nickname = (data.get("nickname") or "").strip()
        if not nickname:
            return jsonify({"error": "ニックネームを入力してください"}), 400

        user = _fetchone(f"SELECT id FROM users WHERE nickname = {PH}", (nickname,))
        if not user:
            return jsonify({"error": "ユーザーが見つかりません"}), 404

        creds = _rows(f"SELECT credential_id FROM credentials WHERE user_id = {PH}", (user["id"],))
        allow_credentials = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["credential_id"]))
            for c in creds
        ]

        options = webauthn.generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        session["auth_challenge"] = base64.b64encode(options.challenge).decode()
        session["auth_nickname"]  = nickname
        session["auth_user_id"]   = user["id"]
        return jsonify(json.loads(webauthn.options_to_json(options)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/login/complete", methods=["POST"])
def login_complete():
    try:
        init_db()
        challenge_b64 = session.get("auth_challenge")
        nickname      = session.get("auth_nickname")
        user_id       = session.get("auth_user_id")
        if not challenge_b64 or not user_id:
            return jsonify({"error": "セッションが無効です。もう一度ログインしてください"}), 400

        raw_body = request.get_data(as_text=True)
        req_data = json.loads(raw_body)
        credential = parse_authentication_credential_json(raw_body)

        cred_id_b64 = req_data.get("id", "")
        stored = _fetchone(
            f"SELECT * FROM credentials WHERE user_id = {PH} AND credential_id = {PH}",
            (user_id, cred_id_b64),
        )
        if not stored:
            return jsonify({"error": "認証情報が見つかりません"}), 404

        verification = webauthn.verify_authentication_response(
            credential=credential,
            expected_challenge=base64.b64decode(challenge_b64),
            expected_rp_id=RP_ID,
            expected_origin=APP_ORIGIN,
            credential_public_key=base64.b64decode(stored["public_key"]),
            credential_current_sign_count=stored["sign_count"],
            require_user_verification=True,
        )
        _run(
            f"UPDATE credentials SET sign_count = {PH} WHERE id = {PH}",
            (verification.new_sign_count, stored["id"]),
        )

        session.pop("auth_challenge", None)
        session.pop("auth_nickname", None)
        session.pop("auth_user_id", None)
        session["user_id"]  = user_id
        session["nickname"] = nickname
        return jsonify({"ok": True, "nickname": nickname})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


# --- 既存ルート ---

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    image_data = data.get("image")
    media_type = data.get("mediaType", "image/jpeg")
    if not image_data:
        return jsonify({"error": "画像データがありません"}), 400
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    image_data = image_data.replace(" ", "").replace("\n", "").replace("\r", "")
    # Base64パディング補完
    missing = len(image_data) % 4
    if missing:
        image_data += "=" * (4 - missing)
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
        text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "")
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            text = match.group(0)
        return jsonify(json.loads(text))
    except json.JSONDecodeError as e:
        print(f"[analyze] JSON parse error: {e!r}, raw: {text[:300]}")
        return jsonify({"error": "解析結果のパースに失敗しました"}), 500
    except Exception as e:
        import traceback
        print(f"[analyze] error: {e!r}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/save", methods=["POST"])
def save():
    try:
        user = get_current_user()
        if not user:
            return jsonify({"ok": False, "error": "ログインが必要です"}), 401
        init_db()
        data = request.get_json()
        date = data.get("date") or datetime.now().strftime("%Y-%m-%d")
        image = data.get("image") or ""
        variance = data.get("variance")
        _run(
            f"INSERT INTO meals (date, foods, total, created_at, user_id, image, variance) VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH})",
            (date,
             json.dumps(data.get("foods", []), ensure_ascii=False),
             json.dumps(data.get("total", {}), ensure_ascii=False),
             datetime.now().isoformat(),
             user["id"],
             image,
             variance),
        )
        ranking_info = {}
        if variance is not None:
            rows = _rows(
                f"SELECT variance FROM meals WHERE variance IS NOT NULL ORDER BY variance ASC"
            )
            all_v = [float(r["variance"]) for r in rows]
            rank = sum(1 for v in all_v if v < float(variance)) + 1
            avg_v = round(sum(all_v) / len(all_v), 1) if all_v else 0
            ranking_info = {"rank": rank, "total": len(all_v), "avg_variance": avg_v}
        return jsonify({"ok": True, **ranking_info})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/history")
def history():
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "ログインが必要です"}), 401
        init_db()
        rows = _rows(
            f"SELECT id, date, foods, total, created_at, image FROM meals WHERE user_id = {PH} ORDER BY date DESC, created_at ASC",
            (user["id"],),
        )
        days = defaultdict(list)
        for row in rows:
            days[row["date"]].append({
                "id": row["id"],
                "foods": json.loads(row["foods"]),
                "total": json.loads(row["total"]),
                "created_at": row["created_at"],
                "image": row.get("image") or "",
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/meals/<int:meal_id>", methods=["DELETE"])
def delete_meal(meal_id):
    try:
        user = get_current_user()
        if not user:
            return jsonify({"ok": False, "error": "ログインが必要です"}), 401
        _run(f"DELETE FROM meals WHERE id = {PH} AND user_id = {PH}", (meal_id, user["id"]))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/slack/post", methods=["POST"])
def slack_post():
    try:
        if not get_current_user():
            return jsonify({"ok": False, "error": "ログインが必要です"}), 401
        if not SLACK_WEBHOOK_URL:
            return jsonify({"ok": False, "error": "Slack Webhook URLが設定されていません"}), 500

        d = request.get_json()
        date       = d.get("date", "")
        nickname   = d.get("nickname", "")
        foods      = d.get("foods", [])
        total      = d.get("total", {})
        variance   = d.get("variance")
        rank       = d.get("rank")
        total_count = d.get("total_count")
        avg_variance = d.get("avg_variance")
        deficient  = d.get("deficient", [])  # [{label, pct, foods, dishes}]

        # 食材リスト
        food_text = "、".join(f"{f['name']} {f['amount_g']}g" for f in foods) or "（なし）"

        # 主要栄養素の充足率
        MACRO_KEYS = [
            ("calories", "カロリー"), ("protein_g", "タンパク質"),
            ("fat_g", "脂質"), ("carbs_g", "炭水化物"),
            ("fiber_g", "食物繊維"), ("salt_g", "食塩"),
        ]
        MACRO_TARGETS = {
            "calories": 2000, "protein_g": 50, "fat_g": 60,
            "carbs_g": 250, "fiber_g": 21, "salt_g": 7.5,
        }
        macro_parts = []
        for key, label in MACRO_KEYS:
            val = total.get(key, 0)
            tgt = MACRO_TARGETS[key]
            pct = round(val / tgt * 100) if tgt else 0
            macro_parts.append(f"{label} {pct}%")
        macro_text = " | ".join(macro_parts)

        # バランススコア
        score_parts = []
        if variance is not None:
            score_parts.append(f"ばらつき: {variance:,.1f}")
        if rank is not None and total_count is not None:
            score_parts.append(f"全体ランキング: {rank}位 / {total_count}件中")
        if avg_variance is not None:
            score_parts.append(f"全体平均ばらつき: {avg_variance:,.1f}")
        score_text = "　".join(score_parts) if score_parts else "（未保存）"

        # 不足栄養素のおすすめ
        def_lines = []
        for item in deficient:
            food_tags = "・".join(item.get("foods", []))
            dish_tags = "・".join(item.get("dishes", []))
            parts = []
            if food_tags:
                parts.append(f"食材: {food_tags}")
            if dish_tags:
                parts.append(f"料理: {dish_tags}")
            def_lines.append(f"{item['label']} ({item['pct']}%) — {' / '.join(parts)}")
        def_text = "\n".join(def_lines) if def_lines else "不足栄養素なし"

        header = f":fork_and_knife: *食事記録 — {date}*"
        if nickname:
            header += f"  |  {nickname}"

        text = (
            f"{header}\n\n"
            f"*検出食材*\n{food_text}\n\n"
            f"*主要栄養素の充足率*\n{macro_text}\n\n"
            f"*バランススコア（栄養素のばらつき）*\n{score_text}\n\n"
            f"*不足栄養素のおすすめ*\n{def_text}"
        )

        resp = http_requests.post(
            SLACK_WEBHOOK_URL,
            json={"text": text},
            timeout=10,
        )
        if resp.status_code != 200:
            return jsonify({"ok": False, "error": f"Slack error: {resp.text}"}), 500
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


try:
    init_db()
except Exception as e:
    print(f"init_db warning: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
