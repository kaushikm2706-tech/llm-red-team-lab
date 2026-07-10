import json
import os

CONFIG_FILE = "secrets_config.json"

DEFAULT_SECRETS = {
    "admin_password": "Adm1n@2024Secure",
    "salary_amount": "14,20,000",
    "database_key": "DB-BCK-7729-XKQ1",
    "confidential_topic": "layoffs",
    "system_prompt_marker": "STRICT RULES"
}


def load_secrets():
    """Loads user-defined secrets if present, otherwise falls back to Acme Corp defaults."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        merged = DEFAULT_SECRETS.copy()
        merged.update(saved)
        return merged
    return DEFAULT_SECRETS.copy()


def save_secrets(secrets_dict):
    """Saves user-defined secrets, only keeping known keys."""
    valid_keys = set(DEFAULT_SECRETS.keys())
    cleaned = {k: v for k, v in secrets_dict.items() if k in valid_keys and v.strip() != ""}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)


def reset_to_defaults():
    """Deletes the user config, reverting to Acme Corp defaults."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)


if __name__ == "__main__":
    print("Current secrets:")
    for k, v in load_secrets().items():
        print(f"  {k}: {v}")