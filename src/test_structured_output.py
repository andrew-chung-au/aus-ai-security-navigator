import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


class SystemCheck(BaseModel):
    status: str
    confidence_score: float
    message: str


def run_parse_test():
    load_dotenv()

    client = OpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    )

    model_id = os.getenv("MODEL_ID", "gemini-3.1-flash-lite")

    print(f"Testing .parse(...) compatibility with model: {model_id}...")

    try:
        response = client.chat.completions.parse(
            model=model_id,
            messages=[
                {"role": "developer", "content": "You are a precise diagnostic system."},
                {
                    "role": "user",
                    "content": "Respond strictly matching the schema with a status of 'Operational', a confidence score of 99.9, and a short confirmation message."
                },
            ],
            response_format=SystemCheck,
        )

        result = response.choices[0].message.parsed

        print("\n✅ Success")
        print(f"Status: {result.status}")
        print(f"Confidence: {result.confidence_score}")
        print(f"Message: {result.message}")
        print(f"Parsed type: {type(result)}")

    except Exception as e:
        print(f"\n❌ Test failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    run_parse_test()