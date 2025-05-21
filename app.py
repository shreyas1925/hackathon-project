from dotenv import load_dotenv
import os
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
more_api_key = os.getenv("MORE_API_KEY")
more_mongo_uri = os.getenv("MORE_MONGO_URI")
app_key = os.getenv("APP_KEY")

from openai import AzureOpenAI
import streamlit as st
import json
from tools.tool_schema import functions
from tools.tool_functions import create_monitor, fetch_ba_level_information, fetch_endpoint_information

# Setup
client = AzureOpenAI(azure_endpoint='https://chat-ai.cisco.com', api_key=openai_api_key, api_version="2023-08-01-preview")

st.set_page_config(page_title="MonitorEase Assistant")
st.title("🛠️ MonitorEase: Observability")

# Session memory
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for role, content in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(content)

user_input = st.chat_input("Ask me to create a monitor or list monitors...")

if user_input:
    st.session_state.chat_history.append(("user", user_input))
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    # First LLM call
    base_system_msg = {
        "role": "system",
        "content": """You are MonitorEase, a helpful assistant that helps app owners and support engineers.
                When the user asks to create a monitor, always map the test type to one of: HTTP, WebTransaction, Network, DNS, FTTP.
                If the user says http, httptest, or similar, use HTTP.
                If unsure, ask the user to clarify."""
    }

    messages = [base_system_msg] + st.session_state.messages[-10:]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        functions=functions,
        function_call="auto",
        user=json.dumps({"appkey": app_key})
    )
    message = response.choices[0].message
    st.session_state.messages.append({"role": "assistant", "content": message.content or ""})

    if message.function_call:
        args = json.loads(message.function_call.arguments)
        name = message.function_call.name

        if name == "create_monitor":
            reply = create_monitor(**args)
        elif name == "fetch_ba_level_information":
            reply = fetch_ba_level_information(**args, user_input=user_input, openai_client=client, app_key=app_key)
        elif name == "fetch_endpoint_information":
            reply = fetch_endpoint_information(**args, user_input=user_input, openai_client=client, app_key=app_key)
        else:
            reply = "Sorry, at this point of time I do not support this request"

        st.session_state.chat_history.append(("assistant", reply))
        st.session_state.messages.append({"role": "function", "name": name, "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

    else:
        reply = message.content or "🤖 Sorry, I didn't get that."
        st.session_state.chat_history.append(("assistant", reply))
        with st.chat_message("assistant"):
            st.markdown(reply)
