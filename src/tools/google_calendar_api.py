# src/tools/google_calendar_api.py

from __future__ import print_function
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Calendar API scope: read + write
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarService:

    def __init__(self):
        self.creds = None
        self.service = None

    # ---------------------------------------------------------
    # Authenticate with Google OAuth
    # ---------------------------------------------------------
    def authenticate(self):
        token_path = "token.json"

        # Load existing credentials
        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh expired credentials
        if self.creds and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())

        # Request new login if none
        if not self.creds or not self.creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            self.creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token:
                token.write(self.creds.to_json())

        # Build calendar API client
        self.service = build("calendar", "v3", credentials=self.creds)

    # ---------------------------------------------------------
    # GET: All events for current week (Mon–Sun)
    # ---------------------------------------------------------
    def get_events_this_week(self):
        """Return all events from Monday through Sunday of the current week."""

        now = datetime.datetime.utcnow()
        monday = now - datetime.timedelta(days=now.weekday())  # start of week
        sunday = monday + datetime.timedelta(days=7)            # end of week

        # Convert to RFC3339 format (Google-compliant)
        time_min = monday.isoformat() + "Z"
        time_max = sunday.isoformat() + "Z"

        events_result = self.service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return events_result.get("items", [])

    # ---------------------------------------------------------
    # GET: Next N events
    # ---------------------------------------------------------
    def get_events(self, max_results=10):
        now = datetime.datetime.utcnow().isoformat() + "Z"

        events_result = self.service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return events_result.get("items", [])

    # ---------------------------------------------------------
    # CREATE: Insert new calendar event
    # ---------------------------------------------------------
    def create_event(self, summary, start_time, end_time):
        """Create a new event in Google Calendar."""

        event_body = {
            "summary": summary,
            "start": {"dateTime": start_time.isoformat(), "timeZone": "America/Denver"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "America/Denver"},
        }

        event = self.service.events().insert(
            calendarId="primary", body=event_body
        ).execute()

        return event
