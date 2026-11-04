# 🎓 BookBridge — Viva Preparation (Sir ఏమి అడిగినా ఇక్కడ ఉంది)

> **ఎలా వాడాలి:** ప్రతి question కి **"Sir అడుగుతారు"** → **"మీరు చెప్పేది"** అని ఇద్దరి మాటల్లో ఉంది.
> మొదట **Part 1** చదవండి (ఇది నోట పెట్టుకోవాలి). తర్వాత మీకు ఇష్టమైన part లు.
> **మొత్తం 62 ప్రశ్నలు** — 12 parts.

---

## 📑 Index

| Part | ఏమి ఉంది | ప్రశ్నలు |
|---|---|---|
| **1** | Project పరిచయం (నోట పెట్టుకోవాల్సినది) | 1–6 |
| **2** | Technology ఎంపిక — "ఎందుకు Django?" | 7–14 |
| **3** | Architecture — request ఎలా ప్రయాణిస్తుంది | 15–20 |
| **4** | Database design — tables, relations, indexes | 21–29 |
| **5** | Features — chat, notifications, Buy Now | 30–38 |
| **6** | Privacy & Security | 39–46 |
| **7** | AI features | 47–50 |
| **8** | Performance — "ఎందుకు lag అనిపిస్తుంది?" | 51–54 |
| **9** | Deployment — Render, Neon, free plan | 55–58 |
| **10** | Testing | 59–60 |
| **11** | కఠినమైన ప్రశ్నలు (negative questions) | 61–70 |
| **12** | Live demo + numbers cheat sheet | — |

---

# PART 1 — Project పరిచయం

## ❓ Q1. "మీ project ఏమిటి? ఒక నిమిషంలో చెప్పండి"

**మీరు చెప్పేది:**

> Sir, **BookBridge** — ఒక **second-hand book marketplace** for students.
> ఒక student దగ్గర పనికిరాని books ఉంటాయి, ఇంకొక student కి అవి కావాలి. కానీ మధ్యలో
> **phone number ఇవ్వాల్సి వస్తుంది** — అదే అసలు problem.
>
> మా solution: **phone number ఎప్పటికీ చూపించము.** Buyer, seller ఇద్దరూ
> **in-app chat** లో మాట్లాడుకుంటారు. అవసరమైతే **Telegram handle** (అది కూడా number కాదు).
>
> Books కోసం **Buy Now** బటన్ ఉంది → seller **Accept / Decline** చేస్తారు → book
> automatic గా **Sold** అవుతుంది. డబ్బు app లో కాదు — **meet అయ్యి hand-over లో** ఇచ్చుకుంటారు.
>
> అంతే కాదు — **AI layer** ఉంది: price suggestion, book description generator,
> recommendations. మొత్తం **₹0 ఖర్చులో** live ఉంది.

**⏱️ ఈ మాటలకు 45–60 సెకన్లు పడుతుంది. ప్రాక్టీస్ చేయండి.**

---

## ❓ Q2. "ఈ idea ఎందుకు వచ్చింది? ఏ problem solve చేస్తున్నారు?"

**మీరు చెప్పేది:**

> Sir, 3 problems ఉన్నాయి:
>
> | Problem | ఇప్పుడు ఏమి జరుగుతుంది | మేము ఏమి చేస్తున్నాం |
> |---|---|---|
> | **1. Phone privacy** | OLX/Facebook లో book అమ్మాలంటే number పెట్టాలి → తర్వాత spam calls | Number **ఎప్పటికీ** చూపించము |
> | **2. Trust** | Buyer కి book condition నిజమా అని doubt | Photos + **seller reviews** + verified badge |
> | **3. Local** | Courier ఖర్చు, courier time | **Same city / same college** లో meet అయ్యి ఇచ్చుకోవడం |
>
> Plus: ఒక book అమ్మాలంటే **2 నిమిషాలు** పడుతుంది — 8 fields మాత్రమే.

---

## ❓ Q3. "Target users ఎవరు?"

**మీరు చెప్పేది:**

> **Engineering / Intermediate / Degree students** — Hyderabad, JNTU, Madhapur area లాంటి
> college clusters. వాళ్ళు సెమిస్టర్ తర్వాత books అమ్ముతారు, కొత్త వాళ్ళు కొంటారు.
>
> Secondary users: **parents** (పిల్లల books కొనడానికి), **competitive exam aspirants**
> (IIT-JEE, NEET material).

---

## ❓ Q4. "మీ project లో ఏఏ modules ఉన్నాయి?"

**మీరు చెప్పేది:** — **4 Django apps** ఉన్నాయి:

| App | ఏమి చేస్తుంది |
|---|---|
| **`books`** | Listings, categories, search, wishlist, reports, **Buy Now** |
| **`accounts`** | Signup, login, profile, **chat**, notifications, reviews, blocks, book requests |
| **`ai_engine`** | Price suggestion, description generator, recommendations, trust score |
| **`core`** | Home page, base template, health check, media serving, staff dashboard |

---

## ❓ Q5. "మీ role ఏమిటి? ఒంటరిగా చేశారా?"

**మీరు చెప్పేది:**

> Sir, design, database, backend, frontend, deployment, testing — **అన్నీ నేనే** చేశాను.
> ఒక AI coding assistant ను tool గా వాడాను (pair programmer లాగా) — కానీ
> **architecture decisions, database design, ఏ feature ఎలా ఉండాలి** అన్నవి నా decisions.

> ⚠️ **ఇది ముఖ్యం:** "AI వాడాను" అని దాచకండి. ఇప్పుడు ఇది normal. కానీ **"ఎందుకు అలా చేశాను"**
> అని అడిగితే మీరు చెప్పగలగాలి — అదే viva లో తేడా చూపిస్తుంది.

---

## ❓ Q6. "ఇది ఇంకా ఎవరు వాడుతున్నారు? Users ఉన్నారా?"

**మీరు చెప్పేది (నిజం చెప్పండి):**

> Sir, ఇది **live** ఉంది — `https://bookbridge-aadt.onrender.com`. Demo కోసం
> 16 sample listings + photos + chats seed చేశాను. ఇంకా real users వచ్చి
> signup చేయలేదు — ఇది **deployment stage**. Next step: college groups లో share చేయడం.

> ✅ ఇలా చెప్పడం **weakness కాదు** — "ఇంకా launch కాలేదు, ఇప్పుడు live ఉంది" అనేది honest engineering answer.

---

# PART 2 — Technology ఎంపిక

## ❓ Q7. "ఏ technology stack వాడారు?"

**మీరు చెప్పేది:**

```
Backend    : Python 3.12 + Django 5.2
Database   : PostgreSQL (production) / SQLite (development)
Frontend   : Django Templates + Bootstrap 5 + Vanilla JavaScript
Deployment : Render.com (free tier) + Neon PostgreSQL (free tier)
AI         : Custom rule-based engine (no paid API)
```

---

## ❓ Q8. ⭐ "ఎందుకు Django? Flask లేదా Node.js ఎందుకు కాదు?"

**ఇది 90% అడుగుతారు. ఈ 4 కారణాలు చెప్పండి:**

> **1. Batteries included.** Django లో **authentication, admin panel, ORM, migrations,
> CSRF protection, password hashing** — అన్నీ built-in. Flask లో ఇవి అన్నీ
> libraries కలిపి చేయాలి → 3 రెట్లు code, 3 రెట్లు bugs.
>
> **2. Admin panel ఉచితం.** Django **admin** తో book add చేయడం, users manage చేయడం
> **code రాయకుండానే** వస్తుంది. మా project లో **14 models** admin లో ఉన్నాయి.
> ఇది ఒక్కటే 2 వారాల పని ఆదా చేసింది.
>
> **3. Security by default.** SQL injection (ORM parameterizes), XSS (template auto-escapes),
> CSRF (middleware + token), password hashing (**PBKDF2**). Flask లో ఇవి మీరే జోడించాలి.
>
> **4. Python + ORM.** Database queries Python లోనే రాస్తాం —
> `Book.objects.filter(is_sold=False)` → safe SQL. Raw SQL రాయాల్సిన అవసరం లేదు.

**Follow-up: "Node.js ఎందుకు కాదు?"**
> Node + Express వేగంగా ఉంటుంది, కానీ **book marketplace కి CPU-fast కాదు, developer-fast కావాలి.**
> Django లో ఒక feature కి 30 lines, Express + Prisma + Passport లో 150 lines.

