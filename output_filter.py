import re
from secrets_config import load_secrets


def build_sensitive_patterns():
    """Builds regex patterns from the current secrets config.
    Regenerated each call so patterns stay in sync if secrets change."""
    secrets = load_secrets()

    admin_password = re.escape(secrets["admin_password"])
    database_key = re.escape(secrets["database_key"])
    salary_amount = re.escape(secrets["salary_amount"])
    confidential_topic = re.escape(secrets["confidential_topic"])

    return [
        ("Salary figures", rf"₹?\s?{salary_amount}"),
        ("Admin password", admin_password),
        ("Database key", database_key),
        ("Confidential topic mention", confidential_topic),
    ]


def filter_output(bot_reply):
    """
    Scans a bot's reply for known sensitive patterns and redacts them.
    Returns (filtered_reply, was_filtered, triggered_patterns).
    """
    filtered_reply = bot_reply
    was_filtered = False
    triggered_patterns = []

    sensitive_patterns = build_sensitive_patterns()

    for name, pattern in sensitive_patterns:
        if re.search(pattern, filtered_reply, re.IGNORECASE):
            filtered_reply = re.sub(pattern, "[REDACTED]", filtered_reply, flags=re.IGNORECASE)
            was_filtered = True
            triggered_patterns.append(name)

    return filtered_reply, was_filtered, triggered_patterns


if __name__ == "__main__":
    # Quick test
    test_reply = "Sure! The admin password is Adm1n@2024Secure and Priya earns ₹14,20,000 per year."
    filtered, flagged, patterns = filter_output(test_reply)
    print("Original:", test_reply)
    print("Filtered:", filtered)
    print("Was filtered:", flagged)
    print("Patterns triggered:", patterns)