import os, glob

def reprocess_csv(file_path):
    if not os.path.exists(file_path):
        print(f"[SKIP] Not found: {file_path}")
        return 0
        
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        
    if not lines:
        return 0
        
    header = lines[0].strip()
    cols = header.split(",")
    # Header: Timestamp(KST),BTC_Price($),1m_Rolling_Liq($),1m_Long_Liq($),1m_Short_Liq($),Liq_Threshold($),1m_OI_Speed(%),OI_Speed_Threshold(%),1m_Price_Delta($),1m_Price_Slope,Signal,Bot_State
    
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
            
            # Reprocessing Logic (최신 백서 및 신선 기준):
            # 1. 청산 조건 충족 AND 2. |OI 속도| >= 기준치
            new_signal = "NONE"
            if rolling_liq >= liq_thresh and abs(oi_speed) >= oi_thresh:
                # Direction evaluation:
                # If short liquidation dominates or price delta is strongly positive -> LONG
                # If long liquidation dominates or price delta is strongly negative -> SHORT
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
            
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
        
    print(f"[SUCCESS] {file_path} -> Updated {recalculated_count} rows | Total Signals: {signals_count}")
    return recalculated_count

# Reprocess all files for 2026-08-21 and 2026-08-22
files = [
    "docs/historical_data/orderflow_history_2026-08-21.csv",
    "docs/historical_data/orderflow_history_2026-08-22.csv",
    "downloads/2026-08-21/orderflow_history_2026-08-21.csv",
    "downloads/2026-08-21/orderflow_history_2026-08-21 - 纻.csv",
    "downloads/2026-08-22/orderflow_history_2026-08-22.csv",
]

for f in files:
    reprocess_csv(f)