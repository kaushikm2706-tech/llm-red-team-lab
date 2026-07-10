from fpdf import FPDF
import json
import os
from datetime import datetime
from fix_suggester import generate_fix_suggestion
import time


def clean_text(text):
    text = text.replace("₹", "Rs.")
    return text.encode("latin-1", "replace").decode("latin-1")


def is_error_suggestion(suggestion):
    """Detects raw error dumps (rate limits, connection errors, etc.)
    so they never appear as-is in the final report."""
    error_markers = [
        "Could not generate suggestion",
        "Error code:",
        "rate_limit_exceeded",
        "Connection error",
        "429",
    ]
    return any(marker in suggestion for marker in error_markers)


def load_json_safe(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def add_section_header(pdf, page_width, title):
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(page_width, 10, title, new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)


def write_attack_summary(pdf, results, label="leaked"):
    bot_names = sorted(set(r["bot"] for r in results))
    for bot_name in bot_names:
        bot_results = [r for r in results if r["bot"] == bot_name]
        count = sum(1 for r in bot_results if r.get(label, False))
        total = len(bot_results)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 8, f"{bot_name}: {count}/{total} attacks succeeded ({label})", new_x="LMARGIN", new_y="NEXT")


def write_detailed_log(pdf, page_width, results, status_field="leaked", question_field="prompt", id_field="attack_id"):
    for r in results:
        status = "LEAKED" if r.get(status_field, False) else "BLOCKED"
        if status_field == "falsely_refused":
            status = "REFUSED" if r.get(status_field, False) else "ANSWERED"

        model_tag = r.get("model", "")
        model_part = f" | {model_tag}" if model_tag else ""

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_x(pdf.l_margin)
        header_line = f"[{status}] {r['bot']}{model_part} - #{r.get(id_field, '?')} ({r.get('category', r.get('expected_topic', ''))})"
        pdf.cell(0, 7, clean_text(header_line), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)

        question_text = r.get(question_field, r.get("question", ""))
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(page_width, 5, clean_text(f"Prompt: {question_text}"))

        reply_preview = r['reply'][:300] + ("..." if len(r['reply']) > 300 else "")
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(page_width, 5, clean_text(f"Reply: {reply_preview}"))

        pdf.ln(3)


def generate_report():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    page_width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, "LLM Red Team Lab", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Unified Security Audit Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)

    # --- Load all result files ---
    print("Loading all result files...")
    single_turn = load_json_safe("results.json")
    multi_turn = load_json_safe("multiturn_results.json")
    indirect = load_json_safe("indirect_injection_results.json")
    mutated = load_json_safe("mutation_results.json")
    usability = load_json_safe("false_refusal_results.json")

    # --- Overall Summary ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 10, "Overall Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)

    if single_turn:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 7, "Single-Turn Attacks:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        write_attack_summary(pdf, single_turn)
        pdf.ln(2)

    if multi_turn:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 7, "Multi-Turn Attacks:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        write_attack_summary(pdf, multi_turn)
        pdf.ln(2)

    if indirect:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 7, "Indirect Injection Attacks:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        write_attack_summary(pdf, indirect)
        pdf.ln(2)

    if mutated:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 7, "Mutated Attacks:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        write_attack_summary(pdf, mutated)
        pdf.ln(2)

    if usability:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 7, "Usability Test (False Refusals):", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        write_attack_summary(pdf, usability, label="falsely_refused")
        pdf.ln(2)

    # --- AI Fix Recommendations (Single-Turn only, as before) ---
    if single_turn:
        add_section_header(pdf, page_width, "Single-Turn Attacks: AI-Generated Fix Recommendations")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(page_width, 5, "Each leaked attack below was individually analyzed to generate a tailored recommendation.")
        pdf.ln(4)

        leaked_results = [r for r in single_turn if r["leaked"]]
        print(f"Generating AI fix suggestions for {len(leaked_results)} leaked single-turn attacks...")

        skipped_count = 0
        for r in leaked_results:
            print(f"  -> Analyzing attack #{r['attack_id']} ({r['bot']})...")
            suggestion = generate_fix_suggestion(
                r["prompt"], r["reply"], r["category"], r.get("severity", "Unknown")
            )
            time.sleep(2)

            if is_error_suggestion(suggestion):
                suggestion = "AI-generated fix suggestion unavailable for this attack (temporary service limit reached during report generation)."
                skipped_count += 1

            model_tag = r.get("model", "")
            model_part = f" | {model_tag}" if model_tag else ""
            header = f"[{r['bot']}{model_part}] Attack #{r['attack_id']} - {r['category']}"

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 7, clean_text(header), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(page_width, 5, clean_text(suggestion))
            pdf.ln(3)

        if skipped_count > 0:
            print(f"Note: {skipped_count} fix suggestions were unavailable due to rate limits.")

    # --- Detailed Logs, one section per attack type ---
    if single_turn:
        add_section_header(pdf, page_width, "Single-Turn Attacks: Detailed Log")
        print(f"Writing single-turn log ({len(single_turn)} entries)...")
        write_detailed_log(pdf, page_width, single_turn)

    if multi_turn:
        add_section_header(pdf, page_width, "Multi-Turn Attacks: Detailed Log")
        print(f"Writing multi-turn log ({len(multi_turn)} entries)...")
        write_detailed_log(pdf, page_width, multi_turn)

    if indirect:
        add_section_header(pdf, page_width, "Indirect Injection Attacks: Detailed Log")
        print(f"Writing indirect injection log ({len(indirect)} entries)...")
        write_detailed_log(pdf, page_width, indirect)

    if mutated:
        add_section_header(pdf, page_width, "Mutated Attacks: Detailed Log")
        print(f"Writing mutated attacks log ({len(mutated)} entries)...")
        write_detailed_log(pdf, page_width, mutated)

    if usability:
        add_section_header(pdf, page_width, "Usability Test: Detailed Log")
        print(f"Writing usability test log ({len(usability)} entries)...")
        write_detailed_log(pdf, page_width, usability, status_field="falsely_refused", question_field="question", id_field="question_id")

    print("Saving PDF...")
    pdf.output("security_report.pdf")
    print("Saved successfully.")
    return "security_report.pdf"


if __name__ == "__main__":
    path = generate_report()
    print(f"Report saved to {path}")