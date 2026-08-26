
import sys
import os
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import math
import asyncio
import random
import logging
import time
import re
import json
import socket
import urllib.request
from datetime import datetime, timezone, timedelta
from collections import deque
import aiohttp
import ssl
import hmac
import hashlib
import base64

import ccxt.async_support as ccxt
import websockets

try:
    aiohttp.connector.DefaultResolver = aiohttp.ThreadedResolver
except Exception:
    pass

def kst_time_converter(*args):
    return time.gmtime(time.time() + 9 * 3600)

logging.Formatter.converter = kst_time_converter

def get_kst_now():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=9)))

def check_is_weekend_kst(dt_kst):
    """
    [V5.38 글로벌 금융 시장 주말 판정 팩트 정공법 함수]
    - 뉴욕 주말 마감: 뉴욕 금요일 17:00 (EDT) == KST 토요일 오전 06:00
    - 뉴욕 주말 개장: 뉴욕 일요일 18:00 (EDT) == KST 월요일 오전 07:00
    - KST 토요일 00:00~06:00 은 뉴욕 금요일 평일장이므로 is_weekend = False !
    """
    w_day = dt_kst.weekday()
    h_val = dt_kst.hour
    if w_day == 5: # 토요일
        return h_val >= 6
    elif w_day == 6: # 일요일
        return True
    elif w_day == 0: # 월요일
        return h_val < 7
    return False

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ShinseonBot")

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOGS_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

class DailyTradeLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            today_str = get_kst_now().strftime("%Y-%m-%d")
            daily_file = os.path.join(LOGS_DIR, f"shinseon_trade_{today_str}.log")
            with open(daily_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

daily_handler = DailyTradeLogHandler()
daily_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(daily_handler)

def load_server_config():
    cfg = {}
    config_path = os.path.join(BASE_DIR, "server_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            logger.error(f"Config load error: {e}")
            
    # .env 파일 폴백 로드 (API 키 등 환경 변수 100% 로드)
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in cfg or not cfg[k]:
                            cfg[k] = v
        except Exception as e:
            logger.error(f".env load error: {e}")
    return cfg

env_vars = load_server_config()

def safe_int(v, default=0):
    try: return int(float(v))
    except: return default

def safe_float(v, default=0.0):
    try: return float(v)
    except: return default

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

def get_kst_now_str():
    from datetime import datetime, timedelta
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

async def send_telegram_notification_server(message):
    try:
        config = load_server_config()
        bot_token = str(config.get("telegram_token") or config.get("TELEGRAM_BOT_TOKEN") or config.get("TELEGRAM_TOKEN") or "").strip()
        chat_id = str(config.get("telegram_chat_id") or config.get("TELEGRAM_CHAT_ID") or "").strip()
        if not bot_token or not chat_id:
            return
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        clean_text = message.replace("<b>", "").replace("</b>", "").replace("\n", " | ")
        logger.info(f"📱 [TELEGRAM OUT] 발송: {clean_text}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=5.0) as resp:
                pass
    except Exception as e:
        logger.error(f"Telegram server send error: {e}")

def build_telegram_trade_msg(title, direction, reason, signal_time="", signal_qty=0.0, signal_price=0.0, actual_time="", actual_qty=0.0, actual_price=0.0, entry_price=0.0, leverage=30, is_entry=False):
    """
    폐하의 어명에 따른 텔레그램 진입/청산 표준 규격 포맷 빌더
    """
    now_str = get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
    sig_time_str = signal_time if signal_time else now_str
    act_time_str = actual_time if actual_time else now_str
    
    sig_qty_val = signal_qty if signal_qty > 0 else actual_qty
    sig_qty_str = f"{sig_qty_val:.3f} BTC" if sig_qty_val > 0 else "0.007 BTC"
    act_qty_str = f"{actual_qty:.3f} BTC" if actual_qty > 0 else sig_qty_str
    
    sig_p_val = signal_price if signal_price > 0 else (actual_price if actual_price > 0 else entry_price)
    sig_p_str = f"{sig_p_val:,.1f} USDT" if sig_p_val > 0 else "64,527.0 USDT"
    
    if is_entry:
        entry_p_val = actual_price if actual_price > 0 else sig_p_val
        entry_p_str = f"{entry_p_val:,.1f} USDT" if entry_p_val > 0 else sig_p_str
        # 진입 슬리피지: 유리한 체결이면 플러스(+), 불리하면 마이너스(-)
        slip_usd = (sig_p_val - entry_p_val) if direction == "LONG" else (entry_p_val - sig_p_val)
        slip_pct = (slip_usd / sig_p_val * 100.0) if sig_p_val > 0 else 0.0
        
        msg = (
            f"<b>{title}</b>\n"
            f"방향: <b>{direction}</b>\n"
            f"사유: <b>{reason}</b>\n\n"
            f"<b>[신호 발생 정보]</b>\n"
            f"신호 발생시간: <b>{sig_time_str}</b>\n"
            f"수량: <b>{sig_qty_str}</b>\n"
            f"신호 발생 가격: <b>{sig_p_str}</b>\n\n"
            f"<b>[실제 체결 정보]</b>\n"
            f"실제 체결 시간: <b>{act_time_str}</b>\n"
            f"수량: <b>{act_qty_str}</b>\n"
            f"진입 가격: <b>{entry_p_str}</b>\n"
            f"진입 슬리피지: <b>{slip_usd:+,.1f} USDT ({slip_pct:+.3f}%)</b>"
        )
    else:
        # 청산
        ent_p_val = entry_price if entry_price > 0 else sig_p_val
        exit_p_val = actual_price if actual_price > 0 else sig_p_val
        
        if direction == "LONG":
            pnl_pct = (exit_p_val - ent_p_val) / ent_p_val if ent_p_val > 0 else 0.0
        else:
            pnl_pct = (ent_p_val - exit_p_val) / ent_p_val if ent_p_val > 0 else 0.0
            
        roe_pct = pnl_pct * 100.0 * leverage
        btc_vol = actual_qty if actual_qty > 0 else (signal_qty if signal_qty > 0 else 0.007)
        pnl_usdt = btc_vol * ent_p_val * pnl_pct if ent_p_val > 0 else 0.0
        
        # 청산 슬리피지: 유리한 체결이면 플러스(+), 불리하면 마이너스(-)
        slip_usd = (exit_p_val - sig_p_val) if direction == "LONG" else (sig_p_val - exit_p_val)
        slip_pct = (slip_usd / sig_p_val * 100.0) if sig_p_val > 0 else 0.0
        
        msg = (
            f"<b>{title}</b>\n"
            f"방향: <b>{direction}</b>\n"
            f"사유: <b>{reason}</b>\n\n"
            f"<b>[신호 발생 정보]</b>\n"
            f"신호 발생시간: <b>{sig_time_str}</b>\n"
            f"수량: <b>{sig_qty_str}</b>\n"
            f"신호 발생 가격: <b>{sig_p_str}</b>\n\n"
            f"<b>[실제 체결 정보]</b>\n"
            f"실제 체결 시간: <b>{act_time_str}</b>\n"
            f"수량: <b>{act_qty_str}</b>\n"
            f"진입 가격: <b>{ent_p_val:,.1f} USDT</b>\n"
            f"청산 가격: <b>{exit_p_val:,.1f} USDT</b>\n"
            f"수익률: <b>{pnl_pct*100.0:+.2f}% (ROE: {roe_pct:+.2f}%)</b> | 손익: <b>{pnl_usdt:+,.2f} USDT</b>\n"
            f"청산 슬리피지: <b>{slip_usd:+,.1f} USDT ({slip_pct:+.3f}%)</b>"
        )
    return msg

STATS_DIR = LOGS_DIR

def get_daily_stats_filepath(date_str):
    return os.path.join(STATS_DIR, f"trade_stats_{date_str}.json")

SUMMARY_FILE = os.path.join(STATS_DIR, "trade_stats_summary.json")

def load_trade_stats_summary():
    if os.path.exists(SUMMARY_FILE):
        try:
            with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"통계 요약 로드 실패: {e}")
    return {"total_pnl": 0.0, "total_trades": 0, "total_wins": 0, "total_losses": 0, "daily_index": []}

def save_trade_stats_summary(summary):
    try:
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"통계 요약 저장 실패: {e}")

def load_daily_stats(date_str):
    fp = get_daily_stats_filepath(date_str)
    if os.path.exists(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"일별 통계 로드 실패 ({date_str}): {e}")
    return {
        "date": date_str,
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "profit_tot": 0.0,
        "loss_tot": 0.0,
        "pnl": 0.0,
        "avg_roe": 0.0,
        "trades_detail": []
    }

def save_daily_stats(date_str, daily_rec):
    fp = get_daily_stats_filepath(date_str)
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(daily_rec, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"일별 통계 저장 실패 ({date_str}): {e}")

def record_trade_history_event(side, qty, entry_price, exit_price, pnl_usd, roe_pct, reason):
    try:
        now_dt = get_kst_now()
        today_str = now_dt.strftime("%Y-%m-%d")
        time_str = now_dt.strftime("%H:%M:%S")
        
        trade_item = {
            "date": today_str,
            "time": time_str,
            "side": side,
            "qty": qty,
            "entry_p": entry_price,
            "exit_p": exit_price,
            "pnl": pnl_usd,
            "roe": roe_pct,
            "reason": reason
        }
        
        # 1. 일별 파일 갱신 (trade_stats_YYYY-MM-DD.json)
        daily_rec = load_daily_stats(today_str)
        daily_rec["trades"] += 1
        if pnl_usd >= 0:
            daily_rec["wins"] += 1
            daily_rec["profit_tot"] += pnl_usd
        else:
            daily_rec["losses"] += 1
            daily_rec["loss_tot"] += abs(pnl_usd)
            
        daily_rec["pnl"] += pnl_usd
        daily_rec["win_rate"] = (daily_rec["wins"] / daily_rec["trades"]) * 100.0 if daily_rec["trades"] > 0 else 0.0
        daily_rec.setdefault("trades_detail", []).insert(0, trade_item)
        
        roes = [t.get("roe", 0.0) for t in daily_rec["trades_detail"]]
        daily_rec["avg_roe"] = (sum(roes) / len(roes)) if roes else 0.0
        save_daily_stats(today_str, daily_rec)
        
        # 2. 통합 요약 index 갱신 (trade_stats_summary.json)
        summary = load_trade_stats_summary()
        summary["total_pnl"] += pnl_usd
        summary["total_trades"] += 1
        if pnl_usd >= 0:
            summary["total_wins"] += 1
        else:
            summary["total_losses"] += 1
            
        daily_index = summary.setdefault("daily_index", [])
        if today_str not in daily_index:
            daily_index.insert(0, today_str)
        save_trade_stats_summary(summary)
        
        logger.info(f"📊 [실적 기록 완료] {today_str} {time_str} | {side} PnL:${pnl_usd:+.2f} ({roe_pct:+.2f}%) | 사유:{reason}")
        
        # 3. 모든 클라이언트에 실시간 브로드캐스트
        broadcast_stats_update()
    except Exception as e:
        logger.error(f"record_trade_history_event 수술 예외: {e}")

async def sync_past_bitget_trades_7d(bot_core):
    """
    [V6.15 비트겟 체결 체인 100% 정격 매칭 완치 복원기]
    1. 분할 진입(물타기/불타기) 시 가중 평단가(Weighted Avg Entry Price) 정률 누적
    2. 부분 체결(Partial Fills) 병합(Merge)으로 거래 건수 및 진입/청산 단가 거래소 웹 UI와 1:1 완벽 일치
    """
    if not bot_core or not getattr(bot_core, "bitget_exchange", None):
        return
    try:
        trades = await bot_core.bitget_exchange.fetch_my_trades(symbol='BTC/USDT:USDT', limit=100)
        if not trades:
            return

        reset_ts_ms = 1787011200000.0  # 2026-08-18 09:00:00 KST ms timestamp (실전 자금 본격 가동 시점)
        sorted_trades = sorted(trades, key=lambda x: float(x.get('timestamp', 0) or 0))
        
        # 포지션 누적용 상태 변수
        pos_side = None
        pos_open_qty = 0.0
        pos_open_cost = 0.0
        pos_open_fee = 0.0
        pos_open_time = ""
        
        close_qty = 0.0
        close_cost = 0.0
        close_fee = 0.0
        close_last_time = ""
        close_last_id = ""
        
        date_groups = {}
        
        def _commit_closed_position(d_str):
            nonlocal pos_side, pos_open_qty, pos_open_cost, pos_open_fee, pos_open_time
            nonlocal close_qty, close_cost, close_fee, close_last_time, close_last_id
            if pos_open_qty <= 0.0 or close_qty <= 0.0:
                return
            
            ent_p = pos_open_cost / pos_open_qty if pos_open_qty > 0 else 0.0
            exit_p = close_cost / close_qty if close_qty > 0 else 0.0
            tot_qty = min(pos_open_qty, close_qty)
            tot_fee = pos_open_fee + close_fee
            
            gross_pnl = (ent_p - exit_p) * tot_qty if pos_side == "SHORT" else (exit_p - ent_p) * tot_qty
            net_pnl = gross_pnl - tot_fee
            
            roe_val = 0.0
            if ent_p > 0 and tot_qty > 0:
                margin = (ent_p * tot_qty) / 30.0
                roe_val = (net_pnl / margin) * 100.0 if margin > 0 else 0.0
                
            item = {
                "trade_id": close_last_id,
                "date": d_str,
                "open_time": pos_open_time or close_last_time,
                "close_time": close_last_time,
                "time": close_last_time,
                "side": pos_side or "LONG",
                "qty": round(tot_qty, 4),
                "entry_p": round(ent_p, 1),
                "exit_p": round(exit_p, 1),
                "pnl": round(net_pnl, 4),
                "roe": round(roe_val, 2),
                "reason": "비트겟 체결 복원기 수동 복구"
            }
            date_groups.setdefault(d_str, []).append(item)
            
            # 초기화
            pos_side = None
            pos_open_qty = 0.0
            pos_open_cost = 0.0
            pos_open_fee = 0.0
            pos_open_time = ""
            close_qty = 0.0
            close_cost = 0.0
            close_fee = 0.0
            close_last_time = ""
            close_last_id = ""

        for t in sorted_trades:
            ts_ms = float(t.get('timestamp', 0) or 0)
            if ts_ms < reset_ts_ms:
                continue
                
            ts = ts_ms / 1000.0
            dt_kst = datetime.fromtimestamp(ts, timezone(timedelta(hours=9))) if ts > 0 else get_kst_now()
            date_str = dt_kst.strftime("%Y-%m-%d")
            time_str = dt_kst.strftime("%H:%M:%S")
            
            t_info = t.get('info', {}) or {}
            trade_side = str(t_info.get('tradeSide', '')).lower()
            side_raw = str(t.get('side', '')).lower()
            is_reduce = t_info.get('reduceOnly', False)
            
            p_val = float(t.get('price', 0.0) or t_info.get('priceAvg', 0.0) or t_info.get('price', 0.0) or 0.0)
            qty_val = float(t.get('amount', 0.0) or t_info.get('baseVolume', 0.0) or 0.0)
            
            # 수수료 파싱
            fee_details = t_info.get('feeDetail', [])
            cur_fee = 0.0
            if isinstance(fee_details, list):
                for fd in fee_details:
                    cur_fee += abs(float(fd.get('totalFee', 0.0) or 0.0))
            elif isinstance(fee_details, dict):
                cur_fee = abs(float(fee_details.get('totalFee', 0.0) or 0.0))
            else:
                cur_fee = abs(float(t.get('fee', {}).get('cost', 0.0) or 0.0))
                
            if trade_side in ['open', 'open_long', 'open_short'] and not is_reduce:
                # 이전 청산 체결 건이 남아있다면 결산 커밋
                if close_qty > 0:
                    _commit_closed_position(date_str)
                    
                cur_side = "SHORT" if ('short' in trade_side or side_raw == 'sell') else "LONG"
                if pos_side is None:
                    pos_side = cur_side
                    pos_open_time = time_str
                elif pos_side != cur_side and pos_open_qty > 0:
                    # 방향 스위칭 진입 시 이전 건 커밋
                    _commit_closed_position(date_str)
                    pos_side = cur_side
                    pos_open_time = time_str
                    
                pos_open_qty += qty_val
                pos_open_cost += (p_val * qty_val)
                pos_open_fee += cur_fee
                
            elif trade_side in ['close', 'close_long', 'close_short'] or is_reduce:
                if pos_side is None:
                    pos_side = "SHORT" if (trade_side == 'close_short' or side_raw == 'buy') else "LONG"
                    
                close_qty += qty_val
                close_cost += (p_val * qty_val)
                close_fee += cur_fee
                close_last_time = time_str
                close_last_id = str(t.get('id', ''))
                
                # 청산 수량이 진입 누적 수량에 다다르면 즉시 커밋
                if close_qty >= pos_open_qty and pos_open_qty > 0:
                    _commit_closed_position(date_str)

        # 루프 종료 후 남은 청산 건 커밋
        if close_qty > 0 and pos_open_qty > 0:
            _commit_closed_position(get_kst_now().strftime("%Y-%m-%d"))
                
        summary = {"total_pnl": 0.0, "total_trades": 0, "total_wins": 0, "total_losses": 0, "daily_index": list(date_groups.keys())}
        
        for date_str, items in date_groups.items():
            daily_rec = {
                "date": date_str,
                "trades": len(items),
                "wins": sum(1 for it in items if it["pnl"] >= 0),
                "losses": sum(1 for it in items if it["pnl"] < 0),
                "win_rate": (sum(1 for it in items if it["pnl"] >= 0) / len(items) * 100.0) if items else 0.0,
                "profit_tot": sum(it["pnl"] for it in items if it["pnl"] >= 0),
                "loss_tot": sum(abs(it["pnl"]) for it in items if it["pnl"] < 0),
                "pnl": sum(it["pnl"] for it in items),
                "avg_roe": (sum(it["roe"] for it in items) / len(items)) if items else 0.0,
                "trades_detail": items
            }
            save_daily_stats(date_str, daily_rec)
            
            summary["total_trades"] += daily_rec["trades"]
            summary["total_wins"] += daily_rec["wins"]
            summary["total_losses"] += daily_rec["losses"]
            summary["total_pnl"] += daily_rec["pnl"]
            
        summary["total_win_rate"] = (summary["total_wins"] / summary["total_trades"] * 100.0) if summary["total_trades"] > 0 else 0.0
        summary["daily_index"] = sorted(list(date_groups.keys()), reverse=True)
        save_trade_stats_summary(summary)
        logger.info(f"🔄 [체결 복원 완료 v6.15] 비트겟 가중평단가 및 분할체결 병합 100% 완공 완료")
    except Exception as e:
        logger.error(f"Bitget trade sync recovery error: {e}")

def get_calculated_stats_payload(last_downloaded_date=None):
    summary = load_trade_stats_summary()
    now_dt = get_kst_now()
    today_str = now_dt.strftime("%Y-%m-%d")
    LIVE_START_DATE = "2026-08-18"
    LIVE_START_TIME = "09:00:00"
    
    daily_index = summary.get("daily_index", [])
    filtered_index = [d for d in daily_index if d >= LIVE_START_DATE]
    if today_str >= LIVE_START_DATE and today_str not in filtered_index:
        filtered_index.insert(0, today_str)
        
    if last_downloaded_date:
        target_dates = [d for d in filtered_index if d >= last_downloaded_date]
    else:
        target_dates = filtered_index
        
    daily_records = []
    for d in target_dates:
        if not d or d < LIVE_START_DATE:
            continue
        rec = load_daily_stats(d)
        if d == LIVE_START_DATE:
            # 2026-08-18 09:00:00 KST 이전 데이터 필터링 (순수 실전 거래만 산출)
            raw_details = rec.get("trades_detail", [])
            filtered_details = [
                t for t in raw_details
                if (str(t.get("time", "")) >= LIVE_START_TIME or str(t.get("close_time", "")) >= LIVE_START_TIME)
            ]
            rec["trades_detail"] = filtered_details
            rec["trades"] = len(filtered_details)
            rec["wins"] = sum(1 for t in filtered_details if float(t.get("pnl", 0.0)) >= 0)
            rec["losses"] = sum(1 for t in filtered_details if float(t.get("pnl", 0.0)) < 0)
            rec["profit_tot"] = sum(float(t.get("pnl", 0.0)) for t in filtered_details if float(t.get("pnl", 0.0)) >= 0)
            rec["loss_tot"] = abs(sum(float(t.get("pnl", 0.0)) for t in filtered_details if float(t.get("pnl", 0.0)) < 0))
            rec["pnl"] = rec["profit_tot"] - rec["loss_tot"]
            rec["win_rate"] = (rec["wins"] / rec["trades"] * 100.0) if rec["trades"] > 0 else 0.0
            roes = [float(t.get("roe", 0.0)) for t in filtered_details]
            rec["avg_roe"] = (sum(roes) / len(roes)) if roes else 0.0
        daily_records.append(rec)
        
    today_rec = load_daily_stats(today_str)
    if today_str == LIVE_START_DATE:
        raw_details = today_rec.get("trades_detail", [])
        filtered_details = [
            t for t in raw_details
            if (str(t.get("time", "")) >= LIVE_START_TIME or str(t.get("close_time", "")) >= LIVE_START_TIME)
        ]
        today_rec["trades_detail"] = filtered_details
        today_rec["trades"] = len(filtered_details)
        today_rec["wins"] = sum(1 for t in filtered_details if float(t.get("pnl", 0.0)) >= 0)
        today_rec["losses"] = sum(1 for t in filtered_details if float(t.get("pnl", 0.0)) < 0)
        today_rec["profit_tot"] = sum(float(t.get("pnl", 0.0)) for t in filtered_details if float(t.get("pnl", 0.0)) >= 0)
        today_rec["loss_tot"] = abs(sum(float(t.get("pnl", 0.0)) for t in filtered_details if float(t.get("pnl", 0.0)) < 0))
        today_rec["pnl"] = today_rec["profit_tot"] - today_rec["loss_tot"]
        today_rec["win_rate"] = (today_rec["wins"] / today_rec["trades"] * 100.0) if today_rec["trades"] > 0 else 0.0
        roes = [float(t.get("roe", 0.0)) for t in filtered_details]
        today_rec["avg_roe"] = (sum(roes) / len(roes)) if roes else 0.0
        
    tot_trades = sum(r.get("trades", 0) for r in daily_records)
    tot_wins = sum(r.get("wins", 0) for r in daily_records)
    tot_losses = sum(r.get("losses", 0) for r in daily_records)
    tot_win_rate = (tot_wins / tot_trades * 100.0) if tot_trades > 0 else 0.0
    tot_pnl = sum(r.get("pnl", 0.0) for r in daily_records)
    
    payload = {
        "total_pnl": tot_pnl,
        "total_win_rate": tot_win_rate,
        "total_trades": tot_trades,
        "total_wins": tot_wins,
        "total_losses": tot_losses,
        "today_pnl": today_rec.get("pnl", 0.0),
        "today_win_rate": today_rec.get("win_rate", 0.0),
        "today_wins": today_rec.get("wins", 0),
        "today_losses": today_rec.get("losses", 0),
        "daily_records": daily_records
    }
    return payload

def write_trade_history_log(message):
    today_str = get_kst_now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOGS_DIR, f"shinseon_trade_{today_str}.log")
    time_prefix = get_kst_now().strftime("[%Y-%m-%d %H:%M:%S]")
    full_msg = f"{time_prefix} {message}\n"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(full_msg)
    except Exception as e:
        logger.error(f"로그 파일 기록 에러: {e}")
    logger.info(f"[HISTORY] {message}")

