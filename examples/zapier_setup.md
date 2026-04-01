# Zapier Integration

Connect any app to Memory Capsule through Zapier without writing code.

## Setup

In any Zapier Zap, add a **Webhooks by Zapier** action:
- Action: **POST**
- URL: `http://YOUR_SERVER:8000/api/webhooks/ingest`
- Payload Type: `JSON`
- Data:
  ```
  text         → [your trigger data]
  source_app   → zapier
  source_sender → [sender field from trigger]
  ```

## Example Zaps

### Gmail → Memory Capsule
- Trigger: **Gmail** → New Email
- Action: Webhooks POST
  ```json
  {
    "text": "Subject: {{subject}}\nFrom: {{from_email}}\n\n{{body_plain}}",
    "source_app": "gmail",
    "source_sender": "{{from_email}}",
    "source_chat": "{{subject}}"
  }
  ```

### Typeform → Memory Capsule
- Trigger: **Typeform** → New Entry
- Action: Webhooks POST
  ```json
  {
    "text": "{{all_answers}}",
    "source_app": "typeform",
    "source_sender": "{{email_field}}",
    "metadata": {"form_name": "{{form_name}}"}
  }
  ```

### Google Calendar → Memory Capsule (meeting notes)
- Trigger: **Google Calendar** → Event Ended
- Action: Webhooks POST
  ```json
  {
    "text": "Meeting: {{summary}}\nAttendees: {{attendees}}\nDescription: {{description}}",
    "source_app": "google_calendar",
    "source_chat": "{{summary}}"
  }
  ```

### Slack Message → Memory Capsule
- Trigger: **Slack** → New Message in Channel
- Action: Webhooks POST
  ```json
  {
    "text": "{{text}}",
    "source_app": "slack",
    "source_sender": "{{user_name}}",
    "source_chat": "#{{channel_name}}"
  }
  ```
