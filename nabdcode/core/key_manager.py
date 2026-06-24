import os

class KeyManager:
    """
    مدير مفاتيح API للتعامل مع التدوير التلقائي (Rotation) وقيود معدل الطلبات.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._key_index = {}

    def get_api_key(self, provider_key: str) -> str | None:
        """استرجاع المفتاح النشط للمزود"""
        provider_config = self.config.get("providers", {}).get(provider_key, {})
        api_keys = provider_config.get("api_keys", [])

        if api_keys:
            current_index = self._key_index.get(provider_key, 0)
            if current_index >= len(api_keys):
                current_index = 0
            return api_keys[current_index]

        env_key_name = provider_config.get("env_key")
        return (
            provider_config.get("api_key")
            or os.getenv(f"{provider_key.upper()}_API_KEY")
            or (os.getenv(env_key_name) if env_key_name else None)
        )

    def rotate_api_key(self, provider_key: str) -> bool:
        """التبديل للمفتاح التالي في حال حدوث خطأ 429"""
        provider_config = self.config.get("providers", {}).get(provider_key, {})
        api_keys = provider_config.get("api_keys", [])

        if len(api_keys) <= 1:
            return False

        current_index = self._key_index.get(provider_key, 0)
        next_index = (current_index + 1) % len(api_keys)
        self._key_index[provider_key] = next_index
        return True

    def get_active_key_index(self, provider_key: str) -> int:
        """جلب رقم المؤشر (Index) للمفتاح الحالي"""
        return self._key_index.get(provider_key, 0)
