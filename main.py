from orchestrator.orchestrator import run_project

# Press the green button in the gutter to run the script.
if __name__ == "__main__":
    run_project("test_project_01", open("tasks/task.md").read())
