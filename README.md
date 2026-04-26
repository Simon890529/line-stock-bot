# LINE Stock Bot

Taiwan stock institutional investor (三大法人) + active ETF holdings change LINE push notification bot.

## Features

- **Auto push at 16:30 Taiwan time daily** — institutional investor buy/sell data
- **Active ETF holdings changes** tracking (top 10 holdings added/removed/changed)
- Custom watchlist via LINE commands
- Completely free deployment (Render free tier)

## Commands

| Command | Description |
|---------|-------------|
| `查詢 2330` | Query institutional data for a stock |
| `新增 2330` | Add to watchlist |
| `刪除 2330` | Remove from watchlist |
| `清單` | Show watchlist |
| `ETF清單` | Show tracked ETFs |
| `我的ID` | Show your LINE User ID |
| `說明` | Show all commands |

## Deployment Steps

### 1. Fork this repo

### 2. Create LINE Bot
1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Create a Messaging API Channel
3. Get `Channel Access Token` and `Channel Secret`

### 3. Deploy to Render
1. Go to [Render](https://render.com) and sign up
2. Connect GitHub and select this repo
3. Create **Web Service** (`render.yaml` is pre-configured)
4. Set environment variables (see below)

### 4. Environment Variables

| Variable | Description |
|----------|-------------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Access Token |
| `LINE_CHANNEL_SECRET` | LINE Bot Channel Secret |
| `LINE_USER_ID` | Your LINE User ID (add bot as friend and send 我的ID) |
| `CRON_SECRET` | Random secret string (protects cron job endpoint) |
| `ETF1_CODE` ~ `ETF5_CODE` | ETF code (e.g. 00981A) |
| `ETF1_NAME` ~ `ETF5_NAME` | ETF name |
| `ETF1_COMPANY` ~ `ETF5_COMPANY` | Fund company (capital/president/fuh-hwa/allianz/yuanta) |
| `DEFAULT_WATCHLIST` | Default watchlist comma-separated (e.g. 2454,2327) |

### 5. Set LINE Webhook URL
1. Get your Render service URL (e.g. `https://your-bot.onrender.com`)
2. In LINE Developers Console set Webhook URL: `https://your-bot.onrender.com/webhook`
3. Enable Use Webhook

### 6. Prevent Render Sleep
Create a job at [cron-job.org](https://cron-job.org) to ping `https://your-bot.onrender.com/health` every 10 minutes.

### 7. Get Your LINE User ID
Add the bot as a friend, then send `我的ID` to get your User ID. Set it as `LINE_USER_ID`.

## Data Sources

- [TWSE Institutional Investors](https://www.twse.com.tw/zh/trading/foreign/T86.html)
- Individual fund company websites for ETF holdings data

## Tech Stack

- **Flask** — Webhook server
- **LINE Messaging API v3** — Push messages
- **APScheduler** — Scheduling (local testing)
- **Render Cron Job** — Production scheduling (UTC 08:30 = Taiwan 16:30)
- **JSON files** — Data persistence
