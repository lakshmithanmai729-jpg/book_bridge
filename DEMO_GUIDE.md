# మీ sir కి backend ఎలా చూపించాలి — 5 నిమిషాల demo script

ఇది ఒక presentation plan. ఈ order లో చూపిస్తే backend ఎంత పూర్తిగా ఉందో
స్పష్టంగా కనిపిస్తుంది.

---

## ⚡ Server లేకుండా చూపించాలా?

```bash
python manage.py export_preview --zip
```
తర్వాత **`preview_static/preview.html`** double-click చేయండి — 26 pages
(frontend + backend + API), అన్నీ offline. వివరాలు `RUN_LOCALLY.md` లో.

Server ఉంటే మాత్రం ఈ కింద script నే వాడండి — అది ఇంకా బాగుంటుంది (live AI పనిచేస్తుంది).

---

## 0. ముందు (demo కి 2 నిమిషాల ముందు)

**Server start:**
```bash
./scripts/dev_up.sh          # Mac/Linux
scripts\dev_up.bat           # Windows
```
లేదా:
```bash
.venv/bin/activate           # Windows: venv\Scripts\activate
python manage.py runserver
```

**Tabs ముందే తెరవండి** (browser లో 5 tabs — demo మధ్యలో type చేయక్కరలేదు):

| # | URL | ఏం చూపిస్తారు |
|---|---|---|
| 1 | `http://127.0.0.1:8000/` | App (user side) |
| 2 | `http://127.0.0.1:8000/backend/` | **Backend tour** ⭐ |
| 3 | `http://127.0.0.1:8000/admin/books/book/` | Django admin — listings |
| 4 | `http://127.0.0.1:8000/staff/` | Team dashboard |
| 5 | `http://127.0.0.1:8000/ai/api/parse/?q=neet under 300` | Live JSON API |

**Login:** `demo` / `bookbridge123` (full admin access ఉంది)

> ముందే login అయ్యి ఉండండి — tab 2, 3, 4 అన్నీ login అయిన తర్వాత refresh చేయండి.

---

## 1. User side — 30 సెకన్లు

**Tab 1 (`/`)** తెరవండి.

చెప్పండి:
> "ఇది BookBridge — పాత books ను దగ్గర్లో ఉన్న students కి అమ్మే app.
> Home page లో AI picks, search, categories అన్నీ ఉన్నాయి."

చూపించండి: ఒక book card → **"AI picks for you"** section (reason తో).

---

## 2. Backend tour — 1 నిమిషం ⭐ (ఇదే main screen)

**Tab 2 (`/backend/`)** కి వెళ్ళండి.

ఇక్కడ ఒక్క page లో:
- **13 database tables** — ప్రతి దానికి **live row count**
- ఏ table ఏం store చేస్తుందో ఒక్క వాక్యం వివరణ
- ప్రతి card నుంచి నేరుగా admin కి link
- **7 live API endpoints**

చెప్పండి:
> "ఇవి 13 database tables. Counts అన్నీ live — database నుంచి వచ్చినవి, hardcoded కాదు.
> ఇది Books, Categories, Reports, Users, Chats, Notifications, AI log — అన్నీ."

**ఉదా చూపించండి:** "Book listings — 16" card నొక్కండి → అది నేరుగా
admin యొక్క books list కి తీసుకెళ్తుంది.

---

## 3. Django admin — 1 నిమిషం

**Tab 3 (`/admin/books/book/`)**

చూపించండి:
1. **16 books** table గా — search box, filters (side panel)
2. ఏదైనా book నొక్కండి → edit form:
   - Title, Author, Price, Condition, Area
   - `is_sold`, `is_hidden` checkboxes ← moderation
3. **"Add book"** button — కొత్త listing నేరుగా database లో create చేయవచ్చు

చెప్పండి:
> "ఇది Django admin — database ను నేరుగా చూడటానికి, edit చేయటానికి.
> ప్రతి table ఇక్కడ manage చేయవచ్చు."

**Left sidebar** చూపించండి — Books, Accounts, AI_engine, Auth అని groups ఉన్నాయి.

---

## 4. Moderation flow — 30 సెకన్లు