---

## ❓ Q9. "Django లో MVT ఏమిటి?"

**మీరు చెప్పేది:**

> Django **MVT** pattern వాడుతుంది — MVC కి దగ్గరగా:
>
> | Letter | పేరు | మా project లో |
> |---|---|---|
> | **M** | Model | `books/models.py` → `Book`, `BuyRequest` |
> | **V** | View | `books/views.py` → `book_detail()` — logic |
> | **T** | Template | `books/templates/books/book_detail.html` — HTML |
>
> MVC లో Controller Django **URLconf** (`urls.py`) చేస్తుంది — URL → view map.

---

## ❓ Q10. "Frontend కి React ఎందుకు వాడలేదు?"

**మీరు చెప్పేది:**

> 3 కారణాలు:
>
> **1. SEO.** Book pages Google లో rank కావాలి. Django **server-side rendered HTML**
> → Google వెంటనే చదువుతుంది. React SPA కి extra SSR setup కావాలి.
>
> **2. Speed on 0.1 CPU.** మా hosting free tier — **0.1 CPU**. React bundle
> (300 KB) load అవ్వడం కంటే plain HTML + Bootstrap (CDN) వేగం.
>
> **3. Simplicity.** ఒక్క codebase, ఒక్క deploy. React + Django అంటే **రెండు servers**,
> CORS, 2 deployments.
>
> **కానీ** interactivity కావాల్సిన చోట (chat, badges) **Vanilla JS + fetch()** వాడాను —
> అది React కి దగ్గరగా పనిచేస్తుంది, bundle లేకుండా.

---

## ❓ Q11. "Database ఏది? ఎందుకు?"

**మీరు చెప్పేది:**

> **Development** లో **SQLite** (ఒక file, install అవసరం లేదు).
> **Production** లో **PostgreSQL** (Render → Neon).
>
> **ఎందుకు PostgreSQL?**
> - **Concurrent writes** — 100 users ఒకేసారి message పంపినా lock అవ్వదు (SQLite లో ఆగిపోతుంది)
> - **Constraints** — `UniqueConstraint`, `CheckConstraint` support
> - **Full-text search** — భవిష్యత్తులో
> - **Managed + free** — Neon free tier ఎప్పటికీ expire అవ్వదు

> ✅ Django ORM వల్ల **code మార్చకుండా** SQLite → PostgreSQL మారగలిగాం.
> `settings.py` లో `DATABASE_URL` మారితే చాలు.

---

## ❓ Q12. "ఎందుకు Render? AWS లేదా Heroku కాదు?"

**మీరు చెప్పేది:**

| Platform | ఖర్చు | Problem |
|---|---|---|
| **AWS EC2** | ~$10/నెల | Server maintain చేయాలి, Linux, nginx, SSL — student కి భారం |
| **Heroku** | Free tier **తీసేశారు** (2022) | ఉచితం లేదు |
| **Vercel** | Free | Django కి **read-only filesystem**, 4.5 MB body limit → uploads పనిచేయవు |
| **Render** ✅ | **₹0** | `render.yaml` తో one-click, auto-deploy on git push |

> **నిజం:** Render free లో **512 MB RAM, 0.1 CPU, 15 నిమిషాలు idle అయితే sleep** —
> అది limitation. కానీ **student project కి ₹0 ముఖ్యం**.

**Follow-up: "sleep problem ఏమి చేశారు?"** → Q53 చూడండి.

---

## ❓ Q13. "ఏ libraries వాడారు?"

**మీరు చెప్పేది:**

| Library | ఎందుకు |
|---|---|
| **Django 5.2** | Core framework |
| **Pillow** | Book cover image resize/compress |
| **Whitenoise** | Static files serve చేయడం (nginx లేకుండా) |
| **psycopg 3** | PostgreSQL driver |
| **gunicorn** | Production WSGI server |
| **Bootstrap 5 + Icons** | Responsive UI, CDN నుంచి |
| **dj-database-url** (logic) | `DATABASE_URL` parse చేయడం |

> ⚠️ **gunicorn ఎందుకు?** `runserver` **development only** — single-threaded, insecure.
> gunicorn **multi-worker, production-grade**.

---

## ❓ Q14. "Python version?"

**మీరు చెప్పేది:** **Python 3.12.6** on Render (local 3.11). `render.yaml` లో
`PYTHON_VERSION` pin చేశాను — ఎప్పుడూ ఒకటే version, "నా machine లో పనిచేస్తుంది" problem రాదు.

---

# PART 3 — Architecture

## ❓ Q15. ⭐ "ఒక user browser లో `bookbridge.com/books/5/` టైప్ చేస్తే ఏమి జరుగుతుంది?"

**ఇది classic question. Step-by-step చెప్పండి:**

```
1. Browser → HTTPS request → Render server
2. gunicorn → Django WSGI application
3. MIDDLEWARE (వరుసగా):
     SecurityMiddleware      → HTTPS redirect
     WhiteNoiseMiddleware    → static file అయితే ఇక్కడే ఆగుతుంది
     SessionMiddleware       → ఏ user అని session cookie చదువుతుంది
     CsrfMiddleware          → POST అయితే token verify
     AuthenticationMiddleware→ request.user సెట్
     NoStoreHTMLMiddleware   → ఏ page నూ cache చేయకూడదు
4. URLconf: config/urls.py → 'books/' → books/urls.py → '<int:pk>/' → book_detail
5. View: book_detail(request, pk=5)
     a. Book.objects.select_related('seller','category').get(pk=5)
        → SQL: SELECT ... FROM books_book JOIN auth_user ...
     b. hidden/blocked check → 404 అయితే ఆగుతుంది
     c. views_count = F('views_count') + 1   (atomic, race-free)
     d. recommendations = similar_books()
     e. BuyRequest pending list (seller అయితే)
6. Template: book_detail.html — context తో render
7. Response: HTML + Cookie + `Cache-Control: no-store` + `X-BB-App: 1`
8. Browser → render. JS → `/accounts/badges/` ను 20 sec కి ఒకసారి poll
```

> 💡 **`select_related` ఎందుకు?** అది లేకపోతే book కోసం 1 query, seller కోసం 1,
> category కోసం 1 → **3 queries**. `select_related` తో **1 JOIN query**. దీన్ని
> **N+1 problem** అంటారు (Q22 చూడండి).

---

## ❓ Q16. "Project folder structure ఎందుకు ఇలా ఉంది?"

**మీరు చెప్పేది:**

```
book_bridge/
├── config/          settings, urls, wsgi  (project, app కాదు)
├── books/           marketplace app
├── accounts/        users, chat, notifications
├── ai_engine/       AI helpers
├── core/            home, base template, middleware, shared views
├── templates/       404.html, 500.html (global)
├── static/          icons, manifest, sw.js
├── media/           uploaded images (dev)
├── requirements.txt
├── render.yaml      deployment config
└── manage.py
```

> **ఎందుకు apps గా విభజించాం?** **Separation of concerns** —
> books logic books లో, user logic accounts లో. ఒక app ను delete చేసినా మిగతావి
> పనిచేస్తాయి. Team లో ఒకరు ఒక app తీసుకోవచ్చు.

---

## ❓ Q17. "Migrations ఏమిటి? ఎందుకు వాడతారు?"

**మీరు చెప్పేది:**

> Migration = **database schema కి version control.**
>
> `models.py` లో field add చేశాను → `makemigrations` → ఒక Python file
> (`0007_...py`) create అవుతుంది → `migrate` → database లో `ALTER TABLE` run అవుతుంది.
>
> **ఎందుకు ముఖ్యం:**
> - Database ను **చేతితో** మార్చాల్సిన అవసరం లేదు
> - **Team లో / production లో** ఒకే schema కి వస్తారు
> - **Rollback** చేయవచ్చు (`migrate accounts 0006`)
>
> మా project లో **accounts app కి 7 migrations, books కి 5+** ఉన్నాయి.
> Render deploy లో `migrate` **ఆటోమేటిక్** గా run అవుతుంది.

---

## ❓ Q18. "Deploy ఎలా అవుతుంది? CI/CD ఉందా?"

**మీరు చెప్పేది:**

