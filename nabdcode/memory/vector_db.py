import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LocalVectorDB:
    """مستودع متجهات محلي خفيف الوزن ومحمي يعتمد على NumPy لإجراء عمليات البحث الدلالي السريع في بيئة الهاتف"""
    
    def __init__(self, storage_path: str = "data/memory/vector_store.json"):
        self.storage_path = storage_path
        self._dirty = False
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self.nodes: List[Dict[str, Any]] = self._load_db()

    def _load_db(self) -> List[Dict[str, Any]]:
        """تحميل المتجهات المخزنة محلياً عند إقلاع المحرك"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Vector store load failed: %s", str(e))
                return []
        return []

    def save(self):
        """تثبيت المتجهات الجديدة في الملف المحلي بصيغة JSON نظيفة بطريقة آمنة"""
        try:
            temp_path = self.storage_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.nodes, f, ensure_ascii=False)
            os.replace(temp_path, self.storage_path)
        except Exception as e:
            raise IOError(f"🚨 فشل حفظ قاعدة بيانات المتجهات محلياً: {e}")

    def flush(self):
        if self._dirty:
            self.save()
            self._dirty = False

    def add_document(self, text: str, embedding: List[float], metadata: Dict[str, Any]):
        """حقن وثيقة أو قطعة كود جديدة مع مصفوفة التضمين والبيانات الوصفية"""
        if not embedding:
            return
            
        n_v = np.array(embedding, dtype=np.float32)
        norm = float(np.linalg.norm(n_v))
            
        node = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata,
            "norm": norm
        }
        self.nodes.append(node)
        self._dirty = True

    def query(self, query_embedding: List[float], top_k: int = 3, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """البحث عن أكثر القطع شبهاً بسؤال المستخدم باستخدام الـ Cosine Similarity المؤتمت عبر NumPy"""
        if not query_embedding or not self.nodes:
            return []

        q_v = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_v)
        
        if q_norm == 0:
            return []

        results = []
        q_len = len(query_embedding)

        for node in self.nodes:
            if filter_type and node["metadata"].get("type") != filter_type:
                continue

            if q_len != len(node["embedding"]):
                continue

            n_v = np.array(node["embedding"], dtype=np.float32)
            n_norm = node.get("norm", float(np.linalg.norm(n_v)))
            
            if n_norm == 0:
                continue

            # حساب الـ Cosine Similarity باستخدام الـ norm المخزن مسبقاً للسرعة
            similarity = float(np.dot(q_v, n_v) / (q_norm * n_norm))
            
            results.append({
                "score": similarity,
                "text": node["text"],
                "metadata": node["metadata"]
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def clear_all(self):
        """تطهير قاعدة البيانات بالكامل"""
        self.nodes = []
        self._dirty = True
        self.flush()
