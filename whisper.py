import os
from pathlib import Path
from openai import OpenAI
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def speech2text(fpath):
  with open(fpath, "rb") as audio_file:
    transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcription.text.strip()