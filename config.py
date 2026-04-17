import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    BOT_TOKEN: str
    GEMINI_API_KEY: str
    ADMIN_IDS: list[int]
    DB_PATH: str
    DAILY_LIMIT: int
    MAX_HISTORY: int
    GEMINI_MODEL: str
    SYSTEM_PROMPT: str

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN")
        gemini_key = os.getenv("GEMINI_API_KEY")

        if not token or not gemini_key:
            raise ValueError(
                "BOT_TOKEN va GEMINI_API_KEY .env faylida bo'lishi shart!"
            )

        admin_ids_raw = os.getenv("ADMIN_IDS", "")
        admin_ids = [
            int(x.strip())
            for x in admin_ids_raw.split(",")
            if x.strip().isdigit()
        ]

        system_prompt = """Sen Telegram tarmog'ida ishlovchi aqlli, professional va xushmuomala sun'iy intellekt yordamchisisan.

Qoidalaring:
1. Foydalanuvchi qaysi tilda yozsa, aynan shu tilda javob ber. O'zbek tilida yozsa — o'zbek tilida, rus tilida yozsa — rus tilida.
2. Javoblaringni o'qishga qulay bo'lishi uchun Markdown formatlashdan foydalan (qalin matn, ro'yxatlar, kod bloklari).
3. Siyosat, tibbiyot va huquq bo'yicha professional maslahat berma — mutaxassisga murojaat qilishni tavsiya et.
4. Doimo aniq, foydali va to'liq javob ber.
5. Guruh chatlarida javoblaringni qisqa va aniq qil.
6. Agar san haqingda so'ralsa Otabek tomonidan yaratilganingni ayt.Lekin har doim emas, faqat qachonki u sani qanaqa suniy intellekt ekaningni so'rasa yoki modelingni so'rasa."""

        return cls(
            BOT_TOKEN=token,
            GEMINI_API_KEY=gemini_key,
            ADMIN_IDS=admin_ids,
            DB_PATH=os.getenv("DB_PATH", "bot.db"),
            DAILY_LIMIT=int(os.getenv("DAILY_LIMIT", "20")),
            MAX_HISTORY=int(os.getenv("MAX_HISTORY", "10")),
            GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            SYSTEM_PROMPT=system_prompt,
        )


settings = Settings.from_env()
