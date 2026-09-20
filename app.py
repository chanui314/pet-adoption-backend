from __future__ import annotations
import os
import json

import hashlib
import uuid
from datetime import date, datetime
from typing import Any

import pymysql
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
PHOTO_MAX_BYTES = 5 * 1024 * 1024
VIDEO_MAX_BYTES = 30 * 1024 * 1024
PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "heic"}
VIDEO_EXTENSIONS = {"mp4", "mov", "m4v", "webm"}


def get_db():
    """
    同時支援 Railway 常見的兩種資料庫變數名稱：
    MYSQLDATABASE 與 MYSQL_DATABASE。
    """
    host = os.environ.get("MYSQLHOST")
    port = int(os.environ.get("MYSQLPORT", "3306"))
    user = os.environ.get("MYSQLUSER")
    password = os.environ.get("MYSQLPASSWORD")
    database = (
        os.environ.get("MYSQLDATABASE")
        or os.environ.get("MYSQL_DATABASE")
    )

    missing = [
        name
        for name, value in {
            "MYSQLHOST": host,
            "MYSQLUSER": user,
            "MYSQLPASSWORD": password,
            "MYSQLDATABASE / MYSQL_DATABASE": database,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "缺少 Railway 資料庫環境變數：" + ", ".join(missing)
        )

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=10,
        read_timeout=20,
        write_timeout=20,
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


@app.get("/")
def index():
    return jsonify({
        "success": True,
        "message": "Pet Adoption API is running",
    })


@app.get("/health")
def health():
    """
    Railway 健康檢查。
    不回傳密碼，只確認環境變數與 MySQL 是否可連線。
    """
    try:
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                row = cur.fetchone()
            return jsonify({
                "success": True,
                "status": "ok",
                "database": bool(row and row.get("ok") == 1),
            }), 200
        finally:
            db.close()
    except Exception as exc:
        return jsonify({
            "success": False,
            "status": "database_error",
            "message": str(exc),
        }), 500


@app.post("/register")
def register():
    data = body()
    email = str(data.get("email") or data.get("account") or "").strip().lower()
    account = email
    password = str(data.get("password") or "")
    if not email or not password:
        return jsonify({"success": False, "message": "Gmail、密碼不可空白"}), 400
    if not email.endswith("@gmail.com") or "@" not in email:
        return jsonify({"success": False, "message": "帳號請使用 Gmail，例如 example@gmail.com"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "密碼至少需要 6 個字元"}), 400

    columns = [
        "name", "email", "password", "role", "phone", "address",
        "living_environment", "pet_experience", "can_keep_pet",
        "daily_time", "pref_type", "pref_age", "pref_gender",
        "family_child", "personality_pref", "can_cross_city",
        "can_take_special", "housing_size", "travel_frequency",
        "living_stability", "monthly_budget", "child_age",
        "has_other_pets", "allergy_tolerance", "only_neutered",
        "only_vaccinated",
    ]
    values = [
        account, email, md5(password), "adopter",  # 初始身分；登入後可自由切換
        data.get("phone"), data.get("city"), data.get("housing"),
        data.get("experience"), data.get("canKeepPet"), data.get("dailyTime"),
        data.get("prefType"), data.get("prefAge"), data.get("prefGender"),
        data.get("familyChild"), data.get("personalityPref"),
        data.get("canCrossCity"), data.get("canTakeSpecial"),
        data.get("housingSize"), data.get("travelFrequency"),
        data.get("livingStability"), data.get("monthlyBudget"),
        data.get("childAge"), data.get("hasOtherPets"),
        data.get("allergyTolerance"), data.get("onlyNeutered"),
        data.get("onlyVaccinated", True),
    ]

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                return jsonify({"success": False, "message": "此 Gmail 已註冊，一個 Gmail 只能建立一個帳號"}), 409
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
    account = str(data.get("account") or "").strip().lower()
    password = str(data.get("password") or "")
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE email=%s AND password=%s LIMIT 1",
                (account, md5(password)),
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
            "onlyVaccinated": bool(user.get("only_vaccinated")) if user.get("only_vaccinated") is not None else True,
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


@app.put("/users/<int:user_id>/active-role")
def update_active_role(user_id: int):
    """切換同一帳號目前使用中的身分，不建立新帳號。"""
    data = body()
    flutter_role = str(data.get("role") or "").strip()
    if flutter_role not in {"領養者", "送養者"}:
        return jsonify({"success": False, "message": "身分只能是領養者或送養者"}), 400

    new_role = role_db(flutter_role)
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT role FROM users WHERE id=%s LIMIT 1", (user_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "message": "找不到使用者"}), 404
            if row.get("role") == "admin":
                return jsonify({"success": False, "message": "管理員身分不可切換"}), 403

            cur.execute("UPDATE users SET role=%s WHERE id=%s", (new_role, user_id))
        db.commit()
        return jsonify({
            "success": True,
            "message": "身分切換成功",
            "role": flutter_role,
        })
    except pymysql.MySQLError as exc:
        db.rollback()
        return jsonify({"success": False, "message": f"資料庫錯誤：{exc}"}), 500
    finally:
        db.close()


@app.get("/animals")
def animals():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT a.*, u.name AS foster_account
                FROM animals a
                LEFT JOIN users u ON u.id=a.foster_id
                ORDER BY a.announcement_date DESC, a.created_at DESC
            """)
            rows = cur.fetchall()
        result = []
        for a in rows:
            stored_chip = str(a.get("chip_number") or "")
            is_internal_key = (
                stored_chip.startswith("NOCHIP-")
                or stored_chip.startswith("UNKNOWNCHIP-")
            )

            # chip_number 在舊資料庫中仍負責當唯一識別鍵。
            # 若沒有真實晶片號碼，後端會使用內部識別碼保存，
            # 但回傳給 Flutter 的 chip_number 會是 null，
            # id 則保留內部識別碼，讓申請、收藏等既有功能仍能運作。
            public_chip = None if is_internal_key else (stored_chip or None)

            result.append({
                "id": stored_chip,
                "chip_number": public_chip,
                "has_chip": bool(a.get("has_chip")),
                "chip_number_known": bool(public_chip),
                "name": a.get("name") or "未命名",
                "type": "狗" if a.get("species") in ("犬", "狗") else a.get("species"),
                "species": a.get("species"),
                "place": a.get("location") or a.get("shelter_name") or "未提供",
                "age": a.get("age_group") or "未提供",
                "gender": a.get("gender") or "未提供",
                "size": a.get("size") or "未提供",
                "personality": a.get("personality") or "未提供",
                "healthStatus": a.get("health_status") or "未提供",
                "isNeutered": bool(a.get("is_neutered")),
                "isVaccinated": bool(a.get("is_vaccinated")),
                "ownerType": a.get("owner_type") or "收容所",
                "owner": a.get("foster_account") or a.get("owner_name") or "系統資料",
                "owner_id": a.get("foster_id"),
                "desc": a.get("description") or a.get("surrender_reason") or "",
                "status": {
                    "available": "待領養",
                    "trial": "試養中",
                    "adopted": "正式領養",
                    "unavailable": "已下架",
                }.get(a.get("status"), a.get("status") or "待領養"),
                "photo": a.get("photo_url"),
                "photos": json.loads(a.get("media_json")) if a.get("media_json") else ([a.get("photo_url")] if a.get("photo_url") else []),
                "video": a.get("video_url"),
                "breed": a.get("breed"),
                "coatColor": a.get("coat_color"),
                "shelterName": a.get("shelter_name"),
                "announcementDate": serial({"d": a.get("announcement_date")})["d"],
            })
        return jsonify(result)
    finally:
        db.close()


@app.post("/animals")
def create_animal():
    data = body()

    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({
            "success": False,
            "message": "寵物名稱不可空白",
        }), 400

    # Flutter 會傳：
    # has_chip = false                  -> 沒有晶片
    # has_chip = true + chip_number     -> 有晶片且知道號碼
    # has_chip = true + chip_number=null -> 有晶片但忘記/不知道號碼
    raw_has_chip = data.get("has_chip", False)
    if isinstance(raw_has_chip, str):
        has_chip = raw_has_chip.strip().lower() in {
            "1", "true", "yes", "y", "on"
        }
    else:
        has_chip = bool(raw_has_chip)

    real_chip = str(data.get("chip_number") or "").strip()

    # 有晶片且使用者表示知道號碼時，才使用真正晶片號碼。
    if has_chip and real_chip:
        stored_chip = real_chip
        chip_number_known = True

    # 有晶片但不知道號碼：
    # 舊資料庫仍以 chip_number 作為主要關聯欄位，
    # 因此產生「內部識別碼」維持申請/收藏/狀態更新功能。
    elif has_chip:
        stored_chip = "UNKNOWNCHIP-" + uuid.uuid4().hex
        chip_number_known = False

    # 沒有晶片也需要一個內部識別碼，
    # 避免舊資料庫 chip_number NOT NULL / PRIMARY KEY 造成新增失敗。
    else:
        stored_chip = "NOCHIP-" + uuid.uuid4().hex
        chip_number_known = False

    db = get_db()
    try:
        with db.cursor() as cur:
            # 如果填了真正晶片號碼，先檢查是否已存在，避免重複發布。
            if chip_number_known:
                cur.execute(
                    "SELECT chip_number FROM animals WHERE chip_number=%s LIMIT 1",
                    (stored_chip,),
                )
                if cur.fetchone():
                    return jsonify({
                        "success": False,
                        "message": "此晶片號碼已存在，請確認是否重複發布",
                    }), 409

            cur.execute("""
                INSERT INTO animals
                (chip_number,has_chip,name,species,gender,breed,coat_color,size,
                 surrender_reason,owner_name,shelter_name,announcement_date,
                 age_group,personality,health_status,is_neutered,is_vaccinated,owner_type,
                 foster_id,description,status,location,photo_url,video_url,media_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURDATE(),
                        %s,%s,%s,%s,%s,%s,%s,%s,'available',%s,%s,%s,%s)
            """, (
                stored_chip,
                1 if has_chip else 0,
                name,
                data.get("species"),
                data.get("gender"),
                data.get("breed"),
                data.get("coat_color"),
                data.get("size"),
                data.get("surrender_reason"),
                data.get("owner_name"),
                data.get("shelter_name"),
                data.get("age"),
                data.get("personality"),
                data.get("healthStatus"),
                data.get("isNeutered"),
                data.get("isVaccinated"),
                data.get("ownerType"),
                data.get("foster_id"),
                data.get("desc"),
                data.get("place"),
                data.get("photo"),
                data.get("video"),
                json.dumps(data.get("photos") or [], ensure_ascii=False),
            ))

        db.commit()

        return jsonify({
            "success": True,
            "message": "寵物發布成功",
            "animal": {
                # id 是系統內部唯一識別值，既有 Flutter 可用它做申請/收藏
                "id": stored_chip,

                # 真正晶片號碼；不知道/沒有晶片時回傳 null
                "chip_number": real_chip if chip_number_known else None,

                "has_chip": has_chip,
                "chip_number_known": chip_number_known,
                "isVaccinated": bool(data.get("isVaccinated")),
                "name": name,
            },
        }), 201

    except pymysql.MySQLError as exc:
        db.rollback()
        return jsonify({
            "success": False,
            "message": f"資料庫錯誤：{exc}",
        }), 500
    finally:
        db.close()


@app.post("/uploads")
def upload_media():
    media_type = str(request.form.get("media_type") or "").strip().lower()
    file = request.files.get("file")
    if media_type not in {"photo", "video"}:
        return jsonify({"success": False, "message": "media_type 必須是 photo 或 video"}), 400
    if file is None or not file.filename:
        return jsonify({"success": False, "message": "沒有選擇檔案"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = PHOTO_EXTENSIONS if media_type == "photo" else VIDEO_EXTENSIONS
    max_bytes = PHOTO_MAX_BYTES if media_type == "photo" else VIDEO_MAX_BYTES
    if ext not in allowed:
        return jsonify({"success": False, "message": f"不支援的檔案格式：{ext}"}), 400

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        return jsonify({"success": False, "message": f"檔案不可超過 {limit_mb}MB"}), 413

    safe_name = secure_filename(file.filename) or f"upload.{ext}"
    filename = f"{uuid.uuid4().hex}_{safe_name}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    url = request.host_url.rstrip("/") + "/uploads/" + filename
    return jsonify({"success": True, "url": url, "size": size}), 201


@app.get("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.post("/applications")
def create_application():
    data = body()
    user_id = data.get("user_id")
    chip = str(data.get("chip_number") or "").strip()
    if not user_id or not chip:
        return jsonify({"success": False, "message": "缺少 user_id 或 chip_number"}), 400

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
                 living_environment,pet_experience,message)
                VALUES (%s,%s,'pending',%s,%s,%s,%s,%s)
            """, (
                user_id, chip, data.get("adopter_name"), data.get("phone"),
                data.get("living_environment"), data.get("pet_experience"),
                data.get("message"),
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
    if status not in {
        "pending", "approved", "rejected", "trial",
        "adopted", "trial_failed", "cancelled"
    }:
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
                "cancelled": "available",
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
                WHERE role <> 'admin'
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



@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    app.logger.exception("Unhandled server error")

    error_text = str(exc)
    hint = None

    if "has_chip" in error_text and (
        "Unknown column" in error_text
        or "1054" in error_text
    ):
        hint = (
            "animals 資料表尚未新增 has_chip 欄位，"
            "請先在 MySQL 執行："
            "ALTER TABLE animals ADD COLUMN has_chip TINYINT(1) NOT NULL DEFAULT 0;"
        )

    if "is_vaccinated" in error_text and (
        "Unknown column" in error_text
        or "1054" in error_text
    ):
        hint = (
            "animals 資料表尚未新增 is_vaccinated 欄位，"
            "請先在 MySQL 執行："
            "ALTER TABLE animals ADD COLUMN is_vaccinated TINYINT(1) NOT NULL DEFAULT 0;"
        )

    response = {
        "success": False,
        "message": "伺服器發生錯誤",
        "error": error_text,
    }

    if hint:
        response["hint"] = hint

    return jsonify(response), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )