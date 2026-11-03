from __future__ import annotations

import os
import json
import hashlib
import uuid
from datetime import date, datetime
from typing import Any

import pymysql
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
# 上傳目錄：沿用 Railway 現有的 UPLOAD_FOLDER 環境變數。
# 範例：Railway Volume 掛載 /app/uploads，則設定 UPLOAD_FOLDER=/app/uploads。
# 若未設定，仍使用 app.py 同層的 uploads 目錄（適用本機開發）。
UPLOAD_DIR = os.path.abspath(os.path.expanduser(os.environ.get(
    'UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
)))
app.config['MAX_CONTENT_LENGTH'] = 55 * 1024 * 1024
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.logger.info('Animal media directory: %s', UPLOAD_DIR)
if os.environ.get('RAILWAY_ENVIRONMENT') and not os.environ.get('RAILWAY_VOLUME_MOUNT_PATH'):
    app.logger.warning('Railway Volume not detected: uploaded files may disappear after redeploy.')
CORS(app, resources={r"/*": {"origins": "*"}})


def get_db():
    return pymysql.connect(
        host=os.getenv("MYSQLHOST", os.getenv("DB_HOST", "127.0.0.1")),
        port=int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", "3306"))),
        user=os.getenv("MYSQLUSER", os.getenv("DB_USER", "root")),
        password=os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", "")),
        database=os.getenv("MYSQLDATABASE", os.getenv("DB_NAME", "pet_adoption")),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def body() -> dict[str, Any]:
    return request.get_json(silent=True) or {}


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def role_db(role: str | None) -> str:
    return {"領養者": "adopter", "送養者": "foster", "管理員": "admin"}.get(
        role or "", role or "adopter"
    )


def role_flutter(role: str | None) -> str:
    return {"adopter": "領養者", "foster": "送養者", "admin": "管理員"}.get(
        role or "", role or "領養者"
    )


def serial(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key, value in list(result.items()):
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
    return result


@app.post('/uploads')
def upload_animal_media():
    kind = request.form.get('kind', '')
    upload = request.files.get('file')
    if kind not in {'photo', 'video'} or not upload or not upload.filename:
        return jsonify({'success': False, 'message': '缺少檔案或檔案類型不正確'}), 400
    extension = os.path.splitext(secure_filename(upload.filename))[1].lower()
    allowed = {'.jpg', '.jpeg', '.png', '.webp'} if kind == 'photo' else {'.mp4'}
    if extension not in allowed:
        return jsonify({'success': False, 'message': '只接受 JPG/PNG/WebP 照片或 MP4 影片'}), 400
    content = upload.read()
    limit = 8 * 1024 * 1024 if kind == 'photo' else 50 * 1024 * 1024
    if not content or len(content) > limit:
        return jsonify({'success': False, 'message': '檔案為空或超過大小限制'}), 413
    # 簡單檔頭驗證，避免直接以任意副檔名上傳其他內容
    valid = (
        (extension in ('.jpg', '.jpeg') and content.startswith(b'\xff\xd8\xff')) or
        (extension == '.png' and content.startswith(b'\x89PNG\r\n\x1a\n')) or
        (extension == '.webp' and content.startswith(b'RIFF') and content[8:12] == b'WEBP') or
        (extension == '.mp4' and len(content) >= 12 and content[4:8] == b'ftyp')
    )
    if not valid:
        return jsonify({'success': False, 'message': '檔案內容與格式不符'}), 400
    filename = uuid.uuid4().hex + extension
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        # 檔案只寫入設定的 UPLOAD_DIR；讀取 API 也使用同一目錄。
        with open(file_path, 'xb') as target:
            target.write(content)
    except OSError:
        app.logger.exception('Failed to save uploaded media in %s', UPLOAD_DIR)
        return jsonify({'success': False, 'message': '伺服器無法儲存檔案，請檢查 UPLOAD_DIR 與 Railway Volume 權限'}), 500

    app.logger.info('Uploaded media: %s (%d bytes) in %s', filename, len(content), UPLOAD_DIR)
    public_base = os.environ.get('PUBLIC_API_BASE_URL', request.url_root.rstrip('/')).rstrip('/')
    return jsonify({'success': True, 'url': f'{public_base}/uploads/{filename}'}), 201


@app.get('/uploads/<filename>')
def get_uploaded_media(filename):
    # send_from_directory 本身會安全地處理檔案路徑，保留舊版檔名相容性。
    if not os.path.isfile(os.path.join(UPLOAD_DIR, filename)):
        app.logger.warning('Media file not found: %s (UPLOAD_DIR=%s)', filename, UPLOAD_DIR)
        return jsonify({'success': False, 'message': '找不到媒體檔案；請檢查 Railway Volume 或重新上傳'}), 404
    return send_from_directory(UPLOAD_DIR, filename)


@app.errorhandler(413)
def uploaded_file_too_large(_error):
    return jsonify({'success': False, 'message': '檔案超過伺服器允許的大小限制（55 MB）'}), 413


@app.get("/")
def index():
    return jsonify({"success": True, "message": "Pet Adoption API is running"})


@app.post("/register")
def register():
    data = body()
    account = str(data.get("account") or "").strip()
    email = str(data.get("email") or "").strip()
    password = str(data.get("password") or "")
    if not account or not email or not password:
        return jsonify({"success": False, "message": "帳號、Email、密碼不可空白"}), 400

    columns = [
        "name", "email", "password", "role", "phone", "address",
        "living_environment", "pet_experience", "can_keep_pet",
        "daily_time", "pref_type", "pref_age", "pref_gender",
        "family_child", "personality_pref", "can_cross_city",
        "can_take_special", "housing_size", "travel_frequency",
        "living_stability", "monthly_budget", "child_age",
        "has_other_pets", "allergy_tolerance", "only_neutered",
    ]
    values = [
        account, email, md5(password), role_db(data.get("role")),
        data.get("phone"), data.get("city"), data.get("housing"),
        data.get("experience"), data.get("canKeepPet"), data.get("dailyTime"),
        data.get("prefType"), data.get("prefAge"), data.get("prefGender"),
        data.get("familyChild"), data.get("personalityPref"),
        data.get("canCrossCity"), data.get("canTakeSpecial"),
        data.get("housingSize"), data.get("travelFrequency"),
        data.get("livingStability"), data.get("monthlyBudget"),
        data.get("childAge"), data.get("hasOtherPets"),
        data.get("allergyTolerance"), data.get("onlyNeutered"),
    ]

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s OR name=%s", (email, account))
            if cur.fetchone():
                return jsonify({"success": False, "message": "帳號或 Email 已存在"}), 409
            cur.execute(
                f"INSERT INTO users ({','.join(columns)}) VALUES ({','.join(['%s'] * len(columns))})",
                values,
            )
            user_id = cur.lastrowid
        db.commit()
        return jsonify({"success": True, "message": "註冊成功", "user_id": user_id}), 201
    except pymysql.MySQLError as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"資料庫錯誤：{exc}"}), 500
    finally:
        db.close()


