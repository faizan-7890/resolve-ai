import requests

try:
    print("Sending POST request to auth/register...")
    res = requests.post("http://localhost:8000/api/auth/register", json={
        "email": "test_py_direct@example.com",
        "name": "Test Py",
        "password": "Password123"
    }, timeout=5)
    print("Status Code:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)
