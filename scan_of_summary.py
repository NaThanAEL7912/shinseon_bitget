import paramiko
import sys
import pandas as pd
import io

def scan_of():
    sys.stdout.reconfigure(encoding='utf-8')
    key = paramiko.RSAKey.from_private_key_file('shinseon-key.pem')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('13.192.187.244', username='ubuntu', pkey=key, timeout=10)
    
    stdin, stdout, stderr = ssh.exec_command('tail -n 600 /home/ubuntu/docs/historical_data/orderflow_history_2026-08-28.csv')
    raw = stdout.read().decode('utf-8')
    ssh.close()
    
    # parse CSV lines
    lines = [l.replace('="', '').replace('"', '') for l in raw.strip().split('\n') if l.strip()]
    header = "Timestamp,BTC_Price,Liq_Total,Long_Liq,Short_Liq,Liq_Thresh,OI_Speed,OI_Thresh,5s_Delta,1m_Delta,1m_Slope,Signal,Bot_State"
    data_str = header + "\n" + "\n".join(lines)
    
    df = pd.read_csv(io.StringIO(data_str))
    print("=== ORDERFLOW 10-MIN AGGREGATION ===")
    print("Rows:", len(df))
    print("Price Min/Max:", df['BTC_Price'].min(), df['BTC_Price'].max())
    print("Max Total Liq:", df['Liq_Total'].max(), "Max Long Liq:", df['Long_Liq'].max(), "Max Short Liq:", df['Short_Liq'].max())
    print("Latest 10 rows:")
    print(df[['Timestamp', 'BTC_Price', 'Liq_Total', 'Long_Liq', 'Short_Liq', 'OI_Speed', '1m_Delta', '1m_Slope']].tail(10).to_string())

if __name__ == '__main__':
    scan_of()
