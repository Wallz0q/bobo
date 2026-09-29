# Telegram Proxy Menu - Full

Menu dan fungsi sudah terhubung ke database `data.json`.

## Fitur

- Cek IP/host:port
- Tambah/hapus proxy
- List proxy
- Cek status semua proxy
- Random proxy
- Wildcard
- Subscription data
- Statistik pemakaian
- Admin menu
- UUID v4 API
- VMess generator

## Instalasi

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export BOT_TOKEN="TOKEN_BOT_TELEGRAM"
export ADMIN_ID="ID_TELEGRAM_ADMIN"

python bot.py
```

## Perintah

```text
/addproxy host port
/delproxy nomor
/check host port
/status
/addwildcard domain
/delwildcard nomor
/sub
/uuid
/uuid 5
/vmess UUID
/vmessauto
/vmessauto 5
/stats
/broadcast teks
```

Data tersimpan di `data.json`.

Catatan: fitur cek status melakukan koneksi TCP ke host/port yang diberikan. Gunakan hanya terhadap server yang kamu miliki atau yang kamu berwenang untuk diperiksa.
