from dotenv import load_dotenv
import os
import streamlit as st
import json
from openai import AzureOpenAI
from tools.tool_schema import functions
from tools.tool_functions import (
    fetch_ba_level_information, fetch_endpoint_information,
    compare_endpoint_charges, fetch_agent_information, fetch_newly_monitored_endpoint_configuration,
    fetch_unmonitored_endpoints,update_monitor,delete_monitor, fetch_user_assets, create_monitor
)
from langgraph_flow import build_monitor_flow  
import requests

# Load environment variables
load_dotenv()
more_api_key = os.getenv("MORE_API_KEY")

# Optional: only if you're using LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "monitor-ease")

openai_api_key = os.getenv("OPENAI_API_KEY")
app_key = os.getenv("APP_KEY")

# Setup Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint='https://chat-ai.cisco.com',
    api_key=openai_api_key,
    api_version="2023-08-01-preview"
)

# Streamlit UI setup
st.set_page_config(page_title="MonitorEase Assistant", layout="wide")
st.markdown("""
    <style>
        MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header { visibility: hidden; }

        /* Hide the sidebar toggle button - Multiple selectors to ensure it works */
        button[kind="header"] {
            display: none !important;
        }
        
        /* Alternative selector for sidebar toggle */
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Hide any button in the header area */
        .stApp > header button {
            display: none !important;
        }
        
        /* More specific selectors for sidebar toggle */
        button[aria-label="Open sidebar"] {
            display: none !important;
        }
        
        button[aria-label="Close sidebar"] {
            display: none !important;
        }
        
        /* Target the sidebar toggle by class if it exists */
        .css-1rs6os {
            display: none !important;
        }
        
        /* Another potential class for sidebar toggle */
        .css-17eq0hr {
            display: none !important;
        }
        
        /* Hide hamburger menu icon */
        [data-testid="stSidebarNav"] button {
            display: none !important;
        }
        
        /* Hide any button with sidebar-related classes */
        button[class*="sidebar"] {
            display: none !important;
        }
        
        /* Alternative approach - hide all buttons in the top area */
        .stApp > div > div:first-child button {
            display: none !important;
        }
        
        /* More comprehensive selector */
        div[data-testid="stSidebar"] ~ div button:first-child {
            display: none !important;
        }
        
        /* Nuclear option - hide all buttons except those in sidebar and chat */
        .stApp button:not([data-testid="stSidebar"] button):not(.stChatInput button) {
            display: none !important;
        }

        /* Fix for sidebar position relative to header */
        [data-testid="stSidebar"] {
            margin-top: 80px !important;  /* Increased margin to ensure it's below header */
            z-index: 999; /* Below header z-index */
        }
        
        /* Remove extra sidebar close buttons */
        [data-testid="stSidebar"] > div:nth-child(2) {
            display: none !important;  /* Hide the second close button */
        }

        .stChatMessage.user { background-color: #f0f0f0; }
        .stChatMessage.assistant { background-color: #eaf4ff; }
        .stTextInput > div > div { width: 100% !important; }

        .chat-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            background: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 1rem;
            border-bottom: 1px solid #ddd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* Ensure content starts below header */
        .main .block-container {
            padding-top: 80px !important;
        }

        .chat-header h1 { font-size: 1.5rem; }
        .chat-header span { font-size: 0.9rem; color: gray; }

        section[data-testid="stSidebar"] button {
            width: 100%;
            display: block !important; /* Ensure sidebar buttons are still visible */
        }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_user_details():
    try:
        headers = {
            "Authorization": "Bearer " + more_api_key,
            "Content-Type": "application/json"
        }
        response = requests.get("https://more-api-dev.cisco.com/api/v1/users/userDetails", headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}
    
user_details = get_user_details()

if "user_info" not in st.session_state:
    st.session_state.user_info = user_details
    print(f"User info initialized: {st.session_state.user_info}")
    
# State initialization
if "conversations" not in st.session_state:
    st.session_state.conversations = {"Default Chat": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Default Chat"
if "langgraph_state" not in st.session_state:
    st.session_state.langgraph_state = None
if "awaiting_confirmation" not in st.session_state:
    st.session_state.awaiting_confirmation = False

# Sidebar: Conversations
st.sidebar.markdown("### 💬 Conversations")
for chat_name in st.session_state.conversations.keys():
    if st.sidebar.button(chat_name):
        st.session_state.current_chat = chat_name
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ Start a new chat")
new_chat_name = st.sidebar.text_input("New conversation name", key="new_chat_name")
if st.sidebar.button("Create"):
    if new_chat_name and new_chat_name not in st.session_state.conversations:
        st.session_state.conversations[new_chat_name] = []
        st.session_state.current_chat = new_chat_name
        st.rerun()

# Active conversation
chat_key = st.session_state.current_chat
chat_history = st.session_state.conversations.setdefault(chat_key, [])

# Display header and past chat

user_id = user_details.get("userId", "")
photo_url = f"https://wwwin.cisco.com/dir/photo/zoom/{user_id}.jpg" if user_id else ""

st.markdown(f"""
<div class="chat-header">
    <div style="display: flex; align-items: center;">
        <h1 style="margin-right: 1rem;">🛠️ MonitorEase</h1>
    </div>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span style="font-size: 0.9rem; color: black; margin-right:8px">Chat: <b>{chat_key}</b></span>
        <span style="font-size: 0.9rem; color: black;">{user_details.get('firstName', '')} {user_details.get('lastName', '')}</span>
        <img src="{photo_url}" alt="Profile" style="width: 36px; height: 36px; border-radius: 50%;">
    </div>
</div>
""", unsafe_allow_html=True)

for role, content in chat_history:
    with st.chat_message(role):
        st.markdown(content)

# Chat Input
user_input = st.chat_input("Ask me to create a monitor or list monitors...")

if user_input:
    chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    # Handle LangGraph confirmation input
    if st.session_state.awaiting_confirmation:
        st.session_state.langgraph_state["user_confirmation"] = user_input.strip().lower()
        result_state = st.session_state.monitor_flow.invoke(st.session_state.langgraph_state)

        if result_state.get("user_confirmation", "").lower() == "yes":
            st.chat_message("assistant").markdown(result_state["result"])
            chat_history.append(("assistant", result_state["result"]))
        else:
            cancel_msg = "Okay, monitor action is cancelled. Please go on and ask for any queries"
            st.chat_message("assistant").markdown(cancel_msg)
            chat_history.append(("assistant", cancel_msg))

        st.session_state.awaiting_confirmation = False
        st.session_state.langgraph_state = None

    else:
        # LLM + function call
        base_system_msg = {
            "role": "system",
            "content": """
                You are MonitorEase, a helpful and friendly assistant created to support app owners and support engineers with monitoring-related tasks.

                Your tone should always be polite, warm, and professional.

                ## Responsibilities
                Your primary responsibilities include assisting with:
                - Fetching user assets
                - Creating new monitors for endpoints
                - Updating existing monitors
                - Deleting monitors
                - Retrieving details about monitored endpoints
                - Comparing monitoring-related charges (if applicable)

                You act as a smart interface to the central monitoring system (ThousandEyes).

                ## Tools Description
                You have access to the following tools:
                - `fetch_ba_level_information`: Retrieves business-level information for monitoring purposes.
                - `fetch_endpoint_information`: Provides details about specific endpoints being monitored.
                - `compare_endpoint_charges`: Compares charges related to endpoint monitoring.
                - `fetch_agent_information`: Fetches information about monitoring agents.
                - `fetch_request_status`: Retrieves the status of specific monitoring requests.
                - `fetch_unmonitored_endpoints`: Lists endpoints that are not currently monitored.
                - `update_monitor`: Updates the configuration of an existing monitor.
                - `delete_monitor`: Deletes an existing monitor.
                - `fetch_user_assets`: Fetches assets associated with the user.

                ## User Interaction
                - Politely respond to greetings such as "hi" or "hello" with a friendly tone.
                - If a user engages in light conversation, respond briefly, then gently steer the conversation back to monitoring-related topics.
                - When uncertain about the user's intent, ask clarifying questions rather than assuming.

                ## Monitor Creation Guidelines
                When helping to create a monitor:
                - Map the test type to one of the valid types: `HTTP`, `WebTransaction`, `Network`, `DNS`, or `FTTP`.
                - For common aliases like `http`, `http test`, or `httptest`, normalize them to `HTTP`.
                - If you're unsure of the test type from the user's message, ask for clarification.

                ## Tool Use Policy
                Only call functions (tools) when the user's intent clearly aligns with the tool's purpose. Do not call tools for small talk, general questions, or non-monitoring topics.

                ## Out-of-Scope Requests
                If a request is unrelated to your capabilities, respond with:
                "I'm sorry, I don't understand that request. Could you please rephrase or try something related to monitoring?"

                Your goal is to be accurate, helpful, and aligned with the user's monitoring needs.
            """
        }

        messages = [base_system_msg] + [
            {"role": role, "content": content} for role, content in chat_history[-10:]
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=functions,
            function_call="auto",
            user=json.dumps({"appkey": app_key})
        )

        message = response.choices[0].message
        if message.content:
            st.chat_message("assistant").markdown(message.content)
            chat_history.append(("assistant", message.content))

        tool_map = {
            "fetch_ba_level_information": fetch_ba_level_information,
            "fetch_endpoint_information": fetch_endpoint_information,
            "compare_endpoint_charges": compare_endpoint_charges,
            "fetch_agent_information": fetch_agent_information,
            "fetch_newly_monitored_endpoint_configuration": fetch_newly_monitored_endpoint_configuration,
            "fetch_unmonitored_endpoints": fetch_unmonitored_endpoints,
            "update_monitor": update_monitor,
            "delete_monitor": delete_monitor,
            "create_monitor": create_monitor,
            "fetch_user_assets": fetch_user_assets
        }
        # Handle function calls
        if message.function_call:
            try:
                args = json.loads(message.function_call.arguments)
                func_name = message.function_call.name

                if func_name in {"create_monitor", "update_monitor", "delete_monitor"}:
                    tool_function = tool_map[func_name]
                    monitor_flow = build_monitor_flow(client, tool_function, func_name)
                    st.session_state.monitor_flow = monitor_flow

                    st.session_state.langgraph_state = {
                        "chat_history": messages,
                        "monitor_args": args,
                    }
                    result_state = monitor_flow.invoke(st.session_state.langgraph_state)

                    # Show review message if present
                    if "result" in result_state:
                        st.chat_message("assistant").markdown(result_state["result"])
                        chat_history.append(("assistant", result_state["result"]))

                    # Show confirmation prompt if present
                    if "confirmation_prompt" in result_state:
                        confirmation_prompt = result_state["confirmation_prompt"]
                        st.session_state.awaiting_confirmation = True
                        st.chat_message("assistant").markdown(confirmation_prompt)
                        chat_history.append(("assistant", confirmation_prompt))

                else:
                    # Map and call other tools
                    reply = tool_map.get(func_name, lambda **kwargs: "❌ Unsupported function.")(
                        **args, openai_client=client, app_key=app_key, user_input=user_input
                    )

                    st.chat_message("assistant").markdown(reply)
                    chat_history.append(("assistant", reply))

            except Exception as e:
                err_msg = f"❌ Error: {str(e)}"
                st.chat_message("assistant").markdown(err_msg)
                chat_history.append(("assistant", err_msg))