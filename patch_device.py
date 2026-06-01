file_path = '/Users/bytedance/Documents/AutoTestHub/backend/app/api/device.py'
with open(file_path, 'r') as f:
    content = f.read()

content = content.replace('res.end_time = datetime.utcnow().isoformat()', 'res.end_time = datetime.utcnow()')

with open(file_path, 'w') as f:
    f.write(content)