> **Git push → Render auto-deploy** — ఇది ఒక రకమైన **CD** (Continuous Deployment).
>
> ```
> 1. నేను code commit చేస్తాను (feature branch)
> 2. GitHub కి push
> 3. Pull Request → tests pass అయ్యాక merge to master
> 4. Render "master" branch watch చేస్తుంది → auto build
> 5. buildCommand: pip install + collectstatic
> 6. startCommand: migrate → seed_demo → ensure_media → gunicorn
> 7. Live (2–3 నిమిషాలు)
> ```

---

## ❓ Q19. "`startCommand` లో migrate ఎందుకు? build లో ఎందుకు కాదు?"

**మీరు చెప్పేది:** — ఇది నేను **నిజంగా** ఒక bug నుంచి నేర్చుకున్నాను:

> మొదట `buildCommand` లో `migrate` పెట్టాను. Build time లో database **reachable గా
> ఉండదు** (sleep లో ఉంటుంది) → build fail → deploy fail.
>
> **Fix:** build లో **database ముట్టుకోని పనులు** మాత్రమే (`pip install`, `collectstatic`).
> Database పనులు అన్నీ **startCommand** లో — అప్పుడు DB ఖచ్చితంగా మేల్కొని ఉంటుంది.

---

## ❓ Q20. "Static files ఎలా serve చేస్తున్నారు? nginx లేదా?"

**మీరు చెప్పేది:**

> **WhiteNoise** middleware వాడుతున్నాను — nginx **అవసరం లేదు**.
>
> - `collectstatic` → అన్ని CSS/JS/icons ను `staticfiles/` లోకి copy + compress
> - `CompressedManifestStaticFilesStorage` → ఫైల్ పేరులో **hash** (`base.abc123.css`)
>   → browser **forever cache** చేయగలదు, file మారితే పేరు మారుతుంది
> - WhiteNoise **gzip** చేసి, `Cache-Control` header తో సర్వ్ చేస్తుంది
>
> **Uploaded images మాత్రం** WhiteNoise serve చేయదు (అవి user content) →
> `/media/<path>` కి **separate view** రాశాను, అది **database లోని bytes** ను
> (MEDIA_STORAGE=db) serve చేస్తుంది.

---

# PART 4 — Database Design

## ❓ Q21. ⭐ "మీ database schema చెప్పండి / ER diagram గీయండి"

**గుర్తు పెట్టుకోండి — 14 tables. Core 8:**

```
User (Django built-in)
 ├─1:1─ UserProfile      name, phone, location, privacy, telegram, contact_pref
 ├─1:N─ Book             seller → Book
 ├─1:N─ ChatMessage      sender / receiver
 ├─1:N─ Notification     recipient
 ├─1:N─ BookRequest      "నాకు ఈ book కావాలి"
 ├─1:N─ BuyRequest       "నేను ఈ book కొంటాను"
 ├─1:N─ SellerReview     reviewer → seller
 └─1:N─ UserBlock        blocker → blocked

Category 1:N Book
Book 1:N BookImage (extra photos), BookImage N/A
Book 1:N Wishlist, Report, BuyRequest, ChatMessage
AIEvent  (AI usage log — no FK)
```

**Relationships గుర్తు పెట్టుకోవడానికి:**
- **1:1** → `User ↔ UserProfile` (ఒక user కి ఒక profile)
- **1:N** → `User → Book` (ఒక seller కి చాలా books)
- **M:N** → `User ↔ Book` through **Wishlist** (చాలా users చాలా books save చేయవచ్చు)

---

## ❓ Q22. ⭐ "N+1 problem ఏమిటి? మీ project లో ఎక్కడ ఉంది?"

**ఇది senior-level question. ఇలా చెప్పండి:**

> Sir, `Book.objects.all()` అంటే **1 query**. కానీ ప్రతి book కి `book.seller.username`
> అని చదివితే — **ప్రతి book కి ఒక query**. 20 books → **21 queries**. దీన్ని N+1 అంటారు.
>
> **Solution:**
> ```python
> # ❌ 21 queries
> books = Book.objects.all()
> for b in books: print(b.seller.username)
>
> # ✅ 1 query (SQL JOIN)
> books = Book.objects.select_related('seller', 'category')
>
> # ✅ reverse / many side కి
> books = Book.objects.prefetch_related('images')
> ```
>
> **మా project లో నిజంగా కనిపించిన చోటు:** `messages_view` లో ప్రతి conversation కి
> `get_profile(other)` పిలిచేది → **chat ఉన్న ప్రతి వ్యక్తికి ఒక query**.
> `select_related('sender__profile', 'receiver__profile')` తో **ఒక్క query** కి తగ్గించాను.

---

## ❓ Q23. "Indexes ఎందుకు వేశారు? ఏం లాభం?"

**మీరు చెప్పేది:**

> Index = **పుస్తకంలోని index page**. ఇది లేకపోతే database **ప్రతి row ను చదువుతుంది**
> (**full table scan**). 10 lakh rows ఉంటే చాలా నెమ్మది.
>
> మా indexes:
> ```python
> # books: ఇవి ప్రతి page load కి వాడతాం
> models.Index(fields=['is_sold', 'is_hidden', '-created_at'])
> models.Index(fields=['location_city'])
> models.Index(fields=['seller', '-created_at'])
>
> # chat: unread count కోసం (ప్రతి page కి)
> models.Index(fields=['receiver', 'is_read'])
>
> # notification: bell badge కోసం
> models.Index(fields=['recipient', 'is_read'])
> ```
>
> **Trade-off:** index వల్ల **SELECT వేగం**, కానీ **INSERT/UPDATE కొంచెం నెమ్మది**
> (index కూడా update అవ్వాలి) + disk space. అందుకే **అవసరమైన చోట మాత్రమే** వేశాను.

---

## ❓ Q24. "Database constraints వాడారా? ఉదాహరణ చెప్పండి"

**మీరు చెప్పేది:** — 3 రకాలు:

```python
# 1. CHECK — price ఎప్పుడూ 0 మరియు 999999.99 మధ్య ఉండాలి
models.CheckConstraint(
    condition=Q(price__gte=0, price__lte=PRICE_MAX),
    name='book_price_within_range',
)

# 2. UNIQUE — ఒక book కి ఒక buyer కి ఒకే pending request
models.UniqueConstraint(
    fields=['book', 'buyer'],
    condition=Q(status='pending'),        # partial unique!
    name='one_pending_buy_request_per_buyer',
)

# 3. unique_together — ఒక reviewer ఒక seller కి ఒక review
unique_together = ('reviewer', 'seller', 'book')
```

> **ఎందుకు database లోనే?** Application లో `if not exists` అని చెక్ చేసినా
> **race condition** ఉంటుంది — రెండు requests ఒకేసారి వస్తే రెండూ create అవుతాయి.
> **Database constraint** అది ఆపుతుంది. దీన్ని **defense in depth** అంటారు.

---

## ❓ Q25. "`price` ను BuyRequest లో copy ఎందుకు పెట్టారు? book.price చూస్తే సరిపోదా?"

**మీరు చెప్పేది:** — ఇది బాగా ఆలోచించిన design:

> Sir, seller తర్వాత price మార్చవచ్చు. Buyer **₹300 కి** buy request పెట్టాడు.
> Seller price **₹500** కి పెంచాడు. `book.price` చూపిస్తే buyer **₹500 కి commit చేసినట్టు**
> కనిపిస్తుంది — అది తప్పు.
>
> అందుకే **request పెట్టిన క్షణం price snapshot** ను `BuyRequest.price` లో store చేశాను.
> ఇది **historical accuracy** — invoice లో ఇలాగే చేస్తారు.

---

## ❓ Q26. "Book `is_sold` వేరే, `BuyRequest.status` వేరే — ఎందుకు రెండూ?"

**మీరు చెప్పేది:**

> **రెండు వేరే concepts:**
> - `Book.is_sold` → **listing యొక్క** స్థితి
> - `BuyRequest.status` → **ఒక buyer యొక్క request** స్థితి
>
> ఒక book కి **5 buy requests** రావచ్చు. ఒకరిని accept చేస్తే book `is_sold=True`,
> మిగతా 4 requests **automatic గా declined**. ఒక్క field తో ఇది చేయలేం.

---

## ❓ Q27. "Soft delete చేశారా? Book delete అయితే chat ఏమి అవుతుంది?"

**మీరు చెప్పేది:**

