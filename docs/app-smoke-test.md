# App Smoke Test

This document gives you one physical checklist for validating the full app before moving to the next stage.

## Automated Gate

Run the smoke test locally:

```bash
python -m unittest discover -s tests -p test_app_smoke.py -q
```

What it covers:
- homepage render
- health endpoints
- billing metadata endpoints
- brief generation route
- analysis creation
- analysis history and detail fetch
- analysis approval
- export creation and download
- shared export access
- legal data export and consent endpoints

CI also runs this automatically in the `CI / smoke` job.

## Manual Test Flow

Start the app first:

```bash
python app.py
```

Open `http://localhost:5000`.

Then validate this sequence:
1. Load the homepage and confirm the main UI renders.
2. Generate a brief from the demo payload below.
3. Run an analysis from the demo payload below.
4. Open the saved analysis from history.
5. Approve the analysis version.
6. Export the approved analysis as Markdown.
7. Download the export and open the shared link.
8. Run a data export and confirm the analysis and export appear in the archive.

## Demo Data

### Demo Brief Payload

Use this in the UI brief modal or POST it to `/api/generate-brief`.

```json
{
  "project_name": "PlanPlate",
  "project_type": "Web Application",
  "core_idea": "Help families plan meals, share grocery lists, and track weekly dinner plans.",
  "target_audience": "Busy households",
  "key_features": "Meal calendar, grocery list, shared household access",
  "ai_provider": "openrouter"
}
```

### Demo Analysis Payload

Use this in the main app form or POST it to `/analyze`.

```json
{
  "requirements": "Build a collaborative meal-planning web app with household accounts, shared grocery lists, weekly meal calendars, notifications, and an admin dashboard.",
  "ai_enhance": false,
  "ai_provider": "openrouter",
  "target_users": "Families, household admins",
  "business_goal": "Reduce meal planning friction and improve grocery coordination.",
  "success_metrics": "Weekly active households, list completion rate"
}
```

### Demo Export Payload

Use this after an analysis has been approved.

Replace `<analysis_id>` with the real ID from the analysis response.

```json
{
  "analysis_id": "<analysis_id>",
  "format": "markdown"
}
```

### Demo Data Deletion Confirmation

Only use this on a disposable workspace.

```json
{
  "confirm": "DELETE_MY_DATA"
}
```

## Curl Examples

### Create Analysis

```bash
curl -X POST http://localhost:5000/analyze ^
  -H "Content-Type: application/json" ^
  -H "Origin: http://localhost:5000" ^
  -H "Referer: http://localhost:5000/" ^
  -d "{\"requirements\":\"Build a collaborative meal-planning web app with household accounts, shared grocery lists, weekly meal calendars, notifications, and an admin dashboard.\",\"ai_enhance\":false,\"ai_provider\":\"openrouter\",\"target_users\":\"Families, household admins\",\"business_goal\":\"Reduce meal planning friction and improve grocery coordination.\",\"success_metrics\":\"Weekly active households, list completion rate\"}"
```

### Export Workspace Data

```bash
curl -X POST http://localhost:5000/api/legal/data-export ^
  -H "Origin: http://localhost:5000" ^
  -H "Referer: http://localhost:5000/"
```

## Exit Criteria

You are ready for the next stage when:
- `python -m unittest discover -s tests -p test_app_smoke.py -q` passes locally
- `CI / smoke` is green
- the manual demo flow completes without unexpected errors
