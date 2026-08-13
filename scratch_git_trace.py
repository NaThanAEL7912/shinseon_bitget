import subprocess

cmd = 'git log -S "short_liq >= long_liq" --pretty=format:"COMMIT: %h | DATE: %ad | AUTHOR: %an | MSG: %s" --date=iso'
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)

print("=== GIT BLAME / LOG TRACE FACT ===")
print(res.stdout)
