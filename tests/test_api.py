import httpx

# Test sending a POST with empty body
response = httpx.post("http://localhost:8000/api/documents/123/export/pdf", json={})
print("JSON Body response:", response.status_code, response.text)

response2 = httpx.post("http://localhost:8000/api/documents/123/export/pdf")
print("No Body response:", response2.status_code, response2.text)
