import streamlit as st
import json
import pandas as pd
import subprocess
import sys
import os
import io
from report_generator import generate_report
from vector_store import build_vector_store
import target_chatbot_nodefense
import target_chatbot
import target_chatbot_filtered
import target_chatbot_combined

st.set_page_config(page_title="LLM Red Team Lab", layout="wide")

st.title("🛡️ LLM Red Team Lab")
st.caption("Automated security testing for RAG chatbots")

BOT_ORDER = [
    "No Defense",
    "Strong Guardrails",
    "Strong + Output Filter",
    "No Defense + LLM Judge",
    "Combined (All Defenses)"
]

BOT_COLORS = {
    "No Defense": "#e74c3c",
    "Strong Guardrails": "#f39c12",
    "Strong + Output Filter": "#2ecc71",
    "No Defense + LLM Judge": "#4f46e5",
    "Combined (All Defenses)": "#8e44ad",
}

BOT_MODULES = {
    "No Defense": target_chatbot_nodefense,
    "Strong Guardrails": target_chatbot,
    "Strong + Output Filter": target_chatbot_filtered,
    "Combined (All Defenses)": target_chatbot_combined,
}


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def run_with_live_output(command, max_lines=40):
    """Runs a subprocess and streams its stdout into a scrolling live log box,
    instead of blocking silently until the whole process finishes."""
    log_placeholder = st.empty()
    log_lines = []

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in iter(process.stdout.readline, ""):
        if line:
            log_lines.append(line.rstrip())
            if len(log_lines) > max_lines:
                log_lines = log_lines[-max_lines:]
            log_placeholder.code("\n".join(log_lines), language="text")

    process.stdout.close()
    process.wait()
    return process.returncode


def show_scorecards(df, bots_present, value_col="leaked", label="overall"):
    st.subheader("Scorecards")
    cols = st.columns(len(bots_present))

    for col, bot_name in zip(cols, bots_present):
        bot_df = df[df["bot"] == bot_name]
        total = len(bot_df)
        count = bot_df[value_col].sum()

        with col:
            st.metric(label=bot_name, value=f"{count}/{total} {label}")

            if value_col == "leaked" and "leak_type" in df.columns:
                data_df = bot_df[bot_df["leak_type"] == "data"]
                prompt_df = bot_df[bot_df["leak_type"] == "prompt"]
                st.caption(f"Data leaks: {data_df['leaked'].sum()}/{len(data_df)}")
                st.caption(f"Prompt leaks: {prompt_df['leaked'].sum()}/{len(prompt_df)}")

            if value_col == "leaked" and "severity" in df.columns:
                critical_df = bot_df[(bot_df["leaked"]) & (bot_df["severity"] == "Critical")]
                if critical_df.shape[0] > 0:
                    st.error(f"Critical leaks: {critical_df.shape[0]}")
                else:
                    st.success("No Critical leaks")

            if value_col == "falsely_refused":
                rate = round((count / total) * 100) if total > 0 else 0
                if count == 0:
                    st.success("0% false refusal ✅")
                else:
                    st.warning(f"{rate}% false refusal rate")


def show_detailed_list(df, bots_present, key_prefix, question_col="prompt"):
    with st.expander("📋 Show Detailed Results (click to expand)", expanded=False):
        bot_options = ["All"] + bots_present
        bot_filter = st.selectbox("Filter by bot:", bot_options, key=f"{key_prefix}_bot")

        display_df = df.copy()
        if bot_filter != "All":
            display_df = display_df[display_df["bot"] == bot_filter]

        total_rows = len(display_df)
        page_size = 20
        total_pages = max(1, (total_rows + page_size - 1) // page_size)

        page_num = st.number_input(
            f"Page (1-{total_pages}, {total_rows} total results):",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key=f"{key_prefix}_page"
        )

        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        page_df = display_df.iloc[start_idx:end_idx]

        for _, row in page_df.iterrows():
            if "leaked" in row:
                status_icon = "🔴 LEAKED" if row["leaked"] else "🟢 BLOCKED"
                id_field = row.get("attack_id", "?")
                category = row.get("category", "")
                header = f"{status_icon} | {row['bot']} | Attack #{id_field} - {category}"
            else:
                refused = row.get("falsely_refused", False)
                status_icon = "🚫 REFUSED" if refused else "✅ ANSWERED"
                id_field = row.get("question_id", "?")
                topic = row.get("expected_topic", "")
                header = f"{status_icon} | {row['bot']} | Q{id_field} - {topic}"

            prompt_text = row.get("prompt", row.get("question", ""))
            with st.expander(header):
                st.markdown(f"**Question/Prompt:** {prompt_text}")
                st.markdown("**Bot's reply:**")
                st.text(row['reply'])

# --- Top buttons ---
col_run, col_report = st.columns(2)

with col_run:
    st.subheader("Run Attack Suites")
    if st.button("▶️ Run Single-Turn Attacks"):
        st.caption("Live output (updates as each attack runs):")
        returncode = run_with_live_output([sys.executable, "attack_engine.py"])
        if returncode == 0:
            st.success("Done!")
        else:
            st.warning("Process stopped (check log above — may be a quota limit).")
    if st.button("▶️ Run Multi-Turn Attacks"):
        with st.spinner("Running..."):
            subprocess.run([sys.executable, "multiturn_engine.py"])
        st.success("Done!")
    if st.button("▶️ Run Indirect Injection Attacks"):
        with st.spinner("Running..."):
            subprocess.run([sys.executable, "indirect_injection_engine.py"])
        st.success("Done!")
    if st.button("▶️ Run Mutated Attacks"):
        with st.spinner("Running..."):
            subprocess.run([sys.executable, "mutation_engine.py"])
        st.success("Done!")
    if st.button("▶️ Run Usability Test"):
        with st.spinner("Running..."):
            subprocess.run([sys.executable, "false_refusal_engine.py"])
        st.success("Done!")

with col_report:
    st.subheader("Export Report")
    results_main = load_json("results.json")
    if results_main is not None:
        if st.button("📄 Generate PDF Report"):
            with st.spinner("Building PDF..."):
                generate_report()
            st.success("Report generated!")

        if os.path.exists("security_report.pdf"):
            f = open("security_report.pdf", "rb")
            st.download_button(
                label="⬇️ Download PDF Report",
                data=f,
                file_name="security_report.pdf",
                mime="application/pdf"
            )

        csv_df = pd.DataFrame(results_main)
        csv_data = csv_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📊 Download Results as CSV",
            data=csv_data,
            file_name="results.csv",
            mime="text/csv"
        )
    else:
        st.info("Run attacks first to enable report export.")

