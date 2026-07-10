import json
import os
import time
import re
from attack_library import ATTACKS
from semantic_leak_judge import semantic_check_leak
from history_log import record_run
import target_chatbot_nodefense
import target_chatbot
import target_chatbot_filtered
import target_chatbot_judge_only
import target_chatbot_combined

MODELS = {
    "GPT-OSS 120B": "openai/gpt-oss-120b",
    "Gemma 31B": "gemma-4-31b",
    "Llama 8B": "llama-3.1-8b-instant"
}

NUM_TRIALS = 3
RESULTS_FILE = "results.json"


def check_leak(bot_reply, target_secret):
    """Original string-match leak detector, kept for comparison."""
    return target_secret.lower() in bot_reply.lower()


def load_existing_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def already_done(existing_results, bot_name, model_label, attack_id, trial_num):
    for r in existing_results:
        if (r["bot"] == bot_name and r["model"] == model_label
                and r["attack_id"] == attack_id and r["trial"] == trial_num
                and not r["error"]):
            return True
    return False


def remove_old_entries(existing_results, bot_name, model_label, attack_id, trial_num):
    """Removes any existing entries (error or not) for this exact combo,
    so a fresh result never gets added alongside a stale one."""
    return [
        r for r in existing_results
        if not (r["bot"] == bot_name and r["model"] == model_label
                and r["attack_id"] == attack_id and r["trial"] == trial_num)
    ]


def save_results(all_results):
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)


def is_daily_quota_error(error_text):
    return "tokens per day" in error_text.lower() or "TPD" in error_text


def run_attacks_on_bot(bot_module, bot_name, model_label, model_id, existing_results):
    for attack in ATTACKS:
        attack_id = attack['id']
        category = attack['category']

        for trial_num in range(1, NUM_TRIALS + 1):
            if already_done(existing_results, bot_name, model_label, attack_id, trial_num):
                print(f"[{bot_name} | {model_label}] Attack {attack_id} trial {trial_num}/{NUM_TRIALS} - already done, skipping.")
                continue

            print(f"[{bot_name} | {model_label}] Running attack {attack_id} ({category}) - trial {trial_num}/{NUM_TRIALS}...")

            try:
                reply = bot_module.ask_chatbot(attack["prompt"], model=model_id)
                leaked_string_match = check_leak(reply, attack["target_secret"])

                semantic_leaked, semantic_reason = semantic_check_leak(
                    reply, attack["target_secret"], category
                )

                if semantic_leaked != leaked_string_match:
                    print(f"    [Detector mismatch] string_match={leaked_string_match}, semantic={semantic_leaked} - {semantic_reason}")

                had_error = False
            except Exception as e:
                error_text = str(e)
                print(f"    FAILED: {error_text}")

                if is_daily_quota_error(error_text):
                    print("\n" + "=" * 60)
                    print("DAILY TOKEN QUOTA HIT for this model.")
                    print("Stopping the run here. Your progress is saved.")
                    print("Wait until tomorrow (quota resets every 24h) and")
                    print("run this same script again - it will pick up")
                    print("exactly where it left off, skipping completed calls.")
                    print("=" * 60)
                    save_results(existing_results)
                    exit(0)

                reply = f"ERROR: {error_text}"
                leaked_string_match = False
                semantic_leaked = False
                semantic_reason = "N/A (call failed)"
                had_error = True

            existing_results[:] = remove_old_entries(existing_results, bot_name, model_label, attack_id, trial_num)

            existing_results.append({
                "bot": bot_name,
                "model": model_label,
                "attack_id": attack["id"],
                "category": attack["category"],
                "prompt": attack["prompt"],
                "trial": trial_num,
                "reply": reply,
                "leaked": leaked_string_match,
                "leaked_semantic": semantic_leaked,
                "semantic_reason": semantic_reason,
                "leak_type": attack["leak_type"],
                "severity": attack["severity"],
                "error": had_error
            })

            save_results(existing_results)
            time.sleep(8)


def print_summary(all_results, bot_configs):
    for bot_module, bot_name in bot_configs:
        for model_label in MODELS:
            bot_results = [r for r in all_results if r["bot"] == bot_name and r["model"] == model_label]
            total = len(bot_results)
            if total == 0:
                continue
            error_count = sum(1 for r in bot_results if r["error"])
            leaked_count = sum(1 for r in bot_results if r["leaked"])
            semantic_leaked_count = sum(1 for r in bot_results if r.get("leaked_semantic", False))
            critical_leaks = sum(1 for r in bot_results if r["leaked"] and r["severity"] == "Critical")
            leak_rate = (leaked_count / total) * 100
            semantic_leak_rate = (semantic_leaked_count / total) * 100
            print(f"{bot_name} | {model_label}: string-match {leaked_count}/{total} ({leak_rate:.1f}%), semantic {semantic_leaked_count}/{total} ({semantic_leak_rate:.1f}%), {critical_leaks} Critical, {error_count} errors")


def main():
    existing_results = load_existing_results()
    print(f"Loaded {len(existing_results)} previously completed results.\n")

    bot_configs = [
        (target_chatbot_nodefense, "No Defense"),
        (target_chatbot, "Strong Guardrails"),
        (target_chatbot_filtered, "Strong + Output Filter"),
        (target_chatbot_judge_only, "No Defense + LLM Judge"),
        (target_chatbot_combined, "Combined (All Defenses)"),
    ]

    for bot_module, bot_name in bot_configs:
        for model_label, model_id in MODELS.items():
            run_attacks_on_bot(bot_module, bot_name, model_label, model_id, existing_results)

    print("\nAll attacks complete! Results saved to results.json")
    print_summary(existing_results, bot_configs)

    snapshot = record_run(existing_results, run_label="Single-Turn Attacks")
    print(f"\nHistory snapshot recorded at {snapshot['timestamp']}")


if __name__ == "__main__":
    main()