@app.post("/login")
def login():
    data = body()
    account = str(data.get("account") or "").strip()
    password = str(data.get("password") or "")
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE (email=%s OR name=%s) AND password=%s LIMIT 1",
                (account, account, md5(password)),
            )
            user = cur.fetchone()
        if not user:
            return jsonify({"success": False, "message": "帳號或密碼錯誤"}), 401

        user.pop("password", None)
        user.update({
            "account": user.get("name"),
            "city": user.get("address"),
            "housing": user.get("living_environment"),
            "experience": user.get("pet_experience"),
            "canKeepPet": bool(user.get("can_keep_pet")),
            "canCrossCity": bool(user.get("can_cross_city")),
            "canTakeSpecial": bool(user.get("can_take_special")),
            "onlyNeutered": bool(user.get("only_neutered")),
            "dailyTime": user.get("daily_time"),
            "prefType": user.get("pref_type"),
            "prefAge": user.get("pref_age"),
            "prefGender": user.get("pref_gender"),
            "familyChild": user.get("family_child"),
            "personalityPref": user.get("personality_pref"),
            "housingSize": user.get("housing_size"),
            "travelFrequency": user.get("travel_frequency"),
            "livingStability": user.get("living_stability"),
            "monthlyBudget": user.get("monthly_budget"),
            "childAge": user.get("child_age"),
            "hasOtherPets": user.get("has_other_pets"),
            "allergyTolerance": user.get("allergy_tolerance"),
            "role": role_flutter(user.get("role")),
        })
        return jsonify({"success": True, "message": "登入成功", "user": serial(user)})
    finally:
        db.close()


