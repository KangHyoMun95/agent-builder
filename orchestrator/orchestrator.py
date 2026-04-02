from utils.prompt_builder import build_prompt
from agents.agent_runner import run_agent
import json

def load_file(path):
    with open(path, "r") as f:
        return f.read()

def run_orchestrator():
    global_rule = load_file("rules/global.md")
    role = load_file("roles/teamlead.md")
    task = load_file("tasks/task.md")

    prompt = build_prompt(global_rule, role, task, "")

    output = run_agent(prompt)
    print(output)
    try:
        output = output.replace("```json", "").replace("```", "").strip()
        data = json.loads(output)
    except:
        print("❌ Invalid JSON")
        return

    if data["decision"] == "NEED_USER_INPUT":
        user_input = input("\n👉 Your answer: ")

        # append vào context
        prompt = prompt + f"""
\n\n# USER ANSWER
{user_input}

# Instruction
Re-evaluate and return JSON.
"""
        output = run_agent(prompt)
        print("\n--- RESUMED ---\n")
        print(output)

        output = output.replace("```json", "").replace("```", "").strip()
        data = json.loads(output)

    # 👉 NEW: ROUTE TO DEVELOPER
    if data["decision"] == "DECIDED" and data.get("next_role") == "developer_be":
        dev_role = load_file("roles/developer_be.md")

        dev_prompt = build_prompt(global_rule, dev_role, task, output)

        dev_output = run_agent(dev_prompt)
        print("\n--- DEVELOPER BE ---\n")
        print(dev_output)
