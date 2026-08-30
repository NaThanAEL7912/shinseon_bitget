import paramiko, sys

def check():
    sys.stdout.reconfigure(encoding='utf-8')
    key = paramiko.RSAKey.from_private_key_file('shinseon-key.pem')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('13.192.187.244', username='ubuntu', pkey=key, timeout=10)
    stdin, stdout, stderr = ssh.exec_command('sed -n "1770,1792p" /home/ubuntu/shinseon_server.py')
    print("=== [AWS SERVER CODE LINES 1770-1792] ===")
    print(stdout.read().decode('utf-8'))
    ssh.close()

if __name__ == '__main__':
    check()
