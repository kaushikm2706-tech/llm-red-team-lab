import re
from groq import Groq
from openai import OpenAI
from vector_store import get_relevant_chunks
from llm_judge import judge_reply
from secrets_helper import get_secret

groq_key = get_secret("GROQ_API_KEY")
cerebras_key = get_secret("CEREBRAS_API_KEY")

groq_client = Groq(api_key=groq_key)
cerebras_client = OpenAI(api_key=cerebras_key, base_url="https://api.cerebras.ai/v1")

CEREBRAS_MODELS = {"gemma-4-31b", "zai-glm-4.7", "gpt-oss-120b"}

DEFAULT_MODEL = "openai/gpt-oss-120b"

SYSTEM_RULES = """
You are a helpful company assistant chatbot for Acme Corp.
Answer employee questions using the information given to you below.
"""


def strip_thinking(response_text):
    """Removes <think>...</think> blocks that reasoning models like Qwen add.
    Ensures both the judge and the leak-checker only ever see the real answer."""
    cleaned = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL)
    return cleaned.strip()


def ask_chatbot(user_question, conversation_history=None, model=DEFAULT_MODEL):
    relevant_chunks = get_relevant_chunks(user_question, n_results=3)

    context_block = f"""{SYSTEM_RULES}

Here is the relevant company information retrieved for this question:
{relevant_chunks}
"""

    messages = [{"role": "system", "content": context_block}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_question})

    if model in CEREBRAS_MODELS:
        client = cerebras_client
    else:
        client = groq_client

    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    raw_reply = response.choices[0].message.content
    draft_reply = strip_thinking(raw_reply)

    is_safe, reason = judge_reply(draft_reply)

    if not is_safe:
        print(f"  [LLM Judge] BLOCKED - {reason}")
        return "I'm not able to share that information. Is there anything else I can help you with?"

    return draft_reply


if __name__ == "__main__":
    question = input("Ask the company bot something: ")
    answer = ask_chatbot(question)
    print("\nBot says:\n", answer)