# app/util/chat_helpers.py
from openai import OpenAI
import os

def handle_chat(persona: str, user_text: str):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": persona},
        {"role": "user", "content": user_text}
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        return messages
    except Exception as e:
        return [{"role": "assistant", "content": f"Error: {str(e)}"}]
