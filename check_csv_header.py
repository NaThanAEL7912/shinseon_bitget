with open("docs/historical_data/orderflow_history_2026-08-21.csv", "r", encoding="utf-8", errors="ignore") as f:
    for i in range(5):
        print(f.readline().strip())