def serialize_animals(rows):
    result = []
    for a in rows:
        result.append({
            "id": a.get("chip_number"),
            "chip_number": a.get("chip_number"),
            "actual_chip_number": a.get("chip_number") if a.get("chip_status", "known") == "known" else None,
            "chip_status": a.get("chip_status", "known"),
            "name": a.get("name") or a.get("chip_number"),
            "type": "狗" if a.get("species") in ("犬", "狗") else a.get("species"),
            "species": a.get("species"),
            "place": a.get("location") or a.get("shelter_name") or "未提供",
            "age": a.get("age_group") or "未提供",
            "gender": a.get("gender") or "未提供",
            "size": a.get("size") or "未提供",
            "personality": a.get("personality") or "未提供",
            "healthStatus": a.get("health_status") or "未提供",
            "isNeutered": bool(a.get("is_neutered")),
            "ownerType": a.get("owner_type") or "收容所",
            "owner": a.get("foster_account") or a.get("owner_name") or "系統資料",
            "owner_id": a.get("foster_id"),
            "desc": a.get("description") or a.get("surrender_reason") or "",
            "status": a.get("status"),
            "photo": a.get("photo_url"),
            "photos": (json.loads(a["media_json"]) if a.get("media_json") else ([a.get("photo_url")] if a.get("photo_url") else [])),
            "video_url": a.get("video_url"),
            "breed": a.get("breed"),
            "coatColor": a.get("coat_color"),
            "shelterName": a.get("shelter_name"),
            "announcementDate": serial({"d": a.get("announcement_date")})["d"],
        })
    return result


@app.get("/animals")
def animals():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT a.*, u.name AS foster_account
                FROM animals a
                LEFT JOIN users u ON u.id=a.foster_id
                WHERE a.status='available'
                ORDER BY a.announcement_date DESC, a.created_at DESC
            """)
            rows = cur.fetchall()
        result = []
        for a in rows:
            result.append({
                "id": a.get("chip_number"),
                "chip_number": a.get("chip_number"),
                "actual_chip_number": a.get("chip_number") if a.get("chip_status", "known") == "known" else None,
                "chip_status": a.get("chip_status", "known"),
                "name": a.get("name") or a.get("chip_number"),
                "type": "狗" if a.get("species") in ("犬", "狗") else a.get("species"),
                "species": a.get("species"),
                "place": a.get("location") or a.get("shelter_name") or "未提供",
                "age": a.get("age_group") or "未提供",
                "gender": a.get("gender") or "未提供",
                "size": a.get("size") or "未提供",
                "personality": a.get("personality") or "未提供",
                "healthStatus": a.get("health_status") or "未提供",
                "isNeutered": bool(a.get("is_neutered")),
                "ownerType": a.get("owner_type") or "收容所",
                "owner": a.get("foster_account") or a.get("owner_name") or "系統資料",
                "owner_id": a.get("foster_id"),
                "desc": a.get("description") or a.get("surrender_reason") or "",
                "status": "待領養",
                "photo": a.get("photo_url"),
            "photos": (json.loads(a["media_json"]) if a.get("media_json") else ([a.get("photo_url")] if a.get("photo_url") else [])),
            "video_url": a.get("video_url"),
                "breed": a.get("breed"),
                "coatColor": a.get("coat_color"),
                "shelterName": a.get("shelter_name"),
                "announcementDate": serial({"d": a.get("announcement_date")})["d"],
            })
        return jsonify(result)
    finally:
        db.close()


@app.get("/animals/owner/<int:owner_id>")
def owner_animals(owner_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT a.*, u.name AS foster_account
                FROM animals a
                LEFT JOIN users u ON u.id=a.foster_id
                WHERE a.foster_id=%s AND a.status <> 'deleted'
                ORDER BY a.created_at DESC
            """, (owner_id,))
            rows = cur.fetchall()
        return jsonify(serialize_animals(rows))
    finally:
        db.close()


