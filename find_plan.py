with open("shinseon_server.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "place-plan-order" in line or "STOP_LOSS" in line or "planType" in line or "plan_type" in line:
            print(str(i) + ": " + line.strip())