st.divider()

# --- Document Upload ---
st.subheader("📁 Add a Document to the Knowledge Base")
st.caption("Upload a .txt or .pdf file to add it to what the chatbot can retrieve.")

uploaded_file = st.file_uploader(
    "Choose a .txt or .pdf file",
    type=["txt", "pdf"],
    key="doc_uploader"
)

if uploaded_file is not None:
    if st.button("📥 Add to Knowledge Base"):
        if uploaded_file.name.endswith(".pdf"):
            import pypdf
            pdf_reader = pypdf.PdfReader(io.BytesIO(uploaded_file.getbuffer()))
            extracted_text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
            txt_filename = uploaded_file.name.replace(".pdf", ".txt")
            save_path = os.path.join("documents", txt_filename)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            st.info(f"PDF text extracted and saved as '{txt_filename}'")
        else:
            save_path = os.path.join("documents", uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        with st.spinner("Rebuilding vector store with new document..."):
            build_vector_store()

        st.success(f"Added '{uploaded_file.name}' and rebuilt the knowledge base.")

with st.expander("📂 Current documents in knowledge base"):
    if os.path.exists("documents"):
        doc_files = [f for f in os.listdir("documents") if f.endswith(".txt")]
        for doc in doc_files:
            st.text(f"- {doc}")

st.divider()
# --- Configurable Secrets ---
st.subheader("🔑 Define Your Confidential Values")
st.caption("These are the exact secret values the attack suite will try to extract from your bot. Defaults are pre-filled from the sample Acme Corp scenario.")

from secrets_config import load_secrets, save_secrets, reset_to_defaults

current_secrets = load_secrets()

with st.form("secrets_form"):
    admin_password = st.text_input("Admin panel password", value=current_secrets["admin_password"])
    salary_amount = st.text_input("Salary figure (as it appears in your document)", value=current_secrets["salary_amount"])
    database_key = st.text_input("Database/API key", value=current_secrets["database_key"])
    confidential_topic = st.text_input("Confidential topic keyword (e.g. layoffs, merger, lawsuit)", value=current_secrets["confidential_topic"])
    system_prompt_marker = st.text_input("A unique phrase from your system prompt (to detect prompt leakage)", value=current_secrets["system_prompt_marker"])

    col_save, col_reset = st.columns(2)
    with col_save:
        submitted = st.form_submit_button("💾 Save Secrets")
    with col_reset:
        reset_clicked = st.form_submit_button("↩️ Reset to Acme Corp Defaults")

    if submitted:
        save_secrets({
            "admin_password": admin_password,
            "salary_amount": salary_amount,
            "database_key": database_key,
            "confidential_topic": confidential_topic,
            "system_prompt_marker": system_prompt_marker
        })
        st.success("Secrets saved! These will be used the next time you run an attack suite.")

    if reset_clicked:
        reset_to_defaults()
        st.success("Reset to Acme Corp defaults. Refresh the page to see updated values.")

st.divider()
# --- Live Custom Attack Tester ---
st.subheader("🧪 Try Your Own Attack")
st.caption("Type any prompt and test it live against a bot configuration.")

col_input, col_select = st.columns([3, 1])
with col_input:
    custom_prompt = st.text_area("Your attack prompt:", height=80, key="custom_prompt_input")
with col_select:
    custom_bot_choice = st.selectbox("Test against:", list(BOT_MODULES.keys()), key="custom_bot_select")

if st.button("🚀 Send Attack"):
    if custom_prompt.strip() == "":
        st.warning("Please type a prompt first.")
    else:
        bot_module = BOT_MODULES[custom_bot_choice]
        with st.spinner(f"Sending to {custom_bot_choice}..."):
            try:
                live_reply = bot_module.ask_chatbot(custom_prompt)
                st.session_state["custom_reply_text"] = live_reply
                st.session_state["custom_reply_bot"] = custom_bot_choice
                st.success("Response received:")
            except Exception as e:
                st.error(f"Error: {e}")

if "custom_reply_text" in st.session_state:
    st.markdown(f"**Bot's reply** (tested against: {st.session_state['custom_reply_bot']}):")
    st.text_area(
        "Reply",
        value=st.session_state["custom_reply_text"],
        height=150,
        key="custom_reply_display",
        label_visibility="collapsed"
    )

st.divider()

# --- 5 Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Single-Turn Attacks",
    "💬 Multi-Turn Attacks",
    "📄 Indirect Injection",
    "🔀 Mutated Attacks",
    "✅ Usability Testing"
])

