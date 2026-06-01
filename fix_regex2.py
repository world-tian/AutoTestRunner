import os
file_path = '/Users/bytedance/Documents/AutoTestRunner/src/autotest_runner/agent/agent.py'
with open(file_path, 'r') as f:
    content = f.read()

content = content.replace('r"本地报告已生成:\\s*([^\\\\n]+)"', 'r"本地报告已生成:\\s*([^\\n]+)"')

with open(file_path, 'w') as f:
    f.write(content)
