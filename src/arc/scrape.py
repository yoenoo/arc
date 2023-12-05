from pathlib import Path
from pytube import YouTube
from utils import hash

SHORTS_DIR = Path("./shorts")

# TODO: add hash support

def download_youtube_shorts(url):
  assert url.startswith("https://www.youtube.com/shorts"), f"video url is not for shorts!"

  yt = YouTube(url)
  stream = yt.streams.get_highest_resolution()
  if stream:
    title = stream.title.strip()
    fname = title + ".mp4"
    print(f"Downloading... [{url}] - [{title}]")
    out = stream.download("./shorts")
    print("Shorts downloaded successfully.")
    return out

if __name__ == "__main__":
  url = "https://www.youtube.com/shorts/nMd4ntAb5aA"
  download_youtube_shorts(url)