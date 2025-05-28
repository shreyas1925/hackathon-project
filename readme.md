# 🛠️ MonitorEase Assistant

MonitorEase Assistant is a Streamlit-based AI-powered tool that assists application owners and support engineers with tasks related to monitoring. It uses OpenAI's GPT model (via Azure OpenAI) and LangGraph flows to understand natural language queries and execute relevant actions like:

- Creating monitoring tests
- Fetching Business Application (BA) level info
- Comparing endpoint charges
- Retrieving asset or agent data
- Fetching request status

---

## 📦 Features

- 💬 **Chat Interface**: User-friendly chat powered by Streamlit.
- 🤖 **LLM-Powered Intelligence**: Uses Azure OpenAI's GPT-4o-mini for natural language understanding.
- 🔄 **LangGraph Flow**: Handles complex workflows like monitor creation with user confirmation.
- 🛠️ **Tool Execution**: Dynamically calls backend functions based on user intent.
- 🔒 **Secure Access**: Uses API keys and dotenv for environment security.

---

## 🧰 Tech Stack

- **Frontend/UI**: Streamlit
- **Backend Logic**: Python, LangGraph
- **LLM**: Azure OpenAI (GPT-4o-mini)
- **Environment Management**: Python-dotenv
- **API Clients**: Requests

---

## 🛠️ Setup & Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/your-org/monitorease-assistant.git
    cd monitorease-assistant
    ```

2. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Create a `.env` file and add**:
    ```plaintext
    OPENAI_API_KEY=your_azure_openai_api_key
    APP_KEY=your_application_key
    MORE_API_KEY=more_api_key
    MORE_MONGO_URI=more_mongo_uri
    ```

4. **Run the app**:
    ```bash
    streamlit run app.py
    ```

---

## 💡 Usage

1. Launch the app and open the URL shown in your terminal.
2. Type queries like:
    - `"Create a monitor for example.com"`
    - `"List the assets for CEC ID abc123"`
    - `"Compare endpoint charges for XYZ"`

The assistant will respond or prompt for confirmation as needed.

---


## ✅ Supported Functions

| Function                     | Description                                   |
|------------------------------|-----------------------------------------------|
| `create_monitor`             | Creates a ThousandEyes monitoring test       |
| `fetch_ba_level_information` | Retrieves Business Application info          |
| `fetch_endpoint_information` | Fetches endpoint monitoring config           |
| `compare_endpoint_charges`   | Compares cost details of endpoints           |
| `fetch_agent_information`    | Lists active/available agents                |
| `fetch_request_status`       | Status of previous monitor requests          |
| `fetch_user_assets`          | Lists ThousandEyes assets for a user         |

---

## 🔐 Security Notes

- Ensure `.env` is not committed to version control.
- Use secure vaults like Conjur for production secrets.

---

## 🙋‍♂️ Maintainers

- Shreyas Shettigar
- Vishwanath Asundi
- Sudheshna Vustipalli

---

## 📜 License

This project is internal to Cisco and governed by internal usage policies.
