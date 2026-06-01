import os

file_path = '/Users/bytedance/Documents/AutoTestRunner/src/autotest_runner/core/runner.py'
with open(file_path, 'r') as f:
    content = f.read()

content = content.replace('pytest_args = target_paths + ["-v", f"--html={report_name}", "--self-contained-html"]',
                          'pytest_args = target_paths + ["-v", f"--html={report_name}", "--self-contained-html", "-p", "no:cacheprovider"]')

with open(file_path, 'w') as f:
    f.write(content)

