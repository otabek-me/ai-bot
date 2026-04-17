import logging
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from config import settings
from memory import memory

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiClient:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=settings.SYSTEM_PROMPT,
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            ),
        )

    async def ask(self, user_id: int, user_text: str) -> tuple[str, int]:
        """
        Foydalanuvchi savoliga javob qaytaradi.
        Returns: (javob_matni, ishlatilgan_tokenlar)
        """
        history = memory.get(user_id)

        chat = self.model.start_chat(history=history)

       

        try:
            response = await chat.send_message_async(user_text)
            reply = response.text

            # Xotiraga saqlash
            memory.add(user_id, "user", user_text)
            memory.add(user_id, "model", reply)

            tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens = response.usage_metadata.total_token_count or 0

            return reply, tokens

        except Exception as exc:
            logger.error(f"Gemini xatosi (user={user_id}): {exc}")
            raise


gemini = GeminiClient()
