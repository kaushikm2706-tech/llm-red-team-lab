import json

with open("results.json", "r", encoding="utf-8") as f:
    all_results = json.load(f)

print(f"Before cleanup: {len(all_results)} total entries")

# Keep only the LATEST entry for each (bot, model, attack_id, trial) combo.
# Prefer non-error entries over error entries when duplicates exist.
best_entries = {}

for entry in all_results:
    key = (entry["bot"], entry["model"], entry["attack_id"], entry["trial"])

    if key not in best_entries:
        best_entries[key] = entry
    else:
        existing = best_entries[key]
        # Replace if current is non-error and existing was error
        if existing["error"] and not entry["error"]:
            best_entries[key] = entry
        # If both are non-error or both are error, keep the later one (already the case since we iterate in order)
        elif existing["error"] == entry["error"]:
            best_entries[key] = entry

cleaned_results = list(best_entries.values())

print(f"After cleanup: {len(cleaned_results)} total entries")

with open("results.json", "w", encoding="utf-8") as f:
    json.dump(cleaned_results, f, indent=2)

print("Done! results.json cleaned and saved.")