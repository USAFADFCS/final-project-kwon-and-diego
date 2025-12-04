# src/tools/google_calendar_api.py

from __future__ import print_function
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarService:

    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self):
        token_path = "token.json"

        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if self.creds and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())

        if not self.creds or not self.creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            self.creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(self.creds.to_json())

        self.service = build("calendar", "v3", credentials=self.creds)

    def create_event(self, summary, start_time, end_time):
        event_body = {
            "summary": summary,
            "start": {"dateTime": start_time.isoformat(), "timeZone": "America/Denver"},
            "end":   {"dateTime": end_time.isoformat(), "timeZone": "America/Denver"},
        }
        return self.service.events().insert(calendarId="primary", body=event_body).execute()

    def get_events_this_week(self):
        """Optional observer — returns real world events."""
        now = datetime.datetime.utcnow()
        start = now - datetime.timedelta(days=now.weekday())
        end = start + datetime.timedelta(days=7)

        events = self.service.events().list(
            calendarId="primary",
            timeMin=start.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return events.get("items", [])
