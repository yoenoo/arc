import streamlit as st
from datetime import datetime
from scrape import download_youtube_shorts
from whisper import speech2text
from chatcompletion import generate_summary
from tasks import get_tasklists, create_task, convert_to_RFC_datetime

# import argparse
# parser = argparse.ArgumentParser()
# parser.add_argument("--url", required=True)
# parser.add_argument("--due", required=True)
# FLAGS,_ = parser.parse_known_args()

today = datetime.today()

@st.cache_data
def get_summary(url):
  fpath = download_youtube_shorts(url)
  txt = speech2text(fpath)
  summary = generate_summary(txt)
  return summary

st.set_page_config(page_title="Backdrop", page_icon="🧊")
st.header("🤖 Youtube Shorts Summary Generator")

google_api_creds = st.file_uploader("Upload your Google API client secret file:", accept_multiple_files=False)
print(google_api_creds)

if google_api_creds is not None:
  with open("credentials_test.json", "w") as f:
    from io import StringIO
    creds = StringIO(google_api_creds.getvalue().decode("utf-8"))
    f.write(creds.read())

text_area = st.empty()
text_area_label = "Place the url of the Youtube Shorts below:"

url = text_area.text_input(label=text_area_label, value=None)
if url is not None:
  if not url.startswith("https://www.youtube.com/shorts"):
    st.error("Please enter valid shorts url!", icon="🚨")

due_date = None
if url is not None and url.startswith("https://www.youtube.com/shorts"):
  due_date = st.date_input("Select the date for the reminder:", value=None, min_value=today)
  print(due_date)

if due_date is not None:
  tasklist_names = [x["title"] for x in get_tasklists()]
  assert len(tasklist_names) > 0
  tasklist_name = st.selectbox("Select the task list to genereate reminders under:", tasklist_names, index=None, placeholder="Select the task list")

if due_date is not None and tasklist_name is not None:
  summary = get_summary(url)
  due = due_date
  due = convert_to_RFC_datetime(due.year, due.month, due.day)
  create_task(tasklist_name, summary, url, due)

  st.write(f"Below summary is saved to your Google Tasks ({tasklist_name}):")
  st.write(summary)