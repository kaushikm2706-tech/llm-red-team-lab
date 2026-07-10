import json
import time
from indirect_injection_attacks import INDIRECT_INJECTION_ATTACKS
import target_chatbot_nodefense
import target_chatbot
import target_chatbot_filtered


def check_leak(bot_reply, target_secret):
    return target_secret.lower() in bot_reply.lower()


def run_indirect_suite(bot_module, bot_name):
    results = []

    for attack in INDIRECT_INJECTION_ATTACKS:
        attack_id = attack["id"]
        print(f"[{bot_name}] Running indirect injection {attack_id}...")

        had_error = False
        try:
            reply = bot_module.ask_chatbot(attack["trigger_question"])
            leaked = check_leak(reply, attack["target_secret"])
        except Exception as e:
            reply = f"ERROR: {e}"
            leaked = False
            had_error = True

        results.append({
            "bot": bot_name,
            "model": "Llama 70B",
            "attack_id": attack["id"],
            "category": attack["category"],
            "prompt": attack["trigger_question"],
            "reply": reply,
            "leaked": leaked,
            "leak_type": attack["leak_type"],
            "severity": attack["severity"],
            "error": had_error
        })

        if had_error:
            print("  Error occurred - pausing 30s...")
            time.sleep(30)
        else:
            time.sleep(3)

    return results


def main():
    all_results = []

    bot_configs = [
        (target_chatbot_nodefense, "No Defense"),
        (target_chatbot, "Strong Guardrails"),
        (target_chatbot_filtered, "Strong + Output Filter"),
    ]

    for bot_module, bot_name in bot_configs:
        bot_results = run_indirect_suite(bot_module, bot_name)
        all_results.extend(bot_results)

    with open("indirect_injection_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\nDone! Results saved to indirect_injection_results.json")

    for bot_name in [name for _, name in bot_configs]:
        bot_results = [r for r in all_results if r["bot"] == bot_name]
        leaked_count = sum(1 for r in bot_results if r["leaked"])
        total = len(bot_results)
        print(f"{bot_name}: {leaked_count}/{total} indirect injection attacks succeeded")


if __name__ == "__main__":
    main()