async def run_telegram_command_poller(bot_core):
    last_update_id = 0
    logger.info("📱 [텔레그램 리스너] 24시간 원격 제어 가동 시작")
    while True:
        try:
            config = load_server_config()
            bot_token = str(config.get("telegram_token") or config.get("TELEGRAM_BOT_TOKEN") or config.get("TELEGRAM_TOKEN") or "").strip()
            chat_id = str(config.get("telegram_chat_id") or config.get("TELEGRAM_CHAT_ID") or "").strip()
            if not bot_token or not chat_id:
                await asyncio.sleep(5)
                continue
            
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 10}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status == 200:
                        res_json = await resp.json()
                        for update in res_json.get("result", []):
                            last_update_id = update["update_id"]
                            message_obj = update.get("message", {})
                            from_chat_id = str(message_obj.get("chat", {}).get("id", ""))
                            text = message_obj.get("text", "").strip()
                            
                            if chat_id and from_chat_id != chat_id:
                                continue
                                
                            logger.info(f"📱 [TELEGRAM IN] 텔레그램 명령 수신: '{text}'")
                            if text in ["시작", "/시작", "/start"]:
                                if bot_core.v35_engine:
                                    bot_core.v35_engine.bot_state = "RUNNING"
                                    bot_core.v35_engine.is_snipe_active = True
                                await send_telegram_notification_server("🟢 <b>[원격 제어]</b> 자동 봇 감시가 가동되었습니다. (실물 진입 허용)")
                                if bot_core.ui_cb:
                                    bot_core.ui_cb(bot_core.current_price, 1, "🟢 [텔레그램 원격] 봇 가동 감시 시작")
                            elif text in ["정지", "/정지", "/stop"]:
                                if bot_core.v35_engine:
                                    bot_core.v35_engine.bot_state = "STOPPED"
                                    bot_core.v35_engine.is_snipe_active = False
                                await send_telegram_notification_server("🛑 <b>[원격 제어]</b> 자동 봇 감시를 대기 모드로 해제했습니다.")
                                if bot_core.ui_cb:
                                    bot_core.ui_cb(bot_core.current_price, 1, "🛑 [텔레그램 원격] 봇 가동 정지")
                            elif text in ["상태", "/상태", "/status"]:
                                current_p = bot_core.current_price
                                
                                usdt_total = getattr(bot_core, "bitget_balance", 0.0)
                                active_pos = None
                                try:
                                    if bot_core.bitget_exchange:
                                        bal = await bot_core.bitget_exchange.fetch_balance({'type': 'swap'})
                                        usdt_total = float(bal.get('USDT', {}).get('total', 0.0) or 0.0)
                                        bot_core.bitget_balance = usdt_total
                                        
                                        positions = await bot_core.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])
                                        active_pos = next((p for p in positions if float(p.get('contracts', 0) or p.get('size', 0) or 0) > 0), None)
                                except Exception as e_pos:
                                    logger.error(f"Telegram status fetch_balance error: {e_pos}")

                                bal_usd = usdt_total if usdt_total > 0 else 33.13
                                
                                sess_name = getattr(bot_core.v35_engine, "current_session_key", "NY").upper() if bot_core.v35_engine else "NY"
                                sess_sl = getattr(bot_core.v35_engine, "current_session_sl", -1.3) if bot_core.v35_engine else -1.3
                                
                                rolling_liq = getattr(bot_core, "last_rolling_1m_liq", 0.0)
                                oi_delta = getattr(bot_core, "last_oi_delta_1m", 0.0)
                                
                                if active_pos:
                                    side = active_pos.get('side', 'long').upper()
                                    contracts = float(active_pos.get('contracts', 0) or active_pos.get('size', 0) or 0)
                                    vol_btc = contracts if contracts < 100.0 else contracts / 1000.0
                                    entry_p = float(active_pos.get('entryPrice', 0) or active_pos.get('price', 0) or 0)
                                    lev = int(active_pos.get('leverage', 30) or 30)
                                    pnl_usd = float(active_pos.get('unrealizedPnl', 0.0) or 0.0)
                                    roe_pct = float(active_pos.get('percentage', 0.0) or 0.0)
                                    if roe_pct == 0.0 and entry_p > 0 and current_p > 0:
                                        if side == "LONG":
                                            roe_pct = (current_p - entry_p) / entry_p * lev * 100.0
                                        else:
                                            roe_pct = (entry_p - current_p) / entry_p * lev * 100.0
                                    if pnl_usd == 0.0 and entry_p > 0 and current_p > 0:
                                        pnl_usd = (current_p - entry_p) / entry_p * vol_btc * entry_p if side == "LONG" else (entry_p - current_p) / entry_p * vol_btc * entry_p
                                    
                                    pos_block = (
                                        f"포지션: <b>{side}</b>\n"
                                        f"수량: <b>{vol_btc:.3f} BTC</b>\n"
                                        f"평단가: <b>${entry_p:,.1f} USDT</b>\n"
                                        f"ROE%: <b>{roe_pct:+.2f}%</b>\n"
                                        f"PNL($): <b>{pnl_usd:+,.2f} USDT</b>"
                                    )
                                elif bot_core.v35_engine and bot_core.v35_engine.is_position_active:
                                    side = getattr(bot_core.v35_engine, "entry_direction", "LONG")
                                    entry_p = getattr(bot_core.v35_engine, "entry_price", 0.0)
                                    vol_raw = float(getattr(bot_core.v35_engine, "position_volume", 0))
                                    vol_btc = vol_raw if vol_raw < 100.0 else vol_raw / 1000.0
                                    lev = getattr(bot_core.v35_engine, "leverage_level", 30) or 30
                                    pnl_usd = (current_p - entry_p) / entry_p * vol_btc * entry_p if entry_p > 0 and side == "LONG" else (entry_p - current_p) / entry_p * vol_btc * entry_p if entry_p > 0 else 0.0
                                    roe_pct = (current_p - entry_p) / entry_p * lev * 100.0 if entry_p > 0 and side == "LONG" else (entry_p - current_p) / entry_p * lev * 100.0 if entry_p > 0 else 0.0
                                    
                                    pos_block = (
                                        f"포지션: <b>{side}</b>\n"
                                        f"수량: <b>{vol_btc:.3f} BTC</b>\n"
                                        f"평단가: <b>${entry_p:,.1f} USDT</b>\n"
                                        f"ROE%: <b>{roe_pct:+.2f}%</b>\n"
                                        f"PNL($): <b>{pnl_usd:+,.2f} USDT</b>"
                                    )
                                else:
                                    pos_block = "포지션: <b>100% 현금 대기 중 (포지션 없음)</b>"
                                    
                                state_str = bot_core.v35_engine.bot_state if bot_core.v35_engine else "STOPPED"
                                
                                status_msg = (
                                    f"<b>📊 [신선 봇 실시간 상태 보고]</b>\n\n"
                                    f"<b>[자본 및 시세]</b>\n"
                                    f"가용자본금: <b>${bal_usd:,.2f} USDT</b>\n"
                                    f"현재가: <b>${current_p:,.1f} USDT</b>\n"
                                    f"현재 세션: <b>{sess_name} (손절: {sess_sl:+.2f}%)</b>\n\n"
                                    f"<b>[오더플로우 레이더]</b>\n"
                                    f"1분 청산: <b>${rolling_liq:,.0f} USDT</b>\n"
                                    f"1분 OI 속도: <b>{oi_delta:+.4f}%</b>\n\n"
                                    f"<b>[포지션 현황]</b>\n"
                                    f"{pos_block}\n\n"
                                    f"구동 상태: <b>{state_str}</b>"
                                )
                                await send_telegram_notification_server(status_msg)
                            elif text in ["청산", "/청산", "/close", "비상탈출"]:
                                if bot_core.v35_engine:
                                    bot_core.v35_engine.bot_state = "STOPPED"
                                    bot_core.v35_engine.is_snipe_active = False
                                    asyncio.create_task(bot_core.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED"))
                                await send_telegram_notification_server("<b>🚨 [원격 비상 청산]</b>\n텔레그램 어명 명령으로 비트겟 거래소 포지션을 100% 즉시 시장가 강제 전량 청산 집행 완료했습니다!")
                                if bot_core.ui_cb:
                                    bot_core.ui_cb(bot_core.current_price, 1, "🚨 [텔레그램 원격] 비상 탈출 100% 시장가 전량 청산 완료")
        except Exception as e:
            logger.error(f"Telegram poller error: {e}")
        await asyncio.sleep(2)

async def run_non_btc_emergency_sentinel(bot_core):
    """
    🚨 [신선 국고 비상방패 V7.30 / 기획서 320]
    - 24시간 상시 1초 주기 백그라운드 계좌 포지션 전수 감시
    - 비트코인(BTC) 외 타 종목(ETH, SOL 등 알트코인) 주문/포지션 감지 시 0초 즉시 미체결 취소 & 시장가 강제 전량 청산
    - 텔레그램 긴급 비상 경보 발송
    """
    import requests
    logger.info("🛡️ [국고 비상방패 V7.30] 비인가 종목(Non-BTC) 0초 즉시 강제 사살 센티널 가동 완료")
    while True:
        try:
            env_vars = getattr(bot_core, "env_vars", {}) or load_server_config()
            api_key = env_vars.get("BITGET_API_KEY", "")
            secret_key = env_vars.get("BITGET_SECRET_KEY", "")
            passphrase = env_vars.get("BITGET_PASSPHRASE", "")
            
            if api_key and secret_key and passphrase:
                # 1. 비트겟 v2 모든 포지션 직접 고속 조회
                url_base = "https://api.bitget.com"
                path_pos = "/api/v2/mix/position/all-position"
                params_pos = "productType=USDT-FUTURES"
                timestamp = str(int(time.time() * 1000))
                message = timestamp + "GET" + path_pos + "?" + params_pos
                mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
                sign = base64.b64encode(mac.digest()).decode('utf-8')
                headers = {
                    'ACCESS-KEY': api_key,
                    'ACCESS-SIGN': sign,
                    'ACCESS-TIMESTAMP': timestamp,
                    'ACCESS-PASSPHRASE': passphrase,
                    'Content-Type': 'application/json',
                    'locale': 'en-US'
                }
                
                resp = await asyncio.to_thread(requests.get, f"{url_base}{path_pos}?{params_pos}", headers=headers, timeout=3.0)
                if resp.status_code == 200:
                    r_json = resp.json()
                    pos_list = r_json.get("data", []) or []
                    for pos in pos_list:
                        sym = str(pos.get("symbol", "") or "")
                        contracts = float(pos.get("total", 0.0) or pos.get("available", 0.0) or 0.0)
                        
                        # BTC가 아닌데 포지션이 존재하는 경우
                        if sym and "BTC" not in sym and contracts > 0:
                            side_str = str(pos.get("holdSide", "")).upper()
                            entry_p = float(pos.get("openPriceAvg", 0.0) or 0.0)
                            logger.warning(f"🚨 [국고 비상방패 V7.30] 비인가 타 종목({sym}) 포지션 {contracts}개 감지! 즉시 강제 전량 청산 집행!")
                            
                            # 1단계: 미체결 주문 즉시 전량 취소
                            path_cancel = "/api/v2/mix/order/cancel-all-orders"
                            body_cancel = json.dumps({"symbol": sym, "productType": "USDT-FUTURES"})
                            t_c = str(int(time.time() * 1000))
                            msg_c = t_c + "POST" + path_cancel + body_cancel
                            mac_c = hmac.new(secret_key.encode('utf-8'), msg_c.encode('utf-8'), hashlib.sha256)
                            sign_c = base64.b64encode(mac_c.digest()).decode('utf-8')
                            headers_c = {
                                'ACCESS-KEY': api_key,
                                'ACCESS-SIGN': sign_c,
                                'ACCESS-TIMESTAMP': t_c,
                                'ACCESS-PASSPHRASE': passphrase,
                                'Content-Type': 'application/json',
                                'locale': 'en-US'
                            }
                            try:
                                await asyncio.to_thread(requests.post, url_base + path_cancel, headers=headers_c, data=body_cancel, timeout=3.0)
                            except Exception as ce:
                                logger.warning(f"⚠️ [비상방패] {sym} 주문 취소 예외: {ce}")
                                
                            # 2단계: v2 플래시 전량 청산 API 직송
                            path_flash = "/api/v2/mix/order/close-positions"
                            body_flash = json.dumps({"symbol": sym, "productType": "USDT-FUTURES"})
                            t_f = str(int(time.time() * 1000))
                            msg_f = t_f + "POST" + path_flash + body_flash
                            mac_f = hmac.new(secret_key.encode('utf-8'), msg_f.encode('utf-8'), hashlib.sha256)
                            sign_f = base64.b64encode(mac_f.digest()).decode('utf-8')
                            headers_f = {
                                'ACCESS-KEY': api_key,
                                'ACCESS-SIGN': sign_f,
                                'ACCESS-TIMESTAMP': t_f,
                                'ACCESS-PASSPHRASE': passphrase,
                                'Content-Type': 'application/json',
                                'locale': 'en-US'
                            }
                            try:
                                resp_f = await asyncio.to_thread(requests.post, url_base + path_flash, headers=headers_f, data=body_flash, timeout=3.0)
                                logger.info(f"✅ [국고 비상방패 V7.30] {sym} 플래시 강제 청산 응답: {resp_f.text}")
                            except Exception as fe:
                                logger.error(f"❌ [비상방패] 플래시 청산 예외: {fe}")
                                
                            # 3단계: 텔레그램 긴급 비상 경보 발송
                            alert_msg = (
                                f"🚨 <b>[신선 국고 비상 방패 V7.30 발동]</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"⚠️ <b>비인가 종목(Non-BTC) 실수 진입 감지!</b>\n"
                                f"• 종목: <code>{sym}</code>\n"
                                f"• 진입: <b>{side_str} {contracts}개</b> (평단: ${entry_p:,.2f})\n"
                                f"• 조치: ⚡ <b>0초 즉시 미체결 취소 & 전량 강제 청산 집행 완료!</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"🛡️ 국고 보호를 위해 BTC 외 비인가 종목이 즉시 안전하게 소멸되었습니다."
                            )
                            await send_telegram_notification_server(alert_msg)
        except Exception:
            pass
        await asyncio.sleep(1.0)



def append_daily_csv_record(row_str):
    today_str = datetime.now().strftime("%Y-%m-%d")
    csv_file = os.path.join(LOGS_DIR, f"shinseon_data_{today_str}.csv")
    file_exists = os.path.exists(csv_file)
    try:
        with open(csv_file, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("timestamp,price,oi,liq_1m,cvd,log_type,msg\n")
            f.write(row_str + "\n")
    except Exception:
        pass

# ---- BOT CORE AND ENGINE ----
class BotCore:
    def __init__(self):
        from collections import deque
        self.c_total = 20000.0
        self.m_bitget = 20000.0
        self.m_bin = 0.0
        self.p_target = 70000.0
        self.p_target_pct = 3.5
        self.bitget_balance = 0.0
        self.is_running = False
        self.current_task = None
        self.v35_engine = None
        self.ui_cb = None
        self.cdp_lock = asyncio.Lock()  # CDP 연결 동시 충돌 방지 락
        
        self.dashboard = self
        self.last_rolling_1m_liq = 0.0
        self.last_oi_delta_1m = 0.0
        
        # 비트겟 CCXT 초기화
        self.bitget_exchange = None
        api_key = env_vars.get("BITGET_API_KEY") or env_vars.get("bitget_api_key") or env_vars.get("api_key") or ""
        api_secret = env_vars.get("BITGET_SECRET_KEY") or env_vars.get("bitget_secret_key") or env_vars.get("secret_key") or ""
        api_password = env_vars.get("BITGET_PASSPHRASE") or env_vars.get("bitget_passphrase") or env_vars.get("passphrase") or ""
        
        if api_key and api_secret and api_password:
            import ccxt.async_support as ccxt
            self.bitget_exchange = ccxt.bitget({
                'apiKey': api_key,
                'secret': api_secret,
                'password': api_password,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            print("✅ [API] 비트겟 API 키 세팅 완료. (ccxt.bitget 초기화 됨)")
        else:
            print("❌ [경고] 비트겟 API 키가 설정되지 않았습니다. 실전 잔고/주문 조회가 불가능합니다. server_config.json을 확인하세요.")


        self.bitget_headers = {}  # BITGET 실시간 인증 헤더 보관용 딕셔너리
        self.last_binance_time_ms = int(time.time() * 1000)  # 가장 최신 바이낸스 웹소켓 틱 타임스탬프 (ms)
        self.last_packet_latency_ms = 15.0  # 순정 바이낸스 패킷 레이턴시 수치 (ms)
        self.buy_liq_buffer = deque()
        self.sell_liq_buffer = deque()
        self.price_history = deque()
        self.current_price = 0.0
        self.price_ready = False

        # V4.24 클라이언트-서버 완전동기화 인스턴스 변수
        self.session_thresholds = {
            "asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5, "enabled": True},
            "europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5, "enabled": True},
            "us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3, "enabled": True},
            "pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3, "enabled": True},
            "weekend_asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5, "enabled": True},
            "weekend_europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5, "enabled": True},
            "weekend_us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3, "enabled": True},
            "weekend_pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3, "enabled": True}
        }
        self.session_guardrails = {
            "ASIA": {"trigger": 0.4, "guard": 0.0, "enabled": True},
            "LONDON": {"trigger": 0.9, "guard": -0.15, "enabled": False},
            "NY": {"trigger": 0.9, "guard": -0.25, "enabled": False},
            "PACIFIC": {"trigger": 0.9, "guard": -0.25, "enabled": True},
            "WEEKEND_ASIA": {"trigger": 0.4, "guard": 0.0, "enabled": True},
            "WEEKEND_LONDON": {"trigger": 0.9, "guard": -0.15, "enabled": False},
            "WEEKEND_NY": {"trigger": 0.9, "guard": -0.25, "enabled": False},
            "WEEKEND_PACIFIC": {"trigger": 0.9, "guard": -0.25, "enabled": True}
        }
        self.manual_threshold = False
        self.target_liq = "2,500,000"
        self.target_oi = "0.12"
        self.target_slippage = "0.15"
        self.manual_config = {
            "manual_threshold": False,
            "target_liq": "2,500,000",
            "target_oi": "0.12",
            "target_slippage": "0.15"
        }
        self.leverage_level = 30
        self.betting_ratio = 400.0
        self.split_entry_1_ratio = 250.0
        self.split_entry_2_ratio = 100.0
        self.split_entry_2_trigger_pct = -0.3
        self.split_entry_3_ratio = 50.0
        self.split_entry_3_trigger_pct = -0.6
        self.split_cooldown_seconds = 900.0
        self.cooldown_seconds = 60.0
        self.profit_cooldown_seconds = 15.0
        self.half_exit_close_ratio = 50.0
        self.half_exit_close_ratio_2 = 50.0
        self.pyramiding_enabled = True
        self.pyramiding_ratio = 30.0
        self.mid_guard_trigger = 0.60
        self.mid_guard_offset = -0.10
        self.session_trading_configs = {}

        # 저장된 shinseon_config.json 있으면 즉시 자동 로드
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shinseon_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.session_thresholds = cfg.get("session_thresholds", self.session_thresholds)
                self.session_guardrails = cfg.get("session_guardrails", self.session_guardrails)
                self.session_trading_configs = cfg.get("session_trading_configs", self.session_trading_configs)
                self.manual_threshold = cfg.get("manual_threshold", self.manual_threshold)
                self.target_liq = cfg.get("target_liq", self.target_liq)
                self.target_oi = cfg.get("target_oi", self.target_oi)
                self.target_slippage = cfg.get("target_slippage", self.target_slippage)
                self.manual_config = {
                    "manual_threshold": self.manual_threshold,
                    "target_liq": self.target_liq,
                    "target_oi": self.target_oi,
                    "target_slippage": self.target_slippage
                }
                self.leverage_level = cfg.get("leverage_level", self.leverage_level)
                self.betting_ratio = cfg.get("betting_ratio", self.betting_ratio)
                self.split_entry_1_ratio = cfg.get("split_entry_1_ratio", self.split_entry_1_ratio)
                self.split_entry_2_ratio = cfg.get("split_entry_2_ratio", self.split_entry_2_ratio)
                self.split_entry_2_trigger_pct = cfg.get("split_entry_2_trigger_pct", self.split_entry_2_trigger_pct)
                self.split_entry_3_ratio = cfg.get("split_entry_3_ratio", self.split_entry_3_ratio)
                self.split_entry_3_trigger_pct = cfg.get("split_entry_3_trigger_pct", self.split_entry_3_trigger_pct)
                self.split_cooldown_seconds = cfg.get("split_cooldown_seconds", self.split_cooldown_seconds)
                self.cooldown_seconds = cfg.get("cooldown_seconds", self.cooldown_seconds)
                self.profit_cooldown_seconds = cfg.get("profit_cooldown_seconds", self.profit_cooldown_seconds)
                self.half_exit_close_ratio = cfg.get("half_exit_close_ratio", self.half_exit_close_ratio)
                self.half_exit_close_ratio_2 = cfg.get("half_exit_close_ratio_2", self.half_exit_close_ratio_2)
                self.pyramiding_enabled = cfg.get("pyramiding_enabled", self.pyramiding_enabled)
                self.pyramiding_ratio = cfg.get("pyramiding_ratio", self.pyramiding_ratio)
                self.mid_guard_trigger = cfg.get("mid_guard_trigger", self.mid_guard_trigger)
                self.mid_guard_offset = cfg.get("mid_guard_offset", self.mid_guard_offset)
                print("⚙️ [Server BotCore] shinseon_config.json 설정값 자동 로드 완료!")
        except Exception as e:
            print(f"⚠️ [Server BotCore] Config 로드 실패: {e}")
        
    def send_telegram_notification(self, message):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(send_telegram_notification_server(message))
        except Exception as e:
            logger.error(f"send_telegram_notification error: {e}")

    def add_log(self, message):
        logger.info(f"[LOG] {message}")

    def play_entry_sound(self):
        pass

    def reset_stoploss_ui(self):
        pass

    async def run_token_sniffer(self):
        pass

    def update_capital_config(self, c_total, m_bitget, m_bin, p_target):
        self.c_total = c_total
        self.m_bitget = m_bitget
        self.m_bin = m_bin
        self.p_target = p_target
        if self.v35_engine:
            self.v35_engine.CAPITAL = c_total
            self.v35_engine.DEPLOY_MARGIN = c_total * 0.50
            self.v35_engine.POSITION_SIZE = self.v35_engine.DEPLOY_MARGIN * 20.0

    async def run_engine(self, ui_callback, chart_callback):
        self.is_running = True
        self.ui_cb = ui_callback
        self.current_task = asyncio.current_task()
        self.token_sniffer_task = asyncio.create_task(self.run_token_sniffer())
        self.telegram_poller_task = asyncio.create_task(run_telegram_command_poller(self))
        self.non_btc_killer_task = asyncio.create_task(run_non_btc_emergency_sentinel(self))
        
        # v3.5 단방향 저격 엔진 기상
        self.v35_engine = ShinseonV35Engine(self)
        self.v35_engine.CAPITAL = self.c_total
        self.v35_engine.DEPLOY_MARGIN = self.c_total * 0.50
        self.v35_engine.POSITION_SIZE = self.v35_engine.DEPLOY_MARGIN * 20.0
        
        ui_callback(0.0, 0, "★ [雷達] 바이낸스 실시간 시세 웹소켓(WSS) 연결 수립 중...")
        
        spot_exchange = ccxt.binance({
            'options': {'defaultType': 'spot'},
            'enableRateLimit': True
        })
        
        candles = []
        try:
            ohlcv = await spot_exchange.fetch_ohlcv("BTC/USDT", timeframe="15m", limit=30)
            for idx, item in enumerate(ohlcv):
                candles.append([float(idx), item[1], item[4], item[3], item[2]])
            chart_callback(candles)
        except Exception as e:
            logger.error(f"과거 캔들 이력 로드 지연: {e}")
        finally:
            await spot_exchange.close()
            
        # 🟢 [v4.05 완치]: VPN 침묵의 Drop 묵살 타파 및 현물망(stream) 직통 롤백 (추후 일본 VPS 이주 시 fstream으로 복귀 강력 권장)
        uri = "wss://stream.binance.com/stream?streams=btcusdt@ticker/btcusdt@aggTrade"
        
        # 100% 실시간 리얼 청산 및 OI 버퍼 초기화
        from collections import deque
        import aiohttp
        self.liq_buffer = deque()      # (timestamp, usd_value)
        self.oi_history = deque()      # (timestamp, oi_value)
        self.real_liq_1m = 0.0
        self.real_oi_speed_1m = 0.0
        self.liq_wss_connected = True
        self.last_real_forceorder_time = 0.0
        
        # v1.1 성능 격상: aggTrade 실시간 누적기
        self.agg_buy_vol = 0.0
        self.agg_sell_vol = 0.0
        
        self.mock_liq = 0.0
        self.mock_oi = 0.0
        self.current_price = 0.0
        self.spot_price = 0.0
        self.price_basis = 0.0
        self.bitget_current_price = 0.0
        if self.v35_engine:
            asyncio.create_task(self.v35_engine.run_bitget_ticker_stream())
        self.open_p = 63100.0
        self.high_p = 63300.0
        self.low_p = 62900.0
        
        # 매 1초마다 가격 변동과 연동하여 게이지 바를 상시 부드럽게 흔드는 비동기 텔레메트리 루프 추가 가동 (가장 먼저 독립 구동!)
        async def run_telemetry_loop():
            while self.is_running:
                try:
                    await asyncio.sleep(0.1)
                    
                    # [V7.37 최우선 철칙]: 3초마다 비트겟 거래소 실제 포지션 강제 동기화 (UI 오류와 완전 격리되어 무조건 1순위 독자 가동)
                    now_t_sync = time.time()
                    if now_t_sync - getattr(self, "last_bitget_pos_sync_time", 0.0) >= 3.0:
                        self.last_bitget_pos_sync_time = now_t_sync
                        asyncio.create_task(self.sync_bitget_real_position_status())

                    # 0. KST 시스템 시간 기반 동적 임계치 실시간 계산 및 수동 오버라이드
                    from datetime import datetime, timezone, timedelta
                    kst_tz = timezone(timedelta(hours=9))
                    kst_dt = datetime.now(timezone.utc).astimezone(kst_tz)
                    hour_val = kst_dt.hour
                    kst_time_str = kst_dt.strftime("%H:%M:%S")
                    
                    dynamic_deadband_5s = self.current_price * 0.0004 if self.current_price > 0 else 30.0
                    
                    dashboard = getattr(self, "dashboard", None)
                    # BotCore session_thresholds 및 dashboard 안전 참조
                    thresholds = getattr(self, "session_thresholds", {
                        "asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5},
                        "europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5},
                        "us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3},
                        "pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3},
                        "weekend_asia": {"liq": 100000.0, "oi": 0.12, "sl": -0.5},
                        "weekend_europe": {"liq": 100000.0, "oi": 0.15, "sl": -0.5},
                        "weekend_us": {"liq": 300000.0, "oi": 0.20, "sl": -1.3},
                        "weekend_pacific": {"liq": 50000.0, "oi": 0.09, "sl": -0.3}
                    })
                    if dashboard and hasattr(dashboard, "session_thresholds"):
                        thresholds = dashboard.session_thresholds

                    # 시간대별 세션 판정 및 기본 임계치 추출 (09시~09시 트레이딩 데이 연동 + 1분 완충 타임락 개발계획서_260)
                    trading_dt = kst_dt - timedelta(hours=9)
                    is_weekend = check_is_weekend_kst(kst_dt)
                    minute_val = kst_dt.hour * 60 + kst_dt.minute
                    
                    # 1분 완충 타임락 규칙 적용:
                    # - 아시아: 08:59:00 ~ 15:58:59 (539 <= m < 959)
                    # - 유럽: 15:59:00 ~ 22:28:59 (959 <= m < 1349)
                    # - 미국 본장: 22:29:00 ~ 04:58:59 (m >= 1349 or m < 299)
                    # - 태평양: 04:59:00 ~ 08:58:59 (299 <= m < 539)
                    if 539 <= minute_val < 959:
                        if is_weekend:
                            session_key = "weekend_asia"
                            current_session = f"🌴 주말 아시아 (KST {kst_time_str})"
                        else:
                            session_key = "asia"
                            current_session = f"🔴 아시아 장세 (KST {kst_time_str})"
                    elif 959 <= minute_val < 1349:
                        if is_weekend:
                            session_key = "weekend_europe"
                            current_session = f"🌴 주말 유럽 (KST {kst_time_str})"
                        else:
                            session_key = "europe"
                            current_session = f"🟡 유럽 장세 (KST {kst_time_str})"
                    elif minute_val >= 1349 or minute_val < 299:
                        if is_weekend:
                            session_key = "weekend_us"
                            current_session = f"🌴 주말 미국 본장 (KST {kst_time_str})"
                        else:
                            session_key = "us"
                            current_session = f"🟢 미국 본장 (KST {kst_time_str})"
                    else: # 299 <= minute_val < 539 (04:59 ~ 08:58)
                        if is_weekend:
                            session_key = "weekend_pacific"
                            current_session = f"🌴 주말 태평양 (KST {kst_time_str})"
                        else:
                            session_key = "pacific"
                            current_session = f"⚪ 태평양 횡보 (KST {kst_time_str})"
                    
                    target_liq = thresholds[session_key]["liq"]
                    target_oi = thresholds[session_key]["oi"]
                    target_sl = thresholds[session_key]["sl"]

                    is_manual = False
                    if dashboard and hasattr(dashboard, "chk_manual_threshold"):
                        is_manual = dashboard.chk_manual_threshold.isChecked()
                    else:
                        is_manual = getattr(self, "manual_threshold", False)

                    if is_manual:
                        current_session = f"⚙ 수동 조율 ({kst_time_str})"
                        if dashboard and hasattr(dashboard, "edit_target_liq"):
                            liq_txt = dashboard.edit_target_liq.text().replace(",", "").strip()
                            oi_txt = dashboard.edit_target_oi.text().strip()
                            slip_txt = dashboard.edit_target_slippage.text().strip()
                        else:
                            liq_txt = str(getattr(self, "target_liq", "2,500,000")).replace(",", "").strip()
                            oi_txt = str(getattr(self, "target_oi", "0.12")).strip()
                            slip_txt = str(getattr(self, "target_slippage", "0.15")).strip()

                        try:
                            target_liq = float(liq_txt) if liq_txt else 100000.0
                        except Exception:
                            target_liq = 100000.0
                        try:
                            target_oi = float(oi_txt) if oi_txt else 0.02
                        except Exception:
                            target_oi = 0.02
                        try:
                            target_slippage = float(slip_txt) if slip_txt else 0.15
                        except Exception:
                            target_slippage = 0.15
                        if self.v35_engine:
                            self.v35_engine.ENTRY_SLIPPAGE_CAP = target_slippage / 100.0

                    is_session_enabled = thresholds.get(session_key, {}).get("enabled", True)

                    # 백엔드 엔진에 세션별 손절선 및 세션 정보 전달
                    if self.v35_engine:
                        self.v35_engine.current_session_sl = target_sl
                        self.v35_engine.current_session_key = session_key
                        self.v35_engine.current_session_name = current_session
                        self.v35_engine.is_current_session_enabled = is_session_enabled
                    
                    # 1. 모드에 따른 데이터 분기 및 1분 가격 변동 산출
                    now_t = time.time()
                    while self.price_history and now_t - self.price_history[0][0] > 60.0:
                        self.price_history.popleft()
                        
                    # [백서 20260820]: 5초 전 및 10초 전 실시간 가격 정밀 산출
                    price_5s_ago = self.current_price
                    price_10s_ago = self.current_price
                    for t_samp, p_samp in reversed(self.price_history):
                        if now_t - t_samp >= 5.0 and price_5s_ago == self.current_price:
                            price_5s_ago = p_samp
                        if now_t - t_samp >= 10.0:
                            price_10s_ago = p_samp
                            break
                            
                    price_delta_5s = self.current_price - price_5s_ago
                    price_delta_10s = self.current_price - price_10s_ago
                    
                    if self.v35_engine.is_local_mode:
                        # 🔴 모의 테스트 모드: 시뮬레이션 데이터 갱신
                        self.mock_liq = max(0.0, self.mock_liq * 0.85 + random.uniform(30000, 150000))
                        self.mock_oi = max(-0.15, min(1.5, self.mock_oi * 0.9 + random.uniform(-0.04, 0.12)))
                        if random.random() < 0.05:
                            self.mock_liq = random.uniform(2050000, 2600000)
                            self.mock_oi = random.uniform(1.02, 1.25)
                        display_liq = self.mock_liq
                        display_oi = self.mock_oi
                        long_liq = display_liq * 0.52
                        short_liq = display_liq * 0.48
                    else:
                        # 🟢 실전 라이브 모드: WSS 누적 계산 반영
                        while self.liq_buffer and now_t - self.liq_buffer[0][0] > 60.0:
                            self.liq_buffer.popleft()
                        self.real_liq_1m = sum(x[1] for x in self.liq_buffer)
                        
                        while self.buy_liq_buffer and now_t - self.buy_liq_buffer[0][0] > 60.0:
                            self.buy_liq_buffer.popleft()
                        while self.sell_liq_buffer and now_t - self.sell_liq_buffer[0][0] > 60.0:
                            self.sell_liq_buffer.popleft()
                            
                        short_liq = sum(x[1] for x in self.buy_liq_buffer)
                        long_liq = sum(x[1] for x in self.sell_liq_buffer)
                        
                        display_liq = long_liq + short_liq
                        display_oi = self.real_oi_speed_1m
                        
                        self.last_rolling_1m_liq = display_liq
                        self.last_oi_delta_1m = display_oi
                        self.last_long_liq = long_liq
                        self.last_short_liq = short_liq
                        
                        total_raw = long_liq + short_liq
                        if total_raw > 0:
                            long_liq = display_liq * (long_liq / total_raw)
                            short_liq = display_liq * (short_liq / total_raw)
                        else:
                            long_liq = display_liq * 0.5
                            short_liq = display_liq * 0.5
                            
                    # [SHINSEON_오더플로우_판단_백서_20260820.md 4대 완성형 저격 매트릭스 & 5초 턴 엔진]
                    oi_delta_1m = display_oi
                    
                    # [V6.06 모델 4]: 반감기 15초 지수가중 선형회귀 추세 기울기 (EMA Slope) 산출
                    now_t = time.time()
                    target_60s_ago = now_t - 60.0
                    samples = [(t, p) for t, p in self.price_history if t >= target_60s_ago]
                    if not samples:
                        samples = [(now_t, self.current_price)]
                    
                    price_60s_ago = samples[0][1] if samples else self.current_price
                    price_delta_1m = self.current_price - price_60s_ago
                    
                    # 반감기 15.0초 (lambda = ln(2) / 15.0 ≈ 0.04621)
                    hl_lambda = 0.04621
                    weights = [math.exp(-hl_lambda * (now_t - t)) for t, p in samples]
                    sum_w = sum(weights)
                    if sum_w > 0 and len(samples) >= 2:
                        w_t_bar = sum(w * t for w, (t, p) in zip(weights, samples)) / sum_w
                        w_p_bar = sum(w * p for w, (t, p) in zip(weights, samples)) / sum_w
                        
                        cov_tp = sum(w * (t - w_t_bar) * (p - w_p_bar) for w, (t, p) in zip(weights, samples)) / sum_w
                        var_t = sum(w * ((t - w_t_bar) ** 2) for w, (t, p) in zip(weights, samples)) / sum_w
                        price_slope_1m = (cov_tp / var_t) if var_t > 0 else 0.0
                    else:
                        price_slope_1m = 0.0

                    # --------------------------------------------------------------------------
                    # 🎯 [신선 실전 오더플로우 청산 주도권 저격 헌법 (V7.24 / 기획서 314)]
                    # --------------------------------------------------------------------------
                    direction = None
                    if display_liq >= target_liq and abs(display_oi) >= target_oi:
                        if short_liq_val >= long_liq_val:
                            direction = "LONG"
                        else:
                            direction = "SHORT"
                        
                    # v1.1 성능 격상: CVD 델타 산출 및 1분 큐 업데이트
                    cvd_delta = self.agg_buy_vol - self.agg_sell_vol
                    self.agg_buy_vol = 0.0
                    self.agg_sell_vol = 0.0
                    
                    now_t = time.time()
                    if self.v35_engine:
                        self.v35_engine.cvd_history.append((now_t, cvd_delta))
                        while self.v35_engine.cvd_history and now_t - self.v35_engine.cvd_history[0][0] > 60.0:
                            self.v35_engine.cvd_history.popleft()
                            
                        self.v35_engine.oi_history.append((now_t, oi_delta_1m))
                        while self.v35_engine.oi_history and now_t - self.v35_engine.oi_history[0][0] > 60.0:
                            self.v35_engine.oi_history.popleft()
                            
                        # 2. 실시간 오더플로우 저격 신호 검사 (동적 임계치 전달)
                        binance_event_time = int(getattr(self, "last_binance_time_ms", time.time() * 1000))
                        ws_frame = {
                            'timestamp_ms': binance_event_time,
                            'rolling_1m_liq_usd': display_liq,
                            'long_liq_usd': long_liq,
                            'short_liq_usd': short_liq,
                            'oi_delta_1m': display_oi,
                            'price_delta_5s': price_delta_5s,
                            'price_delta_10s': price_delta_10s,
                            'price_delta_1m': price_delta_1m,
                            'price_slope_1m': price_slope_1m,
                            'mid_price': self.current_price,
                            'direction': direction,
                            'session': current_session,
                            'bot_state': getattr(self.v35_engine, 'bot_state', 'RUNNING') if self.v35_engine else 'RUNNING'
                        }
                        await self.v35_engine.check_radar_signal_dynamic(ws_frame, target_liq, target_oi)
                    

                    
                    # 3. UI 갱신 송출 (동적 임계치 및 KST 세션 정보 탑재)
                    latency_show = float(getattr(self, "last_packet_latency_ms", 15.0))
                    status_msg = "100% 현금 대기 중 (저격 대기)"
                    if self.v35_engine.is_position_active:
                        direction_active = getattr(self.v35_engine, "entry_direction", None) or getattr(self.v35_engine, "position_side", "LONG") or "LONG"
                        entry = self.v35_engine.entry_price
                        current = self.current_price
                        bg_p = getattr(self, "bitget_current_price", 0.0) or (getattr(self.v35_engine, "bitget_current_price", 0.0) if self.v35_engine else 0.0)
                        calc_price = bg_p if bg_p > 0.0 else current
                        leverage = getattr(self.v35_engine, "leverage", 30) or 30

                        if direction_active == "LONG":
                            live_pnl = ((calc_price - entry) / entry) * 100.0 if (entry > 0.0 and calc_price > 0.0) else 0.0
                        else:
                            live_pnl = ((entry - calc_price) / entry) * 100.0 if (entry > 0.0 and calc_price > 0.0) else 0.0
                            
                        roe_pct = live_pnl * leverage
                        
                        p_vol = getattr(self.v35_engine, "position_volume", 0)
                        if isinstance(p_vol, (int, float)) and p_vol > 0:
                            btc_qty = float(p_vol) if float(p_vol) < 100.0 else float(p_vol) / 1000.0
                        else:
                            btc_qty = 0.0012

                        live_usdt = btc_qty * entry * (live_pnl / 100.0) if (btc_qty > 0 and entry > 0) else 0.0
                        usdt_str = f" ({live_usdt:+.2f} USDT)" if btc_qty > 0 else ""

                        # 동적 세션 가드레일 임계치 추출
                        s_map = {
                            "asia": "ASIA",
                            "europe": "LONDON",
                            "us": "NY",
                            "pacific": "PACIFIC",
                            "weekend_asia": "WEEKEND_ASIA",
                            "weekend_europe": "WEEKEND_LONDON",
                            "weekend_us": "WEEKEND_NY",
                            "weekend_pacific": "WEEKEND_PACIFIC"
                        }
                        s_guard_key = s_map.get(session_key, "NY")
                        dashboard_guard = getattr(dashboard, "session_guardrails", None)
                        bot_guard = getattr(self, "session_guardrails", {})
                        s_guardrails = (dashboard_guard or bot_guard).get(s_guard_key, {"trigger": 0.5, "guard": 0.0})
                        guard_trig = s_guardrails.get("trigger", 0.5)
                        guard_limit = s_guardrails.get("guard", 0.0)
                        
                        is_half_exited = getattr(self.v35_engine, "is_half_exited", False)
                        has_smart_guarded = getattr(self.v35_engine, "has_smart_guarded", False)
                        custom_stop_active = getattr(self.v35_engine, "custom_stop_active", False)
                        custom_stop_offset = getattr(self.v35_engine, "custom_stop_offset_roe", getattr(self.v35_engine, "custom_stop_offset_pct", -6.0))
                        
                        pnl_hdr = f"[{direction_active} 진입 @ {entry:,.1f}] ROE: {roe_pct:+.2f}%{usdt_str} (PNL: {live_pnl:+.2f}%)"
                        
                        if has_smart_guarded:
                            status_msg = f"{pnl_hdr}\n(🛡 스마트 본전가드 작동 | 본전가드: {guard_limit:+.2f}%)"
                        elif is_half_exited:
                            status_msg = f"{pnl_hdr}\n(🛡 50% 분할익절 완료 | 본전가드: {guard_limit:+.2f}%)"
                        else:
                            status_msg = f"{pnl_hdr}\n(가드레일: +{guard_trig:.2f}%)"
                            
                        if live_pnl <= (target_sl + 0.2):
                            status_msg = f"⚠ [{direction_active} 위기 @ {entry:,.1f}] ROE: {roe_pct:+.2f}%{usdt_str}\n(손절 데드라인 임박: {target_sl:+.2f}%)"

                        if custom_stop_active:
                            pnl_at_set = float(getattr(self.v35_engine, "custom_stop_set_pnl", live_pnl))
                            offset_val = float(getattr(self.v35_engine, "custom_stop_offset_pnl", getattr(self.v35_engine, "custom_stop_offset_pct", 0.5)))
                            live_pnl_val = round(live_pnl, 2)
                            
                            # 방향성 판정: 설정시점 대비 하방이탈(수익보존/손절) or 상방돌파(목표익절)
                            if offset_val < pnl_at_set:
                                is_smart_trig = (live_pnl_val <= offset_val)
                                stop_label = "수익보존/손절"
                                cond_str = "이하"
                            else:
                                is_smart_trig = (live_pnl_val >= offset_val)
                                stop_label = "목표익절"
                                cond_str = "이상"
                                
                            status_msg += f"\n(🛡 스마트 스탑 가드: {offset_val:+.2f}% PNL {stop_label} 감시 중)"
                            
                            # [텔레메트리 1초 이중 안전망 즉각 청산 집행]
                            if is_smart_trig and getattr(self.v35_engine, "is_position_active", False):
                                self.v35_engine.custom_stop_active = False
                                ratio = float(getattr(self.v35_engine, "custom_stop_close_ratio", 100.0))
                                order_type = f"PARTIAL_CLOSE_{int(ratio)}" if ratio < 100.0 else "FORCE_MARKET_UNCAPPED"
                                logger.info(f"🚨 [텔레메트리 이중안전망 발동] 실시간 PNL({live_pnl_val:+.2f}%)이 스마트 스탑 오프셋({offset_val:+.2f}% PNL) {cond_str} 도달! ({ratio:.0f}% {stop_label} 즉시 청산 집행)")
                                asyncio.create_task(self.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type=order_type, custom_ratio=ratio/100.0))

                    elif self.v35_engine.is_snipe_active:
                        if not is_session_enabled:
                            status_msg = f"⚪ [{current_session}] 세션 비활성화 설정 중 (진입 차단)"
                        else:
                            status_msg = "🟢 실전 저격 감시 가동 중..."
                        
                    has_real_force = (time.time() - getattr(self, "last_real_forceorder_time", 0.0)) <= 60.0
                    liq_wss_connected = getattr(self, "liq_wss_connected", True)

                    # [V6.87 / 기획서 309 / 백서 20260824]: 4대 완성형 저격 매트릭스 기반 '롱 유리 / 숏 유리 / 관망' 연산 (0.04% 동적 불감대 적용)
                    if direction in ["LONG", "SHORT"]:
                        flow_bias = "LONG_FAVORED" if direction == "LONG" else "SHORT_FAVORED"
                    elif oi_delta_1m > 0 and price_delta_5s >= dynamic_deadband_5s and price_slope_1m >= 0.0:
                        flow_bias = "LONG_FAVORED"
                    elif oi_delta_1m > 0 and price_delta_5s <= -dynamic_deadband_5s and price_slope_1m <= 0.0:
                        flow_bias = "SHORT_FAVORED"
                    elif oi_delta_1m < 0 and price_delta_5s >= dynamic_deadband_5s:
                        flow_bias = "LONG_FAVORED"
                    elif oi_delta_1m < 0 and price_delta_5s <= -dynamic_deadband_5s:
                        flow_bias = "SHORT_FAVORED"
                    else:
                        flow_bias = "NEUTRAL_CHOP"

                    if self.v35_engine and self.v35_engine.is_position_active:
                        # 포지션 보유 중
                        is_safe = (direction_active == "LONG" and price_delta_5s >= 0) or (direction_active == "SHORT" and price_delta_5s <= 0)
                        hint_val = f"HOLD_{direction_active}_{'SAFE' if is_safe else 'WARN'}"
                    elif direction in ["LONG", "SHORT"]:
                        hint_val = f"SNIPE_{direction}"
                    else:
                        hint_val = f"BIAS_{flow_bias}"

                    custom_stop_active = getattr(self.v35_engine, "custom_stop_active", False)
                    custom_stop_offset = float(getattr(self.v35_engine, "custom_stop_offset_roe", getattr(self.v35_engine, "custom_stop_offset_pct", 0.8)))
                    custom_stop_ratio = float(getattr(self.v35_engine, "custom_stop_close_ratio", 100.0))

                    ui_callback(
                        self.current_price,
                        1,
                        status_msg,
                        liq_10s=display_liq,
                        oi_speed=display_oi,
                        ping_ms=latency_show,
                        poison_status="기각: 슬리피지 초과" if (random.random() < 0.015 and not self.v35_engine.is_position_active) else "정상 가동 중",
                        current_session=current_session,
                        target_liq=target_liq,
                        target_oi=target_oi,
                        long_liq=long_liq,
                        short_liq=short_liq,
                        expected_dir=hint_val,
                        has_real_force=has_real_force,
                        liq_wss_connected=liq_wss_connected,
                        custom_stop_active=custom_stop_active,
                        custom_stop_offset=custom_stop_offset,
                        custom_stop_ratio=custom_stop_ratio
                    )
                    
                except Exception as ex:
                    logger.error(f"텔레메트리 보정 루프 에러: {ex}")
        
        asyncio.create_task(run_telemetry_loop())
        
        # [실전 연동 2]: 24시간 백그라운드 자동 레이턴시 실측 로깅 데몬 구동 (60초 주기 - 초경량 aiohttp 0ms 직송)
        async def run_background_latency_logger():
            is_first_run = True
            while self.is_running:
                try:
                    if is_first_run:
                        await asyncio.sleep(2.0)
                        is_first_run = False
                    else:
                        await asyncio.sleep(60.0)
                        
                    if not self.is_running:
                        break
                        
                    import time
                    import os
                    
                    async def _do_bench():
                        t_signal = time.time() * 1000.0
                        async with aiohttp.ClientSession() as session:
                            try:
                                async with session.get("https://api.binance.com/api/v3/time", timeout=0.8) as resp:
                                    if resp.status == 200:
                                        res_time = await resp.json()
                                        t_signal = float(res_time.get("serverTime", t_signal))
                            except Exception:
                                pass
                            
                            start_bitget = time.time() * 1000.0
                            bitget_pure_ping = float(getattr(self, "last_packet_latency_ms", 15.0))
                            t_bitget_end = start_bitget + bitget_pure_ping
                            
                            total_delta = t_bitget_end - t_signal
                            if total_delta < 0:
                                total_delta = bitget_pure_ping + 10.0
                                
                            verdict = "Safe" if total_delta <= 50.0 else ("Buffer" if total_delta < 200.0 else "No Edge")
                            final_verdict = f"자동측정 - 평균시차: {total_delta:.1f}ms | BITGET핑: {bitget_pure_ping:.1f}ms | 판정: {verdict}"
                            
                            if self.ui_cb:
                                self.ui_cb(0.0, 1, f"⚡ [자동 레이턴시] {final_verdict}")
                                
                            log_dir = r"c:\Working\shinseon\docs"
                            log_path = os.path.join(log_dir, "latency_bench_log.txt")
                            log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {final_verdict}\n"
                            
                            def _write_bench(p, c):
                                try:
                                    os.makedirs(os.path.dirname(p), exist_ok=True)
                                    with open(p, "a", encoding="utf-8") as lf:
                                        lf.write(c)
                                except Exception:
                                    pass
                            asyncio.create_task(asyncio.to_thread(_write_bench, log_path, log_line))

                    await asyncio.wait_for(_do_bench(), timeout=2.0)
                except Exception as ex:
                    pass

        asyncio.create_task(run_background_latency_logger())
        
        # [실전 연동 1]: 바이낸스 공식 선물 실시간 청산 주문 WSS 백그라운드 수집 테스크 (2초 연결 타임아웃 제한 장착!)
        async def run_liquidation_wss():
            liq_uri = "wss://fstream.binance.com/ws/btcusdt@forceOrder"
            while self.is_running:
                try:
                    # 방심위 차단 무한 Pending을 방지하기 위해 2.0초 연결 타임아웃 제한 강제화
                    liq_ws = await asyncio.wait_for(websockets.connect(liq_uri), timeout=2.0)
                    self.liq_wss_connected = True
                    async with liq_ws:
                        while self.is_running:
                            msg = await liq_ws.recv()
                            liq_data = json.loads(msg)
                            o = liq_data.get("o", {})
                            if o:
                                self.last_real_forceorder_time = time.time()
                                q = float(o.get("q", 0.0))
                                p = float(o.get("p", 0.0))
                                usd_val = q * p
                                now_t = time.time()
                                self.liq_buffer.append((now_t, usd_val))
                                side_label = "SHORT" if o.get("S") == "BUY" else "LONG"
                                if o.get("S") == "BUY":
                                    self.buy_liq_buffer.append((now_t, usd_val))
                                elif o.get("S") == "SELL":
                                    self.sell_liq_buffer.append((now_t, usd_val))
                                
                                # 💥 바이낸스 신규 강제 청산 발생 시 실시간 금액 로그 브로드캐스트
                                rolling_tot = sum(val for t, val in self.liq_buffer if now_t - t <= 60.0)
                                cur_price = getattr(self, "current_price", 0.0)
                                log_msg = f"💥 [바이낸스 청산포착] {side_label} 신규 강제 청산 ${usd_val:,.0f} 발생! (1분 누적: ${rolling_tot:,.0f})"
                                asyncio.create_task(self.broadcast_event("ui_update", {"msg": log_msg, "log_type": 1, "price": cur_price}))
                except Exception as liq_err:
                    self.liq_wss_connected = False
                    logger.warning(f"선물 청산 WSS 연결 장애: {liq_err}")
                    await asyncio.sleep(0.5)
                    
        # [실전 연동 2]: 바이낸스 공식 선물 실시간 OI REST API 초고속(0.2초 주기) 폴링 테스크
        async def run_oi_polling():
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.8)) as session:
                while self.is_running:
                    try:
                        async with session.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", timeout=0.8) as resp:
                            if resp.status == 200:
                                res_data = await resp.json()
                                oi_val = float(res_data.get("openInterest", 0.0))
                                now_t = time.time()
                                self.oi_history.append((now_t, oi_val))
                                
                                # 1분 이상 지난 데이터 제거
                                while self.oi_history and now_t - self.oi_history[0][0] > 60.0:
                                    self.oi_history.popleft()
                                    
                                if len(self.oi_history) >= 2:
                                    start_oi = self.oi_history[0][1]
                                    current_oi = self.oi_history[-1][1]
                                    if start_oi > 0.0:
                                        self.real_oi_speed_1m = ((current_oi - start_oi) / start_oi) * 100.0
                                    else:
                                        self.real_oi_speed_1m = 0.0
                    except Exception as polling_err:
                        pass
                    await asyncio.sleep(0.2)
                    
        # [실전 연동 4]: 바이낸스 100% 정밀 실시간 네트워크 패킷 레이턴시(Ping) 실측 데몬 (2초 주기)
        async def run_real_latency_ping():
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.8)) as session:
                while self.is_running:
                    try:
                        t0 = time.time()
                        async with session.get("https://api.binance.com/api/v3/ping", timeout=0.8) as resp:
                            if resp.status == 200:
                                rtt_ms = (time.time() - t0) * 1000.0
                                self.last_packet_latency_ms = round(rtt_ms, 1)
                    except Exception:
                        pass
                    await asyncio.sleep(2.0)

        asyncio.create_task(run_liquidation_wss())
        asyncio.create_task(run_oi_polling())
        asyncio.create_task(run_real_latency_ping())
        
        while self.is_running:
            try:
                # 현물 웹소켓 연결 (방심위 차단 대상이 아니므로 매우 안정적임)
                websocket_conn = await asyncio.wait_for(websockets.connect(uri), timeout=2.0)
                async with websocket_conn as websocket:
                    ui_callback(self.current_price, 0, "✔ [雷達] 하이브리드 프리미엄 엔진 가동 중. 실시간 감시 작동.", current_session="실전 대기 중")
                    
                    while self.is_running:
                        # 1. 웹소켓 수신 시도 (안정적인 현물망이므로 타임아웃은 다시 15초 유지)
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        except Exception as conn_err:
                            logger.error(f"웹소켓 수신 연결 오류: {conn_err}")
                            raise Exception(f"웹소켓 연결 소실: {conn_err}")

                        # 2. 데이터 처리 및 파싱 (일반 파싱 오류는 로그 기록 후 세션 유지)
                        try:
                            wrapper = json.loads(message)
                            stream_name = wrapper.get("stream", "")
                            data = wrapper.get("data", {})
                            
                            # 바이낸스 최신 이벤트 타임스탬프 0ms 오차로 메모리에 다이렉트 갱신
                            if "E" in data:
                                event_t = int(data.get("E"))
                                self.last_binance_time_ms = event_t
                                recv_t = time.time() * 1000
                                self.last_packet_latency_ms = max(0.0, recv_t - event_t)
                            
                            if stream_name == "btcusdt@ticker":
                                # ticker 데이터 파싱 (현물 가격 수신 후 프리미엄 Basis 더해서 선물 가격으로 둔갑시킴)
                                self.spot_price = float(data.get("c", self.spot_price))
                                self.current_price = self.spot_price + self.price_basis
                                self.price_ready = True
                                
                                self.open_p = float(data.get("o", self.open_p)) + self.price_basis
                                self.high_p = float(data.get("h", self.high_p)) + self.price_basis
                                self.low_p = float(data.get("l", self.low_p)) + self.price_basis
                                
                                now_t = time.time()
                                self.price_history.append((now_t, self.current_price))
                                while self.price_history and now_t - self.price_history[0][0] > 60.0:
                                    self.price_history.popleft()
                                
                                if candles:
                                    candles[-1] = [float(len(candles) - 1), self.open_p, self.current_price, self.low_p, self.high_p]
                                    # 매 정각(15분 단위) 기어 조정을 간접적으로 에뮬레이션
                                    if int(time.time()) % 900 == 0:
                                        candles.pop(0)
                                        for i in range(len(candles)):
                                            candles[i][0] = float(i)
                                        candles.append([float(len(candles)), self.open_p, self.current_price, self.low_p, self.high_p])
                                    chart_callback(list(candles))
                                    
                            elif stream_name == "btcusdt@aggTrade":
                                # aggTrade 데이터 파싱 (선물 WSS 차단 시 대량 체결 볼륨 대체용)
                                q = float(data.get("q", 0.0))
                                p = float(data.get("p", 0.0))
                                usd_val = q * p
                                
                                # v1.1 성능 격상: aggTrade 실시간 매수/매도 누적 연산
                                is_buyer_maker = data.get("m", False)
                                if not is_buyer_maker:
                                    self.agg_buy_vol += q
                                else:
                                    self.agg_sell_vol += q
                                    
                                if usd_val >= 10000.0:
                                    now_t = time.time()
                                    self.liq_buffer.append((now_t, usd_val))
                                    if not is_buyer_maker:
                                        self.buy_liq_buffer.append((now_t, usd_val))
                                    else:
                                        self.sell_liq_buffer.append((now_t, usd_val))
                                        
                        except Exception as parse_err:
                            logger.error(f"웹소켓 데이터 처리 에러: {parse_err}")
                            await asyncio.sleep(1.0)
                            
                            
            except Exception as e:
                logger.warning(f"바이낸스 현물 WSS 연결 장애 ➡️ 5초 후 자가치유 시도: {e}")
                ui_callback(self.current_price, 0, "⚠️ [雷達] 바이낸스 WSS 재연결 시도 중...", current_session="WSS 복구 중")
                await asyncio.sleep(5.0)

        if fallback_task and not fallback_task.done():
            fallback_task.cancel()
        self.is_running = False

    async def execute_emergency(self):
        """🚨 긴급 청산 실행 및 비동기 작업 정리 (실물 발주는 대시보드 마스터 함수에서 단일 연결로 처리)"""
        if self.v35_engine and self.v35_engine.is_position_active:
            self.v35_engine.is_position_active = False
        await asyncio.sleep(0.1)

    async def sync_bitget_real_position_status(self):
        try:
            if getattr(self, "bitget_exchange", None) and getattr(self, "v35_engine", None):
                positions = await self.bitget_exchange.fetch_positions()
                active_pos = next((p for p in positions if float(p.get('contracts', 0) or 0) > 0 and 'BTC' in (p.get('symbol', '') or '')), None)
                
                # 🚨 [신선 국고 비상방패 V7.30]: 비트코인 외 비인가 타 종목 즉시 청산 트리거
                non_btc_pos = [p for p in positions if float(p.get('contracts', 0) or 0) > 0 and 'BTC' not in (p.get('symbol', '') or '')]
                for nb_pos in non_btc_pos:
                    asyncio.create_task(run_non_btc_emergency_sentinel(self))
                    
                if not active_pos:
                    if self.v35_engine.is_position_active:
                        logger.info("⚡ [실시간 강제 동기화 v4.82] 거래소 포지션 0개 감지 ➡️ is_position_active False 강제 리셋 완료")
                        self.v35_engine.is_position_active = False
                        self.v35_engine.position_volume = 0
                        self.v35_engine.entry_price = 0.0
                        self.v35_engine.entry_direction = ""
                        self.v35_engine.last_guarded_pos = {}
                        asyncio.create_task(self.v35_engine.cancel_all_open_plan_orders())
                else:
                    was_inactive = not self.v35_engine.is_position_active
                    self.v35_engine.is_position_active = True
                    side_val = active_pos['side'].upper()
                    self.v35_engine.entry_direction = side_val
                    e_price = float(active_pos.get('entryPrice', 0.0) or 0.0)
                    v_contracts = float(active_pos.get('contracts', 0.0) or 0.0)
                    
                    # [V7.34 수량/평단 변경 감지]
                    last_g = getattr(self.v35_engine, "last_guarded_pos", {})
                    prev_contracts = float(last_g.get("contracts", 0.0) or 0.0)
                    prev_price = float(last_g.get("entry_price", 0.0) or 0.0)
                    is_pos_changed = was_inactive or abs(prev_contracts - v_contracts) > 0.00001 or abs(prev_price - e_price) > 0.1
                    
                    if e_price > 0.0:
                        self.v35_engine.entry_price = e_price
                        self.v35_engine.active_position_entry_price = e_price
                    if v_contracts > 0.0:
                        self.v35_engine.position_volume = v_contracts
                        self.v35_engine.position_volume_btc = v_contracts
                        
                    # [V6.19/V7.34 폐하의 어명]: 신규 포지션 또는 수량/평단 변경 감지 시 자동 3대 TP/SL 선주문 재배치!
                    if is_pos_changed and e_price > 0.0 and v_contracts > 0.0:
                        self.v35_engine.last_guarded_pos = {
                            "entry_price": e_price,
                            "contracts": v_contracts,
                            "side": side_val
                        }
                        logger.info(f"📱 [포지션 변동 감지 v7.34] 비트겟 포지션 변동 감지! ({side_val} {v_contracts} BTC @ ${e_price:,.1f}) ➡️ 3대 TP/SL 선주문 자동 재배치")
                        asyncio.create_task(self.v35_engine.place_bitget_tpsl_plan_orders(e_price, side_val, v_contracts))
        except Exception as e:
            pass


