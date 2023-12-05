import os
import json
import requests
from datetime import datetime
import google.oauth2.credentials
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import flask
from flask import Flask, request, render_template
from utils import http2https
from scrape import download_youtube_shorts
from whisper import speech2text
from chatcompletion import generate_summary

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
PROJECT_ID = os.getenv("PROJECT_ID")
API_SERVICE_NAME = "tasks"
API_VERSION = "v1"
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/tasks"]

app = Flask(__name__)
app.secret_key = "secret_key placeholder" 

if not os.path.exists(CLIENT_SECRETS_FILE):
  with open(CLIENT_SECRETS_FILE, "w") as f:
    secret = {
      "web": {
        "client_id": CLIENT_ID,
        "project_id": PROJECT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": CLIENT_SECRET,
      }
    }
    json.dump(secret, f)

@app.route('/')
def index():
  if "credentials" not in flask.session:
    tasklists = []
  else:
    credentials = google.oauth2.credentials.Credentials(**flask.session["credentials"]) 
    tasklist_items = get_tasklists(credentials)
    tasklists = [x["title"] for x in tasklist_items]

  return render_template("demo.html", tasklists=tasklists)

@app.route('/', methods=["POST"])
def my_form_post():
  url = request.form["url"]
  _date = request.form["calendar"]
  tasklist = request.form["tasklist"]
  
  credentials = google.oauth2.credentials.Credentials(**flask.session["credentials"]) 
  
  summary = get_summary(url)
  due = datetime.strptime(_date, "%Y-%m-%d")
  due = convert_to_RFC_datetime(due.year, due.month, due.day)
  create_task(credentials, tasklist, summary, url, due)
  out = f"<div>Below summary is saved to your Google Tasks ({tasklist})"
  out += summary_to_html(summary)
  out += "</div>"
  return out

@app.route('/authorize')
def authorize():
  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
  flow.redirect_uri = flask.url_for("oauth2callback", _external=True)
  flow.redirect_uri = http2https(flow.redirect_uri)
  print(flow.redirect_uri, flush=True)

  authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")

  flask.session["state"] = state
  return flask.redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
  state = flask.session["state"]
  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
  flow.redirect_uri = flask.url_for("oauth2callback", _external=True)
  flow.redirect_uri = http2https(flow.redirect_uri)

  authorization_response = http2https(flask.request.url)
  flow.fetch_token(authorization_response=authorization_response)

  credentials = flow.credentials
  flask.session["credentials"] = credentials_to_dict(credentials)
  return flask.redirect(flask.url_for("index"))

@app.route('/revoke')
def revoke():
  if "credentials" not in flask.session:
    return """You need to <a href="/authorize">authorize</a> before testing the code to revoke credentials."""

  credentials = google.oauth2.credentials.Credentials(**flask.session["credentials"])
  revoke = requests.post(
    "https://oauth2.googleapis.com/revoke",
    params = {"token": credentials.token},
    headers = {"content-type": "application/x-www-form-urlencoded"}
  )

  status_code = getattr(revoke, "status_code")
  if status_code == 200:
    return "Credentials successfully revoked." + print_index_table()
  else:
    return "An error occurred." + print_index_table()

@app.route('/clear')
def clear_credentials():
  if "credentials" in flask.session:
    del flask.session["credentials"]
  return "Credentials have been cleared.<br><br>" + print_index_table()

def get_summary(url):
  fpath = download_youtube_shorts(url)
  txt = speech2text(fpath)
  summary = generate_summary(txt)
  return summary

def summary_to_html(summary):
  template = ""
  template += "<ul>"
  for item in summary.strip().split("-"):
    if item.strip() != "":
      template += f"<li>{item.strip()}</li>"

  template += "</ul>"
  return template

def get_tasklists(credentials):
  try:
    service = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    results = service.tasklists().list(maxResults=10).execute()
    items = results.get("items", [])
    if not items: raise RuntimeError("No task lists found.")
    return items
  except HttpError as err:
    print(err)

def create_task(credentials, tasklist, title, url, due):
  service = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
  tasklists = get_tasklists(credentials)
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

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
  dt = datetime(year, month, day, hour, minute, 0, 000).isoformat() + "Z"
  return dt

def credentials_to_dict(credentials):
  return {
    "token": credentials.token,
    "refresh_token": credentials.refresh_token,
    "token_uri": credentials.token_uri,
    "client_id": credentials.client_id,
    "client_secret": credentials.client_secret,
    "scopes": credentials.scopes
  }

def print_index_table():
  return """
  <table>
    <tr>
      <td>
        <a href="/test">Test an API request</a>
      </td>
      <td>
        Submit an API request and see a formatted JSON response. 
        Go through the authorization flow if there are no stored
        credentials for the user.
      </td>
    </tr>
    <tr>
      <td>
        <a href="/authorize">Test the auth flow directly</a>
      </td>
      <td>
        Go directly to the authorization flow. If there are stored
        credentials, you still might not be prompted to reauthorize
        the application.
      </td>
    </tr>
    <tr>
      <td>
        <a href="/revoke">Revoke current credentials</a>
      </td>
      <td>
        Revoke the access token associated with the current user
        session. After revoking credentials, if you go to the test
        page, you should see an <code>invalid_grant</code> error.
      </td>
    </tr>
    <tr>
      <td>
        <a href="/clear">Clear Flask session credentials</a>
      </td>
      <td>
        Clear the access token currently stored in the user session.
        After clearing the token, if you <a href="/test">test the
        API request</a> again, you should go back to the auth flow.
      </td>
    </tr>
  </table>
  """