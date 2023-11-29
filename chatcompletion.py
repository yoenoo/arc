import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv() 

from openai import OpenAI
client = OpenAI()


def generate_summary(text):
  with open("./prompts/openai_system_prompt") as f:
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