@app.put("/animals/<path:chip_number>/status")
def manage_animal(chip_number: str):
    data = body()
    try:
        owner_id = int(data.get("owner_id"))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "缺少送養者編號"}), 400
    target = str(data.get("status") or "")
    if target not in {"inactive", "available", "deleted"}:
        return jsonify({"success": False, "message": "不支援的操作"}), 400
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT foster_id, status FROM animals WHERE chip_number=%s FOR UPDATE", (chip_number,))
            animal = cur.fetchone()
            if not animal:
                return jsonify({"success": False, "message": "找不到寵物"}), 404
            if animal["foster_id"] != owner_id:
                return jsonify({"success": False, "message": "這不是你發布的寵物"}), 403
            current = animal["status"]
            if current not in {"available", "inactive"}:
                return jsonify({"success": False, "message": "目前狀態不可操作"}), 409
            if target == "available" and current != "inactive":
                return jsonify({"success": False, "message": "只有已下架寵物可重新上架"}), 409
            if target == "inactive" and current != "available":
                return jsonify({"success": False, "message": "只有待領養寵物可下架"}), 409
            if target == "deleted":
                cur.execute("SELECT COUNT(*) AS total FROM applications WHERE chip_number=%s", (chip_number,))
                if cur.fetchone()["total"] > 0:
                    return jsonify({"success": False, "message": "已有領養申請紀錄，請使用下架，不可刪除"}), 409
            cur.execute("UPDATE animals SET status=%s WHERE chip_number=%s", (target, chip_number))
        db.commit()
        label = {"inactive": "下架成功", "available": "重新上架成功", "deleted": "刪除成功（保留資料庫紀錄）"}[target]
        return jsonify({"success": True, "message": label})
    except pymysql.MySQLError as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"資料庫錯誤：{exc}"}), 500
    finally:
        db.close()