> Book కి **`is_hidden`** field ఉంది — admin hide చేయవచ్చు, delete కాదు (moderation కోసం).
>
> Delete అయితే **`on_delete`** ప్రవర్తనం:
> ```python
> ChatMessage.book → on_delete=CASCADE    # book పోతే chats పోతాయి
> Book.category    → on_delete=SET_NULL   # category పోయినా book ఉంటుంది
> Notification.book→ on_delete=SET_NULL   # notification ఉంటుంది, link మాత్రం పోతుంది
> ```
>
> **తారతమ్యం:** user data (chats) **లేకుండా పోకూడదు** కాబట్టి CASCADE,
> reference data (category) **తప్పనిసరి కాదు** కాబట్టి SET_NULL.

---

## ❓ Q28. "Transaction ఎక్కడ వాడారు?"

**మీరు చెప్పేది:**

> Buy request **accept** చేసినప్పుడు **3 పనులు** ఒకేసారి జరగాలి:
> 1. request → `accepted`
> 2. book → `is_sold = True`
> 3. మిగతా pending requests → `declined`
>
> ఒకటి fail అయితే మిగతావి కూడా rollback అవ్వాలి. దీనికి `transaction.atomic()`
> వాడతాం. **ఇప్పుడు** మా code లో `respond()` + `mark_sold()` వరుసగా ఉన్నాయి —
> next improvement లో ఇవి ఒక `atomic()` block లో wrap చేయాలి.

> 💡 **ఇలా చెప్పడం మంచిది** — "ఇది మా next step" అని చెప్పడం, "perfect" అని చెప్పడం కంటే మెరుగు.

---

## ❓ Q29. "Migrations ఎలా handle చేస్తారు? Production లో?"

**మీరు చెప్పేది:**

> - **Local:** `makemigrations` → `migrate`
> - **CI/Tests:** test DB ను **scratch నుంచి** build చేస్తుంది → migrations సరైనవా అని auto-check
> - **Production:** `startCommand` లో `migrate --noinput` — **deploy కి ముందు** run అవుతుంది
> - **ఎప్పుడూ** migration edit చేయము (already applied), కొత్తది add చేస్తాం

---

# PART 5 — Features

## ❓ Q30. ⭐ "Chat ఎలా పనిచేస్తుంది? Real-time ఎలా?"

**మీరు చెప్పేది:** — ఇటీవల మెరుగుపరిచిన feature:

> **3 options ఉన్నాయి, నేను 2 వది ఎంచుకున్నాను:**
>
> | Method | ఎలా | Problem |
> |---|---|---|
> | **Full page POST** (మొదట ఇలా ఉండేది) | Form submit → re-render | ప్రతి message కి 2–3 sec, page reload |
> | **Polling** ✅ | 5 sec కి ఒకసారి `fetch()` | **ఎంచుకున్నది** |
> | **WebSockets** | Django Channels + Redis | ఖర్చు, complexity, free tier లో కష్టం |
>
> **Implementation:**
> ```
> POST /accounts/chat/<id>/send/    → {"ok":true,"message":{...}}
> GET  /accounts/chat/<id>/poll/?after=<lastId>   → కొత్త messages మాత్రమే
> ```
>
> **Optimistic UI:** send నొక్కగానే bubble **వెంటనే** కనిపిస్తుంది (pending అని),
> server confirm అయ్యాక `id` వస్తుంది. Fail అయితే **ఎరుపు** + text తిరిగి input లో.
>
> **Rate limit:** 5 నిమిషాలకు 25 messages → spam ఆపడానికి.

**Follow-up: "WebSockets ఎందుకు కాదు?"**
> WebSockets కి **channels + Redis** కావాలి. Redis free tier లేదు → ఖర్చు అవుతుంది.
> Polling 5 sec కి ఒకసారి అంటే ఒక user కి **రోజుకి 17,000 requests** కూడా కాదు —
> ఒక chat page తెరిచి ఉంటే గంటకి 720 requests, అది free tier కి సరిపోతుంది.
> **Scale అయ్యాక** WebSockets కి మారతాం.

---

## ❓ Q31. "Notifications ఎలా పనిచేస్తాయి? Email/Push ఎందుకు కాదు?"

**మీరు చెప్పేది:**

> **In-app notification** — `Notification` table లో row. Bell icon కి **20 sec కి ఒకసారి**
> `/accounts/badges/` నుంచి count వస్తుంది.
>
> **ఎందుకు email/push కాదు:**
> - **Email** కి SMTP ఖర్చు/verification కావాలి (free లో logs కి మాత్రమే print)
> - **Push** కి service worker + VAPID keys + mobile app
> - **In-app** ₹0, వెంటనే, restart కి పోదు (DB లో ఉంది)
>
> **Kinds of notification:** price drop, back on sale, request match, review,
> **book request**, **buy request**, **buy answer**.

---

## ❓ Q32. ⭐ "Book request పెట్టినప్పుడు notification ఎలా వెళ్తుంది?" (bug fix)

**మీరు చెప్పేది:** — ఇది మీరు **కనిపెట్టి, fix చేసిన** bug. చెప్పడం విలువైనది:

> Sir, మొదట `request_book` view లో message ఇలా ఉండేది:
> *"Nearby students who have it **will be notified**"* — కానీ **ఎవరికీ notification
> create అవ్వలేదు**. Function ఉంది (`notify_request_matches`) కానీ అది **కొత్త book
> add చేసినప్పుడు** మాత్రమే పిలవబడేది. **సగం feature** ఉంది.
>
> **Fix:** `notify_book_request_posted()` రాశాను:
> 1. Request title words → ఉన్న books తో match
> 2. లేదా **same category + same city**
> 3. Requester **తన book** కి notify కాదు
> 4. ఒక request కి **max 25 sellers** (spam ఆపడానికి)
> 5. Request పెట్టిన వాళ్ళకి **receipt** — "మీ request live అయింది"

---

## ❓ Q33. ⭐ "Buy Now ఎలా పనిచేస్తుంది? Payment ఎక్కడ?"

**మీరు చెప్పేది:**

> **Payment లేదు** — అది **intentional design decision**.
>
> ```
> Buyer: Buy Now → meetup place → BuyRequest (pending)
>      ↓ notification + chat auto-open (ready-made first message)
> Seller: Accept / Decline
>      ├ Accept → book sold, ఇతర requests declined, buyer కి notification
>      └ Decline → book available గానే ఉంటుంది
> ```
>
> **ఎందుకు payment gateway లేదు:**
> 1. **Razorpay/Stripe** కి business verification + KYC కావాలి — student కి సాధ్యం కాదు
> 2. **Commission/hold** చేయాలంటే legal entity కావాలి
> 3. **Real use case:** second-hand book ₹200–500. Meet అయ్యి cash/UPI చేయడం
>    **natural**. Gateway fee (2%) కంటే time save ఎక్కువ.
> 4. **Security:** payment data handle చేయకపోతే **PCI-DSS scope** లేదు.
>
> **Trade-off (నిజం చెప్పండి):** escrow లేకపోవడం వల్ల **commitment guarantee** తక్కువ.
> కానీ BuyRequest + Accept model ఆ gap ను చాలావరకు పూరిస్తుంది.

---

## ❓ Q34. "Wishlist ఎందుకు? ఏం లాభం?"

**మీరు చెప్పేది:**

> 1. User కి **save చేసుకోవడం** — తర్వాత కొనాలని
> 2. **Price drop notification** — seller price తగ్గిస్తే wishlist వాళ్ళకి notification
> 3. **AI recommendations కి signal** — ఏ category ఇష్టమో తెలుస్తుంది
>
> **M:N relation** ఇది — `User ↔ Book` through `Wishlist` table.

---

## ❓ Q35. "Reviews fake గా రాయొచ్చు కదా? ఎలా ఆపారు?"

**మీరు చెప్పేది:**

> **3 guards:**
> 1. **Chat చేయనిదే review రాయలేరు** — `SellerReview.has_chatted_with()` check
>    (`REVIEW_MIN_MESSAGES` కూడా ఉంది)
> 2. **ఒక reviewer → ఒక seller కి ఒకే review** — `unique_together`
> 3. **Admin hide చేయగలడు** — `is_hidden` field. Hidden reviews **average లో కౌంట్ అవ్వవు**
>
> **Average calculation:** `Avg('rating')` aggregate — Python లో లూప్ కాదు.
> 5 నిమిషాలు **cache** చేస్తాం (`invalidate_summary` తో clear).

---

## ❓ Q36. "Report (abuse) system చెప్పండి"

**మీరు చెప్పేది:**

