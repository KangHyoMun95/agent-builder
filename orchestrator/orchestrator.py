# orchestrator.py
import json
import os
from typing import Dict, Any
from enum import Enum
from agents.agent_runner import run_agent
from utils.prompt_builder import build_prompt

# === Định nghĩa State ===
class ProjectState(Enum):
    INIT = "init"
    BA_WORKING = "ba_working"
    BA_DONE = "ba_done"
    TEAMLEAD_WORKING = "teamlead_working"
    TEAMLEAD_DONE = "teamlead_done"
    DESIGNER_WORKING = "designer_working"
    DESIGNER_DONE = "designer_done"
    FE_DEV_WORKING = "fe_dev_working"
    FE_DEV_DONE = "fe_dev_done"
    BE_DEV_WORKING = "be_dev_working"
    BE_DEV_DONE = "be_dev_done"
    DATA_ENG_WORKING = "data_eng_working"
    DATA_ENG_DONE = "data_eng_done"
    TESTER_WORKING = "tester_working"
    RETRY_DEV = "retry_dev"
    DONE = "done"
    FAILED = "failed"

# === Hàm load file role ===
def load_role(role_name: str) -> str:
    path = f"roles/{role_name}.md"
    if not os.path.exists(path):
        # fallback
        return f"# Role: {role_name}\n\nYou are an expert {role_name}."
    with open(path, "r") as f:
        return f.read()

# === Hàm gọi agent với retry logic ===
def call_agent(role: str, task: str, context: str, global_rule: str) -> Dict[str, Any]:
    prompt = build_prompt(global_rule, load_role(role), task, context)
    output = run_agent(prompt)
    # Loại bỏ markdown json nếu có
    output = output.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # Thử lần 2: yêu cầu model chỉ trả json
        retry_prompt = prompt + "\n\nERROR: Your output was not valid JSON. Return ONLY valid JSON. No extra text."
        output2 = run_agent(retry_prompt)
        output2 = output2.replace("```json", "").replace("```", "").strip()
        return json.loads(output2)

# === Hàm lưu artifact ===
def save_artifact(project_id: str, key: str, value: Any):
    # Lưu vào file hoặc DB
    os.makedirs(f"projects/{project_id}/artifacts", exist_ok=True)
    with open(f"projects/{project_id}/artifacts/{key}.json", "w") as f:
        json.dump(value, f, indent=2)

def load_artifact(project_id: str, key: str) -> Any:
    path = f"projects/{project_id}/artifacts/{key}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

