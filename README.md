# Telegram AI Bot — Gemini + aiogram 3

## Loyiha strukturasi

```
telegram_bot/
├── main.py            # Ishga tushirish nuqtasi
├── config.py          # Sozlamalar (.env dan o'qiladi)
├── database.py        # SQLite bilan ishlash
├── memory.py          # Suhbat xotirasi
├── gemini_client.py   # Gemini API wrapper
├── middlewares.py     # Limit va throttle middleware
├── handlers/
│   ├── __init__.py
│   ├── user.py        # Foydalanuvchi handlerlari
│   └── admin.py       # Admin panel
├── requirements.txt
└── .env.example
```

## O'rnatish va ishga tushirish

### 1. Virtual muhit yaratish
```bash
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows
```

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. .env faylini sozlash
```bash
cp .env.example .env
```
`.env` faylini oching va quyidagilarni to'ldiring:
- `BOT_TOKEN` — @BotFather dan olingan token
- `GEMINI_API_KEY` — https://aistudio.google.com dan olingan kalit
- `ADMIN_IDS` — Sizning Telegram ID'ingiz (@userinfobot orqali bilib olasiz)

### 4. Botni ishga tushirish
```bash
python main.py
```

Bot ishga tushganda avtomatik ravishda command menu qo'shiladi:
- **Foydalanuvchilar uchun**: /start, /reset, /usage
- **Adminlar uchun**: /stats, /setlimit, /unlimit, /ban, /unban, /resetuser, /broadcast

---

## Admin buyruqlari

| Buyruq | Tavsif | Misol |
|--------|--------|-------|
| `/stats` | Kunlik statistika | `/stats` |
| `/setlimit USER_ID N` | Foydalanuvchiga limit o'rnatish | `/setlimit 123 50` |
| `/unlimit USER_ID` | Limitni cheksiz qilish | `/unlimit 123` |
| `/ban USER_ID` | Foydalanuvchini bloklash | `/ban 123` |
| `/unban USER_ID` | Foydalanuvchini blokdan chiqarish | `/unban 123` |
| `/resetuser USER_ID` | Suhbat tarixini tozalash | `/resetuser 123` |
| `/broadcast MATN` | Barcha foydalanuvchilarga xabar | `/broadcast Yangilik!` |
| `/users` | Foydalanuvchilar ro'yxatini ko'rish | `/users` |

## Foydalanuvchi buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni boshlash |
| `/reset` | Suhbat tarixini tozalash |
| `/usage` | Bugungi foydalanishni ko'rish |

---

## Arxitektura haqida

- **Middleware**: Xabar kelishi bilan limit tekshiriladi — Gemini API'ga yubormaydi
- **Suhbat xotirasi**: Har foydalanuvchi uchun oxirgi 10 xabar saqlanadi, 24 soatdan so'ng tozalanadi
- **Rate limiting**: Broadcast da 20 msg/sek, throttle'da 0.5 sek/xabar
- **Error handling**: Barcha xatolar log'ga yoziladi, foydalanuvchiga tushunarli xabar ko'rsatiladi