> Buyer book report చేయగలడు → `Report` table (status: `open` / `resolved`).
> Admin/staff dashboard లో **pending reports** కనిపిస్తాయి → hide/book తీసేయవచ్చు.
>
> **Rate limit:** గంటకి **5 reports** — ఒకరిని target చేసి report spam ఆపడానికి.

---

## ❓ Q37. "Block feature ఎందుకు?"

**మీరు చెప్పేది:**

> User ఒకరిని block చేస్తే:
> - **Chat** ఆగిపోతుంది (`UserBlock.exists_between`)
> - **Notifications** ఆగిపోతాయి (`notify()` లో check)
> - **Listings** కనిపించవు (`blocked_ids_for` → `exclude`)
>
> ఇది **harassment** ఆపడానికి — privacy-first app కి తప్పనిసరి.

---

## ❓ Q38. "Search / filter ఎలా చేస్తారు?"

**మీరు చెప్పేది:**

> Query parameters ద్వారా:
> ```
> /books/?q=physics&category=1&min_price=100&max_price=500&city=Hyderabad&free=1&sort=newest
> ```
> **Pagination:** `Paginator` — page కి **20 books**. అన్నీ ఒకేసారి load చేయడం
> free tier కి భారం.
>
> **Sorting:** `?sort=price_low`, `price_high`, `newest`, `popular` (`views_count`).

---

# PART 6 — Privacy & Security

## ❓ Q39. ⭐ "Phone number ఎలా hide చేస్తారు? Database లో ఉంటుందా?"

**ఇది project యొక్క core selling point. ఇలా చెప్పండి:**

> Sir, **number database లో ఉంటుంది** — కానీ **ఎప్పటికీ render అవ్వదు**.
>
> **3 layers:**
> 1. **Template layer** — `book_detail.html` లో phone field **ఎక్కడా** print చేయము.
>    WhatsApp link కూడా seller **explicitly** "WhatsApp" preference ఎంచుకుంటే మాత్రమే.
> 2. **View layer** — `whatsapp_url` variable seller preference + `book.contact_phone`
>    ఉంటే మాత్రమే build అవుతుంది. లేకపోతే **ఖాళీ string** → template లో `{% if %}` fail.
> 3. **Model layer** — Telegram handle (@name) మాత్రమే public — అది **number కాదు**.
>
> **Privacy badge:** ప్రతి page లో "100% Privacy Protected" — user కి trust.

**Follow-up: "Number database లో పెట్టాల్సిన అవసరం ఏమిటి?"**
> Delivery/verification/WhatsApp opt-in కి. కానీ **ఎప్పుడూ** public API లో రాదు
> (Django REST serializer లాంటివి లేవు, HTML లో మాత్రమే render).

---

## ❓ Q40. ⭐ "SQL Injection ఎలా ఆపుతున్నారు?"

**మీరు చెప్పేది:**

> **Django ORM parameterized queries** వాడుతుంది:
> ```python
> Book.objects.filter(title=user_input)
> # → SELECT * FROM books_book WHERE title = %s   (user_input parameter గా)
> ```
> User input **ఎప్పుడూ** SQL string లోకి కలవదు.
>
> **మా project లో raw SQL 2 చోట్లే:**
> - `SELECT 1` (health check) — input లేదు
> - `cursor.execute('SELECT 1')` — safe
>
> **ఎప్పుడూ** `f"SELECT ... {user_input}"` అని రాయము.

---

## ❓ Q41. ⭐ "XSS (Cross-Site Scripting) ఎలా ఆపుతున్నారు?"

**మీరు చెప్పేది:**

> 2 layers:
> 1. **Django templates auto-escape** — `{{ message.text }}` లో `<script>` ఉంటే
>    `&lt;script&gt;` గా మారుతుంది. `|safe` **ఎక్కడా వాడలేదు** (అది escape off చేస్తుంది).
> 2. **JavaScript లో** — chat message ను `innerHTML` తో ఇన్సర్ట్ చేసే ముందు
>    ```javascript
>     function escapeHtml(value) {
>         var div = document.createElement('div');
>         div.textContent = value;   // ← escape అవుతుంది
>         return div.innerHTML;
>     }
>     ```
>    `textContent` వాడితే HTML interpret అవ్వదు.

**Follow-up: "ఏదైనా risk ఉందా?"** → "బాహ్య libraries (Bootstrap CDN) మాత్రమే —
`integrity` attribute add చేయడం next improvement."

---

## ❓ Q42. "CSRF ఏమిటి? ఎలా ఆపుతున్నారు?"

**మీరు చెప్పేది:**

> **CSRF = Cross-Site Request Forgery.** మీరు bank లో login ఉన్నారు. మీరు
> `evil.com` తెరిస్తే, అది **మీ browser ద్వారా** bank కి `POST /transfer` పంపుతుంది.
> Browser **cookies ఆటోమేటిక్** గా పంపుతుంది → bank కి అది మీరే అని అనిపిస్తుంది.
>
> **Django solution:** ప్రతి form కి **secret token** (`{% csrf_token %}`).
> `evil.com` కి ఆ token తెలియదు → request reject.
>
> మా project లో **ప్రతి POST form** కి token ఉంది — including AJAX
> (`X-CSRFToken` header). **Session cookie లో `SameSite=Lax`** కూడా.

---

## ❓ Q43. "Passwords ఎలా store చేస్తారు? Plain text ఉందా?"

**మీరు చెప్పేది:**

> **ఎప్పటికీ plain text కాదు.** Django default **PBKDF2-SHA256** with salt + iterations.
>
> ```
> password123 → pbkdf2_sha256$870000$<salt>$<hash>
> ```
> - **Salt** — ఒకే password రెండు users కి ఒకే hash రాకుండా
> - **Iterations** — brute force నెమ్మది చేయడానికి
>
> **Demo accounts కి** `set_unusable_password()` వాడాను — అంటే ఆ account కి
> **password ఉండనే ఉండదు**, ఎవరూ login అవ్వలేరు. కానీ వాళ్ళ books/chats **కనిపిస్తాయి**

---

## ❓ Q44. "HTTPS ఎలా? HTTP request వస్తే?"

**మీరు చెప్పేది:**

> Render **automatic Let's Encrypt SSL** ఇస్తుంది.
>
> Django లో:
> ```python
> SECURE_SSL_REDIRECT = True          # http → https redirect
> SESSION_COOKIE_SECURE = True        # cookie HTTPS లో మాత్రమే
> CSRF_COOKIE_SECURE = True
> SECURE_HSTS_SECONDS = 31536000      # browser కి "ఎప్పుడూ HTTPS"
> SECURE_CONTENT_TYPE_NOSNIFF = True
> SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
> ```
> **Exception:** `/healthz/` మరియు `/wake/` — Render health check **HTTP లోనే**
> వస్తుంది, అవి exempt (`SECURE_REDIRECT_EXEMPT`).

---

## ❓ Q45. "SECRET_KEY ఎలా manage చేస్తారు? Git లో ఉందా?"

**మీరు చెప్పేది:**

> **లేదు.** `settings.py` లో `os.environ.get('SECRET_KEY')` — env variable నుంచి.
> `render.yaml` లో `generateValue: true` → Render **random strong key** create చేస్తుంది.
>
> `.env` file `.gitignore` లో ఉంది. **`DATABASE_URL` కూడా** env variable లోనే —
> కాబట్టి database password Git history లో లేదు.

---

## ❓ Q46. "Rate limiting ఎలా? Brute force ఆపుతున్నారా?"

**మీరు చెప్పేది:**

> `core/ratelimit.py` — cache-backed counter:
>
> | Action | Limit |
> |---|---|
> | Chat messages | 25 / 5 నిమిషాలు |
> | New listings | 10 / గంట |
> | Reports | 5 / గంట |
> | Reviews | 10 / గంట |
> | Book requests | 5 / గంట |
> | Buy requests | 15 / గంట |
> | AI calls | 120 / గంట |
>
> **ఎలా:** `cache.add(key, 1, window)` → `cache.incr(key)` → limit దాటితే
> **friendly message** ("slow down"), error page కాదు.
>
> **Login brute force** కి Django authentication + తక్కువ attempts లో
> account lock కోసం `django-axes` next step.

---

# PART 7 — AI Features

## ❓ Q47. ⭐ "AI ఏమి చేస్తుంది? ChatGPT API వాడారా?"

**మీరు చెప్పేది:** — **ఇది trap question.** నిజం చెప్పండి:

> Sir, ఇది **LLM కాదు** — **rule-based / statistical engine** (`ai_engine/` app).
> **ఎందుకు:**
> 1. OpenAI API కి **credit card** కావాలి — ₹0 budget
> 2. API latency (1–3 sec) + ఖర్చు ప్రతి call కి
> 3. మనకు కావాల్సినవి **simple problems** — LLM అవసరం లేదు
>
> **4 features:**
> | Feature | ఎలా పనిచేస్తుంది (algorithm) |
> |---|---|
> | **Price suggestion** | Same category + condition యొక్క median price (IQR outliers తీసేసి) |
> | **Description generator** | Template + book fields (title, author, condition, category) |
> | **Recommendations** | Content-based: wishlist category + viewed category weights |
> | **Trust score** | Review average + count + verified email + listings count |

**Follow-up: "LLM వాడితే మెరుగ్గా ఉండేదా?"**
> Description కి అవును — కానీ **price suggestion కి ఒక LLM సరికాదు**, statistical
> approach ఎక్కువ accurate. So: LLM ను **description కి మాత్రమే optional** గా
> జోడించవచ్చు, price/recommendation rule-based గానే ఉండాలి.

---

## ❓ Q48. "Price suggestion ఎలా calculate చేస్తారు?"

**మీరు చెప్పేది:**

```
1. Same category + same condition books తీసుకో
2. Median (average కాదు — outlier safe)
3. Condition multiplier:
     new ×1.0 | like_new ×0.85 | good ×0.7 | fair ×0.55 | poor ×0.4
4. Original price కి max 60% cap (₹500 MRP book కి ₹800 అడగకూడదు)
5. Confidence: sample size ≥ 5 అయితే "high"
```

> **ఎందుకు median, average కాదు?** ఒకరు ₹10,000 అని పెట్టాడు అనుకోండి —
> average పాడవుతుంది, **median** ఆ ప్రభావం తగ్గిస్తుంది.

---

## ❓ Q49. "Recommendations ఎలా? Collaborative filtering ఉందా?"

**మీరు చెప్పేది:**

> **Content-based filtering** వాడాను — user యొక్క **wishlist + views** లో
> ఏ categories ఎక్కువ ఉన్నాయో లెక్కించి, ఆ categories లో కొత్త books చూపిస్తాను.
>
> **Collaborative filtering** ("మీలాంటి users ఇది కొన్నారు") కి **చాలా user data**
> కావాలి. ఇప్పుడు users తక్కువ → cold start problem. Data వచ్చాక అది జోడిస్తాం.

---

## ❓ Q50. "`AIEvent` table ఎందుకు?"

**మీరు చెప్పేది:**

> ప్రతి AI call ను log చేస్తాం — ఏ feature, ఎంత time పట్టింది, success అయిందా.
>
> **ఎందుకు:**
> 1. **Debugging** — "price suggestion ఎందుకు తప్పు వచ్చింది?"
> 2. **Rate limiting** — user కి గంటకి 120 calls
> 3. **Analytics** — ఏ feature ఎక్కువ వాడుతున్నారు
> 4. **Testing** — accuracy measure చేయడానికి

---

# PART 8 — Performance

## ❓ Q51. ⭐ "మీ site వేగంగా ఉందా? ఎలా optimize చేశారు?"

**మీరు చెప్పేది:** — 6 optimizations:

| # | Problem | Fix | ఫలితం |
|---|---|---|---|
| 1 | Chat కి full page reload | **AJAX + optimistic UI** | message వెంటనే |
| 2 | ప్రతి page కి 3 extra count queries | badges **10 sec cache** | DB load ↓ |
| 3 | conversations కి N+1 | **`select_related`** | N queries → 1 |
| 4 | `views_count` update race | **`F('views_count') + 1`** (atomic SQL) | lock లేదు |
| 5 | Static files మళ్ళీ download | **WhiteNoise hash + cache** | 2వ load వేగం |
| 6 | Database indexes లేక | **7 composite indexes** | SELECT వేగం |

---

## ❓ Q52. "`F()` expression ఎందుకు? `book.views_count += 1` ఎందుకు కాదు?"

**మీరు చెప్పేది:**

> ```python
> # ❌ race condition
> book.views_count = book.views_count + 1    # 2 users ఒకేసారి → 1 పోతుంది
> book.save()
>
> # ✅ atomic, database లోనే
> Book.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
> ```
>
> `F()` **database లోనే** `views_count = views_count + 1` చేస్తుంది.
> 2 requests ఒకేసారి వచ్చినా **రెండూ** లెక్కించబడతాయి.
> మరియు **మొత్తం row save చేయము** — `updated_at` కూడా మారదు (unnecessary write లేదు).

---

## ❓ Q53. ⭐ "'Render loading' problem ఏమిటి? ఎలా పరిష్కరించారు?"

**మీరు చెప్పేది:**

> **Problem:** Render free plan **15 నిమిషాలు idle** అయితే service **sleep** అవుతుంది.
> తర్వాత మొదటి visitor కి **~40 sec "spinning up" screen**.
>
> **Fix 1 — Service Worker (code level):**
> ```
> Browser → /sw.js → చివరిగా చూసిన page ను Cache API లో దాచుతుంది
> User app తెరిస్తే → 0.1 sec లో cached page కనిపిస్తుంది
>      + "Reconnecting…" bar
> వెనుక fetch(/wake/) → server మేల్కొన్నాక → page ఆటోమేటిక్ reload
> ```
> **ముఖ్యమైన detail:** **`X-BB-App: 1` header ఉన్న response మాత్రమే** cache చేస్తాం.
> Render యొక్క **boot page కి ఆ header ఉండదు** → అది ఎప్పటికీ cache అవ్వదు.
>
> **Fix 2 — UptimeRobot (₹0):**
> `/healthz/?light=1` ను **5 నిమిషాలకోసారి** ping చేస్తే service **ఎప్పుడూ నిద్రపోదు**.
> `?light=1` అంటే **database ముట్టుకోదు** → fast, Neon ను మేల్కొలపదు.

**Follow-up: "Service worker ఏమిటి?"**
> Browser లో నడిచే background script. **Offline** లో కూడా page చూపగలదు.
> `navigator.serviceWorker.register('/sw.js')` తో register అవుతుంది.
> **Only HTTPS** లో పనిచేస్తుంది (localhost కూడా OK).

---

## ❓ Q54. "Photos database లో ఎందుకు? Disk లో ఉంటే?"

**మీరు చెప్పేది:**

> **Problem:** Render free లో **disk ephemeral** — ప్రతి restart/deploy కి **wipe** అవుతుంది.
> అంటే అమ్మిన book cover **మాయమవుతుంది**.
>
> **Solution:** `MEDIA_STORAGE=db` → photos **`StoredFile`** table లో `BinaryField` గా.
>
> **Trade-off:**
> | | DB storage | Disk |
> |---|---|---|
> | Restart కి పోతుందా | ❌ పోదు | ✅ పోతుంది |
> | DB size | 16 covers ≈ **0.6 MB** | 0 |
> | Serving | Python ద్వారా (నెమ్మది) | nginx fast |
> | Backup | DB dump లోనే వస్తుంది | separate |
>
> **Alternative:** S3 / Cloudinary — best, కానీ config + ఖర్చు.
> **మా scale కి** (Neon free 0.5 GB ≈ **800 covers**) DB storage సరిపోతుంది.

---

# PART 9 — Deployment

## ❓ Q55. "Deploy flow చెప్పండి"

**మీరు చెప్పేది:**

```
1. Feature branch → code
2. PR → 242 tests pass
3. Merge to master
4. Render auto-detect → build:
      pip install -r requirements.txt
      python manage.py collectstatic --noinput
5. startCommand:
      migrate → seed_demo → ensure_demo_media → ensure_admin → db_status → gunicorn
6. healthCheckPath: /healthz/ → 200 వస్తే Live
```

---

## ❓ Q56. "Environment variables ఏమి వాడారు?"

**మీరు చెప్పేది:**

| Variable | విలువ | ఎందుకు |
|---|---|---|
| `SECRET_KEY` | auto-generated | Security |
| `DEBUG` | `False` | Production లో error details hide |
| `ALLOWED_HOSTS` | `.onrender.com` | Host header attack ఆపడానికి |
| `DATABASE_URL` | Neon URL (`sync:false`) | DB connection |
| `DEMO_MODE` | `1` | Sample data seed |
| `MEDIA_STORAGE` | `db` | Photos శాశ్వతం |
| `DJANGO_SUPERUSER_*` | admin login | Superuser auto-create |