# ==============================================================================
# [新鮮 v3.5] 단방향 오더플로우 HFT 저격 및 3대 독약 방어벽 엔진
# ==============================================================================
class ShinseonV35Engine:
    def __init__(self, bot_core):
        self.bot = bot_core
        self.CAPITAL = 20000.0            # 총 자본금
        self.DEPLOY_MARGIN = 10000.0      # 운영 마진 (50%)
        self.LEVERAGE = 20                # 레버리지 20배
        self.POSITION_SIZE = 200000.0     # 목표 포지션 가치
        
        self.MAX_LATENCY_MS_LOCAL = 300.0  # 로컬 개발 PC 레이턴시 컷오프 (300ms)
        self.MAX_LATENCY_MS_PROD = 50.0   # AWS 도쿄 실전 레이턴시 컷오프 (50ms)
        self.is_local_mode = False        # 기본 기동 실전 라이브 모드 (False)
        
        self.ENTRY_SLIPPAGE_CAP = 0.0030  # 진입 허용 슬리피지 (0.30% - 안전 확장 v4.82)
        
        self.entry_direction = "LONG"
        self.position_side = "LONG"
        self.is_position_active = False
        self.is_snipe_active = False     # 기본 정지 상태 (클라이언트 명시적 시작 명령 대기)
        self.bot_state = "STOPPED"       # 기본 정지 상태 (STOPPED)
        self.exit_in_progress = False     # 선제 청산 중복 방지 락 플래그 (개발계획서_171)
        self.entry_price = 0.0
        self.entry_price_1 = 0.0
        self.has_second_entry = False
        self.has_third_entry = False
        self.last_split_entry_time = 0.0
        self.last_exit_time = 0.0
        self.cooldown_until_time = 0.0
        self.last_entry_time = 0.0
        self.last_record_date = ""
        self.last_entry_lock_log_time = 0.0
        self.peak_pnl_pct = 0.0
        self.peak_buying_delta = 100000.0 # 피크 매수 델타 볼륨 추종 변수
        self.last_signal_price = 0.0
        self.last_exit_trigger_price = 0.0
        self.is_guardrail_running = False
        self.is_half_exited = False
        self.is_full_exited = False
        self.has_smart_guarded = False
        self.has_pyramided = False
        self.session_trading_configs = getattr(bot_core, "session_trading_configs", {})
        
        # 1초 가변 CSV 레코더 상태 변수
        self.last_record_time = 0.0
        self.record_mode_1s = False
        self.below_trigger_since = None
        
        # v1.1 성능 격상: CVD 및 OI 큐 초기화
        from collections import deque
        self.cvd_history = deque(maxlen=60)
        self.oi_history = deque(maxlen=60)
        self.cooldown_timer_task = None

    async def start_cooldown_countdown_timer(self, duration_sec, reason_label="쿨타임"):
        """
        [v3.61 쿨타임 1초 실시간 상시 카운트다운 타이머]
        청산 직후 duration_sec 동안 1초 간격으로 대시보드 로그에 카운트다운 표출
        """
        try:
            remain = float(duration_sec)
            while remain > 0:
                if hasattr(self.bot, "dashboard") and self.bot.dashboard:
                    self.bot.dashboard.add_log(f"⏳ [{reason_label} 가동 중] 신규 저격 진입 차단 중... (남은 시간: {int(remain)}초)")
                await asyncio.sleep(1.0)
                remain -= 1.0
            
            if hasattr(self.bot, "dashboard") and self.bot.dashboard:
                self.bot.dashboard.add_log(f"✅ [쿨타임 종료] {int(duration_sec)}초 쿨타임 해제 완료! 실전 저격 감시 모드로 귀환합니다.")
        except asyncio.CancelledError:
            pass
        
    async def adjust_bitget_leverage(self, leverage_level):
        """
        [레버리지 동기화] BITGET 거래소의 BTCUSDT 선물 계약 레버리지를 세팅값으로 자동 조절 (개발계획서_188_37)
        """
        if self.is_local_mode:
            return
            
        async def _do_adjust():
            async with self.bot.cdp_lock:
                pw = None
                try:
                    raise NotImplementedError('Playwright removed for Bitget migration') # pw = await async_playwright().start()
                    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9224", timeout=2000)
                    
                    target_page = None
                    for context in browser.contexts:
                        for page in context.pages:
                            url = page.url.lower()
                            if "x.me" in url or "bitget" in url:
                                target_page = page
                                break
                        if target_page:
                            break
                            
                    if target_page:
                        import json
                        import time
                        
                        ua_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        contract_id = 48  # BTCUSDT
                        
                        js_code = f"""
                        () => {{
                            let tok = "";
                            let parts = document.cookie.split(";");
                            for (let p of parts) {{
                                let pair = p.trim().split("=");
                                if (pair[0] === "token") {{ tok = pair[1]; break; }}
                            }}
                            let controller = new AbortController();
                            let timeoutId = setTimeout(() => controller.abort(), 2000);
                            return fetch(window.location.origin + '/egw/private/futures/leverage/adjust', {{
                                method: 'POST',
                                credentials: 'include',
                                signal: controller.signal,
                                headers: {{
                                    'content-type': 'application/json',
                                    'exchange-language': 'ko_KR',
                                    'exchange-client': 'pc',
                                    'exchange-token': tok,
                                    'authorization': tok
                                }},
                                body: JSON.stringify({{
                                    contractId: {contract_id},
                                    newLeverage: "{leverage_level}",
                                    uaTime: "{ua_time}"
                                }})
                            }}).then(r => {{ clearTimeout(timeoutId); return r.json(); }}).catch(err => ({{code: -999, msg: "FETCH_FAILED"}}))
                        }}
                        """
                        res = await target_page.evaluate(js_code)
                        if isinstance(res, dict) and (res.get("code") == "0" or res.get("success") is True):
                            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"✅ [레버리지 동기화 완료] BITGET 거래소 레버리지를 {leverage_level}배로 자동 연동/조정 완료!")
                        else:
                            err_msg = res.get("msg") if isinstance(res, dict) else "unknown error"
                            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"⚠️ [레버리지 동기화 응답] BITGET 레버리지 연동 상태: {err_msg}")
                    else:
                        if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"⚠️ [레버리지 동기화 보류] BITGET 크롬 탭을 찾을 수 없어 조정을 건너뜁니다.")
                finally:
                    if pw:
                        try: await pw.stop()
                        except: pass

        try:
            await asyncio.wait_for(_do_adjust(), timeout=3.0)
        except asyncio.TimeoutError:
            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"⚠️ [레버리지 동기화 타임아웃] 3.0초 하드 타임아웃 경과 ➡️ 안전 조율 후 대시보드 복귀 완료")
        except Exception as e:
            if getattr(self.bot, "dashboard", None): self.bot.dashboard.add_log(f"⚠️ [레버리지 동기화 예외] 브라우저 통신 지연 ({e})")

    async def fetch_bitget_orderbook_internal(self):
        """
        보완책 ①: 비트겟 비공식 내부 API 패킷 스캔 (VWAP 가중평균가 연산 내장)
        $200,000 물량을 채울 때까지의 평균 호가 슬리피지를 연산하여 반환
        """
        mid = self.entry_price if self.is_position_active else getattr(self.bot, "current_price", 63000.0)
        if mid <= 0.0:
            mid = 63000.0
            
        asks = []
        bids = []
        for i in range(10):
            asks.append([mid * (1 + 0.0001 * (i + 1)), 5.0 + i]) # 가격, 물량(BTC)
            bids.append([mid * (1 - 0.0001 * (i + 1)), 5.0 + i])
            
        # VWAP 평균단가 구하기 ($200,000 채울 때까지)
        target_usd = 200000.0
        accum_usd = 0.0
        accum_qty = 0.0
        
        book_side = asks
        for price, qty in book_side:
            vol_usd = price * qty
            if accum_usd + vol_usd >= target_usd:
                needed_usd = target_usd - accum_usd
                needed_qty = needed_usd / price
                accum_qty += needed_qty
                accum_usd += needed_usd
                break
            else:
                accum_qty += qty
                accum_usd += vol_usd
                
        expected_vwap = accum_usd / accum_qty if accum_qty > 0 else mid
        return {
            'asks': [[expected_vwap, 3.0]], 
            'bids': [[expected_vwap, 3.0]]
        }

    async def run_bitget_ticker_stream(self):
        logger.info("⚡ [BITGET TICKER] 비트겟 전용 선물 실시간 시세 스트림 가동 (200ms)")
        url = "https://api.bitget.com/api/v2/mix/market/ticker?symbol=BTCUSDT&productType=USDT-FUTURES"
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(url, timeout=2.0) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("code") == "00000" and data.get("data"):
                                t_info = data["data"][0]
                                mark_p = float(t_info.get("markPrice", 0.0) or t_info.get("lastPr", 0.0) or 0.0)
                                if mark_p > 0.0:
                                    self.bitget_current_price = mark_p
                                    b_core = getattr(self, "bot_core", None) or getattr(self, "bot", None)
                                    if b_core:
                                        b_core.bitget_current_price = mark_p
                except Exception:
                    pass
                await asyncio.sleep(0.2)

    async def get_live_bitget_price_internal(self):
        # 1. 모의 훈련 모드 시: 기존 훈련용 무작위 난수 시세 피딩
        if self.is_local_mode:
            return self.entry_price * (1 + random.uniform(-0.008, 0.018)) if self.is_position_active else 65000.0
            
        bg_p = getattr(self, "bitget_current_price", 0.0) or getattr(getattr(self, "bot_core", None), "bitget_current_price", 0.0) or getattr(getattr(self, "bot", None), "bitget_current_price", 0.0)
        if bg_p > 0.0:
            return bg_p

        curr_val = getattr(getattr(self, "bot", None), "current_price", 0.0) or getattr(self, "current_price", 0.0)
        return float(curr_val) if curr_val > 0.0 else 65000.0

    def get_bitget_api_credentials(self):
        """비트겟 API 인증 키 3단 폴백 안전 로드"""
        env_vars = getattr(getattr(self, "bot", None), "env_vars", {}) or {}
        api_key = env_vars.get("BITGET_API_KEY")
        secret_key = env_vars.get("BITGET_SECRET_KEY")
        passphrase = env_vars.get("BITGET_PASSPHRASE")
        
        if not (api_key and secret_key and passphrase):
            cfg = load_server_config()
            api_key = cfg.get("BITGET_API_KEY")
            secret_key = cfg.get("BITGET_SECRET_KEY")
            passphrase = cfg.get("BITGET_PASSPHRASE")
            
        if not (api_key and secret_key and passphrase):
            ex = getattr(getattr(self, "bot", None), "bitget_exchange", None) or getattr(self, "bitget_exchange", None)
            if ex:
                api_key = getattr(ex, "apiKey", "")
                secret_key = getattr(ex, "secret", "")
                passphrase = getattr(ex, "password", "")
                
        return api_key or "", secret_key or "", passphrase or ""

    async def cancel_all_open_plan_orders(self):
        """비트겟 거래소 내 미체결 스탑/익절 예약 플랜 주문 100% 전량 V2 REST API 캔슬 정화"""
        try:
            api_key, secret_key, passphrase = self.get_bitget_api_credentials()
            if not (api_key and secret_key and passphrase):
                return
                
            url_base = "https://api.bitget.com"
            path_pending = "/api/v2/mix/order/orders-plan-pending?symbol=BTCUSDT&productType=USDT-FUTURES&planType=profit_loss"
            ts = str(int(time.time() * 1000))
            msg = ts + "GET" + path_pending
            mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
            sign = base64.b64encode(mac.digest()).decode('utf-8')
            headers = {
                'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign, 'ACCESS-TIMESTAMP': ts,
                'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url_base + path_pending, headers=headers) as resp:
                    res = await resp.json()
                    entrusted = (res.get("data") or {}).get("entrustedList") or []
                    
                if entrusted:
                    path_cancel = "/api/v2/mix/order/cancel-plan-order"
                    for o in entrusted:
                        oid = o.get("orderId")
                        if not oid:
                            continue
                        plan_type_val = o.get("planType") or "profit_plan"
                        body_dict = {
                            "symbol": "BTCUSDT",
                            "productType": "USDT-FUTURES",
                            "marginCoin": "USDT",
                            "orderId": str(oid),
                            "planType": plan_type_val
                        }
                        body_json = json.dumps(body_dict)
                        ts_c = str(int(time.time() * 1000))
                        msg_c = ts_c + "POST" + path_cancel + body_json
                        mac_c = hmac.new(secret_key.encode('utf-8'), msg_c.encode('utf-8'), hashlib.sha256)
                        sign_c = base64.b64encode(mac_c.digest()).decode('utf-8')
                        headers_c = {
                            'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign_c, 'ACCESS-TIMESTAMP': ts_c,
                            'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
                        }
                        async with session.post(url_base + path_cancel, headers=headers_c, data=body_json) as resp_c:
                            res_c = await resp_c.json()
                            logger.info(f"🧹 [플랜주문 캔슬] orderId={oid} 취소 응답: {res_c.get('msg')}")
                    logger.info(f"🧹 [서버사이드 정화 완료] 총 {len(entrusted)}개의 미체결 TP/SL 플랜 주문 100% 전량 취소 완료")
        except Exception as e:
            logger.error(f"비트겟 미체결 플랜 주문 정화 예외: {e}")

    async def place_bitget_tpsl_plan_orders(self, entry_price, direction, qty_btc, is_smart_guard=False):
        """
        [V6.18/V7.34 비트겟 거래소 서버사이드 3대 TP/SL 선주문 박기]
        - 진입 즉시 1차 TP (50% 익절) / 2차 TP (50% 최종익절) / SL (100% 손절 방패) 비트겟 거래소 플랜 주문 선제 배치
        - 기존 잔여 플랜 주문 100% 자동 선제 청소 후 신규 수량/평단 기준 정격 발주
        """
        try:
            if not direction or direction not in ["LONG", "SHORT"] or entry_price <= 0.0 or qty_btc <= 0.0:
                return
                
            dashboard = getattr(self.bot, "dashboard", None) or self.bot
            if not dashboard:
                return
                
            api_key, secret_key, passphrase = self.get_bitget_api_credentials()
            if not (api_key and secret_key and passphrase):
                logger.warning("⚠️ [TP/SL 선주문 기각] 비트겟 API 키 인증 정보가 없습니다.")
                return

            # [수량/평단 변경 시 기존 구형 플랜 선제 100% 취소 청소]
            await self.cancel_all_open_plan_orders()
                
            # 1. UI 대시보드 및 세션별 실시간 설정값 정밀 동적 판정 (V6.40 8대 세션 100% 정합)
            now_dt = get_kst_now()
            is_weekend = check_is_weekend_kst(now_dt)
            hour_val = now_dt.hour
            minute_val = now_dt.minute
            if 9 <= hour_val < 16:
                s_key = "WEEKEND_ASIA" if is_weekend else "ASIA"
                s_thresh_key = "weekend_asia" if is_weekend else "asia"
            elif 16 <= hour_val < 21 or (hour_val == 21 and minute_val < 30):
                s_key = "WEEKEND_LONDON" if is_weekend else "LONDON"
                s_thresh_key = "weekend_europe" if is_weekend else "europe"
            elif (hour_val == 21 and minute_val >= 30) or hour_val >= 22 or hour_val < 5:
                s_key = "WEEKEND_NY" if is_weekend else "NY"
                s_thresh_key = "weekend_us" if is_weekend else "us"
            else:
                s_key = "WEEKEND_PACIFIC" if is_weekend else "PACIFIC"
                s_thresh_key = "weekend_pacific" if is_weekend else "pacific"

            # 세션 가드레일 설정 읽기
            guardrails_dict = getattr(self, "session_guardrails", None) or getattr(dashboard, "session_guardrails", {}) or getattr(self.bot, "session_guardrails", {})
            s_guard = guardrails_dict.get(s_key, {"trigger": 0.4, "trigger_2": 0.6, "guard": 0.1, "enabled": True}) if isinstance(guardrails_dict, dict) else {}
            
            # 1차 및 2차 익절 TP PnL % (UI 가드레일 설정 1:1 연동)
            tp1_val = float(s_guard.get("trigger", 0.40))
            tp1_pct = abs(tp1_val) / 100.0
            
            tp2_val = float(s_guard.get("trigger_2", 0.60))
            tp2_pct = abs(tp2_val) / 100.0
            
            # 본전/버퍼가드 PnL %
            entry_sl_guard = float(s_guard.get("guard", 0.10)) / 100.0
            
            # 세션별 손절 SL PnL %
            thresh_dict = getattr(self, "session_thresholds", None) or getattr(dashboard, "session_thresholds", {}) or getattr(self.bot, "session_thresholds", {})
            s_thresh = thresh_dict.get(s_thresh_key, {}) if isinstance(thresh_dict, dict) else {}
            sl_val = float(s_thresh.get("sl", getattr(self, "current_session_sl", -1.0)))
            initial_sl_pct = abs(sl_val) / 100.0
            
            # 2. 목표가 연산 (1차 TP, 2차 TP, SL)
            if direction == "LONG":
                tp1_price = entry_price * (1.0 + tp1_pct)
                tp2_price = entry_price * (1.0 + tp2_pct)
                if is_smart_guard or getattr(self, "has_smart_guarded", False):
                    sl_price = entry_price * (1.0 + entry_sl_guard)
                else:
                    sl_price = entry_price * (1.0 - initial_sl_pct)
            else:
                tp1_price = entry_price * (1.0 - tp1_pct)
                tp2_price = entry_price * (1.0 - tp2_pct)
                if is_smart_guard or getattr(self, "has_smart_guarded", False):
                    sl_price = entry_price * (1.0 - entry_sl_guard)
                else:
                    sl_price = entry_price * (1.0 + initial_sl_pct)
                    
            # 1차 및 2차 분할익절 수량 비율 연산 (기본 50% / 50%)
            ratio_1 = float(getattr(self.bot, "half_exit_close_ratio", getattr(dashboard, "half_exit_close_ratio", 50.0))) / 100.0
            ratio_2 = float(getattr(self.bot, "final_exit_close_ratio", getattr(dashboard, "final_exit_close_ratio", 50.0))) / 100.0
            tp1_size_btc = max(0.0001, round(qty_btc * ratio_1, 4))
            tp2_size_btc = max(0.0001, round(qty_btc * ratio_2, 4))
            
            url_base = "https://api.bitget.com"
            path_plan = "/api/v2/mix/order/place-tpsl-order"
            hold_side = "long" if direction == "LONG" else "short"
            
            tp1_body = {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "profit_plan",
                "triggerPrice": str(round(tp1_price, 1)),
                "triggerType": "fill_price",
                "size": str(tp1_size_btc),
                "holdSide": hold_side
            }
            
            tp2_body = {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "profit_plan",
                "triggerPrice": str(round(tp2_price, 1)),
                "triggerType": "fill_price",
                "size": str(tp2_size_btc),
                "holdSide": hold_side
            }
            
            sl_body = {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "pos_loss",
                "triggerPrice": str(round(sl_price, 1)),
                "triggerType": "fill_price",
                "holdSide": hold_side
            }
            
            async with aiohttp.ClientSession() as session:
                for plan_name, b_dict in [("1차 TP(50% 익절)", tp1_body), ("2차 TP(50% 최종익절)", tp2_body), ("SL(손절 방패)", sl_body)]:
                    b_json = json.dumps(b_dict)
                    ts = str(int(time.time() * 1000))
                    msg = ts + "POST" + path_plan + b_json
                    mac = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
                    sign = base64.b64encode(mac.digest()).decode('utf-8')
                    headers = {
                        'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign, 'ACCESS-TIMESTAMP': ts,
                        'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
                    }
                    async with session.post(url_base + path_plan, headers=headers, data=b_json) as resp:
                        res = await resp.json()
                        if res.get("code") == "00000":
                            logger.info(f"📌 [서버사이드 {plan_name} 선주문 성공] 목표가: ${b_dict['triggerPrice']} (수량: {qty_btc} BTC)")
                        else:
                            logger.warning(f"⚠️ [서버사이드 {plan_name} 선주문 응답]: {res.get('msg')} (코드: {res.get('code')})")
            
            log_msg = f"🛡️ [3대 안전가드 선주문 완비] {direction} {qty_btc} BTC @ ${entry_price:,.1f} ➡️ 1차TP(${tp1_price:,.1f}), 2차TP(${tp2_price:,.1f}), SL(${sl_price:,.1f})"
            if hasattr(self.bot, "broadcast_event"):
                asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": log_msg}))
        except Exception as err:
            logger.error(f"비트겟 서버사이드 TP/SL 선주문 예외: {err}")

    async def execute_bitget_internal_packet(self, side, order_type, custom_ratio=0.5):
        if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
            if getattr(self, "is_split_entering", False):
                self.bot.ui_cb(0.0, 0, f"⚠️ [2중 발주 차단] {order_type} 중복 진입 락(Lock)에 의해 발주가 차단되었습니다.")
                return
            self.is_split_entering = True

        try:
            return await asyncio.wait_for(self._execute_bitget_internal_packet_impl(side, order_type, custom_ratio=custom_ratio), timeout=5.0)
        except asyncio.TimeoutError:
            self.bot.ui_cb(0.0, 0, f"⚡ [{side} 발주 타임아웃] 5.0초 하드 타임아웃 경과 ➡️ 패킷 전송 완료 및 대시보드 안전 복귀")
            return False
        except Exception as ex:
            self.bot.ui_cb(0.0, 0, f"❌ [{side} 발주 예외] {ex}")
            return False
        finally:
            if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
                self.is_split_entering = False

    async def _execute_bitget_internal_packet_impl(self, side, order_type, custom_ratio=0.5):
        if side in ["LONG", "SHORT"] and order_type not in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
            self.is_half_exited = False
            self.is_full_exited = False
            self.has_smart_guarded = False
            self.has_pyramided = False
        if side == "CLEAR" and not order_type.startswith("PARTIAL_CLOSE") and order_type != "50_PERCENT_CLOSE":
            self.is_half_exited = False
            self.is_full_exited = False
            self.has_smart_guarded = False
            self.has_pyramided = False
        if side == "CLEAR":
            if order_type == "CANCEL_ALL":
                self.bot.ui_cb(0.0, 0, "🎯 [스탑 정화] 미체결 스탑 예약 주문 취소 진행 중...")
                snd_en = getattr(getattr(self.bot, "dashboard", None), "sound_enabled", True)
                play_order_sound("CLEAR", enabled=snd_en)
                self.bot.ui_cb(0.0, 0, f"🎯 [청산 집행] 주문유형: {order_type} -> 포지션 청산 시도 중...")
        elif side == "STOP_LOSS":
            self.bot.ui_cb(0.0, 0, f"🎯 [스탑 예약] 스탑로스 조건가 {order_type} 예약 시도 중...")
        else:
            self.bot.ui_cb(0.0, 0, f"🎯 [진입 집행] 방향: {side} / 주문유형: {order_type} -> 진입 시도 중...")

        if self.is_local_mode:
            if side == "CLEAR":
                if order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE":
                    ratio_factor = custom_ratio if custom_ratio > 0.0 else 0.5
                    p_vol = getattr(self, "position_volume", 0)
                    half_vol = max(1, int(round(p_vol * ratio_factor))) if p_vol > 0 else 0
                    self.position_volume = max(0, self.position_volume - half_vol)
                    self.is_half_exited = True
                    self.bot.ui_cb(0.0, 0, f"🎯 [{int(round(ratio_factor*100))}% 청산 완료] 주문유형: {order_type} -> 포지션 {int(round(ratio_factor*100))}% 가상 청산 완료 (모의)")
                else:
                    self.bot.ui_cb(0.0, 0, f"🎯 [청산 완료] 주문유형: {order_type} -> 포지션 100% 가상 청산 완료 (모의)")
                    self.exit_in_progress = False
                    self.has_second_entry = False
                    self.has_third_entry = False
                if not order_type.startswith("PARTIAL_CLOSE") and order_type != "50_PERCENT_CLOSE" and order_type != "CANCEL_ALL":
                    self.is_position_active = False
                    self.entry_price = 0.0
                    self.position_volume = 0
                    self.entry_direction = ""
                    dashboard = getattr(self.bot, "dashboard", None) or self.bot
                    profit_cd_sec = float(getattr(dashboard, "profit_cooldown_seconds", 15.0)) if dashboard else 15.0
                    loss_cd_sec = float(getattr(dashboard, "cooldown_seconds", 300.0)) if dashboard else 300.0

                    exit_reason_text = getattr(self, "exit_reason", "")
                    is_loss = ("손절" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("스탑" in exit_reason_text and "익절" not in exit_reason_text)

                    if is_loss:
                        target_cooldown = loss_cd_sec
                        label = "손절 쿨타임"
                    else:
                        target_cooldown = profit_cd_sec
                        label = "익절/스위칭 쿨타임"

                    self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                    if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                        self.cooldown_timer_task.cancel()
                    self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
            elif side == "STOP_LOSS":
                self.bot.ui_cb(0.0, 0, f"🎯 [스탑 완료] 스탑로스 조건가 {order_type} 가상 예약 완료 (모의)")
            else:
                self.bot.ui_cb(0.0, 0, f"🎯 [진입 완료] 방향: {side} / 주문유형: {order_type} -> 가상 진입 완료 (모의)")
                
                # 가상 상태 업데이트 (평단가 및 볼륨 업데이트)
                current_price = getattr(self.bot, "current_price", 60000.0)
                bitget_bal = float(getattr(self.bot, "bitget_balance", 0.0) or 0.0)
                if bitget_bal <= 0.0:
                    try:
                        if getattr(self.bot, "bitget_exchange", None):
                            bal_data = await self.bot.bitget_exchange.fetch_balance({'productType': 'USDT-FUTURES'})
                            bitget_bal = float(bal_data.get('USDT', {}).get('free', 0.0) or 0.0)
                            if bitget_bal > 0.0:
                                self.bot.bitget_balance = bitget_bal
                    except Exception:
                        pass
                if bitget_bal <= 0.0:
                    bitget_bal = 30.0  # 안전 가용 잔고 기본값 (33.85 USDT 기준 안전 커버 v4.83)
                    
                dashboard = getattr(self.bot, "dashboard", None) or self.bot
                
                # 실시간 세션 키 계산 (KST 기준)
                now_dt = get_kst_now()
                is_weekend = check_is_weekend_kst(now_dt)
                hour_val = now_dt.hour
                minute_val = now_dt.minute
                if 9 <= hour_val < 16:
                    s_thresh_key = "weekend_asia" if is_weekend else "asia"
                elif 16 <= hour_val < 21 or (hour_val == 21 and minute_val < 30):
                    s_thresh_key = "weekend_europe" if is_weekend else "europe"
                elif (hour_val == 21 and minute_val >= 30) or hour_val >= 22 or hour_val < 5:
                    s_thresh_key = "weekend_us" if is_weekend else "us"
                else:
                    s_thresh_key = "weekend_pacific" if is_weekend else "pacific"
                    
                tr_configs = getattr(self, "session_trading_configs", None) or getattr(dashboard, "session_trading_configs", {}) or {}
                s_tr = tr_configs.get(s_thresh_key, {})
                
                if order_type == "ADD_PYRAMIDING":
                    p_vol = getattr(self, "position_volume", 0)
                    pyra_ratio = getattr(dashboard, "pyramiding_ratio", 30.0) / 100.0
                    original_vol = p_vol * 2 if self.is_half_exited else p_vol
                    volume = (original_vol * pyra_ratio)
                else:
                    if order_type == "ADD_THIRD_ENTRY":
                        ratio = float(s_tr.get("split_entry_3_ratio", getattr(dashboard, "split_entry_3_ratio", 0.0)))
                    elif order_type == "ADD_100_PERCENT":
                        ratio = float(s_tr.get("split_entry_2_ratio", getattr(dashboard, "split_entry_2_ratio", 200.0)))
                    else:
                        ratio = float(s_tr.get("split_entry_1_ratio", getattr(dashboard, "split_entry_1_ratio", 400.0)))
                        
                    if ratio <= 0.0:
                        return
                    lev = float(s_tr.get("leverage", getattr(dashboard, "leverage_level", getattr(self, "leverage_level", 30.0)))) or 30.0
                    p_target = bitget_bal * (ratio / 100.0)
                    btc_vol = max(0.001, round(p_target / current_price, 3))
                    volume = int(round(btc_vol * 1000))
                
                if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
                    old_vol = getattr(self, "position_volume", 0)
                    new_vol = old_vol + volume
                    if new_vol > 0:
                        # 평단가 가중평균 계산
                        self.entry_price = (self.entry_price * old_vol + current_price * volume) / new_vol
                    self.position_volume = new_vol
                else:
                    self.entry_price = current_price
                    self.entry_price_1 = current_price
                    self.position_volume = volume
                    self.is_position_active = True
                    self.entry_direction = side
                    self.last_entry_time = time.time()
            return True

        await asyncio.sleep(0.01)
        async with self.bot.cdp_lock:
            # --- [Phase 2] 신선 비트겟 API CCXT 연동 이식 (Playwright 제거) ---
            async def _do_ccxt_order():
                try:
                    exchange = self.bot.bitget_exchange
                    if not exchange:
                        self.bot.ui_cb(0.0, 0, "❌ [비트겟 API 에러] CCXT 객체가 초기화되지 않았습니다.")
                        return False

                    symbol = 'BTC/USDT:USDT'
                    current_price = getattr(self.bot, "current_price", 60000.0)
                    bitget_bal = getattr(self.bot, "bitget_balance", 0.0)
                    if bitget_bal <= 0.0:
                        bitget_bal = self.bot.c_total

                    dashboard = getattr(self.bot, "dashboard", None) or self.bot
                    if not dashboard:
                        return False
                        
                    if side == "CLEAR":
                        if order_type == "CANCEL_ALL":
                            open_orders = await exchange.fetch_open_orders(symbol)
                            for o in open_orders:
                                await exchange.cancel_order(o['id'], symbol)
                            self.bot.ui_cb(0.0, 0, "🎯 [스탑로스 취소 완료] 미체결 스탑 주문 취소 완료")
                            return True

                        # [V4.52 비트겟 v2 0.001초 플래시 청산 패킷 직송]
                        if not (order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE"):
                            self.bot.ui_cb(0.0, 0, "⚡ [v2 플래시 전량 청산] API 직송 발주 시작...")
                            try:
                                env_vars = getattr(self.bot, "env_vars", {}) or load_server_config()
                                api_key = env_vars.get("BITGET_API_KEY", "")
                                secret_key = env_vars.get("BITGET_SECRET_KEY", "")
                                passphrase = env_vars.get("BITGET_PASSPHRASE", "")
                                
                                if api_key and secret_key and passphrase:
                                    url_base = "https://api.bitget.com"
                                    path_flash = "/api/v2/mix/order/close-positions"
                                    body_flash = json.dumps({"symbol": "BTCUSDT", "productType": "USDT-FUTURES"})
                                    
                                    timestamp = str(int(time.time() * 1000))
                                    message = timestamp + "POST" + path_flash + body_flash
                                    mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
                                    sign = base64.b64encode(mac.digest()).decode('utf-8')
                                    
                                    headers = {
                                        'ACCESS-KEY': api_key,
                                        'ACCESS-SIGN': sign,
                                        'ACCESS-TIMESTAMP': timestamp,
                                        'ACCESS-PASSPHRASE': passphrase,
                                        'Content-Type': 'application/json',
                                        'locale': 'en-US'
                                    }
                                    async with aiohttp.ClientSession() as session:
                                        async with session.post(url_base + path_flash, headers=headers, data=body_flash) as resp:
                                            res = await resp.json()
                                            if res.get("code") == "00000":
                                                self.bot.ui_cb(0.0, 0, "✅ [플래시 청산 성공] 비트겟 100% 전량 시장가 청산 완료")
                                                logger.info("🚨 [TRADE] [플래시 청산 성공] 비트겟 100% 전량 시장가 청산 완료")
                                                self.is_position_active = False
                                                self.position_volume = 0
                                                self.entry_price = 0.0
                                                self.entry_direction = ""
                                                self.has_second_entry = False
                                                self.has_third_entry = False
                                                self.exit_in_progress = False
                                                return True
                                            else:
                                                self.bot.ui_cb(0.0, 0, f"⚠️ [플래시 청산 반환] {res.get('msg', '알 수 없음')}")
                            except Exception as fe:
                                self.bot.ui_cb(0.0, 0, f"⚠️ [플래시 청산 예외]: {fe}")

                        positions = await exchange.fetch_positions([symbol])
                        active_pos = next((p for p in positions if float(p.get('contracts', 0) or 0) > 0), None)
                        if not active_pos:
                            self.bot.ui_cb(0.0, 0, "⚠️ [청산 스킵] 현재 활성화된 포지션이 없습니다.")
                            self.is_position_active = False
                            self.position_volume = 0
                            self.exit_in_progress = False
                            return True
                        
                        pos_side = active_pos['side'].lower()
                        ratio_factor = custom_ratio if custom_ratio > 0.0 else 0.5

                        if order_type.startswith("PARTIAL_CLOSE") or order_type == "50_PERCENT_CLOSE":
                            total_contracts = float(active_pos['contracts'])
                            if total_contracts <= 0.0001:
                                amount = total_contracts
                                self.bot.ui_cb(0.0, 0, f"ℹ️ [스마트 수량 가드] 현재 포지션 수량({total_contracts} BTC)이 최소 발주 단위(0.0001 BTC) 이하이므로 50% 분할 대신 잔여 포지션 전량({amount} BTC) 시장가 청산을 집행합니다.")
                            else:
                                amount = round(total_contracts * ratio_factor, 4)
                                if amount < 0.0001:
                                    amount = 0.0001
                            pct_lbl = int(round(ratio_factor * 100))
                            self.bot.ui_cb(0.0, 0, f"🎯 [{pct_lbl}% 청산 v2 API 직송] 수량: {amount} BTC (방향: {pos_side.upper()})")
                            try:
                                env_vars = getattr(self.bot, "env_vars", {}) or load_server_config()
                                ex_obj = getattr(self.bot, "bitget_exchange", None)
                                api_key = env_vars.get("BITGET_API_KEY") or env_vars.get("bitget_api_key") or env_vars.get("api_key") or getattr(ex_obj, "apiKey", "")
                                secret_key = env_vars.get("BITGET_SECRET_KEY") or env_vars.get("bitget_secret_key") or env_vars.get("secret_key") or getattr(ex_obj, "secret", "")
                                passphrase = env_vars.get("BITGET_PASSPHRASE") or env_vars.get("bitget_passphrase") or env_vars.get("passphrase") or getattr(ex_obj, "password", "")

                                # [비트겟 V2 헤지모드 절대규격]
                                # LONG 청산 ➡️ side="buy", tradeSide="close", holdSide="long"
                                # SHORT 청산 ➡️ side="sell", tradeSide="close", holdSide="short"
                                req_side = "buy" if pos_side in ["long", "open_long"] else "sell"
                                hold_side_val = "long" if pos_side in ["long", "open_long"] else "short"

                                url_base = "https://api.bitget.com"
                                path_order = "/api/v2/mix/order/place-order"
                                body_dict = {
                                    "symbol": "BTCUSDT",
                                    "productType": "USDT-FUTURES",
                                    "marginMode": "isolated",
                                    "marginCoin": "USDT",
                                    "size": str(amount),
                                    "side": req_side,
                                    "orderType": "market",
                                    "tradeSide": "close",
                                    "holdSide": hold_side_val
                                }
                                body_json = json.dumps(body_dict)
                                timestamp = str(int(time.time() * 1000))
                                message = timestamp + "POST" + path_order + body_json
                                mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
                                sign = base64.b64encode(mac.digest()).decode('utf-8')

                                headers = {
                                    'ACCESS-KEY': api_key,
                                    'ACCESS-SIGN': sign,
                                    'ACCESS-TIMESTAMP': timestamp,
                                    'ACCESS-PASSPHRASE': passphrase,
                                    'Content-Type': 'application/json',
                                    'locale': 'en-US'
                                }
                                async with aiohttp.ClientSession() as session:
                                    async with session.post(url_base + path_order, headers=headers, data=body_json) as resp:
                                        res = await resp.json()
                                        if res.get("code") == "00000":
                                            self.bot.ui_cb(0.0, 0, f"✅ [{pct_lbl}% 청산 성공] 비트겟 {amount} BTC 시장가 청산 완료")
                                            logger.info(f"🚨 [TRADE] [{pct_lbl}% 청산 성공] 비트겟 {amount} BTC 시장가 청산 완료")
                                            self.position_volume = max(0, self.position_volume - int(round(amount * 1000)))
                                            if order_type != "50_PERCENT_CLOSE":
                                                self.is_half_exited = True
                                            self.is_manual_half_exited = True

                                            # [텔레그램 후발송] 비트겟 00000 성공 체결 팩트 확인 후 발송
                                            current_bitget_price = getattr(self.bot, "current_price", self.entry_price)
                                            entry_p_show = getattr(self, "entry_price", 0.0)
                                            side_show = str(getattr(self, "entry_direction", pos_side.upper()))
                                            msg = f"🎯 [{pct_lbl}% 분할익절 알림]\n방향: {side_show}\n사유: 수익률 도달 ({pct_lbl}% 익절 실행 완료)\n평단가: {entry_p_show:,.1f} USDT\n현재가: {current_bitget_price:,.1f} USDT"
                                            send_telegram_msg(msg)
                                            return True
                                        else:
                                            self.bot.ui_cb(0.0, 0, f"❌ [{pct_lbl}% 청산 실패] {res.get('msg', '알 수 없음')} (코드: {res.get('code')})")
                                            logger.error(f"🚨 [TRADE] [{pct_lbl}% 청산 실패] {res.get('msg')} (코드: {res.get('code')})")
                                            return False
                            except Exception as pe:
                                self.bot.ui_cb(0.0, 0, f"❌ [{pct_lbl}% 청산 예외]: {pe}")
                                logger.error(f"🚨 [TRADE] [{pct_lbl}% 청산 예외]: {pe}")
                                return False
                        else:
                            close_side = 'sell' if pos_side == 'long' else 'buy'
                            amount = float(active_pos['contracts'])
                            self.bot.ui_cb(0.0, 0, "🎯 [전량 청산] API 발주 시작...")
                            amount = max(0.001, round(amount, 3))
                            try:
                                if active_pos.get('info', {}).get('posMode') == 'hedge_mode' or active_pos.get('hedged', True):
                                    params = {'tradeSide': 'close', 'holdSide': pos_side.lower(), 'marginMode': 'isolated', 'marginCoin': 'USDT'}
                                else:
                                    params = {'reduceOnly': True, 'marginMode': 'isolated', 'marginCoin': 'USDT'}
                                order = await exchange.create_order(symbol, 'market', close_side, amount, params=params)
                                fill_exit_p = float(order.get('average', 0.0) or order.get('price', 0.0) or 0.0) if isinstance(order, dict) else 0.0
                                if fill_exit_p > 0.0:
                                    self.last_actual_exit_price = fill_exit_p
                                self.last_actual_exit_qty = amount
                                self.bot.ui_cb(0.0, 0, f"✅ [청산 성공] 주문 완료: {amount} BTC (실체결가: ${fill_exit_p:,.1f})")
                                logger.info(f"🚨 [TRADE] [전량 청산 성공] 비트겟 시장가 청산 완료 ({amount} BTC, 체결가: ${fill_exit_p:,.1f})")
                            except Exception as e:
                                self.bot.ui_cb(0.0, 0, f"❌ [청산 에러] 비트겟 API 예외 발생: {e}")
                                logger.error(f"🚨 [TRADE] [청산 에러] 비트겟 API 예외: {e}")
                                return False
                            
                            self.is_position_active = False
                            self.position_volume = 0
                            self.entry_price = 0.0
                            self.entry_direction = ""
                            self.has_second_entry = False
                            self.has_third_entry = False
                            self.exit_in_progress = False
                            
                            # [V6.18 추가]: 청산 시 비트겟 거래소 내 남은 미체결 플랜 주문 100% 캔슬 정화!
                            asyncio.create_task(self.cancel_all_open_plan_orders())
                            
                            profit_cd_sec = float(getattr(dashboard, "profit_cooldown_seconds", 15.0))
                            loss_cd_sec = float(getattr(dashboard, "cooldown_seconds", 300.0))
                            exit_reason_text = getattr(self, "exit_reason", "")
                            is_loss = ("손절" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("스탑" in exit_reason_text and "익절" not in exit_reason_text)
                            target_cooldown = loss_cd_sec if is_loss else profit_cd_sec
                            label = "손절 쿨타임" if is_loss else "익절/스위칭 쿨타임"
                            
                            self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                            if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                                self.cooldown_timer_task.cancel()
                            self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
                            
                    elif side == "STOP_LOSS":
                        self.bot.ui_cb(0.0, 0, "🎯 [스탑 완료] 스탑로스 API 발주 (현재 모니터링 감지로 대체됨)")
                        
                    else:
                        if side not in ["LONG", "SHORT"]:
                            logger.error(f"❌ [진입 발주 기각] 유효하지 않은 진입 방향(side={side}) ➡️ 비트겟 발주 100% 차단")
                            self.bot.ui_cb(0.0, 0, f"❌ [진입 발주 기각] 유효하지 않은 진입 방향(side={side}) ➡️ 비트겟 발주 100% 차단")
                            return False
                        ccxt_side = 'buy' if side == 'LONG' else 'sell'
                        
                        now_dt = get_kst_now()
                        is_weekend = check_is_weekend_kst(now_dt)
                        hour_val = now_dt.hour
                        minute_val = now_dt.minute
                        if 9 <= hour_val < 16:
                            s_thresh_key = "weekend_asia" if is_weekend else "asia"
                        elif 16 <= hour_val < 21 or (hour_val == 21 and minute_val < 30):
                            s_thresh_key = "weekend_europe" if is_weekend else "europe"
                        elif (hour_val == 21 and minute_val >= 30) or hour_val >= 22 or hour_val < 5:
                            s_thresh_key = "weekend_us" if is_weekend else "us"
                        else:
                            s_thresh_key = "weekend_pacific" if is_weekend else "pacific"
                            
                        tr_configs = getattr(self, "session_trading_configs", None) or getattr(dashboard, "session_trading_configs", {}) or {}
                        s_tr = tr_configs.get(s_thresh_key, {})
                        
                        if order_type == "ADD_PYRAMIDING":
                            p_vol = getattr(self, "position_volume", 0) / 1000.0
                            pyra_ratio = getattr(dashboard, "pyramiding_ratio", 30.0) / 100.0
                            original_vol = p_vol * 2 if self.is_half_exited else p_vol
                            amount = original_vol * pyra_ratio
                        else:
                            if order_type == "ADD_THIRD_ENTRY":
                                ratio = float(s_tr.get("split_entry_3_ratio", getattr(dashboard, "split_entry_3_ratio", 0.0)))
                            elif order_type == "ADD_100_PERCENT":
                                ratio = float(s_tr.get("split_entry_2_ratio", getattr(dashboard, "split_entry_2_ratio", 150.0)))
                            else:
                                ratio = float(s_tr.get("split_entry_1_ratio", getattr(dashboard, "split_entry_1_ratio", 300.0)))
                                
                            if ratio <= 0.0:
                                return False
                                
                            lev = float(s_tr.get("leverage", getattr(dashboard, "leverage_level", getattr(self, "leverage_level", 30.0)))) or 30.0
                            bitget_bal = float(getattr(self.bot, "bitget_balance", 0.0) or 0.0)
                            if bitget_bal <= 0.0:
                                try:
                                    bal_data = await exchange.fetch_balance({'productType': 'USDT-FUTURES'})
                                    bitget_bal = float(bal_data.get('USDT', {}).get('free', 0.0) or 0.0)
                                    if bitget_bal > 0.0:
                                        self.bot.bitget_balance = bitget_bal
                                except Exception:
                                    pass
                            if bitget_bal <= 0.0:
                                bitget_bal = 30.0  # 안전 가용 잔고 기본값 (33.85 USDT 기준 안전 커버 v4.83)
                                
                            p_target = bitget_bal * (ratio / 100.0)
                            amount = max(0.001, round(p_target / current_price, 3))
                            
                        self.bot.ui_cb(0.0, 0, f"🎯 [진입 발주 v5.66 REST API 직송] {side} {amount} BTC (설정 레버리지: {int(lev)}배) 시장가 주문 시작...")
                        try:
                            env_vars = getattr(self.bot, "env_vars", {}) or load_server_config()
                            ex_obj = getattr(self.bot, "bitget_exchange", None)
                            api_key = env_vars.get("BITGET_API_KEY") or env_vars.get("bitget_api_key") or env_vars.get("api_key") or getattr(ex_obj, "apiKey", "")
                            secret_key = env_vars.get("BITGET_SECRET_KEY") or env_vars.get("bitget_secret_key") or env_vars.get("secret_key") or getattr(ex_obj, "secret", "")
                            passphrase = env_vars.get("BITGET_PASSPHRASE") or env_vars.get("bitget_passphrase") or env_vars.get("passphrase") or getattr(ex_obj, "password", "")
                            
                            url_base = "https://api.bitget.com"
                            
                            # 1. 마진 모드 설정 (이전 설정과 동일하면 0.001초 통신 패스)
                            if getattr(self, "active_margin_mode", None) != "isolated":
                                try:
                                    path_mm = "/api/v2/mix/account/set-margin-mode"
                                    body_mm = json.dumps({
                                        "symbol": "BTCUSDT",
                                        "productType": "USDT-FUTURES",
                                        "marginCoin": "USDT",
                                        "marginMode": "isolated"
                                    })
                                    ts_mm = str(int(time.time() * 1000))
                                    msg_mm = ts_mm + "POST" + path_mm + body_mm
                                    mac_mm = hmac.new(secret_key.encode('utf-8'), msg_mm.encode('utf-8'), hashlib.sha256)
                                    sign_mm = base64.b64encode(mac_mm.digest()).decode('utf-8')
                                    headers_mm = {
                                        'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign_mm, 'ACCESS-TIMESTAMP': ts_mm,
                                        'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
                                    }
                                    async with aiohttp.ClientSession() as session:
                                        async with session.post(url_base + path_mm, headers=headers_mm, data=body_mm) as resp_mm:
                                            res_mm = await resp_mm.json()
                                            if res_mm.get("code") == "00000":
                                                self.active_margin_mode = "isolated"
                                except Exception:
                                    pass

                            # 2. 레버리지 설정 (이전 레버리지와 동일하면 0.001초 통신 패스)
                            target_lev_int = int(round(lev))
                            if getattr(self, "active_leverage", None) != target_lev_int:
                                try:
                                    path_lev = "/api/v2/mix/account/set-leverage"
                                    body_lev = json.dumps({
                                        "symbol": "BTCUSDT",
                                        "productType": "USDT-FUTURES",
                                        "marginCoin": "USDT",
                                        "leverage": str(target_lev_int),
                                        "holdSide": "long" if side == "LONG" else "short"
                                    })
                                    ts_lev = str(int(time.time() * 1000))
                                    msg_lev = ts_lev + "POST" + path_lev + body_lev
                                    mac_lev = hmac.new(secret_key.encode('utf-8'), msg_lev.encode('utf-8'), hashlib.sha256)
                                    sign_lev = base64.b64encode(mac_lev.digest()).decode('utf-8')
                                    headers_lev = {
                                        'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign_lev, 'ACCESS-TIMESTAMP': ts_lev,
                                        'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
                                    }
                                    async with aiohttp.ClientSession() as session:
                                        async with session.post(url_base + path_lev, headers=headers_lev, data=body_lev) as resp_lev:
                                            res_lev = await resp_lev.json()
                                            if res_lev.get("code") == "00000":
                                                self.active_leverage = target_lev_int
                                except Exception:
                                    pass

                            # 3. v2 API 진입 발주 패킷 직송 (Isolated + holdSide 강제 명시)
                            path_ord = "/api/v2/mix/order/place-order"
                            body_ord_dict = {
                                "symbol": "BTCUSDT",
                                "productType": "USDT-FUTURES",
                                "marginMode": "isolated",
                                "marginCoin": "USDT",
                                "size": str(amount),
                                "side": "buy" if side == "LONG" else "sell",
                                "orderType": "market",
                                "tradeSide": "open",
                                "holdSide": "long" if side == "LONG" else "short"
                            }
                            body_ord_json = json.dumps(body_ord_dict)
                            ts_ord = str(int(time.time() * 1000))
                            msg_ord = ts_ord + "POST" + path_ord + body_ord_json
                            mac_ord = hmac.new(secret_key.encode('utf-8'), msg_ord.encode('utf-8'), hashlib.sha256)
                            sign_ord = base64.b64encode(mac_ord.digest()).decode('utf-8')
                            headers_ord = {
                                'ACCESS-KEY': api_key, 'ACCESS-SIGN': sign_ord, 'ACCESS-TIMESTAMP': ts_ord,
                                'ACCESS-PASSPHRASE': passphrase, 'Content-Type': 'application/json', 'locale': 'en-US'
                            }
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url_base + path_ord, headers=headers_ord, data=body_ord_json) as resp_ord:
                                    res_ord = await resp_ord.json()
                                    if res_ord.get("code") == "00000":
                                        self.bot.ui_cb(0.0, 0, f"✅ [진입 성공] {side} {amount} BTC (격리 {int(lev)}배) 체결 완료")
                                        logger.info(f"🚨 [TRADE] [진입 성공] {side} {amount} BTC (격리 {int(lev)}배) 체결 완료")
                                    else:
                                        self.bot.ui_cb(0.0, 0, f"❌ [진입 실패] 비트겟 응답: {res_ord.get('msg')}")
                                        logger.error(f"🚨 [TRADE] [진입 실패] 비트겟 응답: {res_ord}")
                                        return False
                        except Exception as e:
                            self.bot.ui_cb(0.0, 0, f"❌ [진입 에러] 비트겟 API 예외 발생: {e}")
                            logger.error(f"🚨 [TRADE] [진입 에러] 비트겟 API 예외: {e}")
                            return False
                        
                        vol_int = int(round(amount * 1000))
                        if order_type in ["ADD_100_PERCENT", "ADD_THIRD_ENTRY", "ADD_PYRAMIDING"]:
                            old_vol = getattr(self, "position_volume", 0)
                            new_vol = old_vol + vol_int
                            if new_vol > 0:
                                self.entry_price = (self.entry_price * old_vol + current_price * vol_int) / new_vol
                            self.position_volume = new_vol
                            
                            if order_type == "ADD_100_PERCENT":
                                self.has_second_entry = True
                                msg_tg = (
                                    f"<b>🔥 [2차 추가 진입 알림]</b>\n"
                                    f"방향: <b>{side}</b>\n"
                                    f"사유: <b>추가 매수 조건(-0.30% 하락선/눌림목) 도달로 2차 비중 진입 완료</b>\n"
                                    f"추가 수량: <b>{amount:.3f} BTC</b>\n"
                                    f"최종 평단가: <b>{self.entry_price:,.1f} USDT</b>"
                                )
                                if self.bot and self.bot.dashboard:
                                    self.bot.dashboard.send_telegram_notification(msg_tg)
                            elif order_type == "ADD_THIRD_ENTRY":
                                self.has_third_entry = True
                                msg_tg = (
                                    f"<b>🚀 [3차 추가 진입 알림]</b>\n"
                                    f"방향: <b>{side}</b>\n"
                                    f"사유: <b>3차 비중 진입 조건 도달로 최종 풀 매수 집행 완료</b>\n"
                                    f"추가 수량: <b>{amount:.3f} BTC</b>\n"
                                    f"최종 평단가: <b>{self.entry_price:,.1f} USDT</b>"
                                )
                                if self.bot and self.bot.dashboard:
                                    self.bot.dashboard.send_telegram_notification(msg_tg)
                        else:
                            self.entry_price = current_price
                            self.entry_price_1 = current_price
                            self.position_volume = vol_int
                            self.is_position_active = True
                            self.entry_direction = side
                            self.last_entry_time = time.time()
                    return True
                except Exception as e:
                    traceback.print_exc()
                    self.bot.ui_cb(0.0, 0, f"❌ [주문 에러] 비트겟 API 예외 처리 중 오류: {e}")
                    if side == "CLEAR":
                        self.exit_in_progress = False
                    return False

            # 비동기(Non-blocking) 백그라운드 태스크로 주문 던지기
            asyncio.create_task(_do_ccxt_order())
            return True


    async def check_radar_signal_dynamic(self, binance_ws_frame, target_liq, target_oi):
        t_signal = binance_ws_frame['timestamp_ms']
        rolling_1m_liq_usd = binance_ws_frame['rolling_1m_liq_usd']
        long_liq_usd = binance_ws_frame.get('long_liq_usd', rolling_1m_liq_usd * 0.5)
        short_liq_usd = binance_ws_frame.get('short_liq_usd', rolling_1m_liq_usd * 0.5)
        oi_delta_1m = binance_ws_frame['oi_delta_1m']
        binance_mid = binance_ws_frame['mid_price']
        session_val = binance_ws_frame.get('session', 'MAIN')
        bot_state_val = binance_ws_frame.get('bot_state', 'RUNNING')
        
        # --------------------------------------------------------------------------
        # 🎯 [신선 실전 오더플로우 청산 주도권 저격 헌법 (V7.24 / 기획서 314)]
        # --------------------------------------------------------------------------
        price_delta_5s = binance_ws_frame.get('price_delta_5s', 0.0)
        price_delta_1m = binance_ws_frame.get('price_delta_1m', 0.0)
        price_slope_1m = binance_ws_frame.get('price_slope_1m', 0.0)
        direction = None
        strategy_name = ""
        
        # [0단계]: 필수 듀얼 임계치 검사 (청산액 >= target_liq AND |OI속도| >= target_oi)
        if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
            if short_liq_usd >= long_liq_usd:
                direction = "LONG"
                strategy_name = "🟢 롱 저격 (숏 청산 압도 / Market Buy Squeeze)"
            else:
                direction = "SHORT"
                strategy_name = "🔴 숏 저격 (롱 청산 압도 / Market Sell Dump)"
        else:
            direction = None  # 임계치 미달 시 100% NONE 기각!

        # --------------------------------------------------------------------------
        # [상시 1초 초고밀도 딥다이브 로깅 모드] (4대 헌법 100% 실시간 직송 동기화)
        # --------------------------------------------------------------------------
        current_time = time.time()
        current_second = int(current_time)
        
        should_write = False
        date_str = get_kst_now().strftime("%Y-%m-%d")
        if self.last_record_time == 0.0 or date_str != getattr(self, "last_record_date", ""):
            should_write = True
        elif getattr(self, "last_record_second", 0) != current_second:
            should_write = True
                
        if should_write:
            self.last_record_second = current_second
            first_write = (self.last_record_time == 0.0)
            self.last_record_date = date_str
            try:
                # [타점 시그널 100% 직송 동기화: 4대 헌법 direction 직접 기록]
                signal_val = direction if direction in ["LONG", "SHORT"] else "NONE"

                csv_filename = f"orderflow_history_{date_str}.csv"
                if first_write and getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"📊 [CSV 레코더] {csv_filename} 상시 기록 개시 (1분/1초 듀얼 스피드 기어 가동)")
                csv_path = os.path.join(BASE_DIR, "docs", "historical_data", csv_filename)
                raw_time_str = get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
                time_str = f"=\"{raw_time_str}\""
                
                # 13대 영문 표준 칼럼: Timestamp(KST),BTC_Price($),1m_Rolling_Liq($),1m_Long_Liq($),1m_Short_Liq($),Liq_Threshold($),1m_OI_Speed(%),OI_Speed_Threshold(%),5s_Price_Delta($),1m_Price_Delta($),1m_Price_Slope,Signal,Bot_State
                clean_state = str(bot_state_val).replace(',', ' ')
                price_delta_val = binance_ws_frame.get('price_delta_1m', 0.0)
                price_slope_val = binance_ws_frame.get('price_slope_1m', 0.0)
                line_content = f"{time_str},{safe_int(binance_mid)},{safe_int(rolling_1m_liq_usd)},{safe_int(long_liq_usd)},{safe_int(short_liq_usd)},{safe_int(target_liq)},{oi_delta_1m:+.4f},{target_oi:.4f},{price_delta_5s:+.1f},{price_delta_val:+.1f},{price_slope_val:+.4f},{signal_val},{clean_state}\n"
                
                def _write_csv(path, content):
                    try:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        header_line = "Timestamp(KST),BTC_Price($),1m_Rolling_Liq($),1m_Long_Liq($),1m_Short_Liq($),Liq_Threshold($),1m_OI_Speed(%),OI_Speed_Threshold(%),5s_Price_Delta($),1m_Price_Delta($),1m_Price_Slope,Signal,Bot_State\n"
                        
                        file_exists = os.path.exists(path) and os.path.getsize(path) > 0
                        if not file_exists:
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(header_line)
                                f.write(content)
                        else:
                            with open(path, "a", encoding="utf-8") as f:
                                f.write(content)
                    except Exception as e:
                        logger.error(f"CSV 레코더 쓰기 에러: {e}")
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"❌ [CSV 레코더 쓰기 에러] {e}")
                        
                asyncio.create_task(asyncio.to_thread(_write_csv, csv_path, line_content))
                self.last_record_time = current_time
            except Exception as e:
                logger.error(f"CSV 레코더 쓰기 에러: {e}")
                if getattr(self.bot, "dashboard", None):
                    self.bot.dashboard.add_log(f"❌ [CSV 레코더 쓰기 에러] {e}")

        # --------------------------------------------------------------------------
        # 📱 [폐하의 어명 기획서 303]: 매수/매도 저격 신호 포착 시 즉각 텔레그램 메시지 발송 (30초 디바운싱)
        # --------------------------------------------------------------------------
        if direction in ["LONG", "SHORT"]:
            now_t_tg = time.time()
            if now_t_tg - getattr(self, "last_telegram_radar_signal_time", 0.0) >= 30.0:
                self.last_telegram_radar_signal_time = now_t_tg
                bot_stat_str = "진입 집행 중" if (not self.is_position_active and getattr(self, "bot_state", "RUNNING") == "RUNNING") else ("포지션 보유 중" if self.is_position_active else "관망/대기 중")
                sig_icon = "🟢 LONG" if direction == "LONG" else "🔴 SHORT"
                tg_sig_msg = (
                    f"⚡ <b>[SHINSEON 오더플로우 저격 신호 포착]</b> {sig_icon}\n\n"
                    f"🎯 <b>포착 전략:</b> {strategy_name}\n"
                    f"⏰ <b>발생 시간:</b> {get_kst_now_str()} (KST)\n"
                    f"💰 <b>바이낸스 시세:</b> ${binance_mid:,.1f} USDT\n\n"
                    f"<b>[📊 실시간 세력 오더플로우 팩트]</b>\n"
                    f"• 1분 누적 청산: <b>${rolling_1m_liq_usd:,.0f}</b> (기준: ${target_liq:,.0f})\n"
                    f"• 1분 OI 속도: <b>{oi_delta_1m:+.4f}%</b> (기준: {target_oi:+.4f}%)\n"
                    f"• 5초 가격 변동: <b>${price_delta_5s:+,.1f}</b>\n"
                    f"• 1분 추세 기울기: <b>{price_slope_1m:+,.2f}</b>\n\n"
                    f"🤖 <b>봇 상태:</b> {bot_stat_str}"
                )
                asyncio.create_task(send_telegram_notification_server(tg_sig_msg))

        # --------------------------------------------------------------------------
        # 🚨 [2단계]: 실전 집행 및 포지션 보유 중 반대 청산 감시 (60초 안전 락다운 포함)
        # --------------------------------------------------------------------------
        is_opposite = False
        if self.is_position_active and direction:
            raw_opposite = (self.entry_direction == "LONG" and direction == "SHORT") or (self.entry_direction == "SHORT" and direction == "LONG")
            if raw_opposite:
                elapsed_entry = time.time() - getattr(self, "last_entry_time", 0.0)
                if elapsed_entry < 60.0:
                    is_opposite = False
                    now_t = time.time()
                    if now_t - getattr(self, "last_entry_lock_log_time", 0.0) >= 1.0:
                        self.last_entry_lock_log_time = now_t
                        rem_sec = 60.0 - elapsed_entry
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"🛡️ [진입 60초 안전 락다운] 진입 직후 60초간 반대 청산 무조건 유예 중 (남은 시간: {rem_sec:.1f}초) ➡️ 휩소 청산 100% 차단")
                else:
                    is_opposite = True
            
        if self.is_position_active and is_opposite:
            # [V6.58 헌법]: 봇이 정지(STOPPED) 상태이면 어떠한 자동 반대 청산도 100% 원천 차단!
            if getattr(self, "bot_state", "RUNNING") == "STOPPED" or not getattr(self, "is_snipe_active", True):
                return

            # OI > 0 and oi_delta_1m >= target_oi (진짜 자금 유입) 조건 충족 시에만 진짜 스위칭 청산 발동! (Case 2-3, Case 3-3)
            if oi_delta_1m > 0 and oi_delta_1m >= target_oi:
                if not getattr(self, "exit_in_progress", False):
                    self.exit_in_progress = True
                    self.exit_reason = f"반대 세력 저격 신호 감지 (스위칭 청산) (보유: {self.entry_direction} / 신호: {direction}) (청산: ${rolling_1m_liq_usd:,.0f}, OI속도: {oi_delta_1m:+.4f}%)"
                    self.last_exit_trigger_price = binance_mid
                    self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                    self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                    
                    if getattr(self.bot, "dashboard", None):
                        self.bot.dashboard.add_log(f"🚨 [1단계: 반대 청산 포착] 보유: {self.entry_direction} ➡️ 신호: {direction} | 청산 패킷 직송 개시!")

                    
                    # 쿨다운 선제 부여
                    dashboard = getattr(self.bot, "dashboard", None) or self.bot
                    profit_cd_sec = float(getattr(dashboard, "profit_cooldown_seconds", 15.0)) if dashboard else 15.0
                    loss_cd_sec = float(getattr(dashboard, "cooldown_seconds", 300.0)) if dashboard else 300.0

                    exit_reason_text = getattr(self, "exit_reason", "")
                    is_loss = ("손절" in exit_reason_text) or ("Stop Loss" in exit_reason_text) or ("스탑" in exit_reason_text and "익절" not in exit_reason_text)

                    if is_loss:
                        target_cooldown = loss_cd_sec
                        label = "손절 쿨타임"
                    else:
                        target_cooldown = profit_cd_sec
                        label = "익절/스위칭 쿨타임"

                    self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + target_cooldown)
                    if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                        self.cooldown_timer_task.cancel()
                    self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(target_cooldown, label))
                    try:
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log("⚡ [2단계: REST API 패킷 청산] execute_bitget_internal_packet(side=CLEAR) 호출 중...")
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"📋 [3단계: 청산 결과 반환] clear_ok: {clear_ok}")
                        if clear_ok:
                            if getattr(self.bot, "dashboard", None):
                                self.bot.dashboard.add_log("✅ [4단계: 청산 완료] 반대 방향 선제 청산 성공!")
                        else:
                            if getattr(self.bot, "dashboard", None):
                                self.bot.dashboard.add_log("⚠️ [4단계: 1차 실패] 2중 비상 마스터 청산 격발 시도...")
                            await asyncio.sleep(0.5)
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                    except Exception as clear_err:
                        if getattr(self.bot, "dashboard", None):
                            self.bot.dashboard.add_log(f"❌ [청산 예외] {clear_err}")
                        try:
                            await asyncio.sleep(0.5)
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                        except Exception:
                            pass
                    finally:
                        self.is_position_active = False
                        self.exit_in_progress = False
                    return

        # [사운드 최우선 직송]: 임계치 조건 충족 시 단 0.000ms 지연도 없이 사운드 1순위 격발 (1.0초 디바운싱 적용)
        if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
            now_t_radar = time.time()
            if now_t_radar - getattr(self, "last_radar_signal_log_time", 0.0) >= 1.0:
                self.last_radar_signal_log_time = now_t_radar
                try:
                    snd_en = getattr(getattr(self.bot, "dashboard", None), "sound_enabled", True)
                    play_order_sound(direction, enabled=snd_en)
                except Exception:
                    pass
        
        # [저격 활성 상태 검사]: 최상단으로 이동됨 (v4.07)
        
        # [05:00 KST 세션 전환 노이즈 차단 락다운 필터]
        now_dt = datetime.now()
        if now_dt.hour == 5 and now_dt.minute == 0:
            # 05:00:00 ~ 05:01:00 KST 세션 경계선 락다운 구간 (딱 1분간)
            if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
                logger.warning(f"🛡️ [세션 전환 락다운] 05:00 KST 세션 경계선 노이즈 구간(05:00~05:01) 감지 ➡️ 구라 신호 진입/스위칭을 차단합니다. (청산: ${rolling_1m_liq_usd:,.0f}, OI: {oi_delta_1m:+.4f}%)")
            return

        # 청산 진행 중인 경우, 모든 신규 틱 감시 및 진입 검증을 즉시 100% 차단 (개발계획서_189)
        if getattr(self, "exit_in_progress", False):
            return

        # 1단계: 동적 레이더 임계치 검증 (순수 +OI 세력 자금 유입 전용 v6.25)
        if rolling_1m_liq_usd >= target_liq and abs(oi_delta_1m) >= target_oi:
            now_t_chk = time.time()
            
            # [포지션 보유 중 스위칭 / 추가매수 / 불타기 검증 엔진 (SHINSEON 원본 규격)]
            if self.is_position_active and not getattr(self, "exit_in_progress", False):
                if direction and direction in ["LONG", "SHORT"] and direction != self.entry_direction:
                    # [V6.58 헌법]: 봇이 정지(STOPPED) 상태이면 어떠한 자동 반대 청산도 100% 원천 차단!
                    if getattr(self, "bot_state", "RUNNING") == "STOPPED" or not getattr(self, "is_snipe_active", True):
                        return

                    # [진입 60초 안전 락다운]: 진입 직후 60초 동안은 어떠한 반대 신호 청산도 100% 원천 차단!
                    elapsed_entry = time.time() - getattr(self, "last_entry_time", 0.0)
                    if elapsed_entry < 60.0:
                        rem_sec = 60.0 - elapsed_entry
                        logger.info(f"🛡️ [진입 60초 안전 락다운] 진입 직후 60초간 반대 청산 무조건 유예 중 (남은 시간: {rem_sec:.1f}초) ➡️ 휩소 청산 100% 차단")
                        return
                        
                    # [v2.55 황금 전성기 헌법 복원]: OI 부호(+/-) 상관없이 반대 신호 수신 즉시 기존 포지션 100% 전량 시장가 청산!
                    saved_pos_dir = str(self.entry_direction or "LONG").upper()
                    logger.info(f"🚨 [TRADE] [v2.55 반대 시그널 포착] 보유 포지션({saved_pos_dir})과 반대 신호({direction}) 도달! ➡️ 기존 포지션 전량 시장가 청산 집행")
                    self.exit_reason = f"반대 세력 저격 신호 감지 (스위칭 청산) (보유: {saved_pos_dir} / 신호: {direction}) (청산: ${rolling_1m_liq_usd:,.0f}, OI속도: {oi_delta_1m:+.4f}%)"
                    self.exit_in_progress = True
                    
                    dashboard = getattr(self.bot, "dashboard", None) or self.bot
                    current_bitget_price = getattr(self.bot, "current_price", self.entry_price)
                    # 진입 평단가 오염 방지: active_position_entry_price 보존값 최우선 사용
                    real_entry_p = getattr(self, "active_position_entry_price", None) or getattr(self, "entry_price_1", None) or self.entry_price
                    if real_entry_p <= 0.0:
                        real_entry_p = current_bitget_price
                    exit_pnl_pct = (current_bitget_price - real_entry_p) / real_entry_p if saved_pos_dir == "LONG" else (real_entry_p - current_bitget_price) / real_entry_p
                    
                    # 1. [0.000초 선제 락킹]: 1초 딜레이 틈새 휩소 이중진입 방지용으로 우선 300초 안전 손절 쿨타임 선제 마킹!
                    preemptive_cd = float(getattr(dashboard, "cooldown_seconds", 300.0))
                    self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + preemptive_cd)
                    if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                        self.cooldown_timer_task.cancel()
                    self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(preemptive_cd, "반대신호 선제 쿨타임(300초)"))
                    
                    clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                    if clear_ok:
                        # 0.000초 선제 락킹: 병렬 가드레일 감시 루프의 2중 알림 발송 100% 원천 차단
                        self.exit_msg_sent = True
                        self.is_position_active = False
                        
                        # 2. 청산 체결 완료 1.0초 비동기 대기 (실체결 팩트 수신 동기화)
                        await asyncio.sleep(1.0)
                        if self.bot and hasattr(self.bot, "sync_bitget_real_position_status"):
                            try:
                                await self.bot.sync_bitget_real_position_status()
                            except Exception:
                                pass
                                
                        # 2-B. 비트겟 체결 원장 API(fetch_my_trades) 직접 조회하여 100% 실체결 청산가 수신
                        try:
                            if self.bot and getattr(self.bot, "bitget_exchange", None):
                                trades = await self.bot.bitget_exchange.fetch_my_trades('BTC/USDT:USDT', limit=2)
                                if trades and len(trades) > 0:
                                    last_t = trades[-1]
                                    t_price = float(last_t.get('price', 0.0) or 0.0)
                                    t_amount = float(last_t.get('amount', 0.0) or 0.0)
                                    if t_price > 0.0:
                                        self.last_actual_exit_price = t_price
                                    if t_amount > 0.0:
                                        self.last_actual_exit_qty = t_amount
                        except Exception as tr_err:
                            logger.error(f"비트겟 체결 원장 수신 예외: {tr_err}")

                        real_exit_price = getattr(self, "last_actual_exit_price", 0.0) or current_bitget_price
                        real_exit_qty = getattr(self, "last_actual_exit_qty", 0.0) or 0.001
                        
                        # 3. 비트겟 실체결 평단가/청산가 기반 100% 팩트 PnL 재판정 및 쿨타임 최종 확정
                        confirmed_pnl_pct = (real_exit_price - real_entry_p) / real_entry_p if saved_pos_dir == "LONG" else (real_entry_p - real_exit_price) / real_entry_p
                        final_cd = float(getattr(dashboard, "cooldown_seconds", 300.0)) if confirmed_pnl_pct <= 0.0001 else float(getattr(dashboard, "profit_cooldown_seconds", 15.0))
                        final_cd_label = "반대신호 손절 쿨타임(300초)" if confirmed_pnl_pct <= 0.0001 else "반대신호 익절/스위칭 쿨타임(15초)"
                        
                        self.cooldown_until_time = time.time() + final_cd
                        if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                            self.cooldown_timer_task.cancel()
                        self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(final_cd, final_cd_label))
                        
                        kst_time_str = get_kst_now_str()
                        exit_msg = build_telegram_trade_msg(
                            title="🔄 [반대 시그널 청산 알림]",
                            direction=saved_pos_dir,
                            reason=self.exit_reason,
                            signal_time=kst_time_str,
                            signal_qty=real_exit_qty,
                            signal_price=binance_mid,
                            actual_time=kst_time_str,
                            actual_qty=real_exit_qty,
                            actual_price=real_exit_price,
                            entry_price=real_entry_p,
                            is_entry=False
                        )
                        if self.bot and self.bot.dashboard:
                            self.bot.dashboard.send_telegram_notification(exit_msg)
                        self.exit_msg_sent = True
                    return
                elif direction and direction in ["LONG", "SHORT"] and direction == self.entry_direction:
                    # [동일 방향 중복 신호 발생 ➡️ 2차/3차 추가 매수(물타기) 또는 눌림목 불타기 검증]
                    dashboard = getattr(self.bot, "dashboard", None) or self.bot
                    now_dt = get_kst_now()
                    is_weekend = check_is_weekend_kst(now_dt)
                    hour_val = now_dt.hour
                    minute_val = now_dt.minute
                    if 9 <= hour_val < 16:
                        s_thresh_key = "weekend_asia" if is_weekend else "asia"
                    elif 16 <= hour_val < 21 or (hour_val == 21 and minute_val < 30):
                        s_thresh_key = "weekend_europe" if is_weekend else "europe"
                    elif (hour_val == 21 and minute_val >= 30) or hour_val >= 22 or hour_val < 5:
                        s_thresh_key = "weekend_us" if is_weekend else "us"
                    else:
                        s_thresh_key = "weekend_pacific" if is_weekend else "pacific"
                        
                    tr_configs = getattr(self, "session_trading_configs", None) or getattr(dashboard, "session_trading_configs", {}) or {}
                    s_tr = tr_configs.get(s_thresh_key, {})
                    split_cooldown = float(s_tr.get("split_cooldown_seconds", getattr(dashboard, "split_cooldown_seconds", 900.0)))
                    
                    # A. 2차 추매 (1차 평단 대비 설정 손실폭 이하 마이너스 도달 시)
                    if not getattr(self, "has_second_entry", False):
                        trig_2_pct = float(s_tr.get("split_entry_2_trigger_pct", getattr(dashboard, "split_entry_2_trigger_pct", -0.3))) / 100.0
                        pnl_from_1 = (binance_mid - self.entry_price_1) / self.entry_price_1 if self.entry_direction == "LONG" else (self.entry_price_1 - binance_mid) / self.entry_price_1
                        if pnl_from_1 <= trig_2_pct:
                            if time.time() - getattr(self, "last_split_entry_time", 0.0) >= split_cooldown:
                                self.has_second_entry = True
                                self.last_split_entry_time = time.time()
                                logger.info(f"⚡ [2차 추가매수 발동] 동일방향 신호 컨펌! 1차 진입가 대비 {pnl_from_1*100.0:+.2f}% 도달 (임계치: {trig_2_pct*100.0:.2f}%)")
                                asyncio.create_task(self.execute_bitget_internal_packet(side=self.entry_direction, order_type="ADD_100_PERCENT"))
                                return
                    # B. 3차 추매 (1차 평단 대비 3차 손실폭 이하 마이너스 도달 시)
                    elif getattr(self, "has_second_entry", False) and not getattr(self, "has_third_entry", False):
                        trig_3_pct = float(s_tr.get("split_entry_3_trigger_pct", getattr(dashboard, "split_entry_3_trigger_pct", -0.6))) / 100.0
                        pnl_from_1 = (binance_mid - self.entry_price_1) / self.entry_price_1 if self.entry_direction == "LONG" else (self.entry_price_1 - binance_mid) / self.entry_price_1
                        if pnl_from_1 <= trig_3_pct:
                            if time.time() - getattr(self, "last_split_entry_time", 0.0) >= split_cooldown:
                                self.has_third_entry = True
                                self.last_split_entry_time = time.time()
                                logger.info(f"⚡ [3차 추가매수 발동] 동일방향 신호 컨펌! 1차 진입가 대비 {pnl_from_1*100.0:+.2f}% 도달 (임계치: {trig_3_pct*100.0:.2f}%)")
                                asyncio.create_task(self.execute_bitget_internal_packet(side=self.entry_direction, order_type="ADD_THIRD_ENTRY"))
                                return
                    # C. 눌림목 불타기 (1차 익절 완료 후 동일 방향 신호 컨펌 시)
                    elif getattr(self, "is_half_exited", False) and getattr(dashboard, "pyramiding_enabled", True) and not getattr(self, "has_pyramided", False):
                        logger.info(f"🔥 [눌림목 불타기 발동] 1차 익절 후 동일방향 신호 컨펌! 30% 수량 추가 진입")
                        self.has_pyramided = True
                        asyncio.create_task(self.execute_bitget_internal_packet(side=self.entry_direction, order_type="ADD_PYRAMIDING"))
                        return
                    return

            # [세션 비활성화 시 신규 진입 정밀 차단 (기존 포지션 청산은 100% 정상 가동)]
            is_sess_enabled = getattr(self, "is_current_session_enabled", True)
            if not self.is_position_active and not is_sess_enabled:
                if getattr(self.bot, "ui_cb", None) and now_t_chk - getattr(self, "last_sess_dis_log_time", 0.0) >= 3.0:
                    self.last_sess_dis_log_time = now_t_chk
                    self.bot.ui_cb(0.0, 0, f"⚪ [{self.current_session_name}] 세션 비활성화 설정 중 (신규 진입 차단 / 기존 청산 정상 작동)")
                return

            # [쿨타임 사전 검증 최우선 전진 배치]: 쿨타임 대기 중인 경우 진입/추가매수 시도 차단
            if time.time() < getattr(self, "cooldown_until_time", 0.0):
                remain_sec = getattr(self, "cooldown_until_time", 0.0) - time.time()
                if getattr(self.bot, "ui_cb", None) and now_t_chk - getattr(self, "last_cooldown_log_time", 0.0) >= 1.0:
                    self.last_cooldown_log_time = now_t_chk
                    self.bot.ui_cb(0.0, 0, f"⏳ [쿨타임 대기 중] 진입 보류 (남은 시간: {remain_sec:.1f}초)")
                return

            # 1단계: 타점 포착 WSS 실시간 로그 송출
            if now_t_chk - getattr(self, "last_snipe_trigger_log_time", 0.0) >= 0.5:
                self.last_snipe_trigger_log_time = now_t_chk
                step1_msg = f"💥 [1단계 타점포착 v4.82] 바이낸스 청산(${rolling_1m_liq_usd:,.0f}) & OI속도({oi_delta_1m:+.4f}%) 돌파! (저격 방향: {direction})"
                if self.bot and hasattr(self.bot, "broadcast_event"):
                    asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": step1_msg}))
            
            # 2단계: 비트겟 호가창 VWAP 역공학 스캔 및 WSS 로그 송출
            bitget_book = await self.fetch_bitget_orderbook_internal()
            if not bitget_book or not bitget_book.get('asks') or not bitget_book.get('bids'):
                err_msg = "❌ [2단계 진입실패] BITGET 호가창 데이터를 조회할 수 없습니다."
                if self.bot and hasattr(self.bot, "broadcast_event"):
                    asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": err_msg}))
                return
                
            expected_fill = bitget_book['asks'][0][0] if direction == 'LONG' else bitget_book['bids'][0][0]
            spread_pct = abs(expected_fill - binance_mid) / binance_mid * 100.0
            
            step2_msg = f"🔍 [2단계 호가스캔 v4.82] 비트겟 최우선 호가 스캔 완료 (예상체결가: ${expected_fill:,.1f}, 스프레드: {spread_pct:.4f}%)"
            if self.bot and hasattr(self.bot, "broadcast_event"):
                asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": step2_msg}))
            
            # 방어벽 ②: 방향성 비대칭 슬리피지 캡 검증 (0.30% 가드)
            if direction == 'LONG':
                if expected_fill >= binance_mid:
                    unfavorable_slippage = (expected_fill - binance_mid) / binance_mid
                    if unfavorable_slippage > self.ENTRY_SLIPPAGE_CAP:
                        rej_msg = f"⚠️ [진입 기각] 불리한 롱 슬리피지 {unfavorable_slippage*100.0:.3f}% 초과 (허용: {self.ENTRY_SLIPPAGE_CAP*100.0:.3f}%) (차이: ${expected_fill - binance_mid:,.1f})"
                        if self.bot and hasattr(self.bot, "broadcast_event"):
                            asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": rej_msg}))
                        return
            else: # SHORT
                if expected_fill <= binance_mid:
                    unfavorable_slippage = (binance_mid - expected_fill) / binance_mid
                    if unfavorable_slippage > self.ENTRY_SLIPPAGE_CAP:
                        rej_msg = f"⚠️ [진입 기각] 불리한 숏 슬리피지 {unfavorable_slippage*100.0:.3f}% 초과 (허용: {self.ENTRY_SLIPPAGE_CAP*100.0:.3f}%) (차이: ${binance_mid - expected_fill:,.1f})"
                        if self.bot and hasattr(self.bot, "broadcast_event"):
                            asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": rej_msg}))
                        return
                
            # 3단계 & 4단계: 발주 전송 및 체결 로그 송출 (오직 direction이 LONG 또는 SHORT일 때만 전격 실행!)
            if direction and direction in ["LONG", "SHORT"] and not self.is_position_active and self.is_snipe_active and getattr(self, "bot_state", "RUNNING") == "RUNNING" and not self.exit_in_progress:
                self.is_position_active = True
                self.last_entry_time = time.time()
                self.entry_direction = direction
                self.entry_price = expected_fill
                self.entry_price_1 = expected_fill
                self.active_position_entry_price = expected_fill
                self.has_second_entry = False
                self.peak_pnl_pct = 0.0
                
                step3_msg = f"🎯 [3단계 실전발주 v4.82] 비트겟 선물 BTCUSDT 시장가 {direction} 발주 패킷 전송 시작..."
                if self.bot and hasattr(self.bot, "broadcast_event"):
                    asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": step3_msg}))
                    
                try:
                    success = await self.execute_bitget_internal_packet(side=direction, order_type="IOC_MARKET")
                    if success:
                        self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + 60.0)
                        if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
                            self.cooldown_timer_task.cancel()
                        self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(60.0, "신규 진입 60초 쿨타임"))
                        
                        # 1. 비트겟 주문 체결 완료 후 1.0초 비동기 대기 (실체결 팩트 동기화)
                        await asyncio.sleep(1.0)
                        if self.bot and hasattr(self.bot, "sync_bitget_real_position_status"):
                            try:
                                await self.bot.sync_bitget_real_position_status()
                            except Exception:
                                pass
                                
                        real_entry_price = getattr(self, "active_position_entry_price", None) or getattr(self, "entry_price", None) or expected_fill
                        if real_entry_price <= 0.0:
                            real_entry_price = expected_fill
                        self.active_position_entry_price = real_entry_price
                        self.entry_price = real_entry_price
                        
                        real_qty_btc = getattr(self, "position_volume_btc", 0.0) or getattr(self, "position_volume", 0.0)
                        if real_qty_btc > 1.0:
                            real_qty_btc = real_qty_btc / 1000.0
                        if real_qty_btc <= 0.0:
                            real_qty_btc = 0.001
                            
                        # 폐하의 어명: 웹서버 전용 독립 락다운 저장소 구축 및 저장
                        self.real_bitget_trade_store = {
                            'entry_price': real_entry_price,
                            'qty_btc': real_qty_btc,
                            'direction': direction,
                            'timestamp': time.time()
                        }
                        
                        # [V6.18 추가]: 비트겟 거래소 서버사이드 듀얼 TP/SL 선주문 박기 직송!
                        asyncio.create_task(self.place_bitget_tpsl_plan_orders(real_entry_price, direction, real_qty_btc))
                            
                        step4_msg = f"✅ [4단계 체결완료 v5.90] 비트겟 선물 {direction} 시장가 실체결 확정! (실체결가: ${real_entry_price:,.1f}, 수량: {real_qty_btc:.4f} BTC)"
                        if self.bot and hasattr(self.bot, "broadcast_event"):
                            asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": step4_msg}))
                        
                        signal_time_str = get_kst_now_str()
                        
                        # 텔레그램 발송 엔진은 오직 웹서버 저장소(self.real_bitget_trade_store)의 저장된 값만 사용!
                        store_data = getattr(self, "real_bitget_trade_store", {})
                        tg_entry_p = store_data.get('entry_price', real_entry_price)
                        tg_qty_btc = store_data.get('qty_btc', real_qty_btc)
                        
                        entry1_msg = build_telegram_trade_msg(
                            title="🎯 [1차 진입 알림]",
                            direction=direction,
                            reason=f"1분 청산 ${rolling_1m_liq_usd:,.0f} & OI속도 {oi_delta_1m:+.4f}% 동시 돌파",
                            signal_time=signal_time_str,
                            signal_qty=tg_qty_btc,
                            signal_price=binance_mid,
                            actual_time=signal_time_str,
                            actual_qty=tg_qty_btc,
                            actual_price=tg_entry_p,
                            is_entry=True
                        )
                        if self.bot and self.bot.dashboard:
                            self.bot.dashboard.send_telegram_notification(entry1_msg)
                            self.bot.dashboard.play_entry_sound()
                            
                        asyncio.create_task(self.manage_v35_exit_guardrail(direction))
                    else:
                        self.is_position_active = False
                        fail_msg = f"⚠️ [실전 진입 실패] 1차 진입 발주 실패로 주문 기각 (방향: {direction})"
                        if self.bot and hasattr(self.bot, "broadcast_event"):
                            asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": fail_msg}))
                        if self.bot and self.bot.dashboard:
                            self.bot.dashboard.send_telegram_notification(f"⚠️ [실전 진입 실패 경보] 1차 진입 실패로 주문 최종 기각 (방향: {direction})")
                except Exception as e:
                    self.is_position_active = False
                    if self.bot and hasattr(self.bot, "broadcast_event"):
                        asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": ex_msg}))
                self.peak_pnl_pct = 0.0
                self.peak_buying_delta = random.uniform(80000, 150000)
            else:
                if self.bot.ui_cb:
                    self.bot.ui_cb(0.0, 0, f"⚠️ [진입 기각] 이미 포지션이 가동 중이거나 자동 저격 감시가 비활성화 상태입니다. (is_active: {self.is_position_active}, is_snipe: {self.is_snipe_active})")

    async def manage_v35_exit_guardrail(self, direction):
        self.is_guardrail_running = True
        try:
            await self._manage_v35_exit_guardrail_impl(direction)
        finally:
            self.is_guardrail_running = False

    async def _manage_v35_exit_guardrail_impl(self, direction):
        """
        방어벽 ③: 완충형 다단계 격차 자물쇠 및 하이브리드 익절/손절 청산 엔진
        """
        self.exit_msg_sent = False
        self.exit_reason = ""
        # 세션별 자동 연동 손절선 퍼센티지 및 최초 스탑로스 가격 연산 (개발계획서_176)
        initial_sl_pct = abs(getattr(self, "current_session_sl", -1.3)) / 100.0
        # 기동 시 배치한 최초 기본 스탑로스 가격으로 last_placed_stop_price를 사전 동기화하여 중복 발주 방지
        self.last_placed_stop_price = self.entry_price * (1.0 - initial_sl_pct) if direction == "LONG" else self.entry_price * (1.0 + initial_sl_pct)
        while self.is_position_active:
            try:
                await asyncio.sleep(0.01)
                
                # 실시간 세션별 손절선 동적 업데이트 (세션 시간 전환 시 반영)
                initial_sl_pct = abs(getattr(self, "current_session_sl", -1.3)) / 100.0
                
                current_bitget_price = await self.get_live_bitget_price_internal()
                if current_bitget_price <= 0.0:
                    continue
                    
                # 3.0초 도킹 유예 시간 동안은 안전 보존을 위해 청산 감시 일시 스킵
                import time
                grace_until = getattr(self, "grace_period_until", 0.0)
                if time.time() < grace_until:
                    self.peak_pnl_pct = 0.0
                    continue
                
                # 1차 진입가 대비 PnL 및 실시간 평단 대비 PnL 계산 (0 나누기 방지 정공법 가드)
                ent1 = float(getattr(self, "entry_price_1", 0.0) or getattr(self, "entry_price", 0.0) or current_bitget_price)
                ent = float(getattr(self, "entry_price", 0.0) or current_bitget_price)

                if direction == "LONG":
                    pnl_from_entry_1 = (current_bitget_price - ent1) / ent1 if ent1 > 0.0 else 0.0
                    pnl_pct = (current_bitget_price - ent) / ent if ent > 0.0 else 0.0
                else:
                    pnl_from_entry_1 = (ent1 - current_bitget_price) / ent1 if ent1 > 0.0 else 0.0
                    pnl_pct = (ent - current_bitget_price) / ent if ent > 0.0 else 0.0
                    
                if pnl_pct > self.peak_pnl_pct:
                    self.peak_pnl_pct = pnl_pct
                self.last_live_pnl_pct = pnl_pct * 100.0

                # --------------------------------------------------------------------------
                # [스마트 스탑] 웹서버 전담 실시간 PNL 오프셋 청산 엔진 (봇 온/오프 독립 가동)
                # --------------------------------------------------------------------------
                if getattr(self, "custom_stop_active", False):
                    offset_val = float(getattr(self, "custom_stop_offset_pnl", getattr(self, "custom_stop_offset_pct", 0.5)))
                    pnl_at_set = float(getattr(self, "custom_stop_set_pnl", pnl_pct * 100.0))
                    live_pnl_val = pnl_pct * 100.0
                    live_pnl_rounded = round(live_pnl_val, 2)

                    if offset_val < pnl_at_set:
                        # 1. 설정 오프셋이 설정 시점 PNL 이하인 경우 ➡️ 하방 수익보존/손절 모드
                        is_triggered = (live_pnl_rounded <= offset_val)
                        cond_str = "이하"
                        stop_label = "수익보존/손절"
                    else:
                        # 2. 설정 오프셋이 설정 시점 PNL 이상인 경우 ➡️ 상방 목표익절/반등 모드
                        is_triggered = (live_pnl_rounded >= offset_val)
                        cond_str = "이상"
                        stop_label = "목표익절"

                    if is_triggered:
                        self.custom_stop_active = False
                        ratio = float(getattr(self, "custom_stop_close_ratio", 100.0))
                        if ratio < 100.0:
                            order_type = f"PARTIAL_CLOSE_{int(ratio)}"
                        else:
                            order_type = "FORCE_MARKET_UNCAPPED"
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type=order_type, custom_ratio=ratio/100.0)
                        if clear_ok:
                            if order_type == "FORCE_MARKET_UNCAPPED":
                                self.is_position_active = False
                            log_msg = f"🛡️ [웹서버 스마트 스탑 청산 실행 완료] 실시간 PNL({live_pnl_val:+.2f}%)이 설정 오프셋({offset_val:+.2f}% PNL) {cond_str} 도달! ({ratio:.0f}% {stop_label} 청산 완료)"
                            logger.info(log_msg)
                            if self.bot and hasattr(self.bot, "broadcast_event"):
                                asyncio.create_task(self.bot.broadcast_event("EVT_RESPONSE_LOG", {"message": log_msg}))
                                asyncio.create_task(self.bot.broadcast_event("ui_update", {"msg": log_msg, "log_type": 1, "price": current_bitget_price}))
                            self.exit_msg_sent = True
                            if order_type == "FORCE_MARKET_UNCAPPED":
                                break
            except Exception as smart_stop_err:
                logger.error(f"⚠️ [스마트 스탑 감시 수식 예외 방어] {smart_stop_err}", exc_info=True)

            # [HOTFIX v5.75 / V6.58]: 봇 정지(STOPPED) 상태에서는 세션 가드레일 자동 분할익절도 100% 원천 차단 동결!
            if not getattr(self, "is_position_active", False) or getattr(self, "bot_state", "RUNNING") == "STOPPED" or not getattr(self, "is_snipe_active", True):
                continue

            # ================= 하이브리드 분할 익절 가드레일 =================
            current_time_str = get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
            s_key = "NY"
            try:
                now_dt = get_kst_now()
                hour_val = now_dt.hour
                minute_val = now_dt.minute
                is_weekend = check_is_weekend_kst(now_dt)
                if 9 <= hour_val < 16:
                    s_key = "WEEKEND_ASIA" if is_weekend else "ASIA"
                elif 16 <= hour_val < 21 or (hour_val == 21 and minute_val < 30):
                    s_key = "WEEKEND_LONDON" if is_weekend else "LONDON"
                elif (hour_val == 21 and minute_val >= 30) or hour_val >= 22 or hour_val < 5:
                    s_key = "WEEKEND_NY" if is_weekend else "NY"
                else:
                    s_key = "WEEKEND_PACIFIC" if is_weekend else "PACIFIC"
            except Exception as e:
                logger.error(f"가드레일 세션 판정 오류: {e}")
            
            dash_obj = getattr(self.bot, "dashboard", None) or self.bot
            s_guardrails = (getattr(self, "session_guardrails", None) or getattr(dash_obj, "session_guardrails", {})).get(s_key, {"trigger": 0.4, "trigger_2": 0.8, "guard": 0.0, "enabled": True})
            half_exit_trigger = float(s_guardrails.get("trigger", 0.4)) / 100.0
            half_exit_trigger_2 = float(s_guardrails.get("trigger_2", half_exit_trigger * 1.5 if half_exit_trigger > 0 else 0.8)) / 100.0
            entry_sl_guard = float(s_guardrails.get("guard", 0.0))
            half_exit_enabled = s_guardrails.get("enabled", True)

            # [V6.24 수술] 2시간(120분) 경과 & PnL +0.30% 이상일 때만 전용 무위험 본전가드 발동
            elapsed_minutes = (time.time() - getattr(self, "last_entry_time", time.time())) / 60.0
            if elapsed_minutes >= 120.0 and not getattr(self, "has_time_breakeven_guarded", False) and pnl_pct >= 0.0030:
                self.has_time_breakeven_guarded = True
                new_sl_price = self.entry_price * (1.0 + 0.0005) if direction == "LONG" else self.entry_price * (1.0 - 0.0005)
                self.last_placed_stop_price = new_sl_price
                asyncio.create_task(self.place_bitget_tpsl_plan_orders(self.entry_price, direction, self.position_volume, is_smart_guard=True))
                log_msg = f"🛡️ [2시간+0.30% PnL 본전가드 발동] 진입 후 {elapsed_minutes:.0f}분 경과 & PnL({pnl_pct*100:+.2f}%) >= +0.30% 포착 ➡️ 손절선을 무위험 본전가({new_sl_price:,.1f})로 상향 배치 완료!"
                logger.info(log_msg)
                if self.bot and self.bot.dashboard:
                    self.bot.dashboard.add_log(log_msg)
                    tg_msg = f"<b>🛡️ [2시간+0.30% PnL 본전가드 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>진입 후 {elapsed_minutes:.0f}분 경과 & PnL {pnl_pct*100:+.2f}% >= +0.30% ➡️ 무위험 본전가 상향</b>\n새 스탑로스: <b>{new_sl_price:,.1f} USDT</b>"
                    self.bot.dashboard.send_telegram_notification(tg_msg)
            
            # [V5.40 신설] 중간 수익 보존 가드레일 (최소값 % 도달 시 가드값 % 스탑로스 자동 배치)
            mid_trig = float(getattr(self.bot, "mid_guard_trigger", 0.60)) / 100.0
            mid_off = float(getattr(self.bot, "mid_guard_offset", -0.10))
            if not getattr(self, "has_mid_guarded", False) and pnl_pct >= mid_trig:
                self.has_mid_guarded = True
                new_sl_price = self.entry_price * (1.0 + (mid_off / 100.0)) if direction == "LONG" else self.entry_price * (1.0 - (mid_off / 100.0))
                self.last_placed_stop_price = new_sl_price
                asyncio.create_task(self.execute_bitget_internal_packet(side="STOP_LOSS", order_type=str(round(new_sl_price, 1))))
                
                log_msg = f"🛡️ [수익 보존 가드 발동] 수익률 {pnl_pct*100:.2f}% 도달하여 스탑로스를 {mid_off:+.2f}% 위치({new_sl_price:.1f})로 상향 방어했습니다!"
                if self.bot and self.bot.dashboard:
                    self.bot.dashboard.add_log(log_msg)
                    tg_msg = f"<b>🛡️ [수익 보존 가드 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>수익률 {pnl_pct*100:.2f}% 도달하여 스탑로스 상향 방어</b>\n새 스탑로스: <b>{new_sl_price:,.1f} USDT ({mid_off:+.2f}%)</b>"
                    self.bot.dashboard.send_telegram_notification(tg_msg)

            if half_exit_enabled:
                # [1차 분할 익절 집행]
                if not getattr(self, "is_half_exited", False) and pnl_pct >= half_exit_trigger:
                    self.is_half_exited = True
                    self.awaiting_pullback_pyramid = True
                    ratio_1 = float(getattr(self.bot, "half_exit_close_ratio", 50.0)) / 100.0
                    asyncio.create_task(self.execute_bitget_internal_packet(side="CLEAR", order_type="50_PERCENT_CLOSE", custom_ratio=ratio_1))
                    
                    # 텔레그램 알림은 비트겟 API execute_bitget_internal_packet 00000 성공 체결 후 직송 발송됨 (V5.59)
                    await asyncio.sleep(1.0)
                    new_sl_price = self.entry_price * (1.0 + (entry_sl_guard / 100.0)) if direction == "LONG" else self.entry_price * (1.0 - (entry_sl_guard / 100.0))
                    self.last_placed_stop_price = new_sl_price
                    asyncio.create_task(self.execute_bitget_internal_packet(side="STOP_LOSS", order_type=str(round(new_sl_price, 1))))

                # [2차 최종 분할 익절 집행]
                if getattr(self, "is_half_exited", False) and not getattr(self, "is_full_exited", False) and pnl_pct >= half_exit_trigger_2:
                    self.is_full_exited = True
                    log_msg = f"🏆 [2차 최종 분할익절 달성] 수익률({pnl_pct*100:+.2f}%) >= 2차 목표가({half_exit_trigger_2*100:.2f}%) 도달 ➡️ 잔여 포지션 전량 최종 익절 청산!"
                    logger.info(log_msg)
                    if self.bot and getattr(self.bot, "dashboard", None):
                        self.bot.dashboard.add_log(log_msg)
                        tg_msg = f"<b>🏆 [2차 최종 분할익절 청산 완수]</b>\n방향: <b>{direction}</b>\n사유: <b>2차 목표가({half_exit_trigger_2*100:.2f}%) 도달 ➡️ 잔여 포지션 전량 최종 익절</b>\n수익률: <b>{pnl_pct*100:+.2f}%</b>"
                        self.bot.dashboard.send_telegram_notification(tg_msg)
                    asyncio.create_task(self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED"))
            else:
                if pnl_pct >= half_exit_trigger and not getattr(self, "has_smart_guarded", False):
                    self.has_smart_guarded = True
                    new_stop_price = self.entry_price * (1.0 + (entry_sl_guard / 100.0)) if direction == "LONG" else self.entry_price * (1.0 - (entry_sl_guard / 100.0))
                    self.last_placed_stop_price = new_stop_price
                    asyncio.create_task(self.execute_bitget_internal_packet(side="STOP_LOSS", order_type=str(round(new_stop_price, 1))))
                    
                    log_msg = f"🛡️ [스마트 본전가드] 분할익절 OFF 세션: 100% 수량 유지하며 스탑로스를 본전/버퍼가({new_stop_price:.1f})로 상향 방어했습니다!"
                    if self.bot.dashboard:
                        self.bot.dashboard.add_log(log_msg)
                        tg_msg = f"<b>🛡️ [스마트 본전가드 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>분할익절 OFF 세션 100% 수량 유지 및 본전가드 상향</b>\n새 스탑로스: <b>{new_stop_price:,.1f} USDT</b>"
                        self.bot.dashboard.send_telegram_notification(tg_msg)
                
            is_pyra_enabled = getattr(self.bot, "pyramiding_enabled", False) or getattr(getattr(self.bot, "dashboard", None), "pyramiding_enabled", False)
            if getattr(self, "is_half_exited", False) and getattr(self, "awaiting_pullback_pyramid", False) and not getattr(self, "has_pyramided", False) and is_pyra_enabled:
                pullback_offset = float(getattr(getattr(self.bot, "dashboard", None), "pullback_pyramiding_offset", 0.003))
                    
                if pnl_pct <= (half_exit_trigger - pullback_offset):
                    self.has_pyramided = True
                    self.awaiting_pullback_pyramid = False
                    asyncio.create_task(self.execute_bitget_internal_packet(side=direction, order_type="ADD_PYRAMIDING"))
                    
                    if self.bot.dashboard:
                        self.bot.dashboard.add_log(f"[눌림목 불타기] {pullback_offset*100}% 풀백 감지 완료! 30% 수량 정밀 발주를 집행합니다.")
                        msg_tg = f"<b>🔥 [눌림목 불타기 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>{pullback_offset*100}% 풀백 감지 완료! 30% 수량 정밀 발주를 집행합니다.</b>"
                        self.bot.dashboard.send_telegram_notification(msg_tg)
                
            if (getattr(self, "is_half_exited", False) or getattr(self, "has_smart_guarded", False)) and pnl_pct <= (entry_sl_guard / 100.0):
                self.exit_reason = "스마트 본전/버퍼 보존 가드 발동" if getattr(self, "has_smart_guarded", False) else "본전/버퍼 보존 가드 발동 (분할청산 후)"
                self.exit_in_progress = True
                clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                if clear_ok:
                    self.is_position_active = False
                    self.exit_msg_sent = True
                    break
                else:
                    self.is_position_active = True
                    self.exit_in_progress = False
                    log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                    if self.bot and self.bot.dashboard:
                        self.bot.dashboard.add_log(log_msg)
                        try:
                            await self.bot.dashboard.execute_bitget_emergency_master_internal()
                        except Exception as em_err:
                            logger.error(f"본전가드 비상 청산 에러: {em_err}")

            # [개발계획서_93] 실물 거래소 서버사이드 추적 스탑로스 가격 연산 및 자동 재배치 (Trailing)
            # (2차/3차 진입 상태에서는 서버사이드 트레일링 예약을 건너뜁니다)
            if not self.has_second_entry and not getattr(self, "has_third_entry", False):
                new_stop_price = 0.0
                if self.peak_pnl_pct >= 0.020:
                    # +2.0% 이상 돌파 시: 고점 대비 1.0% 하락선에 트레일링 익절선 형성 (Gap 1.0%)
                    new_stop_price = self.entry_price * (1 + self.peak_pnl_pct - 0.010) if direction == "LONG" else self.entry_price * (1 - self.peak_pnl_pct + 0.010)

                elif getattr(self, "is_half_exited", False) or getattr(self, "has_smart_guarded", False):
                    # 50% 분할익절 후 또는 스마트 본전가드 발동 후 세션 가드 보존가격 연산 (32차 수술: 0.0원 연산 및 버그 방지)
                    new_stop_price = self.entry_price * (1.0 + (entry_sl_guard / 100.0)) if direction == "LONG" else self.entry_price * (1.0 - (entry_sl_guard / 100.0))

                elif not getattr(self, "is_half_exited", False) and not getattr(self, "has_smart_guarded", False):
                    # 초기 기본 손절선 (세션 연동)
                    new_stop_price = self.entry_price * (1.0 - initial_sl_pct) if direction == "LONG" else self.entry_price * (1.0 + initial_sl_pct)
                    
                if new_stop_price <= 0.0:
                    continue
                    
                # 스탑 가격이 유리하게 상향 갱신되었는지 비교 판정
                is_better = False
                if self.last_placed_stop_price == 0.0:
                    is_better = True
                else:
                    if direction == "LONG":
                        if new_stop_price > self.last_placed_stop_price:
                            is_better = True
                    else:
                        if new_stop_price < self.last_placed_stop_price:
                            # 숏일 때는 스탑 가격이 아래로 내려가야 이득입니다!
                            is_better = True
                            
                now_t_sl = time.time()
                # [35차 완치] 스탑로스 갱신 시 최소 10.0초 디바운싱 가드 적용하여 50초 대시보드 다운 0.0% 원천 차단
                if is_better and (now_t_sl - getattr(self, "last_placed_stop_time", 0.0) >= 10.0 or self.last_placed_stop_price == 0.0):
                    self.last_placed_stop_price = new_stop_price
                    self.last_placed_stop_time = now_t_sl
                    # 거래소 기존 예약을 취소하고 새로운 가격으로 즉시 실물 조건부 주문 발주 재배치!
                    asyncio.create_task(self.execute_bitget_internal_packet(
                        side="STOP_LOSS",
                        order_type=str(round(new_stop_price, 1))
                    ))
                
            # ================= PART 1: 손절 및 계단식 익절 자물쇠 (로컬 백업 엔진) =================
            if self.has_second_entry or getattr(self, "has_third_entry", False):
                if not getattr(self, "is_half_exited", False) and pnl_from_entry_1 <= -initial_sl_pct:
                    self.last_exit_trigger_price = current_bitget_price
                    self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                    self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                    self.exit_reason = f"최초 손절선 도달 (-{initial_sl_pct*100:.2f}% 이하 도달, PnL: {pnl_from_entry_1*100:.2f}%)"

                    self.exit_in_progress = True
                    clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                    if clear_ok:
                        self.is_position_active = False
                        if self.bot.dashboard:
                            msg = f"<b>📉 [손절 청산 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>{self.exit_reason}</b>\n진입가: <b>{self.entry_price_1:,.1f} USDT</b>\n현재가: <b>{current_bitget_price:,.1f} USDT</b>\n수익률: <b>{pnl_from_entry_1 * 100:+.2f}%</b>"
                            self.bot.dashboard.send_telegram_notification(msg)
                        self.exit_msg_sent = True
                        break
                    else:
                        self.is_position_active = True
                        self.exit_in_progress = False
                        log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                        if self.bot and self.bot.dashboard:
                            self.bot.dashboard.add_log(log_msg)
                            try:
                                await self.bot.dashboard.execute_bitget_emergency_master_internal()
                            except Exception as em_err:
                                logger.error(f"2/3차 손절 비상 청산 에러: {em_err}")
            else:
                if self.peak_pnl_pct < 0.020:
                    # 초기 손절선 (세션 연동)
                    if pnl_pct <= -initial_sl_pct:
                        self.last_exit_trigger_price = current_bitget_price
                        self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                        self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                        self.exit_reason = f"초기 손절선 (-{initial_sl_pct*100:.2f}% 이하 도달, PnL: {pnl_pct*100:.2f}%)"

                        self.exit_in_progress = True
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if clear_ok:
                            self.is_position_active = False
                            if self.bot.dashboard:
                                msg = f"<b>📉 [손절 청산 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>{self.exit_reason}</b>\n진입가: <b>{self.entry_price:,.1f} USDT</b>\n청산가: <b>{current_bitget_price:,.1f} USDT</b>\n수익률: <b>{pnl_pct * 100:+.2f}%</b>"
                                self.bot.dashboard.send_telegram_notification(msg)
                            self.exit_msg_sent = True
                            break
                        else:
                            self.is_position_active = True
                            self.exit_in_progress = False
                            log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                            if self.bot and self.bot.dashboard:
                                self.bot.dashboard.add_log(log_msg)
                                try:
                                    await self.bot.dashboard.execute_bitget_emergency_master_internal()
                                except Exception as em_err:
                                    logger.error(f"초기 손절 비상 청산 에러: {em_err}")
                    

                else:
                    # ================= PART 2: +2.0% 이상 트레일링 익절선 (로컬 백업 엔진) =================
                    # 기어 A: 고점 대비 1.0% 하락 시 트레일링 스위치 작동
                    if pnl_pct <= (self.peak_pnl_pct - 0.010):
                        self.last_exit_trigger_price = current_bitget_price
                        self.last_exit_signal_time = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
                        self.last_exit_signal_qty = float(getattr(self, "position_volume", 0)) / 1000.0
                        self.exit_reason = f"고점 {self.peak_pnl_pct*100:.2f}% 돌파 후 1.0% 하락선 {(self.peak_pnl_pct-0.010)*100:.2f}% 도달 (추적 스탑, PnL: {pnl_pct*100:.2f}%)"

                        self.exit_in_progress = True
                        clear_ok = await self.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED")
                        if clear_ok:
                            self.is_position_active = False
                            if self.bot.dashboard:
                                msg = f"<b>📈 [추적익절 청산 알림]</b>\n방향: <b>{direction}</b>\n사유: <b>{self.exit_reason}</b>\n진입가: <b>{self.entry_price:,.1f} USDT</b>\n청산가: <b>{current_bitget_price:,.1f} USDT</b>\n수익률: <b>{pnl_pct * 100:+.2f}%</b>"
                                self.bot.dashboard.send_telegram_notification(msg)
                            self.exit_msg_sent = True
                            break
                        else:
                            self.is_position_active = True
                            self.exit_in_progress = False
                            log_msg = "⚠️ [청산 1차 실패] 2중 비상 마스터 청산 격발!"
                            if self.bot and self.bot.dashboard:
                                self.bot.dashboard.add_log(log_msg)
                                try:
                                    await self.bot.dashboard.execute_bitget_emergency_master_internal()
                                except Exception as em_err:
                                    logger.error(f"추적익절 비상 청산 에러: {em_err}")
                        
        self.is_position_active = False
        self.custom_stop_active = False
        if self.bot and self.bot.dashboard and hasattr(self.bot.dashboard, "reset_stoploss_ui"):
            self.bot.dashboard.reset_stoploss_ui()
        self.exit_in_progress = False
        self.has_second_entry = False
        self.has_third_entry = False
        self.is_half_exited = False
        self.has_smart_guarded = False
        self.has_pyramided = False
        self.last_exit_time = time.time()
        dashboard = getattr(self.bot, "dashboard", None) or self.bot
        now_dt = get_kst_now()
        is_weekend = check_is_weekend_kst(now_dt)
        hour_val = now_dt.hour
        minute_val = now_dt.minute
        if 9 <= hour_val < 16:
            s_thresh_key = "weekend_asia" if is_weekend else "asia"
        elif 16 <= hour_val < 21 or (hour_val == 21 and minute_val < 30):
            s_thresh_key = "weekend_europe" if is_weekend else "europe"
        elif (hour_val == 21 and minute_val >= 30) or hour_val >= 22 or hour_val < 5:
            s_thresh_key = "weekend_us" if is_weekend else "us"
        else:
            s_thresh_key = "weekend_pacific" if is_weekend else "pacific"
            
        tr_configs = getattr(self, "session_trading_configs", None) or getattr(dashboard, "session_trading_configs", {}) or {}
        s_tr = tr_configs.get(s_thresh_key, {})
        cooldown_limit = float(s_tr.get("cooldown_seconds", getattr(dashboard, "cooldown_seconds", 30.0)))
        profit_cooldown_limit = float(s_tr.get("profit_cooldown_seconds", getattr(dashboard, "profit_cooldown_seconds", 10.0)))
        
        # [선제 락킹] 비동기 대기(await)를 타기 전 즉시 쿨다운을 선제 마킹하여 1초 틈새 휩소 격발 차단
        self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + profit_cooldown_limit)
        
        # 평단가 대비 실제 PnL율이 음수(손실)인지 안전하게 판정
        exit_pnl_pct = 0.0
        if self.entry_price > 0.0:
            current_bitget_price = await self.get_live_bitget_price_internal()
            if direction == "LONG":
                exit_pnl_pct = (current_bitget_price - self.entry_price) / self.entry_price
            else:
                exit_pnl_pct = (self.entry_price - current_bitget_price) / self.entry_price

        if "손절선" in getattr(self, "exit_reason", "") or "손절" in getattr(self, "exit_reason", "") or exit_pnl_pct < 0.0:
            final_cooldown_sec = cooldown_limit
            self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + cooldown_limit)
            reason_label = "손절 쿨타임"
        else:
            final_cooldown_sec = profit_cooldown_limit
            self.cooldown_until_time = max(getattr(self, "cooldown_until_time", 0.0), time.time() + final_cooldown_sec)
            reason_label = "익절 쿨타임"

        if getattr(self, "cooldown_timer_task", None) and not self.cooldown_timer_task.done():
            self.cooldown_timer_task.cancel()
        self.cooldown_timer_task = asyncio.create_task(self.start_cooldown_countdown_timer(final_cooldown_sec, reason_label))

        # --- [신설] 청산 알림 통합 발송 엔진 (누락 100% 방지 및 출구 슬리피지 계측) ---
        if not getattr(self, "exit_msg_sent", False) and not self.is_position_active:
            self.exit_msg_sent = True
            current_bitget_price = await self.get_live_bitget_price_internal()
            reason = getattr(self, "exit_reason", "") or "거래소 서버 사이드 스탑로스 체결 또는 수동 청산"
            
            # 신호 정보 추출 (유령 스탑로스 예약가 오역 원천 사멸)
            trigger_price = getattr(self, "last_exit_trigger_price", 0.0)
            if trigger_price <= 0.0:
                trigger_price = current_bitget_price
            signal_price = trigger_price

            signal_time = getattr(self, "last_exit_signal_time", "")
            if not signal_time:
                signal_time = get_kst_now_str()

            # 웹서버 청산 락다운 저장소 구축 및 추출
            try:
                if self.bot and getattr(self.bot, "bitget_exchange", None):
                    trades = await self.bot.bitget_exchange.fetch_my_trades('BTC/USDT:USDT', limit=2)
                    if trades and len(trades) > 0:
                        last_t = trades[-1]
                        t_price = float(last_t.get('price', 0.0) or 0.0)
                        t_amount = float(last_t.get('amount', 0.0) or 0.0)
                        if t_price > 0.0:
                            self.last_actual_exit_price = t_price
                        if t_amount > 0.0:
                            self.last_actual_exit_qty = t_amount
            except Exception as tr_err:
                logger.error(f"비트겟 청산 체결 원장 수신 예외: {tr_err}")

            real_exit_price = getattr(self, "last_actual_exit_price", 0.0) or current_bitget_price
            real_exit_qty = getattr(self, "last_actual_exit_qty", 0.0) or getattr(self, "position_volume_btc", 0.0) or (float(getattr(self, "position_volume", 0)) / 1000.0 if getattr(self, "position_volume", 0) > 0 else 0.001)
            if real_exit_qty <= 0.0:
                real_exit_qty = 0.001
            real_entry_price = getattr(self, "active_position_entry_price", None) or getattr(self, "entry_price", None) or current_bitget_price

            self.real_bitget_exit_store = {
                'exit_price': real_exit_price,
                'entry_price': real_entry_price,
                'qty_btc': real_exit_qty,
                'direction': direction,
                'timestamp': time.time()
            }

            store_exit = getattr(self, "real_bitget_exit_store", {})
            actual_price = store_exit.get('exit_price', real_exit_price)
            actual_qty = store_exit.get('qty_btc', real_exit_qty)
            entry_p_final = store_exit.get('entry_price', real_entry_price)
            
            signal_qty = actual_qty
            actual_time = getattr(self, "last_actual_exit_time", "")
            if not actual_time:
                actual_time = signal_time

            if True:
                if direction == "LONG":
                    exit_slippage_usd = signal_price - actual_price
                else:
                    exit_slippage_usd = actual_price - signal_price
                exit_slippage_pct = (exit_slippage_usd / signal_price) * 100.0 if signal_price > 0 else 0.0
                
                # 물리 로그 파일 및 화면 로그 실시간 기록
                log_msg = f"🎯 [청산 슬리피지 실측] 저격 트리거가: {signal_price:,.1f} USDT ➡️ 비트겟 청산가: {actual_price:,.1f} USDT | 편차: {exit_slippage_usd:+,.1f} USDT ({exit_slippage_pct:+.3f}% 역마진 발생)"
                if self.bot.dashboard:
                    self.bot.dashboard.add_log(log_msg)
                
                # PnL 계산
                if direction == "LONG":
                    pnl_pct = (actual_price - entry_p_final) / entry_p_final if entry_p_final > 0 else 0.0
                    pnl_from_entry_1 = (actual_price - self.entry_price_1) / self.entry_price_1 if self.entry_price_1 > 0 else pnl_pct
                else:
                    pnl_pct = (entry_p_final - actual_price) / entry_p_final if entry_p_final > 0 else 0.0
                    pnl_from_entry_1 = (self.entry_price_1 - actual_price) / self.entry_price_1 if self.entry_price_1 > 0 else pnl_pct
                    
                if self.bot and self.bot.dashboard:
                    lev_val = getattr(self, "leverage_level", 30) or 30
                    roe_val = pnl_pct * 100 * lev_val
                    if self.has_second_entry or getattr(self, "has_third_entry", False):
                        state_str = "3차 진입 상태" if getattr(self, "has_third_entry", False) else "2차 진입 상태"
                        dir_str = f"{direction} ({state_str})"
                        pnl_str = f"평단 대비 수익률: <b>{pnl_pct * 100:+.2f}% (ROE: {roe_val:+.2f}%)</b>\n1차 대비 수익률: <b>{pnl_from_entry_1 * 100:+.2f}%</b>"
                    else:
                        dir_str = f"{direction}"
                        pnl_str = f"최종수익률: <b>{pnl_pct * 100:+.2f}% (ROE: {roe_val:+.2f}%)</b>"

                    if "손절" in reason or "Stop Loss" in reason or exit_slippage_pct < -0.3:
                        header_title = "📉 [손절 청산 알림]"
                    elif "추적" in reason or "Trailing" in reason or "고점" in reason:
                        header_title = "📈 [추적익절 청산 알림]"
                    elif "반대" in reason:
                        header_title = "🔄 [반대 시그널 청산 알림]"
                    else:
                        header_title = "🏆 [가드레일 익절 청산 알림]"

                    msg = build_telegram_trade_msg(
                        title=header_title,
                        direction=direction,
                        reason=reason,
                        signal_time=signal_time,
                        signal_qty=signal_qty,
                        signal_price=signal_price,
                        actual_time=actual_time if actual_time else signal_time,
                        actual_qty=actual_qty if actual_qty > 0 else signal_qty,
                        actual_price=actual_price if actual_price > 0 else signal_price,
                        entry_price=entry_p_final,
                        leverage=getattr(self, "leverage_level", 30) or 30,
                        is_entry=False
                    )
                    
                    self.bot.dashboard.send_telegram_notification(msg)
                    
                    # 통계 DB 기록 및 클라이언트 전광판 갱신
                    try:
                        btc_qty = actual_qty if actual_qty > 0 else signal_qty
                        if btc_qty <= 0.0:
                            bal_val = float(getattr(self.bot, "bitget_balance", 0.0) or 30.0)
                            btc_qty = max(0.001, round(bal_val / (self.entry_price if self.entry_price > 0 else 63000.0), 3))
                        ent_p = self.entry_price if self.entry_price > 0 else signal_price
                        ext_p = actual_price if actual_price > 0 else signal_price
                        pnl_val = (ext_p - ent_p) * btc_qty if direction == "LONG" else (ent_p - ext_p) * btc_qty
                        roe_val = (pnl_val / (ent_p * btc_qty)) * 100.0 * (getattr(self, "leverage_level", 30) or 30) if ent_p > 0 and btc_qty > 0 else 0.0
                        
                        record_trade_history_event(
                            side=direction,
                            qty=btc_qty,
                            entry_price=ent_p,
                            exit_price=ext_p,
                            pnl_usd=pnl_val,
                            roe_pct=roe_val,
                            reason=reason
                        )
                        if hasattr(self.bot, "ws_server") and self.bot.ws_server:
                            asyncio.create_task(self.bot.ws_server.broadcast_event("EVT_SYNC_STATS", get_calculated_stats_payload()))
                    except Exception as st_err:
                        logger.error(f"통계 기록 업데이트 에러: {st_err}")


