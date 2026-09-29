from dotenv import load_dotenv
load_dotenv()
import os
import re
import json
import base64
import urllib.request
import urllib.error
import time
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "")
DB_FILE = Path("data.json")

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)

SERVER = {
    "ps": "trial",
    "add": "slsss.eu.cc",
    "port": "443",
    "aid": "0",
    "net": "ws",
    "path": "/sg-amz",
    "type": "none",
    "host": "slsss.eu.cc",
    "sni": "slsss.eu.cc",
    "tls": "tls",
}


# ---------- DATABASE ----------
def load_db():
    if not DB_FILE.exists():
        db = {"proxies": [], "wildcards": [], "usage": {}, "settings": {}}
        save_db(db)
        return db
    try:
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"proxies": [], "wildcards": [], "usage": {}, "settings": {}}


def save_db(db):
    DB_FILE.write_text(
        json.dumps(db, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def is_admin(user_id):
    return bool(ADMIN_ID) and str(user_id) == str(ADMIN_ID)


def touch_usage(db, user_id):
    key = str(user_id)
    db.setdefault("usage", {})
    db["usage"][key] = db["usage"].get(key, 0) + 1
    save_db(db)


# ---------- UUID / VMESS ----------
def get_uuids(count=1):
    if not 1 <= count <= 20:
        raise ValueError("Jumlah UUID harus 1-20.")
    url = "https://www.uuidgenerator.net/api/version4"
    if count > 1:
        url += f"/{count}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Telegram-VMess-Bot/1.0", "Accept": "text/plain"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        text = response.read().decode("utf-8")

    uuids = [x.strip() for x in text.splitlines() if x.strip()]
    valid = [x for x in uuids if UUID_RE.fullmatch(x)]
    if len(valid) < count:
        raise RuntimeError("API tidak mengembalikan UUID yang cukup.")
    return valid[:count]


def make_vmess(uuid):
    cfg = {
        "v": "2",
        "ps": SERVER["ps"],
        "add": SERVER["add"],
        "port": SERVER["port"],
        "id": uuid,
        "aid": SERVER["aid"],
        "net": SERVER["net"],
        "path": SERVER["path"],
        "type": SERVER["type"],
        "host": SERVER["host"],
        "sni": SERVER["sni"],
        "tls": SERVER["tls"],
    }
    raw = json.dumps(cfg, indent=2, ensure_ascii=False)
    return "vmess://" + base64.b64encode(raw.encode()).decode()


# ---------- MENU ----------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 Cek IP Proxy", callback_data="cek_ip")],
        [
            InlineKeyboardButton("🌐 Buat Proxy", callback_data="buat_proxy"),
            InlineKeyboardButton("🎲 Proxy Random", callback_data="proxy_random"),
        ],
        [
            InlineKeyboardButton("📄 List PROXY", callback_data="list_proxy"),
            InlineKeyboardButton("📊 All Status", callback_data="all_status"),
        ],
        [
            InlineKeyboardButton("🔍 Cek Status PROXY", callback_data="cek_status"),
            InlineKeyboardButton("🌎 List Wildcard", callback_data="wildcard"),
        ],
        [
            InlineKeyboardButton("🔗 Get Sub Link", callback_data="sub_link"),
            InlineKeyboardButton("📈 Data Pemakaian", callback_data="pemakaian"),
        ],
        [
            InlineKeyboardButton("💝 Donasi", callback_data="donasi"),
            InlineKeyboardButton("💬 Support", callback_data="support"),
            InlineKeyboardButton("🛠 Admin Menu", callback_data="admin"),
        ],
        [InlineKeyboardButton("🆔 VMess UUID", callback_data="vmess")],
    ])


def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Kembali", callback_data="home")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    touch_usage(db, update.effective_user.id)
    await update.message.reply_text(
        "Selamat datang di bot.\n\n"
        "Silahkan pilih menu di bawah ini untuk menggunakan fitur bot.",
        reply_markup=main_menu()
    )


