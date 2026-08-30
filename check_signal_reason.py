import os

log_path = "orderflow_history_2026-08-24.csv"
if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        print("=== Recent 15 Orderflow CSV records ===")
        for l in lines[-15:]:
            print(l.strip())

task_log = "C:/Users/ClawNaEL/.gemini/antigravity/brain/ee372d50-927a-4c14-aa25-d1f50464ecf7/.system_generated/tasks/task-18972.log"
if os.path.exists(task_log):
    with open(task_log, "r", encoding="utf-8", errors="ignore") as f:
        t_lines = f.readlines()
        print("\n=== Recent Task Log Lines ===")
        for tl in t_lines[-20:]:
            print(tl.strip())