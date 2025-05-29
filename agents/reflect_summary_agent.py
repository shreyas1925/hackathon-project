import json
from dotenv import load_dotenv
import os

load_dotenv()
app_key = os.getenv("APP_KEY")

def reflect_and_summarize(openai_client, chat_history):
    messages = [{"role": "system", "content": "Reflect and summarize the user's request for monitor creation."}]
    messages += chat_history[-10:]
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        user=json.dumps({"appkey": app_key})
    )
    return response.choices[0].message.content
