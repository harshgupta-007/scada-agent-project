from scada_summary_agent.agent import root_agent

def test_agent():
    response = root_agent.run(
        "Summarize this SCADA file.",
        file_path="scada_summary_agent/sample_scada.csv"
    )
    print(response)
