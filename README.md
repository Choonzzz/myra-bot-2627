# myra-bot

Telegram bot for RC4 RAs. Tracks IN/OUT status, manages the duty roster, sends duty reminders, runs a wellbeing check-in, and answers questions via an OpenAI-backed RAG assistant ("Myra").

Hosted on Vercel as a Python serverless app. Only Telegram users listed in `FRIEND_TELEGRAM_MAPPINGS` can use the bot — every other sender is silently ignored.

---

## Setup

### 1. Services you need accounts for

| Service | What it stores | Why |
|---|---|---|
| Vercel | The app itself | Hosting |
| Upstash Redis | User statuses, duty schedule, conversation state | Fast key-value store |
| MongoDB Atlas | Training chunks + embeddings for `/askmyra` | RAG knowledge base |
| OpenAI | API key | `/askmyra`, training embeddings, image OCR |
| Telegram BotFather | Bot token + webhook | The bot itself |

When taking over, create your own accounts for each (or get ownership transferred). The OpenAI account is the one that gets billed — keep an eye on usage.

### 2. Environment variables

Set these in Vercel → Project → Settings → Environment Variables.

| Variable | Example | Notes |
|---|---|---|
| `BOT_TOKEN` | `123456:ABC-DEF...` | From @BotFather |
| `GROUP_CHAT_ID` | `-1001234567890` | The RA group chat ID (negative number) |
| `FRIEND_TELEGRAM_MAPPINGS` | `{"Alycia": "111111111", "Jun Wei": "222222222"}` | JSON of `Name → Telegram user ID`. This is also the access allowlist — only these users can use the bot. |
| `REDIS_URL` | `https://xxx.upstash.io` | From Upstash dashboard |
| `REDIS_TOKEN` | `AYA...` | From Upstash dashboard |
| `OPENAI_API_KEY` | `sk-...` | From platform.openai.com |
| `MONGO_URI` | `mongodb+srv://user:pass@cluster...` | Atlas connection string. Database: `myra_training`, collection: `embeddings`. |

How to find a Telegram user ID: ask the user to message [@userinfobot](https://t.me/userinfobot).

### 3. Deploy

```bash
cd bot
vercel --prod
```

The `vercel.json` in `bot/` configures the deployment. Webhook URL will be `https://<your-vercel-domain>/webhook`.

### 4. Register the Telegram webhook

```bash
curl -F "url=https://<your-vercel-domain>/webhook" \
  https://api.telegram.org/bot<BOT_TOKEN>/setWebhook
```

### 5. Set up cron triggers

The app exposes three GET endpoints that need to be hit on a schedule. Use [cron-job.org](https://cron-job.org), GitHub Actions, or Vercel Cron:

| URL | When to call | What it does |
|---|---|---|
| `/refresh` | Every minute (it self-gates to 3 PM SGT on F/S/S, school holidays, and PH eve) | Prompts all RAs to update IN/OUT for the next duty slot |
| `/reminder` | Every minute (self-gates to 9 PM SGT) | DMs tomorrow's duty RA(s) |
| `/wellbeing` | Whenever you want a wellbeing question sent | Sends a random wellbeing prompt |

### 6. Local development

```bash
cd bot
pip install -r requirements.txt
cp .env.example .env  # create this yourself with the vars above
python app.py
```

Use [ngrok](https://ngrok.com) to expose `localhost:8080` if you want to test the webhook locally.

---

## Bot commands

**Status & schedule**
- `/in` — mark yourself IN
- `/out` — mark yourself OUT
- `/status` — show everyone's current status + today's duty
- `/refresh` — ask everyone to update IN/OUT
- `/view_schedule` — show full duty schedule
- `/view_mine` — show your own slots
- `/update_schedule` — replace the schedule (send JSON of `"Jul 24 (Thu) PM": "Alycia"`)
- `/dutyramessage [AM|PM]` — generate the standard "I'm the duty RA today" message

**Swap / cover**
- `/swap_duty` then `/swap <name>` — request a swap with another RA
- `/cover_duty` — pick a slot to cover for someone else

**Myra (AI assistant)**
- `/askmyra <question>` — ask Myra anything; answers using the RAG knowledge base
- `/trainmyra <text>` or `/trainmyra` + send a file/photo — add to Myra's knowledge base (PDFs, images, text)

**Misc**
- `/eatwhat` — random food suggestion
- `/gay` — joke command
- `/thankyou<name>` — send a thank-you message
- `/help` — list commands

---

## Things to update each semester

- **`SCHOOL_HOLIDAYS` in `bot/scheduler.py`** — list of date ranges where the bot should run on weekdays too. Add new ranges when the academic calendar changes; **the bot will not auto-refresh outside these ranges and weekends**.
- **`FRIEND_TELEGRAM_MAPPINGS`** — update in Vercel env vars when RAs join/leave.
- **Duty schedule** — push a new one via `/update_schedule` whenever the roster changes.

---

## Notes for handover

- A few commands (`/eatwhat`, `/gay`, the wellbeing flow) contain hardcoded personalised jokes for specific RA names. Search `features/misc.py` for those names if you want to remove or update them.
- The old monolithic `handlers.py` has been split by domain: `conversation.py` is the main Telegram conversation handler (webhook routing, command/reply dispatch), `config.py`/`telegram_api.py` hold shared env vars and send/lookup helpers, and `features/` has one file per feature group — `status.py` (IN/OUT, duty schedule, reminders), `swap.py` (swap/cover duty), `myra.py` (RAG assistant + training), `misc.py` (jokes, help, wellbeing check-in).
- There's a `PersonalLeave.docx` template file in `bot/` from a previously-removed feature; safe to delete if you want to clean up.
