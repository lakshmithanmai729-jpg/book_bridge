# BookBridge

Local second-hand book marketplace. Buy, sell, donate, request, and find books near you — with private
contact options so your phone number is never exposed to strangers.

Built with Django, Bootstrap 5, and a full-width responsive UI (mobile-first, spacious on laptops).

## Features

- Account signup, login, profile, and password change
- Book listings with photos, condition, price, and location
- Donate a book or mark a listing as negotiable
- Search and filter by title, author, city, pincode, category, and price
- Wishlist and suggested books
- Multiple photos per listing
- **Telegram privacy** — sellers can share an `@username` instead of a phone number
- **In-app chat** — buyer ↔ seller conversations stored per book
- **Book requests** — ask nearby students for a book you cannot find
- **Preferred contact mode** — Telegram (recommended), in-app chat, or WhatsApp / Call
- Full-width layout that keeps the mobile app feel while using the whole laptop screen
- **Seller dashboard** — mark books sold, relist them, edit or delete listings
- **Pagination + filters** — 20 books per page with category, condition, price and sort filters
- **Natural-language search** — “NEET books under ₹300 near Madhapur” works in the AI assistant
- **Reporting & moderation** — buyers report listings, moderators hide them from the admin
- **Password reset + email verification** — secure account recovery over email
- **Image optimisation** — uploads are auto-rotated, resized and converted to WebP, plus cached thumbnails
- **Error pages & logging** — friendly 404/403/500 screens and rotating file logs
- **Seller ratings** — buyers rate a seller after chatting; public seller profile with stars,
  review list and *Top seller* / *Verified* badges
- **Block a member** — hides their listings and pauses chats, with a blocked-users page
- **Rate limiting** — chat, listings, reports, reviews and requests are throttled per user
- **Safety Centre** — a plain-language guide to safe deals, scams and reporting
- **Notifications** — a bell menu with price-drop alerts, “back on sale” pings, book-request
  matches and new-review alerts
- **Seller analytics** — views, favourites, chats and per-listing performance
- **Team dashboard** — `/staff/` with live marketplace numbers and the moderation queue
- **SEO & PWA** — sitemap, robots.txt, social preview tags, installable-app manifest
- **Health check** — `/healthz/` JSON probe for uptime monitors and load balancers
- **AI layer** — offline, private machine learning: fair-price suggestions, a listing
  copywriter, Naive Bayes category detection, explainable recommendations with reasons,
  natural-language assistant search (`/ai/`), and a risk score that flags scam listings.
  See [AI.md](AI.md)

## Privacy model

### Public vs Private account

| | Public | Private (default) |
| --- | --- | --- |
| Name shown to other members | Full name | First name only |
| Area / locality | Shown on your seller profile and listing pages | Hidden |
| Join date | Shown | Hidden |
| Ratings, reviews, listings | Visible | Visible |
| Phone number | Only if you choose WhatsApp / Call | Only if you choose WhatsApp / Call |

You choose this in **Account → Profile → Account Privacy**. The seller always sees their own
full name and details, everywhere.

Each profile also has a `contact_preference`:

| Preference | What buyers see on a listing |
| --- | --- |
| `telegram` (Recommended) | A **Telegram** button linking to `https://t.me/<username>` — no phone number |
| `in_app` | **In-App Chat** only — no phone number |
| `whatsapp` | **WhatsApp** button plus in-app chat — the seller has chosen to share their number |

Phone numbers are never printed in listing markup. The number is only used to build a `wa.me` link when
the seller explicitly picked **WhatsApp / Call**.

## Tech stack

- Python / Django 5.x
- MySQL in production (SQLite fallback for local development when no DB credentials are set)
- Bootstrap 5 + Bootstrap Icons
- Pillow (image uploads)

## Guides

* **[RUN_LOCALLY.md](RUN_LOCALLY.md)** — run the app on your own computer in VS Code
* **[BACKEND.md](BACKEND.md)** — how to see the backend: Django admin (`/admin/`),
  the team dashboard (`/staff/`), the database, and the JSON API
* **[AI.md](AI.md)** — how the AI layer works
* **[DEPLOY.md](DEPLOY.md)** — put it online with a permanent link

## Run it yourself (VS Code)

Want to run BookBridge on your own computer without any assistant? See
**[RUN_LOCALLY.md](RUN_LOCALLY.md)** — it covers the one-click Windows script,
the manual steps, the local link (`http://127.0.0.1:8000`), phone testing on
the same Wi-Fi, and every common error.

## Quick start (no terminal knowledge needed)

**Windows:** double-click **`BookBridge-Start.bat`** in the project folder.
**macOS / Linux:** run **`./BookBridge-Start.sh`**.

The script creates the virtual environment, installs requirements, copies `.env.example` to `.env`
if missing, applies migrations, loads demo data when the database is empty, and opens
<http://127.0.0.1:8000> automatically.

Demo login: **demo / bookbridge123**

## Manual setup

1. Clone the repo and create a virtual environment:

```bash
git clone https://github.com/lakshmithanmai729-jpg/book_bridge.git
cd book_bridge
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy environment variables:

```bash
copy .env.example .env
```

3. Fill `.env` with your Django `SECRET_KEY` and (optionally) MySQL credentials. Do not commit `.env`.
   If `DB_NAME` is left empty, BookBridge uses a local `db.sqlite3` file so you can start instantly.

4. Create the database in MySQL (`book_bridge`) if you are using MySQL, then run:

```bash
python manage.py migrate
python manage.py seed_demo        # optional demo data (see below)
python manage.py createsuperuser
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Demo data

`python manage.py seed_demo` creates four accounts, 14 listings (with generated covers), chats, and book
requests. Run it with `--reset` to start over.

