# Session Summary - Quota Tracker

## Current State (Mar 21, 2026)

### Backend
- `fetch_quota.py` tracks Antigravity and Claude Code only
- Codex and Windsurf support were removed from the app flow
- Cached Antigravity rows are reused if the CLI is unavailable

### UI
- Sidebar groups Google accounts, Antigravity accounts, and service accounts
- Quota display uses `% available`
- Service accounts reflect only supported live sources

### Environment
- `.env` keeps Google OAuth and Anthropic settings only
- OpenAI and Codex-specific settings were removed

### Data
- `quota_data.json` no longer contains Codex rows
- `propertism.tamil` remains filtered from display

## Commands
```bash
# Start server
python app.py

# Refresh data in UI
Click "Refresh" button
```
