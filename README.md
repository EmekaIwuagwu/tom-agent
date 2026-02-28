# TOM - Autonomous AI Agent

TOM is a personal autonomous AI Agent built to operate like a real human employee. He features persistent memory, web browsing, blockchain network monitoring, Gmail management, Telegram notifications, and can run investor outreach campaigns autonomously.

## Capabilities
- **Blockchain Monitoring**: Automatically monitors and reports the status of Kortana Testnet and Mainnet (RPC and block explorer health).
- **Gmail Integration**: Scans your inbox using Playwright for unread emails and sends replies or new emails using the Gmail API (OAuth2).
- **Web Scraping & Outreach**: Scrapes Crunchbase, AngelList, and Google to find investor contacts, extracts details securely, and uses Gemini AI to draft personalized outreach emails.
- **Pipeline Management**: Maintains a full investor CRM with stages (Prospect, Contacted, Replied, etc.) and allows bulk campaign execution.
- **Telegram Interface**: Access Tom via short commands (`/status`, `/emails`, `/prospects`) or natural language. He works exclusively for his owner.

---

## Setup Guide

### 1. Get Telegram Bot Token
1. Open Telegram and search for `@BotFather`.
2. Start a chat and send the command `/newbot`.
3. Follow the instructions to choose a name and username for your bot.
4. Once created, BotFather will give you a **Bot Token**. Save this for the `.env` file (`TELEGRAM_BOT_TOKEN`).
5. To get your personal Telegram User ID (so Tom only listens to you), search for `@userinfobot` or `@RawDataBot` on Telegram and start a chat. Copy the `id` value and save it (`TELEGRAM_OWNER_USER_ID`).

### 2. Set Up Gmail OAuth2 Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Search for "Gmail API" and **Enable** it.
4. Go to **APIs & Services > OAuth consent screen**. Choose "External" (or Internal if you have a Workspace), fill in the basic details, and add the scope `https://www.googleapis.com/auth/gmail.send`. Add your personal email as a test user.
5. Go to **Credentials**, click **Create Credentials > OAuth client ID**.
6. Choose "Desktop app" as the application type.
7. Download the corresponding JSON file and rename it to `gmail_credentials.json`. Place this in the root of the project.
8. Before deploying to a cloud server, you MUST run Tom locally first to perform the OAuth flow. Run `python index.py` locally and it will prompt you to log into Gmail. This will generate `gmail_token.json` and a Playwright state file `gmail_auth.json`. You must upload these to your server or include them in an encrypted state if possible.

### 3. Get Gemini API Key
1. Go to Google AI Studio: [https://aistudio.google.com/](https://aistudio.google.com/)
2. Click on "Get API key".
3. Create an API key in a new or existing project.
4. Copy this key and save it as `GEMINI_API_KEY` in your `.env` file.

---

## How to Deploy to Render.com
Render makes deploying Tom incredibly easy using the included configuration files.

1. Create a repository on GitHub and push all these files.
2. Sign up / Log into [Render.com](https://render.com).
3. Connect your GitHub account and go to the "Blueprints" tab (or click "New" > "Blueprint").
4. Select your repository.
5. Render will automatically detect the `render.yaml` file and configure a persistent disk (`/data`), Python Docker environment, and background worker service.
6. Before clicking "Apply", configure your environment variables in the Render dashboard or allow the Blueprint to ask you for them. 
   - Note: You must manually upload `gmail_credentials.json`, `gmail_token.json` and `gmail_auth.json` to the `/data` mounted volume via SSH on Render, or push them securely so Tom can stay logged in.
7. Click "Apply"! Tom will spin up and message you on Telegram when he is online.

---

## How to Deploy to a Linux VPS (Ubuntu/Debian)
If you prefer running Tom on your own server (like DigitalOcean, Hetzner, AWS EC2):

1. **SSH into your VPS** and ensure Docker and Docker Compose are installed:
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose
   ```

2. **Clone your repository** or copy the files manually.
   ```bash
   git clone <your-repo-url> tom-agent
   cd tom-agent
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Fill in all the keys you got from Steps 1, 2, and 3.

4. **Upload Gmail Auth Files**
   Ensure `gmail_credentials.json`, `gmail_token.json`, and `gmail_auth.json` are present in the directory so headless Playwright and the Gmail API can authenticate seamlessly.

5. **Build and Run with Docker:**
   You can either run the Dockerfile directly using:
   ```bash
   docker build -t tom-agent .
   docker run -d --name tom -v $(pwd)/data:/app/data --env-file .env --restart unless-stopped tom-agent
   ```
   *(By mapping a local folder `/data`, Tom's memory persists even when the container restarts).*

6. **Check Logs:**
   Verify Tom started correctly:
   ```bash
   docker logs -f tom
   ```

---

## Usage
Once Tom is running, open the chat with your Telegram Bot and say `/help` or just "Hey Tom, check my outstanding emails."
