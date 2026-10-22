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

## Privacy model

Each profile has a `contact_preference`:

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

## Tests

```bash
python manage.py test accounts
```

Covers Telegram normalisation, contact-mode privacy (phone never leaked), in-app chat send/read,
empty chat state, and book request create/list/delete.

## Project layout

| App | Role |
| --- | --- |
| `core` | Base layout, home page, unread-message context processor, demo seeder |
| `accounts` | Auth, profile & privacy settings, in-app chat, book requests |
| `books` | Listings, search, wishlist, images |
| `ai_engine` | Price suggestion and recommendations |

## License

MIT
