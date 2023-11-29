import os
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

API_SERVICE_NAME = "tasks"
API_VERSION = "v1"
CLIENT_SECRET_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/tasks"]

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
  dt = datetime(year, month, day, hour, minute, 0, 000).isoformat() + 'Z'
  return dt

# import google.oauth2.credentials
# import google_auth_oauthlib.flow

# flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
#   "credentials.json",
#   scopes=SCOPES,
# )
# flow.redirect_uri = 'https://www.example.com/oauth2callback'

# authorization_url, state = flow.authorization_url(
#   access_type='offline',
#   include_granted_scopes='true'
# )

def auth():
  creds = None
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  elif not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
      creds = flow.credentials
      #creds = flow.run_local_server(port=0)

    with open("token.json", "w") as f:
      f.write(creds.to_json())
  
  return creds


def get_tasklists():
  creds = auth()
  try:
    service = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
    results = service.tasklists().list(maxResults=10).execute()
    items = results.get("items", [])
    if not items:
      raise RuntimeError("No task lists found.")

    print("Task lists:")
    for item in items:
      print(f"{item['title']} ({item['id']})")
    return items
  except HttpError as err:
    print(err)

def create_task(tasklist, title, url, due):
  creds = auth()
  service = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
  tasklists = get_tasklists()
  tasklist_id = None
  for tasklist_item in tasklists:
    if tasklist_item["kind"] == "tasks#taskList" and tasklist_item["title"] == tasklist:
      tasklist_id = tasklist_item["id"]
  assert tasklist_id is not None

  results = service.tasks().insert(
    tasklist=tasklist_id,
    body={
      "title": title, 
      "notes": url, 
      "status": "needsAction",
      "due": due, 
    }
  ).execute()