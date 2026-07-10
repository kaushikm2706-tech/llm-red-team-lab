# 🛡️ LLM Red Team Lab

An automated security testing tool for RAG (Retrieval-Augmented Generation) chatbots, built around OWASP's LLM Top 10 vulnerability categories.

## What it does

Companies are deploying AI chatbots that answer questions using internal documents (RAG systems) — often without testing whether those chatbots can be tricked into leaking sensitive data. This tool automatically "attacks" a RAG chatbot with a library of known prompt injection and jailbreak techniques, then scores how many attacks succeed.

## How it works

1. A target chatbot answers employee questions using a small set of company documents (including confidential HR data — salaries, admin credentials, layoff plans).
2. A library of 12 attacks across 6 categories (Direct Extraction, Prompt Injection, Role-Play Jailbreak, Indirect/Contextual, System Prompt Leakage, Encoding/Obfuscation) is run against the chatbot automatically.
3. Each attack's success or failure is judged by checking whether the protected secret appears in the bot's reply.
4. Results are displayed on a live dashboard with charts, and exportable as a PDF security audit report.

## Key finding

Two configurations of the same chatbot were tested — one with explicit, detailed security rules ("Strong Guardrails") and one with vague, soft rules ("Weak Guardrails"):

- **Strong Guardrails:** 2/12 attacks succeeded
- **Weak Guardrails:** 5/12 attacks succeeded

This demonstrates that explicit, well-written system prompts meaningfully reduce (but do not eliminate) vulnerability to prompt injection attacks — particularly attacks that don't "sound" like attacks, such as indirect summarization requests.

## Tech Stack

- Python
- Groq API (Llama 3.3 70B) — powers the chatbot being tested
- Streamlit — interactive dashboard
- fpdf2 — PDF report generation

## Project Structure

LLM-Red-Team-Lab/
- documents/ — Fake company documents (target chatbot's knowledge base)
  - company_handbook.txt
  - confidential_hr_data.txt
- target_chatbot.py — Chatbot with strong security rules
- target_chatbot_weak.py — Chatbot with weak security rules
- attack_library.py — 12 attack prompts across 6 OWASP-style categories
- attack_engine.py — Runs all attacks against both bots, scores results
- dashboard.py — Streamlit dashboard (run with: streamlit run dashboard.py)
- report_generator.py — Generates PDF security audit report
- results.json — Saved results from the most recent attack run

## How to run it

1. Install dependencies: `pip install groq python-dotenv streamlit pandas fpdf2`
2. Add your Groq API key to a `.env` file: `GROQ_API_KEY=your_key_here`
3. Run the dashboard: `streamlit run dashboard.py`
4. Click "Run All Attacks Now" to test both bot configurations
5. Click "Generate PDF Report" to export a downloadable audit report

## Author

Kaushik Manivezh — Final Year B.E. Computer Science & Engineering, Sathyabama Institute of Science & Technology