# === Orchestrator chính ===
def run_project(project_id: str, initial_task: str):
    # Load hoặc tạo mới project state
    state_file = f"projects/{project_id}/state.json"
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state_data = json.load(f)
        current_state = ProjectState(state_data["state"])
        retry_count = state_data["retry_count"]
        artifacts = state_data.get("artifacts", {})
        context = state_data.get("context", {})
    else:
        current_state = ProjectState.INIT
        retry_count = 0
        artifacts = {}
        context = {"user_inputs": [], "last_error": None, "failed_role": None}
        os.makedirs(f"projects/{project_id}", exist_ok=True)

    global_rule = open("rules/global.md").read()
    task_desc = initial_task  # có thể lưu lại

    project_data = {
        "role_index": 0,
        "role_list": []
    }

    # Vòng lặp state machine
    while current_state not in [ProjectState.DONE, ProjectState.FAILED]:
        print(f"\n--- Project {project_id} : {current_state.value} ---")

        if current_state == ProjectState.INIT:
            # Chuyển sang BA
            current_state = ProjectState.BA_WORKING

        elif current_state == ProjectState.BA_WORKING:
            # Gọi BA agent
            ba_output = call_agent("ba", task_desc, json.dumps(context), global_rule)
            # Giả sử BA trả về { "requirements": "...", "user_stories": [...] }
            artifacts["requirements"] = ba_output
            save_artifact(project_id, "requirements", ba_output)
            current_state = ProjectState.BA_DONE

        elif current_state == ProjectState.BA_DONE:
            current_state = ProjectState.TEAMLEAD_WORKING

        elif current_state == ProjectState.TEAMLEAD_WORKING:
            # Teamlead cần nhận requirements và quyết định architecture, split tasks
            teamlead_input = {
                "requirements": artifacts.get("requirements"),
                "context": context
            }
            tl_output = call_agent("teamlead", "Design system and split tasks", json.dumps(teamlead_input), global_rule)
            # Kiểm tra nếu teamlead cần hỏi user
            if tl_output.get("decision") == "NEED_USER_INPUT":
                print(f"Teamlead hỏi: {tl_output.get('question')}")
                user_ans = input("👉 Your answer: ")
                context["user_inputs"].append({"question": tl_output.get('question'), "answer": user_ans})
                # Lưu lại context và lặp lại state này
                continue  # quay lại đầu vòng lặp, vẫn ở TEAMLEAD_WORKING
            # Nếu DECIDED
            artifacts["architecture"] = tl_output
            save_artifact(project_id, "architecture", tl_output)
            current_state = ProjectState.TEAMLEAD_DONE

        elif current_state == ProjectState.TEAMLEAD_DONE:
            # Quyết định next role dựa trên split tasks (có thể có FE, BE, Data)
            # Ở đây giả sử teamlead output có trường "next_roles": ["designer","fe_dev","be_dev"]
            next_roles = artifacts["architecture"].get("next_roles", [])

            # Lọc bỏ những role đã hoàn thành? Ban đầu thì chưa có.
            project_data["role_list"] = next_roles
            project_data["role_index"] = 0

            if next_roles:
                first_role = next_roles[0]
                if "designer" == first_role:
                    current_state = ProjectState.DESIGNER_WORKING
                elif "fe_dev" == first_role:
                    current_state = ProjectState.FE_DEV_WORKING
                elif "be_dev" == first_role:
                    current_state = ProjectState.BE_DEV_WORKING
                elif "data_engineer" == first_role:
                    current_state = ProjectState.DATA_ENG_WORKING
            else:
                # Không có dev nào? sang tester luôn
                current_state = ProjectState.TESTER_WORKING

        elif current_state == ProjectState.DESIGNER_WORKING:
            design_output = call_agent("designer", "Create UI/UX design based on requirements", json.dumps(artifacts), global_rule)
            artifacts["design"] = design_output
            save_artifact(project_id, "design", design_output)
            current_state = ProjectState.DESIGNER_DONE

        elif current_state == ProjectState.FE_DEV_WORKING:
            fe_input = {
                "requirements": artifacts.get("requirements"),
                "design": artifacts.get("design"),
                "architecture": artifacts.get("architecture")
            }
            fe_output = call_agent("fe_dev", "Implement frontend", json.dumps(fe_input), global_rule)
            artifacts["fe_code"] = fe_output
            save_artifact(project_id, "fe_code", fe_output)
            current_state = ProjectState.FE_DEV_DONE

        elif current_state == ProjectState.BE_DEV_WORKING:
            be_input = {
                "requirements": artifacts.get("requirements"),
                "architecture": artifacts.get("architecture")
            }
            be_output = call_agent("be_dev", "Implement backend APIs", json.dumps(be_input), global_rule)
            artifacts["be_code"] = be_output
            save_artifact(project_id, "be_code", be_output)
            current_state = ProjectState.BE_DEV_DONE

        elif current_state == ProjectState.DATA_ENG_WORKING:
            de_output = call_agent("data_engineer", "Build data pipeline", json.dumps(artifacts), global_rule)
            artifacts["data_pipeline"] = de_output
            save_artifact(project_id, "data_pipeline", de_output)
            current_state = ProjectState.DATA_ENG_DONE

        elif current_state == ProjectState.TESTER_WORKING:
            # Tester cần tất cả artifacts
            test_input = {
                "requirements": artifacts.get("requirements"),
                "fe_code": artifacts.get("fe_code"),
                "be_code": artifacts.get("be_code"),
                "data_pipeline": artifacts.get("data_pipeline")
            }
            test_output = call_agent("tester", "Run tests and report", json.dumps(test_input), global_rule)
            # test_output dạng: {"result": "pass" or "fail", "errors": [{"role": "be_dev", "message": "..."}], "suggestion": "..."}
            if test_output.get("result") == "pass":
                current_state = ProjectState.DONE
            else:
                # fail
                if retry_count >= 3:
                    current_state = ProjectState.FAILED
                else:
                    context["last_error"] = test_output.get("errors")
                    # Xác định role cần sửa (ưu tiên role đầu tiên trong errors)
                    failed_role = test_output["errors"][0]["role"] if test_output.get("errors") else "be_dev"
                    context["failed_role"] = failed_role
                    retry_count += 1
                    current_state = ProjectState.RETRY_DEV

        elif current_state == ProjectState.RETRY_DEV:
            role_to_retry = context["failed_role"]
            if role_to_retry == "fe_dev":
                # Gọi lại FE dev với context lỗi
                retry_input = {
                    "previous_code": artifacts.get("fe_code"),
                    "error_report": context["last_error"],
                    "requirements": artifacts.get("requirements")
                }
                new_output = call_agent("fe_dev", "Fix the following errors", json.dumps(retry_input), global_rule)
                artifacts["fe_code"] = new_output
                save_artifact(project_id, "fe_code", new_output)
            elif role_to_retry == "be_dev":
                retry_input = {
                    "previous_code": artifacts.get("be_code"),
                    "error_report": context["last_error"],
                    "requirements": artifacts.get("requirements")
                }
                new_output = call_agent("be_dev", "Fix the following errors", json.dumps(retry_input), global_rule)
                artifacts["be_code"] = new_output
                save_artifact(project_id, "be_code", new_output)
            # Sau khi sửa, quay lại tester
            current_state = ProjectState.TESTER_WORKING

        elif [
            ProjectState.BE_DEV_DONE,
            ProjectState.FE_DEV_DONE,
            ProjectState.DESIGNER_DONE,
            ProjectState.DATA_ENG_DONE
        ].__contains__(current_state):
            project_data["role_index"] += 1
            idx = project_data["role_index"]
            role_list = project_data["role_list"]
            if idx < len(role_list):
                next_role = role_list[idx]
                if next_role == "fe_dev":
                    current_state = ProjectState.FE_DEV_WORKING
                elif next_role == "be_dev":
                    current_state = ProjectState.BE_DEV_WORKING
                elif next_role == "data_engineer":
                    current_state = ProjectState.DATA_ENG_WORKING
                else:
                    # không còn role nào
                    current_state = ProjectState.TESTER_WORKING
            else:
                current_state = ProjectState.TESTER_WORKING

        # Lưu state sau mỗi bước
        state_data = {
            "state": current_state.value,
            "retry_count": retry_count,
            "artifacts": artifacts,
            "context": context,
            "history": []  # bạn có thể thêm log
        }
        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2)

    # Kết thúc
    if current_state == ProjectState.DONE:
        print(f"✅ Project {project_id} completed successfully!")
    else:
        print(f"❌ Project {project_id} failed after {retry_count} retries.")
