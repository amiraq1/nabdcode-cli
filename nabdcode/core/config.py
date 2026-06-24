import os
import logging

logger = logging.getLogger(__name__)

class AppConfig:
    def __init__(self):
        # يمكنك إضافة المفاتيح هنا مباشرة أو سحبها من بيئة Termux
        self.config = {
            "providers": {
                "google": {
                    "api_keys": [
                        os.getenv("GEMINI_API_KEY_1", "المفتاح_الأول_هنا"),
                        os.getenv("GEMINI_API_KEY_2", "المفتاح_الثاني_هنا")
                    ],
                    "env_key": "GOOGLE_API_KEY"
                }
            }
        }
        
        # تنظيف القائمة من أي مفاتيح فارغة
        self.config["providers"]["google"]["api_keys"] = [k for k in self.config["providers"]["google"]["api_keys"] if k]
        self._key_index = {}

    def get_api_key(self, provider_key: str) -> str | None:
        provider_config = self.config.get("providers", {}).get(provider_key, {})
        api_keys = provider_config.get("api_keys", [])

        if api_keys:
            current_index = self._key_index.get(provider_key, 0)
            if current_index >= len(api_keys):
                current_index = 0
            return api_keys[current_index]

        env_key_name = provider_config.get("env_key")
        key = (
            provider_config.get("api_key")
            or os.getenv(f"{provider_key.upper()}_API_KEY")
            or (os.getenv(env_key_name) if env_key_name else None)
        )
        if not key or not str(key).strip():
            raise ValueError(f"[config] 'api_key' is empty or missing for provider '{provider_key}'")
        return key

    def rotate_api_key(self, provider_key: str) -> bool:
        provider_config = self.config.get("providers", {}).get(provider_key, {})
        api_keys = provider_config.get("api_keys", [])

        if len(api_keys) <= 1:
            return False

        current_index = self._key_index.get(provider_key, 0)
        next_index = (current_index + 1) % len(api_keys)
        self._key_index[provider_key] = next_index
        return True

    def get_active_key_index(self, provider_key: str) -> int:
        return self._key_index.get(provider_key, 0)

# كائن عام يمكن استيراده في كل ملفات المشروع
config = AppConfig()