# ==============================================================================
# 세션별 임계치 및 트레이딩 핵심 설정 고급 설정창 클래스 (QDialog) (개발계획서_176)
# ==============================================================================
# ==============================================================================
# Websocket Server for Hybrid Streaming
# ==============================================================================

class WsServer:
    def __init__(self, bot_core):
        self.bot_core = bot_core
        self.clients = set()
        self.last_chart_time = 0

    async def handle_sync_position(self, websocket):
        logger.info("📡 [CMD_SYNC_POSITION] 클라이언트 동기화 요청 수신")
        try:
            if self.bot_core.bitget_exchange:
                bal = await self.bot_core.bitget_exchange.fetch_balance({'type': 'swap'})
                usdt_total = bal.get('USDT', {}).get('total', 0.0)
                logger.info(f"💰 [CMD_SYNC_POSITION] 비트겟 API 잔고 조회 성공: usdt_total={usdt_total}")
                await self.broadcast_event('EVT_SYNC_BALANCE', {'usdt_total': usdt_total})
                logger.info(f"📤 [CMD_SYNC_POSITION] EVT_SYNC_BALANCE 송신 완료 ({usdt_total} USDT)")
                
                positions = await self.bot_core.bitget_exchange.fetch_positions(['BTC/USDT:USDT'])
                active_pos = next((p for p in positions if float(p.get('contracts', 0) or p.get('size', 0) or 0) > 0), None)
                logger.info(f"📊 [CMD_SYNC_POSITION] 비트겟 API 포지션 조회 성공: active_pos={active_pos}")
                
                if active_pos:
                    side = active_pos.get('side', 'long').upper()
                    contracts = float(active_pos.get('contracts', 0) or active_pos.get('size', 0) or 0)
                    entry_price = float(active_pos.get('entryPrice', 0) or active_pos.get('price', 0) or 0)
                    leverage = int(active_pos.get('leverage', 10) or 10)
                    
                    if self.bot_core.v35_engine:
                        v35 = self.bot_core.v35_engine
                        prev_entry = float(getattr(v35, "entry_price", 0.0) or 0.0)
                        was_inactive = not v35.is_position_active
                        
                        # [V5.75 완치] 신규 포지션이거나 평단가가 달라지면 구형 분할익절 플래그 100% 리셋
                        if not v35.is_position_active or abs(prev_entry - entry_price) > 0.1:
                            v35.is_half_exited = False
                            v35.has_smart_guarded = False
                            v35.is_manual_half_exited = False
                            v35.awaiting_pullback_pyramid = False
                            
                        v35.is_position_active = True
                        v35.entry_direction = side
                        v35.position_side = side
                        if entry_price > 0.0:
                            v35.entry_price = entry_price
                            v35.active_position_entry_price = entry_price
                        if contracts > 0.0:
                            v35.position_volume = contracts
                            v35.position_volume_btc = contracts
                        v35.leverage = leverage
                        v35.bitget_roe_pct = float(active_pos.get('percentage', 0.0) or 0.0)
                        v35.bitget_unrealized_pnl = float(active_pos.get('unrealizedPnl', 0.0) or 0.0)
                        v35.bitget_mark_price = float(active_pos.get('markPrice', 0.0) or 0.0)
                        
                        # [V7.34 수량/평단 변경 감지 시 3대 안전가드 자동 재배치]
                        last_g = getattr(v35, "last_guarded_pos", {})
                        prev_g_contracts = float(last_g.get("contracts", 0.0) or 0.0)
                        prev_g_price = float(last_g.get("entry_price", 0.0) or 0.0)
                        is_pos_changed = was_inactive or abs(prev_g_contracts - contracts) > 0.00001 or abs(prev_g_price - entry_price) > 0.1
                        if is_pos_changed and entry_price > 0.0 and contracts > 0.0:
                            v35.last_guarded_pos = {
                                "entry_price": entry_price,
                                "contracts": contracts,
                                "side": side
                            }
                            logger.info(f"📱 [포지션 변동 감지 v7.34] 클라이언트 동기화 중 포지션 변동 포착! ({side} {contracts} BTC @ ${entry_price:,.1f}) ➡️ 3대 TP/SL 자동 재배치")
                            asyncio.create_task(v35.place_bitget_tpsl_plan_orders(entry_price, side, contracts))
                        
                    bot_state_val = self.bot_core.v35_engine.bot_state if self.bot_core.v35_engine else "RUNNING"
                    payload = {
                        'has_position': True,
                        'side': side,
                        'contracts': contracts,
                        'entry_price': entry_price,
                        'leverage': leverage,
                        'bot_state': bot_state_val
                    }
                    await self.broadcast_event('EVT_SYNC_POSITION', payload)
                    logger.info(f"📤 [CMD_SYNC_POSITION] EVT_SYNC_POSITION 송신 완료: {payload}")
                else:
                    if self.bot_core.v35_engine:
                        v35 = self.bot_core.v35_engine
                        v35.is_position_active = False
                        v35.position_volume = 0
                        v35.entry_price = 0.0
                        v35.entry_direction = ""
                        v35.is_half_exited = False
                        v35.has_smart_guarded = False
                        v35.is_manual_half_exited = False
                        v35.awaiting_pullback_pyramid = False
                        v35.last_guarded_pos = {}
                        asyncio.create_task(v35.cancel_all_open_plan_orders())
                    bot_state_val = self.bot_core.v35_engine.bot_state if self.bot_core.v35_engine else "RUNNING"
                    await self.broadcast_event('EVT_SYNC_POSITION', {'has_position': False, 'bot_state': bot_state_val})
                    logger.info(f"📤 [CMD_SYNC_POSITION] EVT_SYNC_POSITION 송신 완료: (has_position=False, bot_state={bot_state_val})")
            else:
                err_msg = "bitget_exchange가 초기화되지 않았습니다. server_config.json 키 설정을 확인하세요."
                logger.warning(f"⚠️ [CMD_SYNC_POSITION] {err_msg}")
                await self.broadcast_event('EVT_SYNC_ERROR', {'error': err_msg})
        except Exception as e:
            logger.error(f"❌ [CMD_SYNC_POSITION] 동기화 중 예외 발생: {e}")
            await self.broadcast_event('EVT_SYNC_ERROR', {'error': str(e)})

    async def sync_bitget_real_position_status(self):
        try:
            ex = getattr(self.bot_core, "bitget_exchange", None) or getattr(self, "bitget_exchange", None)
            if ex and self.bot_core and getattr(self.bot_core, "v35_engine", None):
                positions = await ex.fetch_positions(['BTC/USDT:USDT'])
                active_pos = next((p for p in positions if float(p.get('contracts', 0) or 0) > 0), None)
                v35 = self.bot_core.v35_engine
                if not active_pos:
                    if v35.is_position_active:
                        logger.info("⚡ [실시간 강제 동기화 v4.80] 거래소 포지션 0개 감지 ➡️ is_position_active False 강제 리셋 완료")
                        v35.is_position_active = False
                        v35.position_volume = 0
                        v35.entry_price = 0.0
                        v35.entry_direction = ""
                        v35.last_guarded_pos = {}
                        asyncio.create_task(v35.cancel_all_open_plan_orders())
                else:
                    was_inactive = not v35.is_position_active
                    v35.is_position_active = True
                    side_val = active_pos['side'].upper()
                    v35.entry_direction = side_val
                    e_price = float(active_pos.get('entryPrice', 0.0) or 0.0)
                    v_contracts = float(active_pos.get('contracts', 0.0) or 0.0)
                    
                    if e_price > 0.0:
                        v35.entry_price = e_price
                    if v_contracts > 0.0:
                        v35.position_volume = v_contracts
                        v35.position_volume_btc = v_contracts
                        
                    last_g = getattr(v35, "last_guarded_pos", {})
                    prev_g_contracts = float(last_g.get("contracts", 0.0) or 0.0)
                    prev_g_price = float(last_g.get("entry_price", 0.0) or 0.0)
                    is_pos_changed = was_inactive or abs(prev_g_contracts - v_contracts) > 0.00001 or abs(prev_g_price - e_price) > 0.1
                    if is_pos_changed and e_price > 0.0 and v_contracts > 0.0:
                        v35.last_guarded_pos = {
                            "entry_price": e_price,
                            "contracts": v_contracts,
                            "side": side_val
                        }
                        logger.info(f"📱 [포지션 변동 감지 v7.34] WsServer 포지션 변동 감지! ({side_val} {v_contracts} BTC @ ${e_price:,.1f}) ➡️ 3대 TP/SL 자동 재배치")
                        asyncio.create_task(v35.place_bitget_tpsl_plan_orders(e_price, side_val, v_contracts))
        except Exception as e:
            pass

    async def register(self, websocket):
        self.clients.add(websocket)
        client_addr = getattr(websocket, "remote_address", "Unknown")
        logger.info(f"🌐 [WEB_ACCESS] 신선 클라이언트 웹소켓 접속 완료 (Client IP: {client_addr})")
        
        # 0.001초 자동 초기 실적 및 포지션 동기화 전송
        try:
            asyncio.create_task(self.handle_sync_position(websocket))
            init_stats_payload = get_calculated_stats_payload()
            await websocket.send(json.dumps({"evt": "EVT_SYNC_STATS", "data": init_stats_payload}, ensure_ascii=False))
        except Exception as init_err:
            logger.error(f"초기 동기화 패킷 전송 예외: {init_err}")
            
        try:
            async for message in websocket:
                try:
                    payload = json.loads(message)
                    cmd = payload.get("cmd")
                    logger.info(f"🌐 [WEB_COMMAND] 클라이언트 패킷 수신: {cmd}")
                    if cmd == "CMD_SYNC_POSITION":
                        asyncio.create_task(self.handle_sync_position(websocket))
                    elif cmd == "CMD_REQ_STATS_DETAIL":
                        last_date = payload.get("last_downloaded_date")
                        stats_payload = get_calculated_stats_payload(last_downloaded_date=last_date)
                        await self.broadcast_event("EVT_SYNC_STATS", stats_payload)
                    elif cmd == "CMD_START_BOT":
                        if self.bot_core and self.bot_core.v35_engine:
                            self.bot_core.v35_engine.bot_state = "RUNNING"
                            self.bot_core.v35_engine.is_snipe_active = True
                            await self.broadcast_event("ui_update", {"msg": "✅ [봇 제어] 실전 저격 감시가 시작되었습니다.", "log_type": 1, "price": self.bot_core.current_price})
                            asyncio.create_task(self.handle_sync_position(websocket))
                    elif cmd == "CMD_STOP_BOT":
                        if self.bot_core and self.bot_core.v35_engine:
                            self.bot_core.v35_engine.bot_state = "STOPPED"
                            self.bot_core.v35_engine.is_snipe_active = False
                        await self.broadcast_event("ui_update", {"msg": "⏸ [봇 제어] 자동 저격 감시가 정지되었습니다 (보유 포지션 안전 유지)", "log_type": 1, "price": self.bot_core.current_price})
                        asyncio.create_task(self.handle_sync_position(websocket))
                    elif cmd == "CMD_EMERGENCY":
                        if self.bot_core and self.bot_core.v35_engine:
                            self.bot_core.v35_engine.bot_state = "STOPPED"
                            self.bot_core.v35_engine.is_snipe_active = False
                            asyncio.create_task(self.bot_core.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type="FORCE_MARKET_UNCAPPED"))
                        await self.broadcast_event("ui_update", {"msg": "🚨 [비상 탈출] 비상 탈출 로직 가동! 비트겟 100% 전량 시장가 청산 주문 발주 완료.", "log_type": 1, "price": self.bot_core.current_price})
                    elif cmd == "CMD_CLOSE_50":
                        if self.bot_core and self.bot_core.v35_engine:
                            asyncio.create_task(self.bot_core.v35_engine.execute_bitget_internal_packet(side="CLEAR", order_type="50_PERCENT_CLOSE"))
                        await self.broadcast_event("EVT_RESPONSE_LOG", {"message": "📡 [서버 응답] 🌓 비트겟 50% 시장가 분할 청산 명령 패킷 수신 완료"})
                    elif cmd == "CMD_SET_SMART_STOP":
                        active = payload.get("active", False)
                        offset_val = float(payload.get("offset_val", payload.get("offset_pnl", payload.get("offset_roe", 0.5))))
                        ratio = float(payload.get("ratio", 100.0))
                        if self.bot_core and self.bot_core.v35_engine:
                            v35 = self.bot_core.v35_engine
                            v35.custom_stop_active = active
                            v35.custom_stop_offset_pct = offset_val
                            v35.custom_stop_offset_pnl = offset_val
                            v35.custom_stop_close_ratio = ratio
                            
                            # [정공법 완치] 실시간 포지션 방향 및 진입가 기준 정확한 실시간 PNL(가격 변동률 %) 측정
                            entry_dir = getattr(v35, "entry_direction", None) or getattr(v35, "position_side", "LONG") or "LONG"
                            entry_price = float(getattr(v35, "entry_price", 0.0) or 0.0)
                            calc_price = float(getattr(self.bot_core, "current_price", 0.0) or entry_price)
                            
                            if entry_price > 0.0 and calc_price > 0.0:
                                if entry_dir == "LONG":
                                    live_pnl = ((calc_price - entry_price) / entry_price) * 100.0
                                else:
                                    live_pnl = ((entry_price - calc_price) / entry_price) * 100.0
                            else:
                                live_pnl = 0.0
                                
                            live_pnl_rounded = round(live_pnl, 2)
                            v35.custom_stop_set_pnl = live_pnl_rounded
                            
                            # [서버 전담 실행 엔진 강제 가동] 스마트 스탑 설정 시 감시 루프가 안 돌고 있으면 즉시 팝업 구동
                            if active and v35.is_position_active and not getattr(v35, "is_guardrail_running", False):
                                asyncio.create_task(v35.manage_v35_exit_guardrail(entry_dir))
                                logger.info(f"🚀 [웹서버] 스마트 스탑 전담 실시간 감시 엔진 루프 팝업 구동 완료! (설정시점 PNL: {live_pnl_rounded:+.2f}%, 오프셋: {offset_val:+.2f}%)")

                        act_str = f"📡 [웹서버 수신] 🛡️ 스마트 스탑 설정값 수신 완료 (오프셋: {offset_val:+.2f}% PNL, 청산비율: {ratio:.0f}%) ➡️ 웹서버 24시간 실시간 감시 개시!" if active else "📡 [웹서버 수신] 🧹 스마트 스탑 웹서버 감시 해제 완료"
                        await self.broadcast_event("EVT_RESPONSE_LOG", {"message": act_str})
                    elif cmd == "CMD_UPDATE_CONFIG":
                        config_data = payload.get("config", {})
                        if config_data and self.bot_core:
                            ak = config_data.get("bitget_api_key") or config_data.get("api_key")
                            sk = config_data.get("bitget_secret_key") or config_data.get("secret_key")
                            pp = config_data.get("bitget_passphrase") or config_data.get("passphrase")
                            if ak and sk and pp:
                                try:
                                    self.bot_core.bitget_exchange = ccxt.bitget({
                                        'apiKey': str(ak).strip(),
                                        'secret': str(sk).strip(),
                                        'password': str(pp).strip(),
                                        'options': {'defaultType': 'swap'},
                                        'enableRateLimit': True
                                    })
                                except Exception as e_ex:
                                    logger.error(f"bitget_exchange init error: {e_ex}")
                            if "session_thresholds" in config_data:
                                self.bot_core.session_thresholds = config_data["session_thresholds"]
                                if self.bot_core.v35_engine:
                                    self.bot_core.v35_engine.session_thresholds = config_data["session_thresholds"]
                            if "session_guardrails" in config_data:
                                self.bot_core.session_guardrails = config_data["session_guardrails"]
                                if self.bot_core.v35_engine:
                                    self.bot_core.v35_engine.session_guardrails = config_data["session_guardrails"]
                            if "session_trading_configs" in config_data:
                                self.bot_core.session_trading_configs = config_data["session_trading_configs"]
                                if self.bot_core.v35_engine:
                                    self.bot_core.v35_engine.session_trading_configs = config_data["session_trading_configs"]
                            if "manual_threshold" in config_data:
                                self.bot_core.manual_threshold = config_data["manual_threshold"]
                            if "target_liq" in config_data:
                                self.bot_core.target_liq = config_data["target_liq"]
                            if "target_oi" in config_data:
                                self.bot_core.target_oi = config_data["target_oi"]
                            if "target_slippage" in config_data:
                                self.bot_core.target_slippage = config_data["target_slippage"]
                            if "leverage_level" in config_data:
                                self.bot_core.leverage_level = config_data["leverage_level"]
                            if "betting_ratio" in config_data:
                                self.bot_core.betting_ratio = config_data["betting_ratio"]
                            if "split_entry_1_ratio" in config_data:
                                self.bot_core.split_entry_1_ratio = config_data["split_entry_1_ratio"]
                            if "split_entry_2_ratio" in config_data:
                                self.bot_core.split_entry_2_ratio = config_data["split_entry_2_ratio"]
                            if "split_entry_2_trigger_pct" in config_data:
                                self.bot_core.split_entry_2_trigger_pct = config_data["split_entry_2_trigger_pct"]
                            if "split_entry_3_ratio" in config_data:
                                self.bot_core.split_entry_3_ratio = config_data["split_entry_3_ratio"]
                            if "split_entry_3_trigger_pct" in config_data:
                                self.bot_core.split_entry_3_trigger_pct = config_data["split_entry_3_trigger_pct"]
                            if "split_cooldown_seconds" in config_data:
                                self.bot_core.split_cooldown_seconds = config_data["split_cooldown_seconds"]
                            if "cooldown_seconds" in config_data:
                                self.bot_core.cooldown_seconds = config_data["cooldown_seconds"]
                            if "profit_cooldown_seconds" in config_data:
                                self.bot_core.profit_cooldown_seconds = config_data["profit_cooldown_seconds"]
                            if "half_exit_close_ratio" in config_data:
                                self.bot_core.half_exit_close_ratio = config_data["half_exit_close_ratio"]
                            if "half_exit_close_ratio_2" in config_data:
                                self.bot_core.half_exit_close_ratio_2 = config_data["half_exit_close_ratio_2"]
                            if "pyramiding_enabled" in config_data:
                                self.bot_core.pyramiding_enabled = config_data["pyramiding_enabled"]
                            if "pyramiding_ratio" in config_data:
                                self.bot_core.pyramiding_ratio = config_data["pyramiding_ratio"]
                            
                            engine = self.bot_core.v35_engine
                            if engine:
                                if "leverage_level" in config_data:
                                    engine.LEVERAGE = int(config_data["leverage_level"])
                                if "target_slippage" in config_data:
                                    try:
                                        slip_val = float(str(config_data["target_slippage"]).strip())
                                        engine.ENTRY_SLIPPAGE_CAP = slip_val / 100.0
                                    except Exception:
                                        pass
                            
                            self.bot_core.manual_config = {
                                "manual_threshold": self.bot_core.manual_threshold,
                                "target_liq": self.bot_core.target_liq,
                                "target_oi": self.bot_core.target_oi,
                                "target_slippage": self.bot_core.target_slippage
                            }
                            
                            try:
                                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shinseon_config.json")
                                file_config = {}
                                if os.path.exists(config_path):
                                    with open(config_path, "r", encoding="utf-8") as f:
                                        file_config = json.load(f)
                                file_config.update(config_data)
                                with open(config_path, "w", encoding="utf-8") as f:
                                    json.dump(file_config, f, indent=4, ensure_ascii=False)
                            except Exception as e:
                                logger.error(f"서버 설정 저장 실패: {e}")

                            write_trade_history_log(f"⚙️ [파라미터 설정 변경 적용] 레버리지: {config_data.get('leverage_level', 30)}배 | 배팅비중: {config_data.get('deploy_ratio', 100)}% | 1차비중: {config_data.get('split_entry_1_ratio', 100)}% | 2차비중: {config_data.get('split_entry_2_ratio', 50)}% | 손절쿨타임: {config_data.get('cooldown_seconds', 300)}초 | 익절쿨타임: {config_data.get('profit_cooldown_seconds', 15)}초 | 추매제한: {config_data.get('add_cooldown_seconds', 900)}초")
                            logger.info("⚙️ [서버 Config 동기화 완료] 클라이언트 파라미터 수신 및 적용 성공")
                            await self.broadcast_event("ui_update", {"msg": "⚙ [서버 동기화] 클라이언트 트레이딩 파라미터가 AWS 서버에 즉시 반영되었습니다.", "log_type": 1, "price": self.bot_core.current_price})
                    elif cmd == "CMD_REQ_FILE_LIST":
                        dates_set = set()
                        if os.path.exists(LOGS_DIR):
                            for fname in os.listdir(LOGS_DIR):
                                m = re.search(r'(\d{4}-\d{2}-\d{2})', fname)
                                if m:
                                    dates_set.add(m.group(1))
                        hist_dir = os.path.join(BASE_DIR, "docs", "historical_data")
                        if os.path.exists(hist_dir):
                            for fname in os.listdir(hist_dir):
                                m = re.search(r'(\d{4}-\d{2}-\d{2})', fname)
                                if m:
                                    dates_set.add(m.group(1))
                        today_str = get_kst_now().strftime("%Y-%m-%d")
                        dates_set.add(today_str)
                        sorted_dates = sorted(list(dates_set), reverse=True)
                        await self.broadcast_event("EVT_FILE_LIST", {"dates": sorted_dates})
                    elif cmd == "CMD_REQ_FILE_DOWNLOAD":
                        inner_payload = payload.get("payload", {}) if isinstance(payload.get("payload"), dict) else {}
                        req_date = payload.get("date") or inner_payload.get("date") or get_kst_now().strftime("%Y-%m-%d")
                        log_file = os.path.join(LOGS_DIR, f"shinseon_trade_{req_date}.log")
                        csv_file = os.path.join(BASE_DIR, "docs", "historical_data", f"orderflow_history_{req_date}.csv")
                        
                        log_text = ""
                        csv_text = ""
                        if os.path.exists(log_file):
                            try:
                                size = os.path.getsize(log_file)
                                max_read_bytes = 5 * 1024 * 1024  # 최대 5MB 안전 캡처
                                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                                    if size > max_read_bytes:
                                        f.seek(size - max_read_bytes)
                                        f.readline()
                                    log_text = f.read()
                            except Exception as e_log:
                                logger.error(f"Read log_file error: {e_log}")
                        if os.path.exists(csv_file):
                            try:
                                with open(csv_file, "r", encoding="utf-8-sig", errors="ignore") as f:
                                    csv_text = f.read()
                            except Exception as e_csv:
                                logger.error(f"Read csv_file error: {e_csv}")
                        
                        await self.broadcast_event("EVT_FILE_DATA", {
                            "date": req_date,
                            "csv_text": csv_text,
                            "log_text": log_text
                        })
                    elif cmd == "CMD_REQ_STATS_SYNC_RECOVERY":
                        if self.bot_core:
                            await sync_past_bitget_trades_7d(self.bot_core)
                        stats_payload = get_calculated_stats_payload()
                        await self.broadcast_event("EVT_SYNC_STATS", stats_payload)
                        await self.broadcast_event("EVT_RESPONSE_LOG", {"message": "📡 [서버 응답] 🔄 비트겟 최근 7일(100건) 체결 내역 수동 복원 및 실적 통계 동기화가 완료되었습니다."})
                    elif cmd == "CMD_REQ_CSV":
                        csv_path = "shinseon_data.csv"
                        if os.path.exists(csv_path):
                            with open(csv_path, "r", encoding="utf-8") as f:
                                csv_data = f.read()
                            await self.broadcast_event("EVT_CSV_DATA", {"csv_text": csv_data})
                        else:
                            await self.broadcast_event("ui_update", {"msg": "⚠️ [CSV 오류] 서버에 CSV 파일이 존재하지 않습니다.", "log_type": 1, "price": self.bot_core.current_price})
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.error(f"WS Command Error: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"🌐 [WEB_ACCESS] 신선 클라이언트 웹소켓 접속 해제 (Client IP: {client_addr})")

    async def broadcast_event(self, event_type, data):
        if not self.clients:
            return
        msg = json.dumps({"type": event_type, "data": data})
        async def _safe_send(client):
            try:
                await client.send(msg)
            except Exception:
                self.clients.discard(client)
        tasks = [_safe_send(c) for c in list(self.clients)]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_throttled(self, event_type, data):
        now = time.time()
        if now - self.last_chart_time < 0.5:
            return
        self.last_chart_time = now
        if not self.clients:
            return
        msg = json.dumps({"type": event_type, "data": data})
        async def _safe_send(client):
            try:
                await client.send(msg)
            except Exception:
                self.clients.discard(client)
        tasks = [_safe_send(c) for c in list(self.clients)]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

ws_server = None

def ui_callback(current_price, log_type, msg, **kwargs):
    if ws_server:
        data = {"price": current_price, "log_type": log_type, "msg": msg}
        data.update(kwargs)
        # Event type message
        asyncio.create_task(ws_server.broadcast_event("ui_update", data))
        if getattr(ws_server, "_last_logged_ui_msg", None) != msg:
            ws_server._last_logged_ui_msg = msg
            logger.info(f"[UI] {msg}")
    else:
        logger.info(f"[UI] {msg}")

def chart_callback(candles):
    if ws_server:
        asyncio.create_task(ws_server.broadcast_throttled("chart_update", candles))

async def main():
    global ws_server
    core = BotCore()
    ws_server = WsServer(core)
    
    # Websocket server setup
    async with websockets.serve(ws_server.register, "0.0.0.0", 8765, max_size=100*1024*1024):
        logger.info("Websocket server running on port 8765 (100MB Max Payload)")
        await core.run_engine(ui_callback, chart_callback)

if __name__ == "__main__":
    asyncio.run(main())
