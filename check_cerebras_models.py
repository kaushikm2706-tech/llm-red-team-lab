import requests

api_key = "csk-hn6km5w5ttdc3n8n66rey46pvkh96cfwf6xtf923wxnhyhmx"

response = requests.get(
    "https://api.cerebras.ai/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)

print(response.json())