Admin లో **Reports** నొక్కండి (`/admin/books/report/`).

చూపించండి: ఒక buyer report చేసిన listing (reason: "wrong price").

చెప్పండి:
> "Buyer ఒక listing ను report చేస్తే ఇక్కడ వస్తుంది. మేము status ను
> resolved కి మార్చవచ్చు, లేదా ఆ book ను hide చేయవచ్చు."

---

## 5. AI usage — 30 సెకన్లు

**Tab 4 (`/staff/`)** కి వెళ్ళండి.

చూపించండి:
1. పైన **numbers** — users, listings, sold, open reports
2. **"AI usage · last 7 days"** — ఏ AI feature ఎంత సార్లు వాడారు
3. **"AI risk check on reports"** — ప్రమాదకరమైన listing కి score + కారణం

చెప్పండి:
> "ఇది మా సొంత dashboard — marketplace మొత్తం ఒక్క page లో.
> AI ఎంత వాడుతున్నారో, ఏ listing ప్రమాదకరమో ఇక్కడే కనిపిస్తుంది."

Admin లో **AI events** నొక్కండి (`/admin/ai_engine/aievent/`) →
> "ప్రతి AI call ఇక్కడ log అవుతుంది — కేవలం counts, user text కాదు. Privacy కోసం."

---

## 6. Live API — 30 సెకన్లు

**Tab 5 (`/ai/api/parse/?q=neet under 300`)** కి వెళ్ళండి.

Screen లో JSON కనిపిస్తుంది:
```json
{"ok": true, "filters": {"category": "NEET", "max_price": 300}, ...}
```

చెప్పండి:
> "ఇది live API. 'NEET books under 300' అని ఇచ్చినప్పుడు backend ఏమి
> అర్థం చేసుకుందో ఇక్కడ JSON లో కనిపిస్తుంది."

ఇంకా try చేయండి (address bar లో):
- `/ai/api/search/?q=free novels` → results
- `/ai/api/price/?category=2&condition=good` → price + confidence
- `/healthz/` → database status

---

## 7. Code — 1 నిమిషం (VS Code)

VS Code లో ఈ 4 files తెరవండి:

| File | ఏం చెప్పాలి |
|---|---|
| `books/models.py` | "ఇది Book table — title, price, condition, location, sold flag" |
| `books/views.py` | "ఇది logic — search, filters, pagination" |
| `ai_engine/pricing.py` | "AI price suggestion — comparable listings నుంచి median" |
| `config/settings.py` | "Settings — database, security, email" |

చెప్పండి:
> "మొత్తం 4 apps: books, accounts, ai_engine, core. ప్రతి దానిలో
> models (database), views (logic), admin (backend screen)."

---

## 8. ముగింపు — 15 సెకన్లు

> "మొత్తం backend పూర్తయింది — 13 tables, 50+ routes, 173 automated tests,
> 7 AI features. ఇది ఇప్పుడు local లో run అవుతోంది; Render.com లో deploy
> చేస్తే శాశ్వత public link వస్తుంది."

---

## sir ఇలా అడిగితే — సమాధానాలు

| ప్రశ్న | సమాధానం |
|---|---|
| **"Database ఏది?"** | Development లో SQLite (`db.sqlite3`), production లో PostgreSQL (Render) |
| **"ఎన్ని tables?"** | 13 — tour page లో count తో కనిపిస్తాయి |
| **"API ఉందా?"** | ఉంది — `/ai/api/...` JSON endpoints, `AI.md` లో పూర్తి list |
| **"AI ఎలా పనిచేస్తుంది?"** | Offline ML: TF-IDF, Naive Bayes, collaborative filtering — `AI.md` చూడండి |
| **"Tests ఉన్నాయా?"** | 173 automated tests — `python manage.py test` |
| **"Security?"** | CSRF, rate limiting, private-by-default profiles, no demo accounts in production |
| **"Deploy ఎలా?"** | `DEPLOY.md` — Render blueprint, 4 clicks |

---

## Demo తర్వాత

Demo data మళ్ళీ మొదటికి రావాలంటే:
```bash
python manage.py seed_demo --reset --with-admin
```

Server ఆపడానికి: **Ctrl + C**
