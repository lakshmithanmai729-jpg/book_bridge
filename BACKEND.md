# BookBridge backend — ఎలా చూడాలి (how to see the backend)

BookBridge లో "backend" అంటే **3 వేర్వేరు విషయాలు**. మీకు ఏది కావాలో దాన్ని బట్టి
ఈ కింద చూడండి:

| ఏం చూడాలి | ఎక్కడ | Login |
| --- | --- | --- |
| Database లో ఉన్న data (books, users, chats, notifications, AI log) | `/admin/` | staff / superuser |
| Business overview — numbers, reports, AI usage, risk scores | `/staff/` | staff |
| Machine-facing JSON API (price, search, risk, health) | `/ai/api/...`, `/healthz/` | కొన్నింటికి login |
| Code itself (models, views, migrations) | VS Code file list | — |

---

## 1. Django admin — `/admin/` (ఇదే అసలైన "backend" screen)

ఇక్కడ **database లో ఉన్న ప్రతి row** table రూపంలో కనిపిస్తుంది, edit చేయవచ్చు.

### Local గా (VS Code)
1. Server start చేయండి: `python manage.py runserver`
2. Browser లో తెరవండి: **http://127.0.0.1:8000/admin/**
3. Login: `demo` / `bookbridge123` (demo staff కి పరిమితమైన permissions ఉన్నాయి)
   — పూర్తి access కావాలంటే మీ సొంత superuser create చేయండి:
   ```bash
   python manage.py createsuperuser
   ```

### Deploy తర్వాత
```
https://bookbridge-XXXX.onrender.com/admin/
```
Login: మీ `DJANGO_SUPERUSER_*` account

### ఇక్కడ ఏమి కనిపిస్తుంది

| Group | Models |
| --- | --- |
| **Books** | Books, Categories, Reports, Wishlists |
| **Accounts** | User profiles, Chat messages, Book requests, Seller reviews, User blocks, Notifications |
| **AI_engine** | AI events (ఏ AI feature ఎంత వాడారో — read-only) |
| **Auth** | Users, Groups |

ఉపయోగకరమైన పనులు:

* ఒక book ను **hide** చేయడం → Books → book → `is_hidden` ✓ → Save
* spam report ను **resolved** చేయడం → Reports → status → `resolved`
* ఒక user ను **block/ban** చేయడం → Users → `is_active` తీసేయండి
* ఏదైనా notification పంపడం → Notifications → Add
* సేల్ price తప్పుగా ఉంటే నేరుగా సరిచేయడం → Books → price

### Admin branding
Header **"BookBridge — team backend"** గా ఉంటుంది (`core/apps.py` లో సెట్ చేశాం).

---

## 2. Team dashboard — `/staff/`

ఇది BookBridge కోసం specially రాసిన dashboard (Django admin కాదు):

* మొత్తం users, listings, sold, hidden, open reports
* **AI usage** — గత 7 రోజుల్లో ఏ feature ఎంత వాడారు
* **AI risk check** — open reports లో ఏ listing ప్రమాదకరంగా ఉంది (score + కారణం)
* Latest listings, new members, quick action links

Entry points:
* నేరుగా: `http://127.0.0.1:8000/staff/`
* **Account → Team dashboard** (staff users కి మాత్రమే కనిపిస్తుంది)
* **Account → Backend (Django admin)**

> Demo account కి staff access ఉంది (`seed_demo --with-admin`). Deploy లో
> మీ superuser కి అన్నీ కనిపిస్తాయి.

---

## 3. Database ను నేరుగా చూడాలంటే

Local లో SQLite file: **`db.sqlite3`** (project root).

**Option A — VS Code extension (సులభం)**
1. Extensions లో **"SQLite Viewer"** (Florian Klampfer) install చేయండి
2. `db.sqlite3` file ను click చేయండి → tables అన్నీ browse చేయవచ్చు

**Option B — Django shell**
```bash
python manage.py shell
```
```python
from books.models import Book
Book.objects.count()                    # ఎన్ని books
Book.objects.filter(is_hidden=True)     # hidden books
Book.objects.first().__dict__           # ఒక book యొక్క అన్ని fields

from django.contrib.auth.models import User
User.objects.values_list('username', 'is_staff')

from ai_engine.models import AIEvent
AIEvent.objects.values('kind').order_by()   # ఏ AI feature ఎంత వాడారు
```

**Option C — SQL నేరుగా**
```bash
sqlite3 db.sqlite3
```
```sql
.tables
SELECT id, title, price, is_sold FROM books_book LIMIT 10;
.quit
```

---

## 4. JSON API (browser లోనే చూడవచ్చు)

| URL | ఏం చూపిస్తుంది |
| --- | --- |
| `/healthz/` | status, database, book count |
| `/ai/api/price/?category=2&condition=good` | price suggestion + comparables |
| `/ai/api/search/?q=neet under 300` | parsed filters + results |
| `/ai/api/parse/?q=free novels` | query ఎలా అర్థం చేసుకుంది |
| `/ai/api/similar/5/` | ఇలాంటి books + reason |
| `/sitemap.xml`, `/robots.txt` | SEO |

POST endpoints (`/ai/api/describe/`, `/ai/api/classify/`, `/ai/api/risk/`) కి
curl లేదా app UI వాడాలి.

---

## 5. Code లో backend ఎక్కడ ఉంది

```
config/settings.py       ← అన్ని settings (DEBUG, DB, email, security)
config/urls.py           ← root URL map

core/                    ← home page, staff dashboard, health check, AI docs page
accounts/                ← users, profiles, chat, reviews, notifications
books/                   ← listings, search, wishlist, reports
ai_engine/               ← AI layer (pricing, classify, recommend, trust)

*/models.py              ← database tables (12 models)
*/views.py               ← business logic
*/urls.py                ← routes
*/admin.py               ← ఏ model admin లో కనిపిస్తుంది
*/migrations/            ← database schema history
```

Schema మార్చాలంటే:
```bash
# models.py edit చేయండి
python manage.py makemigrations
python manage.py migrate
```

---

## 6. Login accounts

| Username | Password | Role |
| --- | --- | --- |
| `demo` | `bookbridge123` | staff (limited permissions) — local only |
| మీ superuser | మీరు పెట్టినది | full access |

⚠️ Deploy అయిన public site లో `demo` account **ఉండదు** (భద్రత కోసం).
అక్కడ మీ `DJANGO_SUPERUSER_*` account మాత్రమే ఉంటుంది.

---

## 7. Common గొడవలు

**`/admin/` కి వెళ్ళినప్పుడు "You don't have permission"**
→ Login అయిన account కి `is_staff` లేదు. `python manage.py createsuperuser`
తో కొత్తది create చేయండి.

**Admin లో కొన్ని models కనిపించడం లేదు**
→ Demo account కి పరిమితమైన permissions. Superuser తో login అయితే 13 models
అన్నీ కనిపిస్తాయి.

**`db.sqlite3` తెరవడం లేదు**
→ VS Code లో "SQLite Viewer" extension install చేయండి, లేదా
`python manage.py dbshell` వాడండి.

**Deploy లో `/admin/` 500 ఇస్తోంది**
→ Build logs లో `migrate` run అయ్యిందా చూడండి. Render → Logs.