@app.post("/animals")
def create_animal():
    data = body()
    chip = str(data.get("chip_number") or "").strip()
    name = str(data.get("name") or "").strip()
    chip_status = str(data.get("chip_status") or "known")
    if chip_status not in {"known", "forgot", "none"}:
        return jsonify({"success": False, "message": "晶片狀態不正確"}), 400
    if not name or (chip_status == "known" and not chip):
        return jsonify({"success": False, "message": "請填寫寵物名稱及必要的晶片號碼"}), 400
    if chip_status != "known":
        chip = "TEMP-" + uuid.uuid4().hex.upper()

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO animals
                (chip_number,name,species,gender,breed,coat_color,size,
                 surrender_reason,owner_name,shelter_name,announcement_date,
                 age_group,personality,health_status,is_neutered,owner_type,
                 foster_id,description,status,location,photo_url,chip_status,media_json,video_url)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURDATE(),
                        %s,%s,%s,%s,%s,%s,%s,'available',%s,%s,%s,%s,%s)
            """, (
                chip, name, data.get("species"), data.get("gender"),
                data.get("breed"), data.get("coat_color"), data.get("size"),
                data.get("surrender_reason"), data.get("owner_name"),
                data.get("shelter_name"), data.get("age"), data.get("personality"),
                data.get("healthStatus"), data.get("isNeutered"),
                data.get("ownerType"), data.get("foster_id"), data.get("desc"),
                data.get("place"), data.get("photo"), chip_status,
                json.dumps(data.get('photos') or [], ensure_ascii=False),
                data.get('video_url') or None,
            ))
        db.commit()
        return jsonify({"success": True, "message": "寵物發布成功", "animal_id": chip}), 201
    except pymysql.MySQLError as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"資料庫錯誤：{exc}"}), 500
    finally:
        db.close()


@app.post("/applications")
def create_application():
    data = body()
    user_id = data.get("user_id")
    chip = str(data.get("chip_number") or "").strip()
    if not user_id or not chip:
        return jsonify({"success": False, "message": "缺少 user_id 或 chip_number"}), 400

    photo_url = str(data.get('environment_photo_url') or '').strip()
    if not photo_url:
        return jsonify({"success": False, "message": "請上傳飼養環境照片"}), 400
    if len(photo_url) > 1000 or not photo_url.startswith(('https://', 'http://')):
        return jsonify({"success": False, "message": "飼養環境照片網址格式不正確"}), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id FROM applications WHERE user_id=%s AND chip_number=%s",
                (user_id, chip),
            )
            if cur.fetchone():
                return jsonify({"success": False, "message": "你已申請過這隻寵物"}), 409
            cur.execute("""
                INSERT INTO applications
                (user_id,chip_number,status,adopter_name,phone,
                 living_environment,pet_experience,message,environment_photo_url)
                VALUES (%s,%s,'pending',%s,%s,%s,%s,%s,%s)
            """, (
                user_id, chip, data.get("adopter_name"), data.get("phone"),
                data.get("living_environment"), data.get("pet_experience"),
                data.get("message"), photo_url,
            ))
            app_id = cur.lastrowid
        db.commit()
        return jsonify({"success": True, "message": "申請送出成功", "application_id": app_id}), 201
    except pymysql.MySQLError as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"資料庫錯誤：{exc}"}), 500
    finally:
        db.close()


def application_query(where: str, value: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(f"""
                SELECT ap.*, a.name AS pet, a.species,
                       adopter.email AS adopter_email,
                       COALESCE(adopter.name, ap.adopter_name, '未提供') AS user,
                       COALESCE(owner.name, a.owner_name, a.shelter_name, '系統資料') AS owner
                FROM applications ap
                LEFT JOIN animals a ON a.chip_number=ap.chip_number
                LEFT JOIN users adopter ON adopter.id=ap.user_id
                LEFT JOIN users owner ON owner.id=a.foster_id
                WHERE {where}=%s
                ORDER BY ap.created_at DESC, ap.id DESC
            """, (value,))
            return [serial(row) for row in cur.fetchall()]
    finally:
        db.close()


@app.get("/applications/user/<int:user_id>")
def user_applications(user_id: int):
    return jsonify(application_query("ap.user_id", user_id))


@app.get("/applications/owner/<int:owner_id>")
def owner_applications(owner_id: int):
    return jsonify(application_query("a.foster_id", owner_id))


@app.put("/applications/<int:application_id>/status")
def update_application_status(application_id: int):
    status = str(body().get("status") or "")
    if status not in {"pending", "approved", "rejected", "trial", "adopted", "trial_failed"}:
        return jsonify({"success": False, "message": "不合法的狀態"}), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT chip_number FROM applications WHERE id=%s", (application_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "message": "找不到申請"}), 404
            cur.execute("UPDATE applications SET status=%s WHERE id=%s", (status, application_id))
            animal_status = {
                "rejected": "available",
                "trial_failed": "available",
                "trial": "trial",
                "approved": "adopted",
                "adopted": "adopted",
            }.get(status)
            if animal_status:
                cur.execute(
                    "UPDATE animals SET status=%s WHERE chip_number=%s",
                    (animal_status, row["chip_number"]),
                )
        db.commit()
        return jsonify({"success": True, "message": "狀態更新成功"})
    finally:
        db.close()


@app.get("/chat/messages")
def get_chat_messages():
    pet = str(request.args.get("pet_name") or "")
    user_a = str(request.args.get("user_a") or "")
    user_b = str(request.args.get("user_b") or "")
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT id, pet_name, sender, receiver, message, created_at
                FROM chat_messages
                WHERE pet_name=%s
                  AND ((sender=%s AND receiver=%s)
                    OR (sender=%s AND receiver=%s))
                ORDER BY created_at ASC, id ASC
            """, (pet, user_a, user_b, user_b, user_a))
            rows = cur.fetchall()
        return jsonify([serial(row) for row in rows])
    finally:
        db.close()


@app.post("/chat/messages")
def send_chat_message():
    data = body()
    pet = str(data.get("pet_name") or "").strip()
    sender = str(data.get("sender") or "").strip()
    receiver = str(data.get("receiver") or "").strip()
    message = str(data.get("message") or "").strip()
    if not pet or not sender or not receiver or not message:
        return jsonify({"success": False, "message": "聊天資料不完整"}), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_messages (pet_name,sender,receiver,message) VALUES (%s,%s,%s,%s)",
                (pet, sender, receiver, message),
            )
        db.commit()
        return jsonify({"success": True, "message": "訊息已送出"}), 201
    finally:
        db.close()


