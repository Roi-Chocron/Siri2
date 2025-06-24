import datetime
from jarvis_assistant.core.google_auth_manager import GoogleAuthManager
from jarvis_assistant.utils.logger import get_logger
# We might need dateutil.parser for more flexible date string parsing later
# from dateutil import parser as dateutil_parser

logger = get_logger("GoogleCalendarManager")

# Define the scopes required for Google Calendar API
# Read/write access: 'https://www.googleapis.com/auth/calendar'
# Read-only access: 'https://www.googleapis.com/auth/calendar.readonly'
# Event-specific access: 'https://www.googleapis.com/auth/calendar.events' (allows read/write of events)
CALENDAR_SCOPES_READ_WRITE = ['https://www.googleapis.com/auth/calendar']
CALENDAR_SCOPES_READ_ONLY = ['https://www.googleapis.com/auth/calendar.readonly']


class GoogleCalendarManager:
    def __init__(self, read_only=False):
        """
        Manages interactions with Google Calendar.

        Args:
            read_only (bool): If True, requests read-only permissions.
                              Otherwise, requests read/write permissions.
        """
        scopes = CALENDAR_SCOPES_READ_ONLY if read_only else CALENDAR_SCOPES_READ_WRITE
        # The client_secret_file path is handled by GoogleAuthManager's default
        self.auth_manager = GoogleAuthManager(scopes=scopes)
        self.service = None

    def _get_service(self):
        """Ensures the Google Calendar service is initialized."""
        if not self.service:
            self.service = self.auth_manager.get_authenticated_service('calendar', 'v3')
        if not self.service:
            # This means authentication failed or service build failed.
            # get_authenticated_service already logs errors.
            raise ConnectionError("Failed to connect to Google Calendar service. Check authentication and logs.")
        return self.service

    def list_upcoming_events(self, max_results=10, days_ahead=7, time_period_str=None):
        """
        Lists upcoming events from the primary calendar.

        Args:
            max_results (int): Maximum number of events to return.
            days_ahead (int): Number of days ahead to look for events if time_period_str is not specific.
            time_period_str (str, optional): A string like "today", "tomorrow", "next 3 days".
                                             If provided, it overrides days_ahead for timeMin/timeMax calculation.

        Returns:
            list: A list of event strings, or an empty list if no events / error.
            str: A status message (e.g., "Found 5 events." or "No upcoming events found.")
        """
        try:
            service = self._get_service()
            now_utc = datetime.datetime.utcnow()
            time_min_dt = now_utc
            time_max_dt = None

            if time_period_str:
                time_period_str = time_period_str.lower()
                if "today" in time_period_str:
                    time_min_dt = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
                    time_max_dt = time_min_dt + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
                elif "tomorrow" in time_period_str:
                    time_min_dt = (now_utc + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    time_max_dt = time_min_dt + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
                elif "next" in time_period_str and ("days" in time_period_str or "day" in time_period_str) :
                    try:
                        num_days_match = [int(s) for s in time_period_str.split() if s.isdigit()]
                        if num_days_match:
                            num_days = num_days_match[0]
                            # time_min_dt is now (or start of today if preferred)
                            time_max_dt = now_utc + datetime.timedelta(days=num_days)
                        else: # Default to days_ahead if "next X days" is malformed
                            time_max_dt = now_utc + datetime.timedelta(days=days_ahead)
                    except ValueError:
                         time_max_dt = now_utc + datetime.timedelta(days=days_ahead)
                # Add more parsing for "this week", "next week", specific dates if needed

            if not time_max_dt: # Default if time_period_str didn't set it
                 time_max_dt = now_utc + datetime.timedelta(days=days_ahead)

            time_min_iso = time_min_dt.isoformat() + 'Z'
            time_max_iso = time_max_dt.isoformat() + 'Z'

            logger.info(f"Fetching events from {time_min_iso} to {time_max_iso}, max_results={max_results}")

            events_result = service.events().list(
                calendarId='primary', timeMin=time_min_iso, timeMax=time_max_iso,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            if not events:
                return [], "No upcoming events found in the specified period."

            event_list_formatted = []
            for event in events:
                start_ts = event['start'].get('dateTime', event['start'].get('date'))
                # Try to parse and format the date/time nicely
                try:
                    if 'T' in start_ts: # Datetime
                        start_dt_obj = datetime.datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
                        # Convert to local timezone for display (Python 3.9+)
                        start_dt_obj_local = start_dt_obj.astimezone()
                        formatted_start = start_dt_obj_local.strftime("%a, %b %d, %Y at %I:%M %p %Z")
                    else: # Date only
                        start_dt_obj = datetime.date.fromisoformat(start_ts)
                        formatted_start = start_dt_obj.strftime("%a, %b %d, %Y (All day)")
                except ValueError:
                    formatted_start = start_ts # Fallback to raw string

                event_list_formatted.append(f"{formatted_start} - {event['summary']}")

            return event_list_formatted, f"Found {len(event_list_formatted)} event(s)."

        except ConnectionError as ce:
            logger.error(f"Connection error listing events: {ce}")
            return [], str(ce)
        except Exception as e:
            logger.error(f"Error listing calendar events: {e}", exc_info=True)
            return [], f"An error occurred while fetching calendar events: {e}"

    def create_event(self, summary, start_datetime_iso, end_datetime_iso, description=None, attendees=None):
        """
        Creates a new event on the primary calendar.

        Args:
            summary (str): The title or summary of the event.
            start_datetime_iso (str): Start date/time in ISO 8601 format (e.g., "2024-07-04T10:00:00-07:00").
                                      For all-day events, use "YYYY-MM-DD" date format for both start and end.
            end_datetime_iso (str): End date/time in ISO 8601 format.
            description (str, optional): A description for the event.
            attendees (list of str, optional): List of email addresses for attendees.

        Returns:
            dict: The created event object from Google Calendar API if successful.
            str: A status message.
        """
        if not summary or not start_datetime_iso or not end_datetime_iso:
            return None, "Event summary, start time, and end time are required."

        try:
            service = self._get_service()

            event_body = {
                'summary': summary,
                'start': {},
                'end': {},
            }

            # Check if it's an all-day event based on ISO string format
            if 'T' not in start_datetime_iso: # Likely a date string YYYY-MM-DD
                event_body['start']['date'] = start_datetime_iso
            else:
                event_body['start']['dateTime'] = start_datetime_iso
                # Google Calendar API often requires a timeZone if dateTime is used.
                # If not provided in ISO string, it might default or use user's primary.
                # For robustness, one might extract or add timezone info.
                # Example: event_body['start']['timeZone'] = "America/Los_Angeles"

            if 'T' not in end_datetime_iso:
                event_body['end']['date'] = end_datetime_iso
            else:
                event_body['end']['dateTime'] = end_datetime_iso
                # Similar timezone consideration for end time.

            if description:
                event_body['description'] = description

            if attendees and isinstance(attendees, list):
                event_body['attendees'] = [{'email': email} for email in attendees]

            logger.info(f"Creating event: {summary} from {start_datetime_iso} to {end_datetime_iso}")
            created_event = service.events().insert(calendarId='primary', body=event_body).execute()

            logger.info(f"Event created successfully: ID - {created_event.get('id')}, Link - {created_event.get('htmlLink')}")
            return created_event, f"Event '{summary}' created successfully. View it here: {created_event.get('htmlLink', 'N/A')}"

        except ConnectionError as ce:
            logger.error(f"Connection error creating event: {ce}")
            return None, str(ce)
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}", exc_info=True)
            # Try to parse Google API error for a more specific message
            error_details = getattr(e, 'content', str(e))
            try:
                error_json = json.loads(error_details)
                message = error_json.get('error', {}).get('message', str(e))
            except:
                message = str(e)
            return None, f"Failed to create event: {message}"


if __name__ == '__main__':
    # Example Usage (for testing purposes)
    print("Testing GoogleCalendarManager...")
    # Assuming client_secret.json is in the project root (jarvis_assistant/)

    # Test with read-write permissions
    # Set read_only=True for read-only tests
    try:
        calendar_manager = GoogleCalendarManager(read_only=False)

        # --- Test Listing Events ---
        print("\n--- Listing Upcoming Events (next 7 days) ---")
        events, status_msg = calendar_manager.list_upcoming_events(max_results=5, days_ahead=7)
        print(status_msg)
        if events:
            for event_str in events:
                print(event_str)

        print("\n--- Listing Today's Events ---")
        events_today, status_today = calendar_manager.list_upcoming_events(time_period_str="today")
        print(status_today)
        if events_today:
            for event_str in events_today:
                print(event_str)

        # --- Test Creating an Event ---
        # Note: This will actually create an event on your primary calendar if authentication is successful.
        # Use with caution or a test calendar if preferred (though 'primary' is hardcoded for now).

        # To create a timed event, ensure your ISO strings include time and timezone offset
        # Example: "2024-07-15T10:00:00-07:00" (for PDT, adjust to your local offset or UTC)
        # For UTC: "2024-07-15T17:00:00Z"

        # Create a test event for tomorrow
        tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)
        start_iso_timed = f"{tomorrow_date.isoformat()}T14:00:00Z" # 2 PM UTC tomorrow
        end_iso_timed = f"{tomorrow_date.isoformat()}T15:00:00Z"   # 3 PM UTC tomorrow

        # Create an all-day event for day after tomorrow
        day_after_tomorrow = datetime.date.today() + datetime.timedelta(days=2)
        start_iso_allday = day_after_tomorrow.isoformat()
        end_iso_allday = (day_after_tomorrow + datetime.timedelta(days=1)).isoformat() # All-day events end on the start of the next day

        print(f"\n--- Attempting to Create a Timed Event for tomorrow at 2 PM UTC ---")
        # You might want to comment this out after first successful test to avoid duplicate events
        # created_event_obj, create_status = calendar_manager.create_event(
        #     summary="JARVIS Test Event (Timed)",
        #     start_datetime_iso=start_iso_timed,
        #     end_datetime_iso=end_iso_timed,
        #     description="This is a test event created by J.A.R.V.I.S.",
        #     attendees=[] # e.g., ["your_other_email@example.com"]
        # )
        # print(create_status)
        # if created_event_obj:
        #     print(f"Event details: ID: {created_event_obj.get('id')}")

        # print(f"\n--- Attempting to Create an All-Day Event for the day after tomorrow ---")
        # created_event_allday, create_status_allday = calendar_manager.create_event(
        #     summary="JARVIS Test Event (All-Day)",
        #     start_datetime_iso=start_iso_allday,
        #     end_datetime_iso=end_iso_allday,
        #     description="All-day test."
        # )
        # print(create_status_allday)
        # if created_event_allday:
        #     print(f"Event details: ID: {created_event_allday.get('id')}")

        print("\n(Event creation tests are commented out by default in the script to prevent accidental creations.)")
        print("Uncomment them in `google_calendar_manager.py` if you wish to test event creation.")

    except FileNotFoundError as fnf_error:
        print(f"\nTest Error: {fnf_error}")
        print("Make sure 'client_secret.json' is in the 'jarvis_assistant' directory for this test to run.")
    except ConnectionError as conn_err:
        print(f"\nTest Connection Error: {conn_err}")
        print("This might be due to failed authentication or network issues.")
    except Exception as e:
        print(f"\nAn unexpected error occurred during the Calendar Manager test: {e}")
        logger.error("Calendar Manager Test exception", exc_info=True)

    print("\nGoogleCalendarManager test finished.")