# ---------- CALLBACKS ----------
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action = q.data
    db = load_db()
    touch_usage(db, q.from_user.id)

    if action == "home":
        await q.edit_message_text(
            "Selamat datang di bot.\n\n"
            "Silahkan pilih menu di bawah ini untuk menggunakan fitur bot.",
            reply_markup=main_menu()
        )
        return

    if action == "cek_ip":
        text = (
            "🧪 <b>Cek IP Proxy</b>\n\n"
            "Kirim IP/host:port untuk memeriksa koneksi TCP.\n"
            "Contoh: <code>example.com:443</code>"
        )

    elif action == "buat_proxy":
        text = (
            "🌐 <b>Buat Proxy</b>\n\n"
            "Gunakan:\n"
            "<code>/addproxy host port</code>\n\n"
            "Contoh:\n"
            "<code>/addproxy example.com 443</code>"
        )

    elif action == "proxy_random":
        proxies = db["proxies"]
        if not proxies:
            text = "🎲 <b>Proxy Random</b>\n\nBelum ada proxy di database."
        else:
            item = proxies[int(time.time()) % len(proxies)]
            text = (
                "🎲 <b>Proxy Random</b>\n\n"
                f"<code>{item['host']}:{item['port']}</code>\n"
                f"Status: {item.get('status', 'unknown')}"
            )

    elif action == "list_proxy":
        proxies = db["proxies"]
        if not proxies:
            text = "📄 <b>List PROXY</b>\n\nBelum ada proxy."
        else:
            lines = ["📄 <b>List PROXY</b>\n"]
            for i, p in enumerate(proxies[:50], 1):
                lines.append(
                    f"{i}. <code>{p['host']}:{p['port']}</code> — {p.get('status','unknown')}"
                )
            text = "\n".join(lines)

    elif action == "all_status":
        proxies = db["proxies"]
        online = sum(p.get("status") == "online" for p in proxies)
        offline = sum(p.get("status") == "offline" for p in proxies)
        unknown = len(proxies) - online - offline
        text = (
            "📊 <b>All Status</b>\n\n"
            f"Total: {len(proxies)}\n"
            f"🟢 Online: {online}\n"
            f"🔴 Offline: {offline}\n"
            f"⚪ Unknown: {unknown}"
        )

    elif action == "cek_status":
        text = (
            "🔍 <b>Cek Status PROXY</b>\n\n"
            "Gunakan:\n"
            "<code>/check host port</code>\n\n"
            "Contoh:\n"
            "<code>/check example.com 443</code>"
        )

    elif action == "wildcard":
        wildcards = db["wildcards"]
        if not wildcards:
            text = (
                "🌎 <b>List Wildcard</b>\n\n"
                "Belum ada wildcard.\n"
                "Admin dapat menambahkan dengan /addwildcard."
            )
        else:
            text = "🌎 <b>List Wildcard</b>\n\n" + "\n".join(
                f"{i}. <code>{w}</code>" for i, w in enumerate(wildcards, 1)
            )

    elif action == "sub_link":
        text = (
            "🔗 <b>Get Sub Link</b>\n\n"
            "Gunakan:\n"
            "<code>/sub</code>\n\n"
            "Bot akan membuat subscription berbasis proxy yang tersimpan."
        )

    elif action == "pemakaian":
        usage = db.get("usage", {})
        mine = usage.get(str(q.from_user.id), 0)
        total = sum(usage.values())
        text = (
            "📈 <b>Data Pemakaian</b>\n\n"
            f"Pemakaian kamu: {mine}\n"
            f"Total aktivitas bot: {total}"
        )

    elif action == "donasi":
        text = (
            "💝 <b>Donasi</b>\n\n"
            "Tambahkan nomor rekening/e-wallet milikmu "
            "di variabel DONASI atau ubah teks pada bot.py."
        )

    elif action == "support":
        text = (
            "💬 <b>Support</b>\n\n"
            "Hubungi admin bot untuk bantuan."
        )

    elif action == "admin":
        if not is_admin(q.from_user.id):
            text = "⛔ Menu Admin hanya untuk admin."
        else:
            text = (
                "🛠 <b>Admin Menu</b>\n\n"
                "/addproxy host port\n"
                "/delproxy nomor\n"
                "/addwildcard domain\n"
                "/delwildcard nomor\n"
                "/broadcast teks\n"
                "/stats"
            )

    elif action == "vmess":
        text = (
            "🆔 <b>VMess UUID</b>\n\n"
            "<code>/uuid</code> — UUID v4 dari API\n"
            "<code>/uuid 5</code> — 5 UUID\n"
            "<code>/vmess UUID</code> — konversi UUID\n"
            "<code>/vmessauto</code> — UUID API → VMess"
        )
    else:
        text = "Menu tidak ditemukan."

    await q.edit_message_text(
        text, parse_mode="HTML", reply_markup=back_menu()
    )


