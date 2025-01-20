import base64

from openai import OpenAI

client = OpenAI(base_url="http://localhost:8001/openai")

with open(
    "000000039769.jpg",
    "rb",
) as image_file:
    image = base64.b64encode(image_file.read()).decode("utf-8")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What is in the image?",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"}
                },
            ],
        }
    ],
)

print(response)

client = OpenAI(base_url="http://localhost:8001/ollama")

response = client.chat.completions.create(
    model="llama3.2-vision",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What is in the image?",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"}
                },
            ],
        }
    ],
)

print(response)
