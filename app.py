import os
import flask
from flask import Flask, request, render_template
import requests

from datetime import datetime
from scrape import download_youtube_shorts
from whisper import speech2text
from chatcompletion import generate_summary
from tasks import get_tasklists, create_task, convert_to_RFC_datetime

import google.oauth2.credentials
import google_auth_oauthlib.flow
# import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)
app.secret_key = 'REPLACE ME - this value is here as a placeholder.'


with open("client_secret.json", "w") as f:
  import os 
  CLIENT_ID = os.getenv("CLIENT_ID")
  CLIENT_SECRET = os.getenv("CLIENT_SECRET")
  PROJECT_ID = os.getenv("PROJECT_ID")
  print(CLIENT_ID, CLIENT_SECRET, PROJECT_ID)
  secret = {
    "web": {
      "client_id": CLIENT_ID,
      "project_id": PROJECT_ID,
      "auth_uri":"https://accounts.google.com/o/oauth2/auth",
      "token_uri":"https://oauth2.googleapis.com/token",
      "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
      "client_secret":CLIENT_SECRET
    }
  }
  import json
  json.dump(secret, f)

API_SERVICE_NAME = "tasks"
API_VERSION = "v1"
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/tasks"]

@app.route('/')
def index():
  if 'credentials' not in flask.session:
    return flask.redirect('authorize')

  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials']) 

  tasklist_items = get_tasklists(credentials)
  tasklists = [x["title"] for x in tasklist_items]
  return render_template('demo.html', tasklists=tasklists)

  return f"""
  <form method="POST">
    <input name="text">
    <input name="calendar" type="date" />
    <input name="tasklist">

    <p>{tasklists}</p>
    <select id="tasklist">
      <option value="My Task">My Task</option>
      <option value="backdrop">backdrop</option>
    </select>

    <input type="submit">
  </form>
  """
  # return render_template("index.html")
  # return print_index_table()

def get_summary(url):
  fpath = download_youtube_shorts(url)
  txt = speech2text(fpath)
  summary = generate_summary(txt)
  return summary

@app.route('/', methods=['POST'])
def my_form_post():
  url = request.form['url']
  _date = request.form['calendar']
  tasklist = request.form['tasklist']
  
  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials']) 

  
  print(url, _date, tasklist)
  summary = get_summary(url)
  print(summary)
  due = datetime.strptime(_date, "%Y-%m-%d")
  print(due)
  due = convert_to_RFC_datetime(due.year, due.month, due.day)
  print(due)
  create_task(credentials, tasklist, summary, url, due)
  return f"Below summary is saved to your Google Tasks ({tasklist}): {summary}"


@app.route('/test')
def test_api_request():
  if 'credentials' not in flask.session:
    return flask.redirect('authorize')

  # Load credentials from the session.
  credentials = google.oauth2.credentials.Credentials(
      **flask.session['credentials'])

  # drive = googleapiclient.discovery.build(
  #     API_SERVICE_NAME, API_VERSION, credentials=credentials)

  # files = drive.files().list().execute()

  service = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
  results = service.tasklists().list(maxResults=10).execute()
  items = results.get("items", [])
  if not items:
    raise RuntimeError("No task lists found.")

  print("Task lists:")
  for item in items:
    print(f"{item['title']} ({item['id']})")


  # Save credentials back to session in case access token was refreshed.
  # ACTION ITEM: In a production app, you likely want to save these
  #              credentials in a persistent database instead.
  flask.session['credentials'] = credentials_to_dict(credentials)

  # return flask.jsonify(**files)
  return flask.jsonify(items)


@app.route('/authorize')
def authorize():
  # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES)

  # The URI created here must exactly match one of the authorized redirect URIs
  # for the OAuth 2.0 client, which you configured in the API Console. If this
  # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
  # error.
  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  authorization_url, state = flow.authorization_url(
      # Enable offline access so that you can refresh an access token without
      # re-prompting the user for permission. Recommended for web server apps.
      access_type='offline',
      # Enable incremental authorization. Recommended as a best practice.
      include_granted_scopes='true')

  # Store the state so the callback can verify the auth server response.
  flask.session['state'] = state

  return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
  # Specify the state when creating the flow in the callback so that it can
  # verified in the authorization server response.
  state = flask.session['state']

  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  # Use the authorization server's response to fetch the OAuth 2.0 tokens.
  authorization_response = flask.request.url
  flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  # ACTION ITEM: In a production app, you likely want to save these
  #              credentials in a persistent database instead.
  credentials = flow.credentials
  flask.session['credentials'] = credentials_to_dict(credentials)

  return flask.redirect(flask.url_for('index'))


@app.route('/revoke')
def revoke():
  if 'credentials' not in flask.session:
    return ('You need to <a href="/authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials'])

  revoke = requests.post('https://oauth2.googleapis.com/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return('Credentials successfully revoked.' + print_index_table())
  else:
    return('An error occurred.' + print_index_table())


@app.route('/clear')
def clear_credentials():
  if 'credentials' in flask.session:
    del flask.session['credentials']
  return ('Credentials have been cleared.<br><br>' +
          print_index_table())

def get_tasklists(credentials):
  try:
    service = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
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


def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}

def print_index_table():
  return ('<table>' +
          '<tr><td><a href="/test">Test an API request</a></td>' +
          '<td>Submit an API request and see a formatted JSON response. ' +
          '    Go through the authorization flow if there are no stored ' +
          '    credentials for the user.</td></tr>' +
          '<tr><td><a href="/authorize">Test the auth flow directly</a></td>' +
          '<td>Go directly to the authorization flow. If there are stored ' +
          '    credentials, you still might not be prompted to reauthorize ' +
          '    the application.</td></tr>' +
          '<tr><td><a href="/revoke">Revoke current credentials</a></td>' +
          '<td>Revoke the access token associated with the current user ' +
          '    session. After revoking credentials, if you go to the test ' +
          '    page, you should see an <code>invalid_grant</code> error.' +
          '</td></tr>' +
          '<tr><td><a href="/clear">Clear Flask session credentials</a></td>' +
          '<td>Clear the access token currently stored in the user session. ' +
          '    After clearing the token, if you <a href="/test">test the ' +
          '    API request</a> again, you should go back to the auth flow.' +
          '</td></tr></table>')