# ---------- PROXY ----------
def check_host(host, port, timeout=4):
    import socket
    start = time.time()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True, round((time.time() - start) * 1000)
    except Exception:
        return False, None


async def addproxy(update, context):
    if len(context.args) != 2:
        await update.message.reply_text("Gunakan: /addproxy host port")
        return
    host, port = context.args
    try:
        port = int(port)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Port harus 1-65535.")
        return

    db = load_db()
    db["proxies"].append({
        "host": host,
        "port": port,
        "status": "unknown",
        "created_by": update.effective_user.id,
        "created_at": int(time.time()),
    })
    save_db(db)
    await update.message.reply_text(f"✅ Proxy ditambahkan: {host}:{port}")


async def delproxy(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Gunakan: /delproxy nomor")
        return
    try:
        idx = int(context.args[0]) - 1
        db = load_db()
        item = db["proxies"].pop(idx)
        save_db(db)
        await update.message.reply_text(
            f"🗑 Dihapus: {item['host']}:{item['port']}"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("Nomor proxy tidak valid.")


async def check_cmd(update, context):
    if len(context.args) != 2:
        await update.message.reply_text("Gunakan: /check host port")
        return
    host, port = context.args
    ok, ms = check_host(host, port)

    db = load_db()
    for p in db["proxies"]:
        if p["host"] == host and str(p["port"]) == str(port):
            p["status"] = "online" if ok else "offline"
            p["latency_ms"] = ms
    save_db(db)

    if ok:
        await update.message.reply_text(
            f"🟢 ONLINE\n{host}:{port}\nLatency: {ms} ms"
        )
    else:
        await update.message.reply_text(f"🔴 OFFLINE\n{host}:{port}")


async def status_all(update, context):
    db = load_db()
    proxies = db["proxies"]
    lines = []
    for p in proxies:
        ok, ms = check_host(p["host"], p["port"])
        p["status"] = "online" if ok else "offline"
        p["latency_ms"] = ms
        icon = "🟢" if ok else "🔴"
        lines.append(
            f"{icon} {p['host']}:{p['port']}"
            + (f" — {ms}ms" if ms else "")
        )
    save_db(db)

    if not lines:
        await update.message.reply_text("Belum ada proxy.")
        return
    await update.message.reply_text(
        "📊 Status proxy:\n\n" + "\n".join(lines[:50])
    )


# ---------- WILDCARD ----------
async def addwildcard(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Gunakan: /addwildcard domain")
        return
    domain = context.args[0].lower().strip()
    db = load_db()
    if domain not in db["wildcards"]:
        db["wildcards"].append(domain)
        save_db(db)
    await update.message.reply_text(f"✅ Wildcard ditambahkan: {domain}")


async def delwildcard(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Gunakan: /delwildcard nomor")
        return
    try:
        idx = int(context.args[0]) - 1
        db = load_db()
        value = db["wildcards"].pop(idx)
        save_db(db)
        await update.message.reply_text(f"🗑 Dihapus: {value}")
    except (ValueError, IndexError):
        await update.message.reply_text("Nomor wildcard tidak valid.")


# ---------- SUBSCRIPTION ----------
async def sub_cmd(update, context):
    db = load_db()
    proxies = db["proxies"]
    if not proxies:
        await update.message.reply_text("Belum ada proxy untuk subscription.")
        return

    # Base64 URL-safe text subscription; data berasal dari database bot.
    lines = [
        f"{p['host']}:{p['port']}"
        for p in proxies
    ]
    encoded = base64.urlsafe_b64encode(
        "\n".join(lines).encode()
    ).decode().rstrip("=")

    await update.message.reply_text(
        "🔗 <b>Subscription data</b>\n\n"
        "Gunakan data berikut sebagai isi subscription:\n"
        f"<code>{encoded}</code>",
        parse_mode="HTML"
    )


# ---------- VMESS ----------
async def uuid_cmd(update, context):
    try:
        count = int(context.args[0]) if context.args else 1
        uuids = get_uuids(count)
        if count == 1:
            await update.message.reply_text(f"<code>{uuids[0]}</code>", parse_mode="HTML")
        else:
            await update.message.reply_text(
                "\n".join(f"{i+1}. {u}" for i, u in enumerate(uuids)),
            )
    except Exception as e:
        await update.message.reply_text(f"Gagal: {e}")


async def vmess_cmd(update, context):
    if not context.args:
        await update.message.reply_text("Gunakan: /vmess UUID")
        return
    uuid = context.args[0].strip()
    if not UUID_RE.fullmatch(uuid):
        await update.message.reply_text("UUID tidak valid.")
        return
    vmess = make_vmess(uuid)
    await update.message.reply_text(
        f"UUID:\n<code>{uuid}</code>\n\nVMess:\n<code>{vmess}</code>",
        parse_mode="HTML"
    )


async def vmessauto_cmd(update, context):
    try:
        count = int(context.args[0]) if context.args else 1
        if not 1 <= count <= 10:
            raise ValueError("jumlah 1-10")
        uuids = get_uuids(count)
        configs = [make_vmess(u) for u in uuids]
        filename = Path(f"vmess_{update.effective_user.id}.txt")
        filename.write_text("\n".join(configs) + "\n", encoding="utf-8")
        try:
            with open(filename, "rb") as f:
                await update.message.reply_document(
                    f, caption=f"✅ {count} VMess berhasil dibuat."
                )
        finally:
            filename.unlink(missing_ok=True)
    except Exception as e:
        await update.message.reply_text(f"Gagal: {e}")


# ---------- ADMIN ----------
async def stats_cmd(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    db = load_db()
    await update.message.reply_text(
        "🛠 Statistik\n\n"
        f"Proxy: {len(db['proxies'])}\n"
        f"Wildcard: {len(db['wildcards'])}\n"
        f"User tercatat: {len(db.get('usage', {}))}\n"
        f"Total aktivitas: {sum(db.get('usage', {}).values())}"
    )


async def broadcast(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Gunakan: /broadcast teks")
        return

    text = " ".join(context.args)
    db = load_db()
    success = 0

    for uid in db.get("usage", {}):
        try:
            await context.bot.send_message(int(uid), text)
            success += 1
        except Exception:
            pass

    await update.message.reply_text(f"Broadcast selesai. Terkirim: {success}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Set BOT_TOKEN terlebih dahulu.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addproxy", addproxy))
    app.add_handler(CommandHandler("delproxy", delproxy))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("status", status_all))
    app.add_handler(CommandHandler("addwildcard", addwildcard))
    app.add_handler(CommandHandler("delwildcard", delwildcard))
    app.add_handler(CommandHandler("sub", sub_cmd))
    app.add_handler(CommandHandler("uuid", uuid_cmd))
    app.add_handler(CommandHandler("vmess", vmess_cmd))
    app.add_handler(CommandHandler("vmessauto", vmessauto_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(menu))

    print("Bot berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
