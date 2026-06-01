import requests
import json

url = "http://localhost:8000/api/execution-queue/889c0b68-7c5b-4b0a-9995-c226bbe0d5e4/complete"
data = {
    "success": True,
    "result": "foo",
    "html_report": "bar"
}
try:
    response = requests.post(url, json=data)
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print(e)