@app.get("/users/adopters")
def get_adopters():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT id, name AS account, email, phone, address AS city,
                       '領養者' AS role
                FROM users
                WHERE role='adopter'
                ORDER BY name
            """)
            rows = cur.fetchall()
        return jsonify(rows)
    finally:
        db.close()


@app.get("/ratings")
def get_ratings():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT id, adopter, rater, pet_name AS pet,
                       responsibility, tracking, environment, care,
                       score, comment, created_at
                FROM adopter_ratings
                ORDER BY created_at DESC, id DESC
            """)
            rows = cur.fetchall()
        return jsonify([serial(row) for row in rows])
    finally:
        db.close()


@app.post("/ratings")
def create_rating():
    data = body()
    adopter = str(data.get("adopter") or "").strip()
    rater = str(data.get("rater") or "").strip()
    pet = str(data.get("pet_name") or "").strip()
    scores = [
        int(data.get("responsibility") or 0),
        int(data.get("tracking") or 0),
        int(data.get("environment") or 0),
        int(data.get("care") or 0),
    ]
    if not adopter or not rater or any(s < 1 or s > 5 for s in scores):
        return jsonify({"success": False, "message": "評分資料不完整"}), 400

    avg = sum(scores) / 4
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO adopter_ratings
                (adopter,rater,pet_name,responsibility,tracking,
                 environment,care,score,comment)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  responsibility=VALUES(responsibility),
                  tracking=VALUES(tracking),
                  environment=VALUES(environment),
                  care=VALUES(care),
                  score=VALUES(score),
                  comment=VALUES(comment),
                  updated_at=CURRENT_TIMESTAMP
            """, (
                adopter, rater, pet, scores[0], scores[1], scores[2],
                scores[3], avg, data.get("comment"),
            ))
        db.commit()
        return jsonify({"success": True, "message": "評分已儲存"}), 201
    finally:
        db.close()


@app.get("/notifications/<user>")
def get_notifications(user: str):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT id, user_account AS user, title, content, created_at
                FROM notifications
                WHERE user_account=%s
                ORDER BY created_at DESC, id DESC
            """, (user,))
            rows = cur.fetchall()
        return jsonify([serial(row) for row in rows])
    finally:
        db.close()


@app.post("/notifications")
def create_notification():
    data = body()
    user = str(data.get("user") or "").strip()
    title = str(data.get("title") or "").strip()
    content = str(data.get("content") or "").strip()
    if not user or not title:
        return jsonify({"success": False, "message": "通知資料不完整"}), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO notifications (user_account,title,content) VALUES (%s,%s,%s)",
                (user, title, content),
            )
        db.commit()
        return jsonify({"success": True, "message": "通知已建立"}), 201
    finally:
        db.close()



@app.get('/favorites/user/<int:user_id>')
def favorite_list(user_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT user_id, chip_number FROM favorites WHERE user_id=%s', (user_id,))
            return jsonify(cur.fetchall())
    finally:
        db.close()

@app.post('/favorites')
def favorite_add():
    data = body()
    try:
        uid = int(data.get('user_id'))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '缺少使用者編號'}), 400
    chip = str(data.get('chip_number') or '').strip()
    if not chip:
        return jsonify({'success': False, 'message': '缺少動物晶片號碼'}), 400
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT 1 FROM favorites WHERE user_id=%s AND chip_number=%s LIMIT 1', (uid, chip))
            if not cur.fetchone():
                cur.execute('INSERT INTO favorites (user_id, chip_number) VALUES (%s, %s)', (uid, chip))
        db.commit()
        return jsonify({'success': True})
    except pymysql.MySQLError as e:
        db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.close()

@app.delete('/favorites')
def favorite_remove():
    data = body()
    try:
        uid = int(data.get('user_id'))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '缺少使用者編號'}), 400
    chip = str(data.get('chip_number') or '').strip()
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('DELETE FROM favorites WHERE user_id=%s AND chip_number=%s', (uid, chip))
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)