| Username | Password | Contact preference |
| --- | --- | --- |
| `demo` | `bookbridge123` | Telegram |
| `arjun` | `bookbridge123` | Telegram |
| `priya` | `bookbridge123` | WhatsApp / Call |
| `rahul` | `bookbridge123` | In-App Chat |

## Key URLs

| Page | URL |
| --- | --- |
| Home | `/` |
| Browse books | `/books/` |
| Book detail + contact actions | `/books/<id>/` |
| Messages / active chats | `/accounts/messages/` |
| Chat room | `/accounts/chat/<user_id>/?book=<book_id>` |
| Start chat from a listing | `/accounts/chat/start/<book_id>/` |
| Profile | `/accounts/profile/` |
| Request a book | `/accounts/request-book/` |
| My listings (seller dashboard) | `/books/my/` |
| Report a listing | `/books/<id>/report/` |
| Forgot password | `/accounts/password-reset/` |
| Confirm email | `/accounts/email/verify/<token>/` |
| Public seller profile | `/accounts/sellers/<user_id>/` |
| Rate a seller | `/accounts/sellers/<user_id>/review/` |
| Block / unblock a member | `/accounts/block/<user_id>/` (POST) |
| Blocked users | `/accounts/blocked/` |
| Safety Centre | `/safety/` |
| Notifications | `/accounts/notifications/` |
| Seller analytics | `/accounts/analytics/` |
| Team dashboard (staff only) | `/staff/` |
| BookBridge AI (assistant + picks) | `/ai/` |
| AI price / classify / describe / risk API | `/ai/api/...` (see [AI.md](AI.md)) |
| Health check | `/healthz/` |
| Sitemap / robots / manifest | `/sitemap.xml`, `/robots.txt`, `/manifest.webmanifest` |

## Tests

```bash
python manage.py test
```

**104 tests** cover Telegram normalisation, contact-mode privacy (phone never leaked), in-app chat
send/read, empty chat state, book requests, pagination & filters, mark-sold/relist, reporting and
moderation visibility, image optimisation, email verification, password reset, chat notifications,
seller reviews (chat-gated, editable, clamped, moderated), blocking (feeds, chats, unblocking) and
rate limiting, notifications (price drops, relists, request matching, reviews), analytics totals,
search ranking, sitemap/robots/manifest, social meta tags and the health check.

## Project layout

| App | Role |
| --- | --- |
| `core` | Base layout, home & safety pages, health check, staff dashboard, sitemaps, rate limiter, middleware, demo seeder |
| `accounts` | Auth, profile & privacy, in-app chat, book requests, reviews, blocks, notifications |
| `books` | Listings, search, wishlist, images |
| `ai_engine` | Price suggestion and recommendations |

## Admin & moderation

`python manage.py createsuperuser` then open `/admin/`:

- **Reports** — review reported listings and use the actions
  *“Hide the reported listing and close the report”*, *“Dismiss”* or *“Mark as reviewed”*.
- **Books** — bulk actions to mark sold, relist, hide or unhide listings.
- **Seller reviews** — hide a fake or abusive review (it immediately stops counting towards the
  seller's average) or unhide it again.
- **User blocks** — see who blocked whom, useful when investigating harassment reports.

### Trust & safety rules

- A review can only be written by someone who has exchanged at least one chat message with the
  seller, so ratings cannot be farmed.
- Ratings are clamped to 1–5 on save, and hidden reviews are excluded from the average.
- Blocking is mutual and silent: neither person sees the other's listings or chats, and the other
  person is not notified.
- Write actions are rate limited (`settings.RATE_LIMITS`) through the cache — 25 chat messages per
  5 minutes, 10 listings an hour, 5 reports an hour, 10 reviews an hour.

## Running the app again after a restart

```bash
./scripts/dev_up.sh          # preview mode, auto-login as demo
./scripts/dev_up.sh --fresh  # rebuild the demo data too
./scripts/dev_up.sh --prod   # gunicorn with production settings
```

Windows: `scripts\dev_up.bat`. The script is idempotent — it only installs,
migrates, seeds or collects static files when something is actually missing.

## Going to production

### Deploy to a host (permanent URL)

`render.yaml` (Render blueprint), `Procfile` (Railway/Heroku) and `fly.toml` (Fly.io)
are included, so any of them can deploy this repo with no extra configuration.
See **[DEPLOY.md](DEPLOY.md)** for the step-by-step guide (including the free tier
caveats) — the app reads `DATABASE_URL`, `RENDER_EXTERNAL_HOSTNAME` and `SITE_URL`
automatically.

### Docker (fastest)

```bash
cp .env.example .env      # fill in SECRET_KEY, ALLOWED_HOSTS, email
docker compose up --build # app on http://localhost:8000
```

`docker-compose.yml` runs migrations, collects static files and starts gunicorn with a
`/healthz/` health check. A PostgreSQL service is included — set `DB_ENGINE=postgres` plus
`DB_NAME/DB_USER/DB_PASSWORD/DB_HOST=db` in `.env` to use it (uncomment `psycopg[binary]` in
`requirements.txt`).

### Manual

1. `.env`: set `DEBUG=False`, a strong `SECRET_KEY`, `ALLOWED_HOSTS`, `SITE_URL`, and real SMTP
   credentials (`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`).
2. `python manage.py collectstatic --noinput` (WhiteNoise serves the files — no nginx needed).
3. Run `gunicorn config.wsgi:application --bind 0.0.0.0:8000` (or `waitress-serve` on Windows).
4. Point your uptime monitor at `/healthz/`; it reports the database status and listing count.
5. Switch `CACHES` to Redis (and `RATE_LIMITS` follows automatically) when you run more than one
   worker — the default LocMem cache is per process.
4. Keep `media/` on a persistent volume or switch to object storage before scaling.

## License

MIT
