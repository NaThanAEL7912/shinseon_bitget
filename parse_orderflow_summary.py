import paramiko, io
import pandas as pd

key = paramiko.RSAKey.from_private_key_file('shinseon-key.pem')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('13.192.187.244', username='ubuntu', pkey=key, timeout=10)
stdin, stdout, stderr = ssh.exec_command('tail -n 600 /home/ubuntu/docs/historical_data/orderflow_history_2026-08-28.csv')
content = stdout.read().decode('utf-8')
ssh.close()

lines = [l.replace('=', '').replace('"', '') for l in content.strip().split('\n') if l.strip()]
headers = ['Timestamp', 'Price', 'Liq_Total', 'Liq_Long', 'Liq_Short', 'Liq_Threshold', 'OI_Speed', 'OI_Threshold', '5s_Delta', '1m_Delta', '1m_Slope', 'Signal', 'Bot_State']
df = pd.DataFrame([row.split(',') for row in lines], columns=headers)

for col in ['Price', 'Liq_Total', 'Liq_Long', 'Liq_Short', 'Liq_Threshold', 'OI_Speed', 'OI_Threshold', '5s_Delta', '1m_Delta', '1m_Slope']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

print("=== 10-MINUTE ORDERFLOW SUMMARY (11:58 ~ 12:08 KST) ===")
print(f"Price Range: ${df['Price'].min():.1f} ~ ${df['Price'].max():.1f} (Current: ${df['Price'].iloc[-1]:.1f})")
print(f"1m Delta Range: ${df['1m_Delta'].min():.1f} ~ ${df['1m_Delta'].max():.1f} (Current: ${df['1m_Delta'].iloc[-1]:.1f})")
print(f"1m OI Speed Range: {df['OI_Speed'].min():.4f}% ~ {df['OI_Speed'].max():.4f}% (Current: {df['OI_Speed'].iloc[-1]:.4f}%)")
print(f"Latest Liquidation 1m: Long ${df['Liq_Long'].iloc[-1]:,.0f} vs Short ${df['Liq_Short'].iloc[-1]:,.0f} (Total ${df['Liq_Total'].iloc[-1]:,.0f})")
print(f"1m Price Slope: Current {df['1m_Slope'].iloc[-1]:.4f}")

# Look at 1-minute sampled data
sample = df.iloc[::60]
print("\n=== 1-MINUTE SAMPLES ===")
print(sample[['Timestamp', 'Price', 'Liq_Total', 'Liq_Long', 'Liq_Short', 'OI_Speed', '1m_Delta', '1m_Slope']].to_string())

