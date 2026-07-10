import json

MODELS = ["GPT-OSS 120B", "Gemma 31B", "Llama 8B"]
BOTS = ["No Defense", "Strong Guardrails", "Strong + Output Filter", "No Defense + LLM Judge"]

with open("results.json", "r", encoding="utf-8") as f:
    all_results = json.load(f)

for bot_name in BOTS:
    for model_label in MODELS:
        bot_results = [r for r in all_results if r["bot"] == bot_name and r["model"] == model_label]
        total = len(bot_results)
        if total == 0:
            continue
        error_count = sum(1 for r in bot_results if r["error"])
        leaked_count = sum(1 for r in bot_results if r["leaked"])
        critical_leaks = sum(1 for r in bot_results if r["leaked"] and r["severity"] == "Critical")
        leak_rate = (leaked_count / total) * 100
        print(f"{bot_name} | {model_label}: {leaked_count}/{total} leaks ({leak_rate:.1f}%), {critical_leaks} Critical, {error_count} errors")