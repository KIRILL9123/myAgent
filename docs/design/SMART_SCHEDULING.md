# Smart Scheduling v1

Status: **implemented 2026-08-04**
Owner: Calendar domain, exposed through Assistant (Web Chat and Telegram)

## Product placement

Smart Scheduling is a Calendar read model, not a new domain, entity, route, or
notification type. The user asks Mira for a suitable time in Chat or Telegram;
Mira reads the configured calendar, applies explicit approved scheduling rules
from Memory, and proposes concrete local-time options.

The source of truth remains the configured Calendar provider. Memory remains the
source of truth for preferences. The Assistant is the interface that coordinates
the two domains.

## Contract

The central GREEN tool is `find_calendar_slots`:

- read-only; it never creates, moves, or deletes an event;
- accepts a date range up to 31 inclusive calendar days;
- accepts duration, daily earliest/latest time, and a result limit;
- uses the shared `calendar_service.py` provider boundary;
- uses the shared `TemporalContext` and configured personal timezone;
- applies only active, approved Memory facts that match the explicit scheduling
  preference parser (earliest start, latest end, blocked weekday);
- returns a small list of concrete `start`/`end` options and the effective rules
  used to calculate them;
- does not expose unrelated event titles or descriptions in its result.

The existing `create_event` tool remains the only write path. It still performs
conflict and Memory-preference preflight before saving. Mira should call it only
after the user selects a proposed slot; the normal Calendar confirmation and
conflict rules remain in force.

## Conversation flow

1. Parse the user's date, duration, and optional working window into the tool
   arguments.
2. Call `find_calendar_slots` and explain the returned options in the user's
   language.
3. Wait for the user to choose an option or change the constraints.
4. Call `create_event` with the selected exact timestamps.
5. If a conflict is returned, show it and require the existing explicit
   confirmation path; never silently force the event through.

Chat and Telegram use the same registry, schema, permission level, handler, and
Calendar service. No channel-specific scheduling implementation is allowed.

## Explicit boundaries

Out of scope for v1:

- automatic scheduling or rescheduling without the user's choice;
- writing a separate availability table or cache;
- ranking participants, travel time, or external calendars not configured in
  Mira;
- interpreting vague Memory statements as hard constraints;
- sending a Telegram reminder as a side effect of merely searching for a slot.

## Verification

Coverage lives in `backend/tests/test_calendar_availability.py` and the tool
registry/validation tests. The tests cover busy-event exclusion, approved
Memory window and weekday rules, the inclusive 31-day limit, invalid limits,
and the fact that the service only reads events.
