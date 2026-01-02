# MetaTrader Automation Bot

## ▶️ Running the Bot (Terminal Instructions)

This bot requires **two terminals** running at the same time:

-   **Terminal 1** → runs the Python bot (Selenium + webhook server)
-   **Terminal 2** → runs the Cloudflare tunnel (exposes the webhook to
    TradingView)

Chrome will be opened automatically by Selenium.

------------------------------------------------------------------------

### 1️⃣ Open Terminal 1 --- Start the Python Bot

From the **root of the repository**:

``` powershell
cd MetaTrader-Automation
```

Activate your virtual environment (if you use one):

``` powershell
.\venv\Scripts\activate
```

Run the bot:

``` powershell
python bot_server.py
```

You should see output similar to:

    Logged in and selected XAUUSD. Sleeping 15s...
    Ready. Waiting for TradingView webhook signals...

⚠️ **Do not close this terminal** while trading.

------------------------------------------------------------------------

### 2️⃣ Open Terminal 2 --- Start Cloudflare Tunnel

Open a **second PowerShell window**.

Run:

``` powershell
cloudflared tunnel --url http://localhost:8000
```

Cloudflare will print a public URL like:

    https://example-name.trycloudflare.com

Leave this terminal **open and running**.

------------------------------------------------------------------------

### 3️⃣ Configure TradingView Webhook

In TradingView, set your alert webhook URL to:

    https://<your-cloudflare-url>.trycloudflare.com/webhook

Alert message (JSON):

``` json
{
  "token": "YOUR_SECRET_TOKEN",
  "side": "{{strategy.order.action}}"
}
```

------------------------------------------------------------------------

### 4️⃣ Verify Everything Is Running

For the bot to work, **all three must be active**:

  Component                    Status
  ---------------------------- ---------
  Python bot terminal          Running
  Cloudflare tunnel terminal   Running
  Chrome (Selenium)            Open

------------------------------------------------------------------------

### 5️⃣ Stopping the Bot (Important)

❌ **Do NOT close Chrome manually**

To stop safely:

1.  Go to **Terminal 1**
2.  Press **CTRL + C**

------------------------------------------------------------------------

### ⚠️ Notes About Cloudflare URLs

-   `trycloudflare.com` URLs are **temporary**
-   Every restart generates a **new URL**
-   Update TradingView if the URL changes

A **permanent Cloudflare tunnel** is recommended for long-term use.
