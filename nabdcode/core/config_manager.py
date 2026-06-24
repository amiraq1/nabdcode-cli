import os
import subprocess
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, ClassVar

try:
    import tomllib
except ImportError:
    import toml as tomllib

from nabdcode.core.logger import logger


class ConfigManager:
    """
    Central Configuration Manager for NabdCode CLI.
    Handles reading, permanent storage, and dynamic hot-reloading of system settings
    across both JSON and TOML formats under a unified system.
    """

    DEFAULT_CONFIG: ClassVar[dict[str, Any]] = {
        "provider": "openrouter",
        "model": "deepseek-v4-flash",
        "api_key": "",
        "max_tokens": 4096,
        "temperature": 0.2,
        "taste_profile_enabled": True,
        "max_context_file_size": 50000
    }

    def __init__(self, config_path: str | None = None):
        self._token_cache = {}
        if config_path is None:
            # Fallback: check if config.toml exists in current working directory, else use user's home configuration
            if os.path.exists("config.toml"):
                self.config_path = Path("config.toml")
            else:
                self.config_path = Path.home() / ".config" / "nabdcode" / "config.json"
        else:
            self.config_path = Path(config_path)

        self.config: dict[str, Any] = self.load_config()

    def load_config(self) -> dict[str, Any]:
        """Load configuration from file or build defaults if not present."""
        if not self.config_path.exists():
            if self.config_path.suffix == ".toml":
                return {}
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()

        if self.config_path.suffix == ".toml":
            try:
                with open(self.config_path, "rb") as f:
                    return tomllib.load(f)
            except Exception as e:
                logger.error(f"Error parsing TOML config: {e}")
                return {}
        else:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    complete_config = self.DEFAULT_CONFIG.copy()
                    complete_config.update(loaded)
                    return complete_config
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read JSON config, using defaults: {e}")
                return self.DEFAULT_CONFIG.copy()

    def save_config(self, config_data: dict[str, Any] | None = None) -> bool:
        """Save current configuration to the persistent storage format securely."""
        data_to_save = config_data if config_data is not None else self.config
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            if self.config_path.suffix == ".toml":
                import toml
                with open(self.config_path, "w", encoding="utf-8") as f:
                    toml.dump(data_to_save, f)
                self.config = data_to_save
                logger.info(f"Config saved to {self.config_path}")
                return True
            else:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, indent=4, ensure_ascii=False)
                try:
                    os.chmod(self.config_path, 0o600)
                except (OSError, AttributeError):
                    pass
                self.config = data_to_save
                return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def _get_command_auth_token(self, provider_key: str, auth_config: dict[str, Any]) -> str | None:
        """Execute external command to fetch authentication token with cache TTL management."""
        now = time.time()
        if provider_key in self._token_cache:
            token, expiry = self._token_cache[provider_key]
            if now < expiry:
                return token

        command = auth_config.get("command")
        if not command:
            return None

        args = auth_config.get("args", [])
        timeout_seconds = float(auth_config.get("timeout_ms", 5000)) / 1000.0
        refresh_interval_seconds = float(auth_config.get("refresh_interval_ms", 300000)) / 1000.0

        try:
            full_command = [command] + args
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=True
            )
            token = result.stdout.strip()
            if not token:
                logger.error(f"Authentication command for '{provider_key}' returned an empty token.")
                return None

            self._token_cache[provider_key] = (token, now + refresh_interval_seconds)
            logger.info(f"Successfully fetched and cached new dynamic token for {provider_key}.")
            return token
        except subprocess.TimeoutExpired:
            logger.error(f"Authentication command for '{provider_key}' timed out after {timeout_seconds}s.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Authentication command failed with exit code {e.returncode}. Error: {e.stderr.strip()}")
        except Exception as e:
            logger.error(f"Failed to execute authentication command for {provider_key}: {e}")

        return None

    def get_active_provider(self) -> dict[str, Any]:
        """Return configuration settings for the active provider, merging dynamic tokens and HTTP headers."""
        provider_key = self.config.get("model_provider") or self.config.get("provider") or "local_ollama"
        providers = self.config.get("model_providers") or self.config.get("providers") or {}
        provider_config = providers.get(provider_key, {})

        if not provider_config:
            root_api_key = self.config.get("api_key", "")
            provider_config = {
                "name": provider_key,
                "type": "openai_compatible" if provider_key == "openrouter" else "openai",
                "base_url": "https://openrouter.ai/api/v1" if provider_key == "openrouter" else "",
                "api_key": root_api_key,
            }

        # --- 1. Process Authentication ---
        api_key = None
        auth_config = provider_config.get("auth")
        if auth_config and "command" in auth_config:
            api_key = self._get_command_auth_token(provider_key, auth_config)

        if not api_key:
            env_key_name = provider_config.get("env_key")
            api_key = (
                provider_config.get("api_key")
                or os.getenv(f"{provider_key.upper()}_API_KEY")
                or (os.getenv(env_key_name) if env_key_name else None)
                or self.config.get("api_key")
            )

        # --- 2. Process HTTP Headers ---
        headers = provider_config.get("http_headers") or provider_config.get("headers") or {}
        headers = headers.copy()

        env_headers = provider_config.get("env_http_headers", {})
        for header_key, env_var_name in env_headers.items():
            env_value = os.getenv(env_var_name, "")
            if env_value:
                headers[header_key] = env_value
            else:
                logger.warning(f"Environment variable '{env_var_name}' for header '{header_key}' is not set.")

        if api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {api_key}"

        if not api_key or not str(api_key).strip():
            raise ValueError(f"[config] 'api_key' is empty or missing for provider '{provider_key}'")

        return {
            "name": provider_config.get("name", provider_key),
            "base_url": provider_config.get("base_url", ""),
            "api_key": api_key,
            "env_key": provider_config.get("env_key"),
            "model": provider_config.get("model") or self.config.get("model", "default-model"),
            "headers": headers,
        }

    def list_providers(self) -> list[str]:
        """Return the names of all available providers."""
        providers = self.config.get("model_providers") or self.config.get("providers") or {}
        return list(providers.keys())

    def get_config(self) -> dict[str, Any]:
        """Return the current configuration dictionary."""
        return self.config

    def get(self, key: str, default: Any = None) -> Any:
        """Safely fetch a configuration value from memory cache."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Update and save a configuration value with dynamic type casting constraint matching."""
        if key in ("model_provider", "provider"):
            self.config["model_provider"] = str(value)
            self.config["provider"] = str(value)
            return self.save_config()

        if key in self.DEFAULT_CONFIG:
            expected_type = type(self.DEFAULT_CONFIG[key])
            try:
                if expected_type == bool:
                    if isinstance(value, str):
                        self.config[key] = value.lower() in ("true", "1", "yes", "on")
                    else:
                        self.config[key] = bool(value)
                elif expected_type == int and not isinstance(value, bool):
                    self.config[key] = int(value)
                elif expected_type == float:
                    self.config[key] = float(value)
                else:
                    self.config[key] = value
                return self.save_config()
            except (ValueError, TypeError) as e:
                logger.error(f"Error casting data type for key '{key}': {e}")
                return False
        else:
            self.config[key] = value
            return self.save_config()

    def reset_to_defaults(self) -> bool:
        """Reset all configuration values to original default values."""
        self.config = self.DEFAULT_CONFIG.copy()
        return self.save_config()


class TomlConfigManager(ConfigManager):
    """Legacy wrapper maintaining backward compatibility for TomlConfigManager."""
    def __init__(self, config_path: str = "config.toml"):
        super().__init__(config_path)
