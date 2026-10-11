---
name: model-leaderboard-dashboard
description: Research current open-weight and open-source LLMs from public leaderboards and build an interactive HTML dashboard of their parameters, context, license, speed, price and benchmark scores. Use when asked to compare or research local / open models.
---

# Model leaderboard dashboard

Do these steps in order. Each step is ONE tool call. Copy commands exactly.
After each tool result, go straight to the next step's tool call. Do not stop, summarize or ask questions until Step 4.
Never type model names or numbers yourself: the scripts read them from the fetched pages.

## Step 1: fetch the leaderboards

Do NOT use web_search_exa for this skill. Call `web_fetch_exa` with exactly:

- urls: ["https://benchlm.ai/best/open-source", "https://seminal.ai/open-source-large-language-models/", "https://artificialwatch.com/open-weights", "https://artificialanalysis.ai/models/open-source", "https://www.vellum.ai/open-llm-leaderboard"]
- maxCharacters: 60000

The result is large, so TrueForge saves it to a file under /opt/tf/tool-results. That is expected. Do not read or summarize it.

## Step 2: extract the data

Call `exec` with cwd "/opt/tf" and command:

    python3 /opt/tf/skills/model-leaderboard-dashboard/scripts/extract.py

It prints how many tables and models it found per source.

## Step 3: build the dashboard

Call `exec` with cwd "/opt/tf" and command:

    python3 /opt/tf/skills/model-leaderboard-dashboard/scripts/build_dashboard.py

It writes /opt/tf/work/dashboard.html.

## Step 4: answer

Reply with the printed output of steps 2 and 3 and the path /opt/tf/work/dashboard.html.
If any command fails, reply with the exact error instead.
