from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print(
    client.embeddings.create(
        model="text-embedding-3-small",
        input="test"
    ).data[0].embedding[:5]
)