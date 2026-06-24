import os
from openai import OpenAI

class LocalEmbeddingEngine:
    """محرك التضمين المركزي المربوط مباشرة بالـ Proxy المحلي عبر المنفذ 8317"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8317/v1", provider_key: str = None):
        api_key = (
            provider_key
            or os.getenv("NABDCODE_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or "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"
        )
        
        if not api_key:
            raise ValueError("No API key configured for embedding engine")
            
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.default_model = "nvidia/embeddings-nv-embed-qa-4"
        self.MAX_EMBED_CHARS = 8000

    def _truncate_text(self, text: str) -> str:
        if len(text) > self.MAX_EMBED_CHARS:
            return text[:self.MAX_EMBED_CHARS]
        return text

    def generate_embedding(self, text: str, model_name: str = None) -> list:
        """توليد مصفوفة الأرقام الحقيقية (Vector) للنص الممرر عبر البروكسي"""
        try:
            safe_text = self._truncate_text(text)
            response = self.client.embeddings.create(
                input=[safe_text],
                model=model_name or self.default_model
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"🚨 خطأ في الاتصال بنقطة تضمين البروكسي: {str(e)}")

    def generate_embeddings(self, texts: list[str], model_name: str | None = None) -> list[list[float]]:
        """توليد مصفوفات مجمعة (Batch) لعدة نصوص دفعة واحدة"""
        try:
            safe_texts = [self._truncate_text(t) for t in texts]
            response = self.client.embeddings.create(
                input=safe_texts,
                model=model_name or self.default_model
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise RuntimeError(f"🚨 خطأ في الاتصال بنقطة تضمين البروكسي (Batch): {str(e)}")
