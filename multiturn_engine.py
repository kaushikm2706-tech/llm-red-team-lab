import json
import time
from multiturn_attacks import MULTITURN_ATTACKS
import target_chatbot_nodefense
import target_chatbot
import target_chatbot_filtered


def check_leak(bot_reply, target_secret):
    return target_secret.lower() in bot_reply.lower()


def run_multiturn_attack(bot_module, attack):
    """
    Runs a single multi-turn attack: sends each turn one after another,
    building up conversation_history, and checks only the FINAL reply.
    """
    conversation_history = []
    final_reply = ""

    for i, turn_message in enumerate(attack["turns"]):
        is_last_turn = (i == len(attack["turns"]) - 1)

        reply = bot_module.ask_chatbot(turn_message, conversation_history)

        conversation_history.append({"role": "user", "content": turn_message})
        conversation_history.append({"role": "assistant", "content": reply})

        if is_last_turn:
            final_reply = reply

        time.sleep(2)

    return final_reply


def run_multiturn_suite(bot_module, bot_name):
    results = []

    for attack in MULTITURN_ATTACKS:
        attack_id = attack["id"]
        category = attack["category"]
        print(f"[{bot_name}] Running multi-turn attack {attack_id} ({len(attack['turns'])} turns)...")

        had_error = False
        try:
            final_reply = run_multiturn_attack(bot_module, attack)
            leaked = check_leak(final_reply, attack["target_secret"])
        except Exception as e:
            final_reply = f"ERROR: {e}"
            leaked = False
            had_error = True

        results.append({
            "bot": bot_name,
            "attack_id": attack["id"],
            "category": attack["category"],
            "prompt": " -> ".join(attack["turns"]),
            "reply": final_reply,
            "leaked": leaked,
            "leak_type": attack["leak_type"],
            "severity": attack["severity"],
            "error": had_error,
            "is_multiturn": True
        })

        if had_error:
            print("  Error occurred - pausing 30s...")
            time.sleep(30)

    return results


def main():
    all_results = []

    bot_configs = [
        (target_chatbot_nodefense, "No Defense"),
        (target_chatbot, "Strong Guardrails"),
        (target_chatbot_filtered, "Strong + Output Filter"),
    ]

    for bot_module, bot_name in bot_configs:
        bot_results = run_multiturn_suite(bot_module, bot_name)
        all_results.extend(bot_results)

    # Save separately from single-turn results, for now
    with open("multiturn_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\nDone! Multi-turn results saved to multiturn_results.json")

    for bot_name in [name for _, name in bot_configs]:
        bot_results = [r for r in all_results if r["bot"] == bot_name]
        leaked_count = sum(1 for r in bot_results if r["leaked"])
        total = len(bot_results)
        print(f"{bot_name}: {leaked_count}/{total} multi-turn attacks succeeded")


if __name__ == "__main__":
    main()