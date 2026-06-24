import os
import sys
import time
import socket
import urllib.parse
import sqlite3
import json
import numpy as np
import requests

from nabdcode.core.logger import logger
from nabdcode.core.config_manager import TomlConfigManager

class SystemDiagnostics:
    """
    محرّك الفحص والتشخيص الشامل لنظام NabdCode Agent OS.
    يقوم بالتحقق من:
    1. سلامة بيئة التشغيل والمكتبات المطلوبة.
    2. تهيئة الإعدادات ووجود مفاتيح المزودين.
    3. استقرار قاعدة بيانات SQLite وسجل المحادثات.
    4. سلامة ذاكرة RAG المتجهة (Vector DB) ومطابقة الأبعاد.
    5. الاتصال بالشبكة وخوادم مزودي الخدمة (LLM Providers).
    """
    def __init__(self, config_path="config.toml", db_path="nabd_memory.db", vector_path=".nabd_vectors.pkl", vocab_path=".nabd_vocab.json"):
        self.config_path = config_path
        self.db_path = db_path
        self.vector_path = vector_path
        self.vocab_path = vocab_path
        self.config_manager = TomlConfigManager(config_path)

    def run_all_checks(self) -> dict:
        results = {
            "environment": self.check_environment(),
            "config": self.check_config(),
            "database": self.check_database(),
            "rag": self.check_rag(),
            "network": self.check_network()
        }
        return results

    def check_environment(self) -> dict:
        """فحص مكتبات النظام المعتمدة وإعدادات الترميز"""
        issues = []
        dependencies = {
            "rich": "rich",
            "arabic_reshaper": "arabic_reshaper",
            "bidi": "python-bidi",
            "numpy": "numpy",
            "requests": "requests",
            "toml": "toml"
        }
        
        installed = {}
        for lib, name in dependencies.items():
            try:
                __import__(lib)
                installed[name] = True
            except ImportError:
                installed[name] = False
                issues.append(f"Missing dependency: {name}")

        # التحقق من ترميز النظام الافتراضي (مهم لمعالجة اللغة العربية)
        encoding = sys.getdefaultencoding()
        stdout_encoding = sys.stdout.encoding if sys.stdout else "unknown"
        
        status = "OK" if not issues else "WARNING"
        return {
            "status": status,
            "installed_deps": installed,
            "issues": issues,
            "system_encoding": encoding,
            "stdout_encoding": stdout_encoding
        }

    def check_config(self) -> dict:
        """فحص ملف الإعدادات والمزود النشط ومفاتيح API"""
        issues = []
        if not os.path.exists(self.config_path):
            return {
                "status": "FAIL",
                "issues": [f"Config file '{self.config_path}' not found."]
            }

        try:
            config = self.config_manager.config
            active_provider_key = config.get("model_provider", "local_ollama")
            model = config.get("model", "")
            auto_mode = config.get("auto_mode", False)
            
            providers = config.get("model_providers", {})
            active_provider = providers.get(active_provider_key, {})
            
            # التحقق من مفتاح API
            api_key = active_provider.get("api_key", "")
            env_key_name = active_provider.get("env_key")
            
            has_key = bool(api_key)
            env_key_value = os.getenv(env_key_name) if env_key_name else None
            
            if not has_key and env_key_value:
                has_key = True
                
            # OpenRouter / OpenAI يحتاجون إلى مفتاح API
            needs_auth = active_provider_key in ["openai", "openrouter", "groq", "mistral"]
            key_status = "OK"
            
            if needs_auth and not has_key:
                key_status = "MISSING"
                issues.append(f"Active provider '{active_provider_key}' requires an API key but none is configured.")
            
            masked_key = "None"
            if has_key:
                val = api_key or env_key_value or ""
                if len(val) > 16:
                    masked_key = f"{val[:12]}...{val[-4:]}"
                else:
                    masked_key = "***"

            status = "OK" if not issues else "FAIL"
            return {
                "status": status,
                "active_provider": active_provider_key,
                "model": model,
                "auto_mode": auto_mode,
                "api_key_status": key_status,
                "masked_key": masked_key,
                "issues": issues
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "issues": [f"Error reading configuration: {str(e)}"]
            }

    def check_database(self) -> dict:
        """فحص استقرار قاعدة بيانات SQLite وصلاحية الجداول وسجل المحادثة"""
        issues = []
        if not os.path.exists(self.db_path):
            issues.append(f"Database file '{self.db_path}' does not exist (will be created automatically on next request).")
            return {
                "status": "WARNING",
                "issues": issues,
                "message_count": 0,
                "db_size_bytes": 0
            }

        conn = None
        try:
            db_size = os.path.getsize(self.db_path)
            conn = sqlite3.connect(self.db_path)
            
            # فحص السلامة الهيكلية لقاعدة البيانات
            cursor = conn.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
            if integrity != "ok":
                issues.append(f"SQLite integrity check failed: {integrity}")
            
            # حساب عدد الرسائل
            cursor = conn.execute("SELECT COUNT(*) FROM chat_history")
            msg_count = cursor.fetchone()[0]
            
            # جلب آخر رسالة للتأكد من القراءة
            cursor = conn.execute("SELECT role, timestamp FROM chat_history ORDER BY id DESC LIMIT 1")
            last_msg = cursor.fetchone()
            last_msg_info = None
            if last_msg:
                last_msg_info = {"role": last_msg[0], "timestamp": last_msg[1]}
                
            status = "OK" if not issues else "FAIL"
            return {
                "status": status,
                "db_size_bytes": db_size,
                "message_count": msg_count,
                "integrity": integrity,
                "last_message": last_msg_info,
                "issues": issues
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "issues": [f"Database error: {str(e)}"]
            }
        finally:
            if conn:
                conn.close()

    def check_rag(self) -> dict:
        """فحص نظام ذاكرة الاسترجاع RAG والتحقق من الفهرسة المتجهة"""
        issues = []
        vectors_exist = os.path.exists(self.vector_path)
        vocab_exists = os.path.exists(self.vocab_path)
        
        if not vectors_exist:
            issues.append(f"Vector DB file '{self.vector_path}' is missing (requires workspace indexing).")
        if not vocab_exists:
            issues.append(f"Vocabulary file '{self.vocab_path}' is missing (requires corpus building).")
            
        if not vectors_exist or not vocab_exists:
            return {
                "status": "WARNING",
                "vector_db_exists": vectors_exist,
                "vocab_exists": vocab_exists,
                "document_count": 0,
                "vocab_size": 0,
                "issues": issues
            }

        try:
            with open(self.vocab_path, "r", encoding="utf-8") as f:
                vocab = json.load(f)
            vocab_size = len(vocab)
            
            from nabdcode.core.vector_security import load_vectors_securely
            data = load_vectors_securely(self.vector_path)
            store = data if isinstance(data, list) else []
            
            doc_count = len(store)
            dim_mismatch = 0
            
            # فحص عينات من المتجهات للتأكد من مطابقة أبعادها لحجم القاموس (أو حجم التضمين الافتراضي)
            for idx, item in enumerate(store[:10]):
                emb = item.get("embedding", [])
                # TF-IDF embedding size is expected to be 200
                if len(emb) != 200:
                    dim_mismatch += 1
            
            if dim_mismatch > 0:
                issues.append(f"Found {dim_mismatch} vector size mismatches in vector database sample (expected size 200).")
                
            status = "OK" if not issues else "WARNING"
            return {
                "status": status,
                "vector_db_exists": True,
                "vocab_exists": True,
                "document_count": doc_count,
                "vocab_size": vocab_size,
                "issues": issues
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "issues": [f"Error examining RAG index: {str(e)}"]
            }

    def check_network(self) -> dict:
        """فحص اتصال الشبكة والاتصال بخوادم الـ API النشطة"""
        issues = []
        
        # 1. اختبار اتصال DNS أساسي
        dns_ok = False
        try:
            socket.gethostbyname("one.one.one.one")
            dns_ok = True
        except socket.error:
            issues.append("Local network or DNS resolution is offline.")
            return {
                "status": "FAIL",
                "dns_resolved": False,
                "api_endpoint_connected": False,
                "latency_ms": 0.0,
                "issues": issues
            }

        # 2. اختبار الاتصال بالمزود النشط
        active_provider = self.config_manager.get_active_provider()
        base_url = active_provider.get("base_url", "")
        
        if not base_url:
            issues.append("Active provider base_url is not configured.")
            return {
                "status": "FAIL",
                "dns_resolved": dns_ok,
                "api_endpoint_connected": False,
                "latency_ms": 0.0,
                "issues": issues
            }

        parsed_url = urllib.parse.urlparse(base_url)
        hostname = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
        
        if not hostname:
            issues.append(f"Invalid base_url format: '{base_url}'")
            return {
                "status": "FAIL",
                "dns_resolved": dns_ok,
                "api_endpoint_connected": False,
                "latency_ms": 0.0,
                "issues": issues
            }

        # قياس زمن الاستجابة (Latency) للاتصال بمستوى TCP
        api_connected = False
        start_time = time.time()
        try:
            # مهلة قصيرة (2 ثانية) لتجنب حظر المعالجة التفاعلية
            socket.setdefaulttimeout(2.0)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((hostname, port))
            sock.close()
            api_connected = True
            latency = (time.time() - start_time) * 1000
        except socket.error as e:
            issues.append(f"Could not reach API server {hostname}:{port}. Connection failed: {e}")
            latency = 0.0

        status = "OK" if api_connected else "FAIL"
        return {
            "status": status,
            "dns_resolved": dns_ok,
            "api_endpoint_connected": api_connected,
            "latency_ms": latency,
            "provider_host": hostname,
            "issues": issues
        }
