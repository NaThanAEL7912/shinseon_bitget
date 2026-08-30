pkill -f shinseon_server.py
sleep 1
nohup /home/ubuntu/botenv/bin/python -u /home/ubuntu/shinseon_server.py > /home/ubuntu/server.log 2>&1 &
sleep 2
ps aux | grep shinseon_server.py | grep -v grep