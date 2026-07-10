import json
import time
from attack_library import ATTACKS
from attack_mutator import generate_variants
import target_chatbot_nodefense
import target_chatbot
import target_chatbot_filtered


def check_leak(bot_reply, target_secret):
    return target_secret.lower() in bot_reply.lower()


def run_mutation_suite(bot_module, bot_name, mutated_attacks):
    results = []

    for attack in mutated_attacks:
        attack_id = attack["id"]
        print(f"[{bot_name}] Running mutated attack {attack_id}...")

        had_error = False
        try:
            reply = bot_module.ask_chatbot(attack["prompt"])
            leaked = check_leak(reply, attack["target_secret"])
        except Exception as e:
            reply = f"ERROR: {e}"
            leaked = False
            had_error = True

        results.append({
            "bot": bot_name,
            "attack_id": attack["id"],
            "category": attack["category"],
            "prompt": attack["prompt"],
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
    # Pick a small, focused subset to mutate - the Critical-severity attacks
    # that we most care about, to keep API usage manageable.
    base_attacks = [a for a in ATTACKS if a["severity"] == "Critical"]

    print(f"Generating mutations for {len(base_attacks)} Critical-severity attacks...\n")

    mutated_attacks = []
    next_id = 1000  # use high numbers to avoid clashing with original attack IDs

    for attack in base_attacks:
        variants = generate_variants(attack["prompt"], num_variants=2)
        time.sleep(2)

        for variant_text in variants:
            mutated_attacks.append({
                "id": next_id,
                "category": f"Mutated - {attack['category']}",
                "prompt": variant_text,
                "target_secret": attack["target_secret"],
                "leak_type": attack["leak_type"],
                "severity": attack["severity"]
            })
            next_id += 1

    print(f"Generated {len(mutated_attacks)} mutated attacks.\n")

    all_results = []
    bot_configs = [
        (target_chatbot_nodefense, "No Defense"),
        (target_chatbot, "Strong Guardrails"),
        (target_chatbot_filtered, "Strong + Output Filter"),
    ]

    for bot_module, bot_name in bot_configs:
        bot_results = run_mutation_suite(bot_module, bot_name, mutated_attacks)
        all_results.extend(bot_results)

    with open("mutation_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\nDone! Results saved to mutation_results.json")

    for bot_name in [name for _, name in bot_configs]:
        bot_results = [r for r in all_results if r["bot"] == bot_name]
        leaked_count = sum(1 for r in bot_results if r["leaked"])
        total = len(bot_results)
        print(f"{bot_name}: {leaked_count}/{total} mutated attacks succeeded")


if __name__ == "__main__":
    main()