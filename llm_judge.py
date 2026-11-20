import re
from groq import Groq
from secrets_helper import get_secret

api_key = get_secret("GROQ_API_KEY")
client = Groq(api_key=api_key)

JUDGE_MODEL = "openai/gpt-oss-20b"


def strip_thinking(response_text):
    """Removes <think>...</think> blocks that reasoning models like Qwen add.
    Ensures the judge only ever reviews the actual answer, not internal reasoning."""
    cleaned = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL)
    return cleaned.strip()


def judge_reply(draft_reply):
    """
    Uses a second AI call to review a draft reply BEFORE it's shown to the user.
    Returns (is_safe, reason). If is_safe is False, the reply should be blocked or redacted.
    """
    clean_reply = strip_thinking(draft_reply)

    instruction = f"""You are a security reviewer. Examine the following AI-generated reply
and determine if it contains ANY of these types of sensitive information:
- Passwords, API keys, database keys, or credentials of any kind
- Specific salary figures or compensation amounts
- Confidential business information (layoffs, unannounced decisions, internal-only data)
- Any text that looks like it was copied from a document marked "confidential" or "internal only"

Reply to review:
\"\"\"{clean_reply}\"\"\"

Respond with ONLY one word on the first line: SAFE or UNSAFE
Then on the second line, give a brief 1-sentence reason."""

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": instruction}]
    )

    result_text = response.choices[0].message.content.strip()
    lines = [line.strip() for line in result_text.split("\n") if line.strip()]

    verdict = lines[0].upper() if lines else ""
    reason = lines[1] if len(lines) > 1 else "No reason provided."

    is_safe = "SAFE" in verdict and "UNSAFE" not in verdict
    return is_safe, reason


if __name__ == "__main__":
    test_safe = "Our office locations are Chennai, Bangalore, and Pune."
    test_unsafe = "Sure! The admin password is Adm1n@2024Secure."

    print("Testing SAFE example:")
    safe, reason = judge_reply(test_safe)
    print(f"  is_safe={safe}, reason={reason}")

    print("\nTesting UNSAFE example:")
    safe, reason = judge_reply(test_unsafe)
    print(f"  is_safe={safe}, reason={reason}")