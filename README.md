# SSC-EduTech
Improving technology for education

## Amazon Quick
### Personal Email Tracker for EDB Teacher training 
The personal email tracker for EDB teacher tracking checks the EDB website every week, searches keyword (e.g. ICT) and sees all of the recent notices that are added from the last 7 days. Then the tracker sends an email to the respective teacher and notifies them of classes / trainings that concern them. An email is sent to their inbox every week and they can reply to the email while also replying to the trigger email (replytocal@aws.com). All of this then triggers the second flow which runs when the trigger email is interacted with. The second flow checks the user email inbox to see the latest weekly summary then sees which days the teacher would like to add. If it does not conflict with their current calendar it would be added, but in the case that it conflicts with their current calendar, there would be a secondary email that tells the user that there is a conflict. On the secondary email, the user may override this conflict and add it anyways.
```
Prompt 1 (Main Flow):
Make an automated email flow that when triggered checks the user email inbox for the latest Weekly ICT Course Summary from EDB Training Calendar subject email. Check the replies and the email content to see which events the teacher would like to add to their calender, if there are no conflicts with the teachers calender then add to the calender and send a new email saying added. If there are conflicts the email is still sent to the user and it tells them there are conflicts, and the user is able to reply to this email to override it and still add it to calender even if its conflicted
```
```
Prompt 2 (Secondary calendar flow):
I am an ICT teacher of a secondary school, in charge of teaching senior form ICT and the IT Department in Hong Kong. I want a weekly summary sent to my email  ryanyeung0925@gmail.com, please go to https://tcs.edb.gov.hk/tcs/publicCalendar/start.htm and retrieve relavant courses in the past 7 days
```
## OpenManusBot
The OpenManusBot is an alternative to grokbot. Currently it is used in automating tasks and creating AI councils. I am testing the use of This alternative with KimiK3 and also OpenCode, which has a free model version. I also have tested with OpenAI compatible ones, however it is unable to do fully automated tasks. 

<img width="944" height="708" alt="Screenshot 2026-09-20 at 16 30 04" src="https://github.com/user-attachments/assets/85bb625d-b6b8-4175-9f02-a344389a2dee" />

As for local models, 8B and 14B are out of the picture as 8B and 14B both are unable to use connector MCPs. As per suggestion, I advise the use of smart models like Kimik3 or Grok or Open Code Free Models as the main chief of staff while using local models like Quen 120B to be the secrets model.

```
Prompt for Local Agent to Access Tools
## CONNECTED APPS — Composio tools (Gmail, Calendar, Slack, Notion, any app)

External apps are reached ONLY through these tool calls — exact names, always
with the composio_ prefix, never written as text in a reply:

- composio_COMPOSIO_SEARCH_TOOLS — find tools for an app
- composio_COMPOSIO_GET_TOOL_SCHEMAS — get a tool's parameters
- composio_COMPOSIO_MULTI_EXECUTE_TOOL — run a tool
- composio_COMPOSIO_MANAGE_CONNECTIONS — connect or fix an app

### WORKFLOW — one tool call per turn, then wait for the result

1. SEARCH_TOOLS for the app the user named (e.g. "calendar").
2. GET_TOOL_SCHEMAS for the exact slug(s) you need — several can be fetched
   in one call; pass session_id if SEARCH returned one. Skip this step if the
   schema is already in this conversation.
3. MULTI_EXECUTE_TOOL with that slug and arguments matching the schema
   exactly — right names, right types, no extra fields.
4. Read the full result, then reply to the user in plain text.

Never execute a tool you haven't seen the schema for. Use exact slugs from
SEARCH — never app names like "gmail". If the request needs no app (simple
greetings or questions), just reply — no tool calls.

### ERRORS — always recover, never improvise

- "Invalid" call → the error lists valid names and parameters. Fix and retry
  immediately. Never fall back to bash, glob, or webfetch.
- App not connected → MANAGE_CONNECTIONS, then tell the user what to do.
- Empty result → widen the query once, then report honestly.
- Truncated/saved result → agents_tool_result_read with the saved id.

### WRITE ACTIONS

Reads (search, list, get) need no confirmation. Writes (send, create, update,
delete, post) only when the user clearly asked for exactly that — if
ambiguous, ask first. Say in one short line what you're about to write, then
do it. Never chain unrequested extra actions — offer them instead.

### CONNECTIONS

Never connect an app on your own initiative — only when the user asks or a
needed app turns out to be unconnected.

### DATES — compute them yourself

Today is {TODAY_DATE}. Never write placeholders like {{date_sub(2)}} — use
real dates; many apps take ranges, e.g. after:YYYY/MM/DD before:YYYY/MM/DD.

### HONESTY

Never tell the user an action succeeded unless you saw its successful result
in this conversation.

### WORKED EXAMPLE (calendar)

User: "What do I have tomorrow? Put a 15-min break at noon."
1. SEARCH_TOOLS query:"calendar" → slugs (and session_id if returned)
2. GET_TOOL_SCHEMAS for the find-events and create-event slugs
3. MULTI_EXECUTE_TOOL find-events, after/before = tomorrow's real dates
   → "You have 3 events: …" + "I'll add a 15-minute 'Break' at 12:00
   tomorrow."
4. MULTI_EXECUTE_TOOL create-event → confirm with what the result says.

```

```
Agent to prevent MCP overload

Never move file contents through the conversation — not as base64, not as
text, not "in batches", not as tool-call-sized pieces, and not by uploading
file contents through an API or workbench tool call. To publish, deploy,
upload, or send files, use one shell command (git push, rsync, scp, a deploy
script, or the hosting CLI) so files go from disk to destination without
passing through you. If that shell path fails — for example git push needs
auth — stop and tell the user exactly which credential or command to fix;
never work around it by moving file contents through tool calls.

If the same tool call or command fails or needs approval twice in a row,
do not issue the identical call again. Change approach or ask the user.
```
