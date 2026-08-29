import os
import sys
import glob
import csv
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def download_latest_csv_from_aws():
    key_path = os.path.join(BASE_DIR, "shinseon-key.pem")
    if not os.path.exists(key_path):
        print("⚠️ [AWS 다운로드 건너뜀] shinseon-key.pem 파일이 없습니다.")
        return False
        
    try:
        import paramiko
        print("🚀 [AWS 도쿄 서버] 최신 실측 CSV 다운로드 접속 시도 (13.192.187.244)...")
        key = paramiko.RSAKey.from_private_key_file(key_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("13.192.187.244", username="ubuntu", pkey=key, timeout=10)
        
        sftp = ssh.open_sftp()
        
        # 오늘 날짜 CSV 파일명 확인
        today_csv = "orderflow_history_2026-08-29.csv"
        remote_csv_path = f"/home/ubuntu/docs/historical_data/{today_csv}"
        
        local_dir_29 = os.path.join(BASE_DIR, "downloads", "2026-08-29")
        os.makedirs(local_dir_29, exist_ok=True)
        local_csv_29 = os.path.join(local_dir_29, today_csv)
        
        print(f" 📥 SFTP 다운로드: AWS {remote_csv_path} ➡️ {local_csv_29}")
        sftp.get(remote_csv_path, local_csv_29)
        
        # docs/historical_data 로도 복사
        hist_dir = os.path.join(BASE_DIR, "docs", "historical_data")
        os.makedirs(hist_dir, exist_ok=True)
        hist_csv_29 = os.path.join(hist_dir, today_csv)
        shutil.copy2(local_csv_29, hist_csv_29)
        print(f" 📋 사본 저장 완료: {hist_csv_29}")
        
        sftp.close()
        ssh.close()
        print(" ✅ [AWS 다운로드 성공] 최신 실측 CSV 수송 완료!")
        return True
    except Exception as e:
        print(f" ⚠️ [AWS 다운로드 예외]: {e}")
        return False

def get_field_val(row, candidate_keys, default=0.0):
    for k in candidate_keys:
        if k in row and row[k] is not None:
            v = str(row[k]).replace('="', '').replace('"', '').strip()
            if v:
                try:
                    return float(v)
                except ValueError:
                    pass
    return default

def recalc_single_csv(file_path):
    print(f"\n📂 [재연산 처리 중]: {file_path}", flush=True)
    if not os.path.exists(file_path):
        print(f" ❌ 파일 없음: {file_path}", flush=True)
        return None
        
    before_counts = {"LONG": 0, "SHORT": 0, "NONE": 0, "OTHER": 0}
    after_counts = {"LONG": 0, "SHORT": 0, "NONE": 0, "OTHER": 0}
    changed_count = 0
    total_rows = 0
    
    specific_window_records = [] # 09:16:40 ~ 09:17:50
    
    rows = []
    fieldnames = None
    
    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                print(" ⚠️ 빈 CSV 파일 건너뜀", flush=True)
                return None
                
            signal_key = None
            for k in ["Signal", "signal", "SIGNAL"]:
                if k in fieldnames:
                    signal_key = k
                    break
            if not signal_key:
                signal_key = "Signal"
                fieldnames.append("Signal")
                
            for row in reader:
                total_rows += 1
                raw_sig = row.get(signal_key)
                old_signal = str(raw_sig if raw_sig is not None else "NONE").replace('="', '').replace('"', '').strip().upper()
                if not old_signal:
                    old_signal = "NONE"
                    
                if old_signal not in before_counts:
                    before_counts["OTHER"] += 1
                else:
                    before_counts[old_signal] += 1
                    
                price = get_field_val(row, ["BTC_Price($)", "BTC_Price", "Price", "btc_price"])
                rolling_1m_liq = get_field_val(row, ["1m_Rolling_Liq($)", "Rolling_Liq($)", "Rolling_Liq", "1m_liq", "Liq"])
                target_liq = get_field_val(row, ["Liq_Threshold($)", "Liq_Threshold", "liq_threshold"])
                if target_liq <= 0:
                    target_liq = 1400000.0  # 기본 1.4M
                    
                oi_speed = get_field_val(row, ["1m_OI_Speed(%)", "OI_Speed(%)", "1m_OI_Speed", "OI_Speed", "oi_speed"])
                target_oi = get_field_val(row, ["OI_Speed_Threshold(%)", "OI_Speed_Threshold", "oi_speed_threshold"])
                if target_oi <= 0:
                    target_oi = 0.18  # 기본 0.18%
                    
                price_delta_5s = get_field_val(row, ["5s_Price_Delta($)", "5s_Delta", "5s_price_delta"])
                price_delta_1m = get_field_val(row, ["1m_Price_Delta($)", "1m_Delta", "1m_price_delta"])
                price_slope_1m = get_field_val(row, ["1m_Price_Slope", "Price_Slope", "1m_slope", "slope"])

                # V2.55 황금 매트릭스 & 0.035% 동적 불감대 로직
                deadband_val = price * 0.00035
                is_price_up = (price_delta_5s >= deadband_val) or (price_delta_1m > 0 and price_slope_1m >= 0.30)
                is_price_down = (price_delta_5s <= -deadband_val) or (price_delta_1m < 0 and price_slope_1m <= -0.30)
                
                if rolling_1m_liq >= target_liq and abs(oi_speed) >= target_oi:
                    if is_price_down and oi_speed < 0:
                        new_signal = "LONG"
                    elif is_price_up and oi_speed < 0:
                        new_signal = "SHORT"
                    elif oi_speed > 0:
                        if is_price_up:
                            new_signal = "LONG"
                        elif is_price_down:
                            new_signal = "SHORT"
                        else:
                            new_signal = "NONE"
                    else:
                        new_signal = "NONE"
                else:
                    new_signal = "NONE"
                    
                if new_signal != old_signal:
                    changed_count += 1
                    
                if new_signal not in after_counts:
                    after_counts["OTHER"] += 1
                else:
                    after_counts[new_signal] += 1
                    
                ts = row.get("Timestamp(KST)") or row.get("Timestamp") or ""
                clean_ts = str(ts).replace('="', '').replace('"', '').strip()
                if "09:16:40" <= clean_ts.split()[-1] <= "09:17:50" if clean_ts.split() else False:
                    specific_window_records.append({
                        "ts": clean_ts,
                        "price": price,
                        "liq": rolling_1m_liq,
                        "oi_spd": oi_speed,
                        "d5s": price_delta_5s,
                        "d1m": price_delta_1m,
                        "slope": price_slope_1m,
                        "old_sig": old_signal,
                        "new_sig": new_signal,
                        "is_up": is_price_up,
                        "is_down": is_price_down
                    })

                row[signal_key] = new_signal
                rows.append(row)
                
    except Exception as e:
        print(f" ❌ 파일 읽기/파싱 오류 ({file_path}): {e}", flush=True)
        return None
        
    if not rows:
        print(" ⚠️ 유효 행 없음 건너뜀", flush=True)
        return None

    # 파일 다시 쓰기
    try:
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        print(f" ❌ 파일 쓰기 오류 ({file_path}): {e}", flush=True)
        return None
        
    print(f"  - 총 행수: {total_rows:,} | 변경된 신호 행수: {changed_count:,}", flush=True)
    print(f"  - [Before] LONG: {before_counts['LONG']}, SHORT: {before_counts['SHORT']}, NONE: {before_counts['NONE']}", flush=True)
    print(f"  - [After ] LONG: {after_counts['LONG']}, SHORT: {after_counts['SHORT']}, NONE: {after_counts['NONE']}", flush=True)
    
    return {
        "file": file_path,
        "total_rows": total_rows,
        "changed": changed_count,
        "before": before_counts,
        "after": after_counts,
        "window_records": specific_window_records
    }

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
        
    print("================================================================================")
    print(" 🌟 [V2.55 황금 매트릭스 & 0.035% 동적 불감대] 실측 CSV 전수 재연산 엔진 가동 🌟 ")
    print("================================================================================")
    
    # 1. AWS 서버에서 최신 CSV 다운로드
    download_latest_csv_from_aws()
    
    # 2. 모든 CSV 파일 탐색
    csv_files = []
    # downloads 디렉토리
    downloads_dir = os.path.join(BASE_DIR, "downloads")
    if os.path.exists(downloads_dir):
        for root, _, files in os.walk(downloads_dir):
            for file in files:
                if file.endswith(".csv"):
                    csv_files.append(os.path.join(root, file))
                    
    # docs/historical_data 디렉토리
    hist_dir = os.path.join(BASE_DIR, "docs", "historical_data")
    if os.path.exists(hist_dir):
        for root, _, files in os.walk(hist_dir):
            for file in files:
                if file.endswith(".csv"):
                    csv_files.append(os.path.join(root, file))
                    
    csv_files = sorted(list(set(csv_files)))
    print(f"\n🔍 총 {len(csv_files)}개의 실측 CSV 파일 발견. 전수 재연산 시작...")
    
    total_files = 0
    grand_total_rows = 0
    grand_total_changed = 0
    grand_before = {"LONG": 0, "SHORT": 0, "NONE": 0}
    grand_after = {"LONG": 0, "SHORT": 0, "NONE": 0}
    
    today_29_window = []
    
    for f in csv_files:
        res = recalc_single_csv(f)
        if res:
            total_files += 1
            grand_total_rows += res["total_rows"]
            grand_total_changed += res["changed"]
            for k in ["LONG", "SHORT", "NONE"]:
                grand_before[k] += res["before"].get(k, 0)
                grand_after[k] += res["after"].get(k, 0)
            if "2026-08-29" in f and res["window_records"]:
                today_29_window = res["window_records"]
                
    print("\n================================================================================")
    print(" 📊 [전수 CSV V2.55 재연산 최종 통계 종합] ")
    print("================================================================================")
    print(f" • 정상 처리 파일 수: {total_files}개")
    print(f" • 전수 검증 데이터 행수: {grand_total_rows:,}행")
    print(f" • 신호 상태 변경 행수: {grand_total_changed:,}행")
    print(f" • [Before 누적] LONG: {grand_before['LONG']:,}개 | SHORT: {grand_before['SHORT']:,}개 | NONE: {grand_before['NONE']:,}개")
    print(f" • [After  누적] LONG: {grand_after['LONG']:,}개 | SHORT: {grand_after['SHORT']:,}개 | NONE: {grand_after['NONE']:,}개")
    print("================================================================================")
    
    if today_29_window:
        print("\n🎯 [2026-08-29 09:16:40 ~ 09:17:50 롱 청산 스퀴즈 해소 구간 전후 정밀 대조표]")
        print("-------------------------------------------------------------------------------------------------------------------------")
        print(f"{'시간(KST)':<20} | {'BTC가격':<8} | {'1m청산액($)':<12} | {'OI속도(%)':<10} | {'5s변화':<7} | {'Before':<7} | {'After':<7} | {'판정근거'}")
        print("-------------------------------------------------------------------------------------------------------------------------")
        for r in today_29_window:
            reason = ""
            if r["new_sig"] == "LONG":
                if r["oi_spd"] < 0 and r["is_down"]:
                    reason = "Case 1 (롱청산/OI감소+급락 -> 롱반등저격)"
                elif r["oi_spd"] > 0 and r["is_up"]:
                    reason = "Case 3 (신규롱/OI증가+급등 -> 롱추세추종)"
            elif r["new_sig"] == "SHORT":
                if r["oi_spd"] < 0 and r["is_up"]:
                    reason = "Case 2 (숏청산/OI감소+급등 -> 숏반락저격)"
                elif r["oi_spd"] > 0 and r["is_down"]:
                    reason = "Case 4 (신규숏/OI증가+급락 -> 숏하방추종)"
            else:
                reason = "조건미충족 / 불감대"
                
            print(f"{r['ts']:<20} | {r['price']:<8.1f} | {r['liq']:<12,.0f} | {r['oi_spd']:<+10.4f} | {r['d5s']:<+7.1f} | {r['old_sig']:<7} | {r['new_sig']:<7} | {reason}")
        print("-------------------------------------------------------------------------------------------------------------------------")

if __name__ == "__main__":
    main()
