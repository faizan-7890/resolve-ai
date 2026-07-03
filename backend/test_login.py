import requests

try:
    print("Sending POST request to auth/login...")
    res = requests.post("http://localhost:8000/api/auth/login", json={
        "email": "test_py_direct@example.com",
        "password": "Password123"
    }, timeout=5)
    print("Status Code:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)
