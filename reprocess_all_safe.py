import os, glob, shutil

def reprocess_csv_safe(file_path):
    if not os.path.exists(file_path):
        print(f"[SKIP] Not found: {file_path}")
        return 0
        
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        
    if not lines:
        return 0
        
    header = lines[0].strip()
    out_lines = [header + "\n"]
    recalculated_count = 0
    signals_count = {"LONG": 0, "SHORT": 0, "NONE": 0}
    
    for line in lines[1:]:
        parts = line.strip().split(",")
        if len(parts) < 12:
            out_lines.append(line)
            continue
            
        try:
            ts = parts[0]
            price = parts[1]
            rolling_liq = float(parts[2]) if parts[2] else 0.0
            long_liq = float(parts[3]) if parts[3] else 0.0
            short_liq = float(parts[4]) if parts[4] else 0.0
            liq_thresh = float(parts[5]) if parts[5] else 1500000.0
            oi_speed = float(parts[6]) if parts[6] else 0.0
            oi_thresh = float(parts[7]) if parts[7] else 0.25
            price_delta = float(parts[8]) if parts[8] else 0.0
            price_slope = float(parts[9]) if parts[9] else 0.0
            old_signal = parts[10]
            bot_state = parts[11]
            
            new_signal = "NONE"
            if rolling_liq >= liq_thresh and abs(oi_speed) >= oi_thresh:
                if long_liq > short_liq or (long_liq == short_liq and price_delta < 0):
                    new_signal = "SHORT"
                elif short_liq > long_liq or (long_liq == short_liq and price_delta > 0):
                    new_signal = "LONG"
                else:
                    new_signal = "SHORT" if price_slope < 0 else "LONG"
            
            if new_signal != old_signal:
                recalculated_count += 1
                
            signals_count[new_signal] = signals_count.get(new_signal, 0) + 1
            parts[10] = new_signal
            out_lines.append(",".join(parts) + "\n")
        except Exception as e:
            out_lines.append(line)
            
    # Try writing to original path
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
        print(f"[SUCCESS] {file_path} -> Updated {recalculated_count} rows | Total: {signals_count}")
    except PermissionError:
        # If open in Excel, write to _updated.csv or temporary, then copy
        alt_path = file_path.replace(".csv", "_NEW.csv")
        with open(alt_path, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
        print(f"[LOCKED BY EXCEL -> SAVED TO]: {alt_path} (Updated {recalculated_count} rows | Total: {signals_count})")
        
    return recalculated_count

# Find all 2026-08-21 and 2026-08-22 CSVs
patterns = [
    "docs/historical_data/*.csv",
    "downloads/2026-08-21/*.csv",
    "downloads/2026-08-22/*.csv",
]

for pat in patterns:
    for f in glob.glob(pat):
        if not f.endswith("_NEW.csv"):
            reprocess_csv_safe(f)