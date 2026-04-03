# SCADA Summary Agent

An intelligent agent powered by Google's Gemini models designed to analyze and summarize SCADA (Supervisory Control and Data Acquisition) power system demand data.

## 🚩 Problem Statement

Power system operators and analysts deal with massive amounts of SCADA (Supervisory Control and Data Acquisition) data daily. Identifying trends, detecting anomalies (like sudden demand drops), and comparing historical data (e.g., "Diwali 2023 vs 2024") requires complex SQL queries or manual spreadsheet analysis. This process is time-consuming, error-prone, and requires technical expertise that not all stakeholders possess.

## 💡 Solution

The **SCADA Summary Agent** is an intelligent, LLM-powered assistant that democratizes access to power system data. It allows users to ask natural language questions like *"What was the peak demand yesterday?"* or *"Compare the load profile of last Sunday with the previous one."*

The agent autonomously:
1.  **Parses natural language dates** (e.g., "last Friday", "Diwali").
2.  **Retrieves and filters data** from the SCADA database (mocked via CSV for this demo).
3.  **Analyzes patterns** to compute metrics (Peak, Min, Avg) and detect anomalies.
4.  **Generates human-readable summaries** with actionable insights.

## 📋 Overview

The SCADA Summary Agent helps power system operators and analysts quickly understand demand patterns, detect anomalies, and compare data across different time periods using natural language queries. It leverages a suite of specialized tools to interact with SCADA data.

## ✨ Features

-   **Automated Summarization**: Generates concise natural language summaries of demand data, including min, max, average, and total demand.
-   **Natural Language Date Parsing**: Understands complex date queries like "yesterday", "last Diwali", "next Friday", or specific date ranges.
-   **Anomaly Detection**: Identifies spikes, drops, and missing data blocks in the demand curve.
-   **Region-wise Analysis**: Provides insights into regional demand profiles (e.g., CZ, EZ, WZ, MP).
-   **Comparative Analysis**: Compares demand metrics between two different dates or periods to highlight trends.

## 🏗️ Agent Architecture

The project implements a **hierarchical agentic workflow** using the Google Gen AI SDK and the Agent Development Kit (ADK).

### High-Level Design
The system is designed as a **Root Agent** that orchestrates specialized tools to fulfill user requests. It maintains **session state** (memory) to handle follow-up questions and context-aware queries.

### Components
1.  **`scada_summary_agent/agent.py` (Root Agent)**:
    *   **Role**: The brain of the system. It receives user input, plans the execution steps, selects the appropriate tools, and synthesizes the final response.
    *   **Capabilities**: Complex reasoning, multi-step planning, error handling.
    *   **Model**: Powered by `gemini-1.5-flash` for fast and accurate reasoning.

2.  **`scada_summary_agent/tools/` (Tool Layer)**:
    *   **`parse_natural_date_tool`**: Converts natural language (e.g., "yesterday") into structured date formats (`YYYYMMDD`).
    *   **`fetch_scada_summary_tool`**: Connects to the data source to retrieve demand, generation, and frequency metrics.
    *   **`detect_scada_anomalies_tool`**: Statistical analysis to identify outliers in the demand curve.
    *   **`region_demand_profile_tool`**: Aggregates data for specific regions (CZ, EZ, WZ, MP).
    *   **`compare_scada_dates_tool`**: Performs side-by-side comparison of two distinct time periods.

3.  **Persistence Layer**:
    *   Uses `SqliteSessionService` to store conversation history in a local SQLite database (`scada_session.db`). This enables the agent to remember context across multiple turns.

## 🛠️ Tools Used

-   **Google Gemini API**: The core LLM powering the agent's reasoning and generation.
-   **Google Gen AI SDK**: For model interaction and tool definition.
-   **Agent Development Kit (ADK)**: Framework for building, managing, and running the agent.
-   **Pandas**: For efficient data manipulation and analysis of SCADA CSV data.
-   **SQLite**: For local session persistence.
-   **Python 3.11**: The runtime environment.

## 🚀 Getting Started

### Prerequisites

-   Python 3.10+
-   A Google Cloud Project with Vertex AI or Gemini API access.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd scada-agent-project
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1  # Windows PowerShell
    # source .venv/bin/activate   # Linux/Mac
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**:
    Create a `.env` file in the root directory and add your Google API key:
    ```env
    GOOGLE_API_KEY=your_api_key_here
    ```

## 🏃 Usage

### Running the Agent

You can interact with the agent using the provided test script or by creating your own runner.

**Example using `tests/test_scada_agent.py`:**

```python
from scada_summary_agent.agent import root_agent

response = root_agent.run(
    "Summarize the SCADA demand for last Friday.",
)
print(response)
```

### Persistence & Session State

To run the agent with memory (persistence), use the `run_agent_persistent.py` script. This uses a local SQLite database (`scada_session.db`) to store conversation history.

```bash
python run_agent_persistent.py
```

This allows the agent to remember context from previous turns (e.g., "What was the peak demand?" followed by "Compare that to last year").

### Sample Queries

-   "What was the peak demand yesterday?"
-   "Compare the demand between Diwali 2023 and Diwali 2024."
-   "Are there any anomalies in the data for 25th Dec 2023?"
-   "Give me the regional breakdown for the Western Zone (WZ) for last week."

## 📊 Evaluation

The agent's performance can be evaluated by running the following test cases, which cover different aspects of its capabilities:

1.  **Basic Retrieval**:
    *   *Input*: "Summarize the SCADA demand for 2025-11-01."
    *   *Success Criteria*: Returns correct Peak, Min, and Avg demand for that specific date.

2.  **Contextual Memory**:
    *   *Input 1*: "My name is [Name]."
    *   *Input 2* (After restart): "What is my name?"
    *   *Success Criteria*: Agent correctly recalls the name from the persistent session.

3.  **Complex Reasoning (Comparison)**:
    *   *Input*: "Compare the demand between 2025-11-01 and 2025-11-02."
    *   *Success Criteria*: Agent fetches data for both dates and generates a comparative summary highlighting the differences.

4.  **Error Handling**:
    *   *Input*: "Summarize demand for 2099-01-01" (Future date with no data).
    *   *Success Criteria*: Agent gracefully handles the missing data and informs the user.

## 📂 Directory Structure

```
scada-agent-project/
├── scada_summary_agent/       # Main package
│   ├── agent.py               # Advanced Root Agent definition
│   ├── main_agent.py          # Basic Summary Agent definition
│   ├── tools/                 # Tool implementations
│   │   ├── date_parser.py     # Natural language date parsing
│   │   ├── scada_analysis.py  # Core analysis logic
│   │   ├── scada_anomaly.py   # Anomaly detection
│   │   └── ...
│   └── models/                # Data models (if any)
├── tests/                     # Test scripts
├── run_agent_local.py         # Local runner script (to be implemented)
├── requirements.txt           # Project dependencies
└── README.md                  # Project documentation
```
