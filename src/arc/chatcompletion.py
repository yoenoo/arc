import os
from pathlib import Path
from openai import OpenAI
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def generate_summary(text):
  with open("./prompts/openai_system_prompt.sample") as f:
    content = f.read().strip()

  response = client.chat.completions.create(
    model="gpt-3.5-turbo-1106",
    temperature=0,
    messages=[
      {
        "role": "system",
        "content": content,
      },
      {
        "role": "user",
        "content": text
      }
    ]
  )
  return response.choices[0].message.content.strip()