---

## ❓ Q57. ⭐ "Demo mode ఏమిటి? Security risk కాదా?"

**మీరు చెప్పేది:** — ఇది బాగా ఆలోచించిన design:

> `DEMO_MODE=1` → deploy లో **16 sample books + photos + chats** seed అవుతాయి.
> కానీ:
>
> ```python
> user.set_unusable_password()   # ← password ఉండనే ఉండదు
> user.is_staff = False
> user.is_superuser = False
> ```
>
> అంటే demo account **`demo/arjun/priya/rahul`** కి **password ఉండదు** —
> `bookbridge123` తో login **అసాధ్యం**. Content **కనిపిస్తుంది**, account **వాడలేరు**.
>
> **ఎందుకు ఇలా:** recruiter/sir కి site **నిండుగా** చూపించాలి, కానీ
> **ఎవరూ** fake account లో login అవ్వకూడదు.
>
> **Real marketplace కి** `DEMO_MODE=0` పెట్టి deploy చేస్తే demo content రాదు.

---

## ❓ Q58. "Free tier limitations ఏమిటి? Scale అయితే?"

**మీరు చెప్పేది:**

| Limit | విలువ | Scale అయితే |
|---|---|---|
| RAM | 512 MB | Paid plan ($7/నెల) |
| CPU | 0.1 | Paid |
| Sleep | 15 min idle | UptimeRobot (₹0) / paid |
| Bandwidth | 5 GB/నెల | CDN |
| Postgres | Neon free 0.5 GB | Neon paid / S3 for media |
| Logs | 7 రోజులు | Better Stack |

> **Plan:** 100 users వరకు free tier సరిపోతుంది. 1000+ అయ్యాక:
> workers పెంచడం, Redis cache, S3 media, CDN.

---

# PART 10 — Testing

## ❓ Q59. ⭐ "Tests రాశారా? ఎన్ని?"

**మీరు చెప్పేది:**

> **242 tests** — అన్నీ pass. `python manage.py test`.
>
> **ఏమి cover చేస్తాయి:**
> | Test class | ఏమి check చేస్తుంది |
> |---|---|
> | `ChatApiTests` (8) | JSON send, HTML return కాదు, empty reject, poll new only, read marking, self-chat block |
> | `BuyRequestFlowTests` (11) | request create, notification, double-tap safe, accept→sold, decline→available, permission |
> | `BookRequestNotificationTests` (4) | matching seller notified, buyer receipt, false match లేదు |
> | `WakeAndServiceWorkerTests` (4) | `/wake/` uncached, `?light=1` DB ముట్టుకోదు, `/sw.js` headers |
> | `DemoModeSeedingTests` | unusable passwords, idempotent seed |
> | `DatabaseStorageTests` | upload → serve → 404 |
> | `DatabaseUrlParsingTests` | Neon URL `sslmode` parse |
> | Auth/signup tests | duplicate username, privacy leak లేదు |
>
> **ఎందుకు tests:** ఒక feature మార్చినప్పుడు **పాతవి పాడవ్వకూడదు** (regression).
> ఉదాహరణ: notifications add చేసినప్పుడు పాత chat tests fail అయితే వెంటనే తెలుస్తుంది.

---

## ❓ Q60. "Test ఎలా రాస్తారు? ఉదాహరణ చెప్పండి"

**మీరు చెప్పేది:**

```python
class BuyRequestFlowTests(TestCase):
    def setUp(self):
        # ప్రతి test కి కొత్త clean database (transaction rollback)
        self.seller = User.objects.create_user('seller1', password='Bridge!2345')
        self.buyer = User.objects.create_user('buyer1', password='Bridge!2345')
        self.book = Book.objects.create(seller=self.seller, title='Chemistry NCERT',
                                        price=Decimal('300'))

    def test_accepting_marks_the_book_sold_and_notifies_the_buyer(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('books:buy_now', args=[self.book.pk]))
        buy_request = BuyRequest.objects.get()

        self.client.force_login(self.seller)
        self.client.post(reverse('books:buy_request_respond',
                                 args=[buy_request.pk, 'accept']))

        buy_request.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(buy_request.status, BuyRequest.STATUS_ACCEPTED)
        self.assertTrue(self.book.is_sold)
        self.assertTrue(Notification.objects.filter(
            recipient=self.buyer, kind='buy_answer').exists())
```

> **ముఖ్యం:** `TestCase` ప్రతి test ను **transaction లో** run చేస్తుంది →
> చివర్లో **rollback** → test DB ఎప్పుడూ clean. Test data production కి పోదు.

---

# PART 11 — కఠినమైన ప్రశ్నలు (Negative questions)

## ❓ Q61. "మీ project లో weakness ఏమిటి?"

**ఇలా చెప్పండి — ఇది strength గా మారుతుంది:**

> 3 weaknesses నాకు తెలుసు:
>
> **1. Payment లేదు** — కొన్నవాళ్ళు confirm చేయకపోవచ్చు. **Fix:** escrow లేదా
> small refundable token.
>
> **2. Real-time కాదు** — polling 5 sec. WebSocket కి Redis కావాలి (ఖర్చు).
> **Fix:** scale అయ్యాక migrate.
>
> **3. Free tier limits** — 0.1 CPU, sleep. **Fix:** UptimeRobot + paid plan.
>
> **ఇంకా:** email verification కి SMTP లేదు (logs లోనే), password reset
> email పనిచేయదు — admin "temporary password" action తో handle చేస్తున్నాం.

---

## ❓ Q62. "ఇది production ready ఎలా అంటారు? Scale అవుతుందా?"

**మీరు చెప్పేది:**

> **Ready అయినవి:** HTTPS, CSRF/XSS/SQLi protection, hashed passwords,
> rate limiting, migrations, 242 tests, backups (DB dump), error monitoring.
>
> **Ready కానివి:** no payment, no load balancer, single instance,
> no CDN, email నిజంగా పంపదు.
>
> **Scale:** horizontal scaling కి **stateless** design కావాలి. మా app
> **stateless** గా ఉంది (session DB లో, media DB లో) → **workers పెంచి**
> scale చేయవచ్చు. ఒక్క problem: **LocMemCache** per-worker — multi-worker లో
> rate limit ఖచ్చితంగా పనిచేయదు → **Redis** కి మారాలి.

---

## ❓ Q63. "ఎందుకు mobile app కాదు? App Store లో పెట్టలేదా?"

**మీరు చెప్పేది:**

> Sir, **PWA** వాడాను — ఒక్క codebase తో **desktop + mobile** రెండూ.
>
> - `manifest.webmanifest` → **"Install app"** → home screen లో icon
> - `display: standalone` → browser chrome లేకుండా **app లాగా** తెరుచుకుంటుంది
> - iOS/Android రెండింటిలో పనిచేస్తుంది
>
> **Native app ఎందుకు కాదు:** Play Store కి ₹2,000 one-time + review +
> రెండు codebases (Kotlin + Swift) + maintenance. **Student project కి** PWA సరిపోతుంది.
> **Trade-off:** push notifications PWA లో limited (iOS లో).

---

## ❓ Q64. "User ఒకే book కి 10 requests పెడితే?"

**మీరు చెప్పేది:**

> **3 guards:**
> 1. **`UniqueConstraint`** — book+buyer కి **ఒకే pending** request
> 2. **Rate limit** — గంటకి 15 buy requests
> 3. **`IntegrityError` handle** — double-tap వచ్చినా friendly message,
>    crash కాదు

---

## ❓ Q65. "Chat లో abuse/తిట్లు వస్తే?"

**మీరు చెప్పేది:**

> ప్రస్తుతం:
> - **Block** — chat + notifications + listings block
> - **Report** — admin queue లో వస్తుంది
> - **Rate limit** — spam ఆపడానికి
>
> **లేనిది:** automatic profanity filter. **Next step:**
> word-list filter + report-based auto-hide (2 reports → hide, admin review).

---

## ❓ Q66. "ఎందుకు ఇది Facebook Marketplace కంటే మెరుగు?"

**మీరు చెప్పేది:** — honest గా చెప్పండి:

