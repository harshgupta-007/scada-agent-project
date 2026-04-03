# SCADA AI Agent & Dashboard - Comprehensive Documentation

## 1. Project Overview
The **SCADA Summary Agent & Dashboard** is a sophisticated, AI-powered analytical platform designed for power system operators and analysts. It seamlessly integrates a rich, interactive **Streamlit frontend dashboard** with an autonomous backend **Google Gemini LLM Agent** built on the Google Agent Development Kit (ADK).

The primary goal of the project is to democratize access to massive amounts of SCADA (Supervisory Control and Data Acquisition) data. Instead of building complex SQL queries or analyzing spreadsheets manually, users can simply ask natural language questions or explore the data visually through interactive charts.

---

## 2. System Architecture

The project follows a decoupled, two-tier architecture:

### 2.1. Frontend Dashboard (Streamlit)
The user interface is built securely via Streamlit ([app.py](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/app.py)), enabling an overarching view of operations.

*   **Navigation & Layout**: Uses a responsive sidebar ([build_sidebar](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/app.py#15-55)) for page routing and a global date filter that seamlessly scopes data across all non-chat pages.
*   **Overview**: Renders dynamic KPI cards and overarching system demand trends (via Plotly charts).
*   **Regional Analysis**: Breaks down power demand across different regions (e.g., WRP, NRP, ERP, SRP, NERP).
*   **Generation Mix**: Provides analysis on the proportion of energy generated from Thermal, Hydel, and Renewable sources over the selected period.
*   **Intraday Profile**: Analyzes high-granularity demand patterns across the 96 15-minute time blocks of a typical day.
*   **Agent Chat Interface**: Integrates the `scada_summary_agent` seamlessly for interactive Q&A. The chat is fully asynchronous and persists sessions to the SQLite database.

### 2.2. Backend LLM Agent (ADK & Gemini)
The "brain" of the platform is defined in [scada_summary_agent/agent.py](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/scada_summary_agent/agent.py). It utilizes the `gemini-2.5-flash-lite` model initialized with custom guardrails and instructions.

*   **Model Tier**: Google Gemini handles reasoning, tool execution, and query summarization.
*   **Tool Registry**: A suite of granular tools exposes specific capabilities to the agent securely.
*   **Memory & Persistence**: Context is maintained across chat turns using [DatabaseSessionService](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/.venv/Lib/site-packages/google/adk/sessions/database_session_service.py#433-736) connecting to a local SQLite database ([scada_streamlit_session.db](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/scada_streamlit_session.db)). The agent easily remembers the context of previous dates securely.

---

## 3. Tool Suite (scada_summary_agent/tools)

The agent leverages a comprehensive set of deterministic Python tools to extract and interpret data correctly without hallucinations:

1.  **Date Parsing ([date_parser.py](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/scada_summary_agent/tools/date_parser.py))**: Translates natural language relative queries ("yesterday", "next Friday", "Diwali week") into precise `YYYYMMDD` formats or date ranges.
2.  **Basic Retrieval ([scada_analysis.py](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/scada_summary_agent/tools/scada_analysis.py))**: Fetches SCADA summaries including peak demand, minimum demand, average demand, and total volume.
3.  **Anomaly Detection ([scada_anomaly.py](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/scada_summary_agent/tools/scada_anomaly.py))**: Uses statistical validation to identify missing data blocks, uncommon spikes, or severe drops in the curve.
4.  **Regional Tools ([region_profile.py](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/scada_summary_agent/tools/region_profile.py))**: Analyzes regional deviations and specific zone profiles.
5.  **Comparative Analysis ([compare_scada_dates.py](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/scada_summary_agent/tools/compare_scada_dates.py))**: Fetches multiple datasets side-by-side to explain variances between two different operational periods.
6.  **Data Ingestion ([scada_mongodb.py](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/scada_summary_agent/tools/scada_mongodb.py))**: Scripts connecting to external database environments (like MongoDB) for the raw SCADA blocks.

---

## 4. Key Execution Workflows

### 4.1. The Agent Conversation Flow
When a user submits a query through the Streamlit Agent Chat page:
1.  **Message Formatting**: The input is wrapped in a `types.Content` object and passed to the synchronously evaluated `runner.run(...)`.
2.  **Session Restoration**: ADK pulls the `streamlit_demo_session` from SQLite to give the model immediate access to the conversation history.
3.  **Execution & Tool Iteration**: The LLM analyzes the user prompt against its internal guardrails. If a date is provided, it calls `parse_natural_date_tool`. It evaluates the bounds and executes analytic backend tools (e.g. `detect_scada_anomalies_tool`).
4.  **Streaming & Finalizing**: The runner iterates the events asynchronously in the background and commits changes to SQLite. The Streamlit script captures the full non-partial text content authored by `scada_summary_agent` and displays the markdown response.

### 4.2. Global Data Filtering
For the chart dashboards:
1.  **State Loading**: [utils/data_loader.py](file:///d:/Self_Learning/scada-agent-project%20-Anti_Gravity/utils/data_loader.py) fetches and formats [sample_scada.csv](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/sample_scada.csv) securely.
2.  **Date Range Capture**: The sidebar takes `start_date` and `end_date` widgets to filter the dataframe. The filtered result is cached in `st.session_state['filtered_df']` ensuring charts update near-instantly without hitting the disk directly.

---

## 5. Development & Deployment Procedures

### 5.1. Requirements
*   **Python**: 3.10+ recommended.
*   **Environment**: A valid [.env](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/.env) file holding `GOOGLE_API_KEY`.
*   **Packages**: Install dependencies defined in [requirements.txt](file:///D:/Self_Learning/scada-agent-project%20-Anti_Gravity/requirements.txt) (Streamlit, Pandas, Plotly, Google Gen AI SDK, SQLAlchemy, aiosqlite).

### 5.2. Running the Application
To launch the dashboard and the agent system:
```bash
# Ensure the virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Launch the Streamlit application
streamlit run app.py
```

### 5.3. Guardrails & Safety
The Agent is strictly protected by `SYSTEM_GUARDRAIL` within the main agent configuration:
*   Never exposes internal error logs or Python tracebacks.
*   Never explicitly references internal tool names or raw formatting structures to the user.
*   Fails gracefully if the dates are entirely out-of-bounds ("No SCADA data available").

---
*Generated autonomously by Antigravity AI.*
