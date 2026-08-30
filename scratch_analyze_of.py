import paramiko
import pandas as pd
import io

key = paramiko.RSAKey.from_private_key_file('shinseon-key.pem')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('13.192.187.244', username='ubuntu', pkey=key, timeout=10)

stdin, stdout, stderr = ssh.exec_command('tail -n 1500 /home/ubuntu/docs/historical_data/orderflow_history_2026-08-28.csv')
content = stdout.read().decode('utf-8')
ssh.close()

header = 'Timestamp,BTC_Price,Liq_1m,Long_Liq_1m,Short_Liq_1m,Liq_Threshold,OI_Speed_1m,OI_Speed_Thresh,Price_Delta_5s,Price_Delta_1m,Price_Slope_1m,Signal,Bot_State\n'
df = pd.read_csv(io.StringIO(header + content))
df['Timestamp'] = df['Timestamp'].astype(str).str.replace('=', '').str.replace('"', '')
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

print('Time range:', df['Timestamp'].min(), 'to', df['Timestamp'].max())
print('Price range in last 25m:', df['BTC_Price'].min(), '~', df['BTC_Price'].max())
print('Latest Price:', df['BTC_Price'].iloc[-1])
print('Max 1m Liq:', df['Liq_1m'].max(), 'at', df.loc[df['Liq_1m'].idxmax(), 'Timestamp'])
print('Total Long Liq max peak:', df['Long_Liq_1m'].max())
print('Total Short Liq max peak:', df['Short_Liq_1m'].max())
print('Mean OI Speed:', df['OI_Speed_1m'].mean(), 'Min OI Speed:', df['OI_Speed_1m'].min(), 'Max OI Speed:', df['OI_Speed_1m'].max())
print('\nLatest row:')
print(df.iloc[-1].to_dict())

df.set_index('Timestamp', inplace=True)
resample_df = df.resample('3min').agg({
    'BTC_Price': ['first', 'max', 'min', 'last'],
    'Liq_1m': 'max',
    'Long_Liq_1m': 'max',
    'Short_Liq_1m': 'max',
    'OI_Speed_1m': 'mean',
    'Price_Slope_1m': 'last'
})
print('\n=== 3-Min Resampled Summary ===')
print(resample_df.to_string())
