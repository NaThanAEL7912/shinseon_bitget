import os

print("=== ALL CSV FILES ON AWS SERVER ===")
for root, dirs, files in os.walk('/home/ubuntu'):
    for f in files:
        if f.endswith('.csv'):
            path = os.path.join(root, f)
            print("CSV FOUND:", path, "SIZE:", os.path.getsize(path))
