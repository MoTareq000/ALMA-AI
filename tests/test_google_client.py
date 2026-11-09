from unittest.mock import patch, MagicMock
from alma_lessons.llm.google_client import GoogleGeminiLLMClient

def test_google_client_init():
    client = GoogleGeminiLLMClient(api_key="test_key", default_model="gemini-3.5-flash-lite")
    assert client.api_key == "test_key"
    assert client.default_model == "gemini-3.5-flash-lite"

@patch("alma_lessons.llm.google_client.requests.post")
def test_google_client_generate_json(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"result": "success", "count": 42}'}]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 15,
            "candidatesTokenCount": 25,
            "totalTokenCount": 40
        }
    }
    mock_post.return_value = mock_response

    client = GoogleGeminiLLMClient(api_key="test_key")
    resp = client.generate(prompt="Give me JSON", json_mode=True)

    assert resp.parsed_json == {"result": "success", "count": 42}
    assert resp.prompt_tokens == 15
    assert resp.completion_tokens == 25
    assert resp.model_name == "gemini-3.5-flash-lite"