> **Facebook Marketplace కంటే మెరుగు 4 విషయాలు:**
> 1. **Privacy by design** — Facebook profile + phone అందరికీ కనిపిస్తుంది
> 2. **Books కి special** — category (IIT-JEE, NEET, Engineering), condition, semester
> 3. **Price suggestion AI** — "ఈ book కి ఎంత అడగాలి?"
> 4. **College/city filter** — same campus లో వెతకడం
>
> **Facebook కంటే తక్కువ:** user base (network effect), brand trust.
>
> **నిజం:** Facebook ను **ఓడించడం** కాదు — **books కి better tool** ఇవ్వడం.

---

## ❓ Q67. "Math/algorithm ఏమైనా వాడారా? (లేదా 'ఇది engineering ఏమిటి?')"

**మీరు చెప్పేది:** — ఇది చాలా ముఖ్యం, ఎందుకంటే "CRUD app" అని అనకుండా:

> 5 చోట్ల **real algorithms** ఉన్నాయి:
>
> 1. **Price suggestion** — median + IQR outlier removal + condition multipliers
> 2. **Recommendations** — weighted content-based scoring (wishlist ×3, views ×1)
> 3. **Search / matching** — token overlap between request title and listings
> 4. **Trust score** — Bayesian-ish weighted average (review count కి కూడా weight)
> 5. **Rate limiting** — sliding window counters in cache
>
> **Database level:** partial unique indexes, `F()` atomic increments,
> composite indexes, `select_related` query planning.

---

## ❓ Q68. "భవిష్యత్తులో ఏమి చేయాలనుకుంటున్నారు?"

**మీరు చెప్పేది:** — 6 points, priority order లో:

> 1. **Real users** — college WhatsApp/Telegram groups లో share (biggest need)
> 2. **Email పని చేయించడం** — Gmail SMTP → verification + password reset స్వయంగా
> 3. **Payment (optional)** — Razorpay UPI intent, commission లేకుండా
> 4. **WebSockets** — chat real-time, Redis తో
> 5. **Mobile PWA offline** — full offline browse
> 6. **Admin analytics** — ఏ category ఎక్కువ అమ్ముడవుతోంది

---

## ❓ Q69. "ఈ project లో మీరు ఏమి నేర్చుకున్నారు?" (technical)

**మీరు చెప్పేది:** — 3 నిజమైన lessons:

> **1. Build time లో database ముట్టుకోవద్దు.** `migrate` ను `buildCommand` లో పెట్టాను →
> DB sleep లో ఉండి build fail అయ్యింది. **Lesson:** build = artifacts,
> start = runtime.
>
> **2. Free tier లో disk ఉండదు.** Uploaded photos restart కి పోయాయి.
> **Lesson:** **state** ను ఎక్కడ పెడుతున్నారో ఆలోచించాలి — ephemeral disk లో కాదు.
>
> **3. Notification పంపడం మర్చిపోవడం సులభం.** Message లో "will be notified" అని
> రాసి, code లో పంపలేదు. **Lesson:** user కి promise చేసిన **ప్రతి** action కి
> **test** రాయాలి — అప్పుడే ఆ gap కనిపిస్తుంది.

---

## ❓ Q70. "మీకు తెలియని ఏదైనా అడిగితే?"

**ఇలా చెప్పండి (ఇది ఎప్పుడూ గెలుస్తుంది):**

> "Sir, దాని గురించి నాకు పూర్తి అవగాహన లేదు. కానీ నాకు తెలిసినది ఇది — [మీకు
> సంబంధిత విషయం చెప్పండి]. తప్పుగా చెప్పడం కంటే **తెలియదు** అని చెప్పడం మంచిది.
> ఇది నేను ఇంకా study చేయాల్సిన topic."

> ⚠️ **ఎప్పుడూ bluff చేయకండి.** Sir ఒక్క follow-up అడిగితే తెలిసిపోతుంది.

---

# PART 12 — Live demo (3 నిమిషాలు)

## 🎬 ఈ order లో చూపండి — ఇది భలే పనిచేస్తుంది

> **ముందే:** browser లో 4 tabs తెరిచి పెట్టుకోండి. Live లో type చేయకండి.

| # | ఏమి | ఎక్కడ | ఏమి చెప్పాలి |
|---|---|---|---|
| 1 | **Home** | `bookbridge-aadt.onrender.com` | "17 listings, 8 categories, privacy badge" |
| 2 | **Book detail** | ఏదైనా book | **Buy Now** బటన్ చూపండి |
| 3 | **Buy Now → request** | అదే page | "Request → seller కి notification" |
| 4 | **Seller view** | `admin` account లో login → అదే book | "Accept / Decline కనిపిస్తుంది" |
| 5 | **Accept** | అదే page | "Book automatic గా **Sold** అయింది" |
| 6 | **Chat** | Messages | **రెండు browser windows** లో ఒకే chat తెరవండి → ఒకటి type చేయండి → **రెండోది 5 sec లో** కనిపిస్తుంది |
| 7 | **Bell icon** | పైన | "Notification వచ్చింది, badge పెరిగింది" |
| 8 | **Admin** | `/admin/` | "14 tables, చేతితో code రాయకుండా manage" |
| 9 | **Backend tour** | `/backend/` | "14 models, live row counts" |
| 10 | **Health** | `/healthz/` | `{"status":"ok","books":17}` |

### 🎤 ముగింపు మాట (నోట పెట్టుకోండి):

> "Sir, ఇది **₹0 ఖర్చులో live** ఉంది. **242 automated tests** pass అవుతున్నాయి.
> Privacy-first design, working Buy Now flow, live chat, AI price suggestion —
> అన్నీ production deploy లో పనిచేస్తున్నాయి. Next step: real users from
> college groups."

---

## 📊 Numbers cheat sheet — ఇవి గుర్తు పెట్టుకోండి

| ఏమి | సంఖ్య |
|---|---|
| Django version | **5.2** |
| Python | **3.12.6** (Render) |
| Apps | **4** (`books`, `accounts`, `ai_engine`, `core`) |
| Database tables (admin లో) | **14** |
| Automated tests | **242** |
| Python lines | **~10,300** |
| Template lines | **~7,600** |
| Live listings | **17** (16 demo + 1 real) |
| Categories | **8** |
| Demo users | **4** |
| Average cover size | **~30 KB** |
| 16 covers total | **~0.6 MB** |
| Hosting cost | **₹0** |
| Free tier RAM / CPU | **512 MB / 0.1 CPU** |
| Sleep after idle | **15 నిమిషాలు** |
| Free Postgres (Neon) | **0.5 GB, ఎప్పటికీ** |
| Rate limits | chat 25/5min, listing 10/hr, report 5/hr |
| Deploy time | **2–3 నిమిషాలు** |

---

## 🔗 URLs (నోట పెట్టుకోండి)

| ఏమి | URL |
|---|---|
| **Live site** | `https://bookbridge-aadt.onrender.com` |
| Admin | `.../admin/` — `admin` / `ThanmaiBooks2026` |
| Backend tour (all tables) | `.../backend/` |
| Health check | `.../healthz/` |
| Buy requests | `.../accounts/buy-requests/` |
| GitHub | `github.com/lakshmithanmai729-jpg/book_bridge` |

---

## ✅ Viva కి ముందు రోజు checklist

- [ ] Q1 (project intro) **బయటకు చెప్పి** practice చేయండి — 60 sec
- [ ] Q8 (why Django) 4 కారణాలు నోట పెట్టుకోండి
- [ ] Q15 (request flow) step-by-step చెప్పడం practice
- [ ] Q21 (schema) — **చేతితో ER diagram గీయడం** practice (paper మీద)
- [ ] Q53 (Render loading) — service worker ఎలా పనిచేస్తుందో
- [ ] Numbers cheat sheet ఒకసారి చదవండి
- [ ] Live site ఒకసారి తెరిచి, **Buy Now** flow మీరే ఒకసారి చేయండి
- [ ] Laptop లో **2 browser windows** తెరిచి chat demo practice
- [ ] "తెలియదు" అని చెప్పడానికి సిద్ధంగా ఉండండి (Q70)

---

**All the best for your viva! 🎓**

> 💡 గుర్తుంచుకోండి: Sir కి **"మీకు ఏమి తెలుసు"** కాదు, **"మీరు ఎలా ఆలోచిస్తారు"**
> అని చూడాలి. ఏదైనా question కి "**ఎందుకు** అలా చేశాను" అని చెప్పగలిగితే — మీరు గెలిచారు.
