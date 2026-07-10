import json
import os
from datetime import datetime

HISTORY_FILE = "run_history.json"


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def record_run(results, run_label="Single-Turn Attacks"):
    """Snapshots the current leak rate per bot/model at this point in time."""
    history = load_history()

    bot_model_combos = sorted(set((r["bot"], r.get("model", "")) for r in results))
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "run_label": run_label,
        "results": []
    }

    for bot_name, model_name in bot_model_combos:
        subset = [r for r in results if r["bot"] == bot_name and r.get("model", "") == model_name]
        total = len(subset)
        leaked = sum(1 for r in subset if r.get("leaked", False))
        critical = sum(1 for r in subset if r.get("leaked", False) and r.get("severity") == "Critical")
        snapshot["results"].append({
            "bot": bot_name,
            "model": model_name,
            "total": total,
            "leaked": leaked,
            "leak_rate": round((leaked / total) * 100, 1) if total > 0 else 0,
            "critical": critical
        })

    history.append(snapshot)
    save_history(history)
    return snapshot


if __name__ == "__main__":
    history = load_history()
    print(f"Total recorded runs: {len(history)}")
    for snap in history:
        print(f"\n{snap['timestamp']} - {snap['run_label']}")
        for r in snap["results"]:
            print(f"  {r['bot']} | {r['model']}: {r['leaked']}/{r['total']} ({r['leak_rate']}%), {r['critical']} Critical")