import os
import hashlib
import logging
import asyncio
from typing import Dict, List, Any

from nabdcode.memory.chunker import SmartCodeChunker
from nabdcode.memory.embeddings import LocalEmbeddingEngine
from nabdcode.memory.vector_db import LocalVectorDB

logger = logging.getLogger(__name__)

class SemanticMemoryManager:
    """الأوركسترا المركزية للذاكرة: يربط التقطيع والتضمين والمستودع لخدمة وكيل نبض"""
    
    def __init__(self, config_manager=None):
        # 1. استدعاء المكونات الثلاثة المحصنة
        self.chunker = SmartCodeChunker(chunk_size=1000, chunk_overlap=200)
        self.embedding_engine = LocalEmbeddingEngine(base_url="http://127.0.0.1:8317/v1")
        self.vector_db = LocalVectorDB(storage_path="data/memory/vector_store.json")
        self.MAX_CONTEXT_CHARS = 4000
        self._query_cache: Dict[str, List[float]] = {}
        
        self.cache_path = "data/memory/file_index_cache.json"
        self.file_mtimes = self._load_mtimes()

    def _load_mtimes(self) -> Dict[str, float]:
        if os.path.exists(self.cache_path):
            try:
                import json
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_mtimes(self):
        try:
            import json
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.file_mtimes, f)
        except Exception as e:
            logger.warning(f"Could not save mtimes: {e}")

    def index_file_to_memory(self, file_path: str) -> int:
        """قراءة ملف محلي، تقطيعه ذكياً، توليد متجهاته، وحفظه في الذاكرة الصخرية"""
        if not os.path.exists(file_path):
            return 0
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            
            # تقطيع الملف بناءً على القواعد البنيوية
            chunks = self.chunker.chunk_file(file_path, content)
            if not chunks:
                return 0

            # توليد التضمينات بنظام الحزم (Batch) للسرعة
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedding_engine.generate_embeddings(chunk_texts)
            
            inserted_count = 0
            
            for chunk, embedding in zip(chunks, embeddings):
                try:
                    chunk["metadata"]["file_hash"] = file_hash
                    
                    # حقن القطعة في المستودع السريع
                    self.vector_db.add_document(
                        text=chunk["text"],
                        embedding=embedding,
                        metadata=chunk["metadata"]
                    )
                    inserted_count += 1
                except Exception as e:
                    logger.warning("Failed to add chunk: %s", str(e))
                    continue
            
            self.vector_db.flush()
            return inserted_count
            
        except Exception as e:
            logger.warning("⚠️ فشل أرشفة الملف دلالياً %s: %s", file_path, str(e))
            return 0

    def index_workspace(self, directory: str = "./src"):
        """القيام بمسح آلي (Auto-Indexing) لملفات بيئة العمل بالكامل"""
        if not os.path.exists(directory):
            return 0
            
        total_indexed = 0
        new_mtimes = {}
        for root, _, files in os.walk(directory):
            # تخطي المجلدات المخفية مثل .git أو __pycache__
            if '/.' in root or '\\.' in root or '__pycache__' in root:
                continue
                
            for file in files:
                # فلترة مبدئية للامتدادات المدعومة
                if file.endswith(('.py', '.js', '.ts', '.go', '.java', '.cpp', '.c', '.h', '.md', '.txt')):
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    new_mtimes[file_path] = mtime
                    
                    if self.file_mtimes.get(file_path) != mtime:
                        indexed = self.index_file_to_memory(file_path)
                        total_indexed += indexed
        
        # حذف الملفات التي لم تعد موجودة من الفهرس (اختياري)
        self.file_mtimes = new_mtimes
        self._save_mtimes()
        return total_indexed

    def get_context_for_query(self, user_query: str, top_k: int = 3) -> str:
        """استرجاع القطع البرمجية الأكثر صلة بسؤال المستخدم وصياغتها كسياق محقون"""
        # 1. توليد متجه السؤال (مع كاش في الذاكرة لتسريع الأسئلة المتكررة)
        if user_query in self._query_cache:
            query_embedding = self._query_cache[user_query]
        else:
            try:
                query_embedding = self.embedding_engine.generate_embedding(user_query)
                if query_embedding:
                    self._query_cache[user_query] = query_embedding
            except Exception as e:
                logger.warning("Query embedding generation failed: %s", str(e))
                return ""
                
        if not query_embedding:
            return ""
            
        # 2. استعلام المستودع السريع المخزن بالـ norms مسبقاً
        relevant_nodes = self.vector_db.query(query_embedding, top_k=top_k)
        
        if not relevant_nodes:
            return ""
            
        # 3. بناء نص السياق ضمن حدود الـ Max Chars لحماية مساحة السياق
        context_parts = ["=== سياق مسترجع من ملفات المشروع المحلية ==="]
        total_chars = len(context_parts[0])
        
        for idx, node in enumerate(relevant_nodes, 1):
            file_info = node["metadata"].get("file_path", "unknown")
            score_info = f"(درجة التشابه الدلالي: {node['score']:.4f})"
            
            part = (
                f"📎 قطعة رقم [{idx}] من الملف [{file_info}] {score_info}:\n"
                f"```\n{node['text']}\n```\n"
            )
            
            if total_chars + len(part) > self.MAX_CONTEXT_CHARS:
                break
                
            context_parts.append(part)
            total_chars += len(part)
            
        return "\n".join(context_parts)

    def add_knowledge(self, text: str, metadata: Dict) -> str:
        """إضافة معرفة جديدة إلى VectorDB"""
        import uuid
        doc_id = str(uuid.uuid4())
        metadata["id"] = doc_id
        
        # توليد embedding
        embedding = self.embedding_engine.generate_embedding(text)
        if not embedding:
            raise ValueError("Failed to generate embedding for the content.")
            
        # تخزين في المستودع المحلي
        self.vector_db.add_document(text=text, embedding=embedding, metadata=metadata)
        self.vector_db.flush()
        return doc_id
    
    def search(self, query: str, top_k: int = 3, tags: List[str] = None) -> List[Dict]:
        """البحث في الذاكرة الدلالية"""
        query_embedding = self.embedding_engine.generate_embedding(query)
        if not query_embedding:
            return []
            
        results = self.vector_db.query(query_embedding, top_k=top_k * 2) # Fetch extra for tag filtering
        
        filtered_results = []
        for res in results:
            if tags:
                item_tags = res.get("metadata", {}).get("tags", [])
                if not any(t in item_tags for t in tags):
                    continue
            filtered_results.append(res)
            if len(filtered_results) >= top_k:
                break
                
        return filtered_results