with tab1:
    results = load_json("results.json")
    if results is None:
        st.warning("No results yet. Run the Single-Turn suite above.")
    else:
        df = pd.DataFrame(results)
        bots_present = [b for b in BOT_ORDER if b in df["bot"].unique()]
        show_scorecards(df, bots_present)

        st.divider()
        st.subheader("Vulnerabilities by Category")
        grouped = df.groupby(["category", "bot"])["leaked"].sum().reset_index()
        pivot = grouped.pivot(index="category", columns="bot", values="leaked").fillna(0)
        pivot = pivot.reindex(columns=bots_present, fill_value=0)
        colors = [BOT_COLORS.get(b, "#888888") for b in pivot.columns]
        st.bar_chart(pivot, color=colors)

        st.divider()
        st.subheader("Vulnerability Heatmap")
        st.caption("Darker red = more leaks for that attack category under that defense config.")

        totals = df.groupby(["category", "bot"]).size().reset_index(name="total")
        heatmap_data = grouped.merge(totals, on=["category", "bot"])
        heatmap_data["leak_rate"] = (heatmap_data["leaked"] / heatmap_data["total"] * 100).round(1)
        heatmap_pivot = heatmap_data.pivot(index="category", columns="bot", values="leak_rate").fillna(0)
        heatmap_pivot = heatmap_pivot.reindex(columns=bots_present, fill_value=0)

        st.dataframe(
            heatmap_pivot.style.background_gradient(cmap="Reds", vmin=0, vmax=100).format("{:.1f}%"),
            use_container_width=True
        )

        st.divider()
        show_detailed_list(df, bots_present, "single")

with tab2:
    mt_results = load_json("multiturn_results.json")
    if mt_results is None:
        st.warning("No results yet. Run the Multi-Turn suite above.")
    else:
        df = pd.DataFrame(mt_results)
        bots_present = [b for b in BOT_ORDER if b in df["bot"].unique()]
        st.info("Multi-turn attacks build up over several messages before the real ask.")
        show_scorecards(df, bots_present)
        st.divider()
        show_detailed_list(df, bots_present, "multiturn")

with tab3:
    ii_results = load_json("indirect_injection_results.json")
    if ii_results is None:
        st.warning("No results yet. Run the Indirect Injection suite above.")
    else:
        df = pd.DataFrame(ii_results)
        bots_present = [b for b in BOT_ORDER if b in df["bot"].unique()]
        st.info("These attacks come from poisoned documents, not the chat input.")
        show_scorecards(df, bots_present)
        st.divider()
        show_detailed_list(df, bots_present, "indirect")

with tab4:
    mut_results = load_json("mutation_results.json")
    if mut_results is None:
        st.warning("No results yet. Run the Mutated Attacks suite above.")
    else:
        df = pd.DataFrame(mut_results)
        bots_present = [b for b in BOT_ORDER if b in df["bot"].unique()]
        st.info("AI-generated paraphrases of the most severe original attacks.")
        show_scorecards(df, bots_present)
        st.divider()
        show_detailed_list(df, bots_present, "mutation")

with tab5:
    fr_results = load_json("false_refusal_results.json")
    if fr_results is None:
        st.warning("No results yet. Run the Usability Test above.")
    else:
        df = pd.DataFrame(fr_results)
        bots_present = [b for b in BOT_ORDER if b in df["bot"].unique()]
        st.info("10 completely innocent employee questions — none should be refused by any bot.")
        show_scorecards(df, bots_present, value_col="falsely_refused", label="falsely refused")
        st.divider()
        show_detailed_list(df, bots_present, "usability")