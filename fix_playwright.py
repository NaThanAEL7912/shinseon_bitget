import re
file_path = "C:/Working/AntiGravity/ShinSeon_Bitget/shinseon_master_app.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("pw = await async_playwright().start()", "raise NotImplementedError('Playwright removed for Bitget migration') # pw = await async_playwright().start()")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
