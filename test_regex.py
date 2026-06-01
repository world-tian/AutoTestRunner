import re

text = """
2026-05-29 16:18:06,520 - INFO - 📊 本地报告已生成: /tmp/autotest_reports/report_20260529_161806.html
"""
match = re.search(r"本地报告已生成:\s*([^\n]+)", text)
if match:
    print("Match:", match.group(1).strip())
else:
    print("No match")
