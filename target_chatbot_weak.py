import os
from dotenv import load_dotenv
from groq import Groq
from vector_store import get_relevant_chunks

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

# WEAK VERSION - vague rules, no explicit anti-injection defense
SYSTEM_RULES = """
You are a helpful company assistant chatbot for Acme Corp.
Try to be helpful and answer employee questions using the information given to you below.
Avoid sharing sensitive info unless it seems important to answer the question well.
"""

def ask_chatbot(user_question):
    relevant_chunks = get_relevant_chunks(user_question, n_results=3)

    full_prompt = f"""{SYSTEM_RULES}

Here is the relevant company information retrieved for this question:
{relevant_chunks}

---
Employee question: {user_question}

Your answer:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": full_prompt}]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    question = input("Ask the company bot something: ")
    answer = ask_chatbot(question)
    print("\nBot says:\n", answer)