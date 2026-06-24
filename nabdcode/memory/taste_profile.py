import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from nabdcode.memory.vector_db import VectorDB

class TasteProfileManager:

    CACHE_FILE = ".nabd_taste_profile.json"

    ACTION_WEIGHTS = {
        "ACCEPT": 1,
        "EDIT": 2,
        "REJECT": -2,
    }

    def __init__(
        self,
        vector_db: VectorDB,
        workspace_dir: str = "."
    ):
        self.vector_db = vector_db

        self.cache_path = (
            Path(workspace_dir)
            / self.CACHE_FILE
        )

        self.summary_cache = self._load_cache()

    # --------------------------------------------------
    # Cache Management
    # --------------------------------------------------

    def _load_cache(self) -> Dict[str, Any]:
        try:
            if self.cache_path.exists():
                return json.loads(
                    self.cache_path.read_text(
                        encoding="utf-8"
                    )
                )
        except Exception:
            pass

        return {
            "accepted": [],
            "edited": [],
            "rejected": []
        }

    def _save_cache(self) -> None:
        try:
            self.cache_path.write_text(
                json.dumps(
                    self.summary_cache,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )
        except Exception:
            pass

    # --------------------------------------------------
    # Learning
    # --------------------------------------------------

    def log_interaction(
        self,
        action: str,
        prompt: str,
        generated_code: str,
        user_modification: Optional[str] = None,
        language: str = "unknown",
        task_type: str = "general",
    ) -> bool:

        action = action.upper()

        if action not in self.ACTION_WEIGHTS:
            raise ValueError(
                f"Invalid action: {action}"
            )

        semantic_payload = (
            f"User Prompt:\n{prompt}\n\n"
            f"Generated Code:\n{generated_code}\n\n"
            f"Action:\n{action}\n"
        )

        if user_modification:
            semantic_payload += (
                f"\nUser Modification:\n"
                f"{user_modification}\n"
            )

        metadata = {
            "action": action,
            "weight": self.ACTION_WEIGHTS[action],
            "language": language,
            "task_type": task_type,
            "timestamp": time.time(),
            "has_edit": bool(
                user_modification
            ),
        }

        try:

            self.vector_db.add_text(
                text=semantic_payload,
                metadata=metadata
            )

            cache_key = action.lower()

            if cache_key == "accept":
                cache_key = "accepted"

            elif cache_key == "edit":
                cache_key = "edited"

            elif cache_key == "reject":
                cache_key = "rejected"

            self.summary_cache[
                cache_key
            ].append(
                {
                    "prompt": prompt[:150],
                    "language": language,
                    "task_type": task_type,
                    "timestamp": metadata[
                        "timestamp"
                    ]
                }
            )

            self.summary_cache[
                cache_key
            ] = self.summary_cache[
                cache_key
            ][-50:]

            self._save_cache()

            return True

        except Exception:
            return False

    # --------------------------------------------------
    # Retrieval
    # --------------------------------------------------

    def retrieve_taste_context(
        self,
        current_prompt: str,
        limit: int = 5
    ) -> str:

        try:

            results = self.vector_db.search(
                query=current_prompt,
                limit=limit * 2
            )

            if not results:
                return ""

            accepted = []
            edited = []
            rejected = []

            for result in results:

                metadata = result.get(
                    "metadata",
                    {}
                )

                action = metadata.get(
                    "action",
                    ""
                )

                text = result.get(
                    "text",
                    ""
                )

                if action == "ACCEPT":
                    accepted.append(text)

                elif action == "EDIT":
                    edited.append(text)

                elif action == "REJECT":
                    rejected.append(text)

            context_parts = []

            if accepted:
                context_parts.append(
                    "=== PREFERRED PATTERNS ==="
                )

                context_parts.extend(
                    accepted[:3]
                )

            if edited:
                context_parts.append(
                    "\n=== USER CORRECTIONS ==="
                )

                context_parts.extend(
                    edited[:2]
                )

            if rejected:
                context_parts.append(
                    "\n=== AVOID THESE PATTERNS ==="
                )

                context_parts.extend(
                    rejected[:2]
                )

            return "\n\n".join(
                context_parts
            )

        except Exception:
            return ""

    # --------------------------------------------------
    # Quick Summary
    # --------------------------------------------------

    def get_taste_summary(self) -> Dict[str, Any]:

        return {
            "accepted_count": len(
                self.summary_cache.get(
                    "accepted",
                    []
                )
            ),
            "edited_count": len(
                self.summary_cache.get(
                    "edited",
                    []
                )
            ),
            "rejected_count": len(
                self.summary_cache.get(
                    "rejected",
                    []
                )
            ),
        }
