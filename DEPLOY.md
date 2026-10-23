# BookBridge — permanent గా ఎలా online పెట్టాలి

ఇప్పటివరకు app ఈ sandbox లో నడుస్తోంది. Sandbox restart అయినప్పుడల్లా server ఆగిపోతుంది —
అది మీ తప్పు కాదు, ఈ environment అలా పనిచేస్తుంది.

దీనికి **రెండు పరిష్కారాలు** ఉన్నాయి:

| | Option A — One-command restart | Option B — Permanent hosting ⭐ |
| --- | --- | --- |
| ఎక్కడ నడుస్తుంది | ఈ sandbox లో | Render.com (free) |
| Sandbox restart అయితే | ఒక్క command తో మళ్ళీ start | ఏమీ చేయాల్సిన పని లేదు |
| Session ముగిసిన తర్వాత | ఆగిపోతుంది | **24/7 online** |
| Link | preview link మారుతుంది | **శాశ్వత link** (`https://bookbridge-xxxx.onrender.com`) |
| ఖర్చు | ₹0 | ₹0 (free tier) |
| ఎవరు చేయాలి | నేను (లేదా మీరు) | మీరు — 4 clicks (Render account కావాలి) |

---

## Option A — One command తో మళ్ళీ start

Sandbox restart అయినప్పుడల్లా ఇది ఒక్కటి run చేయండి:

```bash
./scripts/dev_up.sh
```

అది తనంతట తానే:

1. Python environment create చేస్తుంది (ఒకసారి మాత్రమే)
2. dependencies install చేస్తుంది
3. database migrations run చేస్తుంది
4. database ఖాళీగా ఉంటేనే demo data seed చేస్తుంది (మీ data తుడిచిపెట్టదు)
5. static files collect చేస్తుంది
6. `0.0.0.0:8000` పై server start చేస్తుంది

ఇతర options:

```bash
./scripts/dev_up.sh --fresh   # demo data మళ్ళీ కొత్తగా create చేయి
./scripts/dev_up.sh --prod    # gunicorn తో production style run
```

Windows లో: `scripts\dev_up.bat`

> ఇది sandbox లో మాత్రమే పనిచేస్తుంది. Arena session ముగిసిన తర్వాత ఇది నడవదు.

---

## Option B — Permanent hosting (Render.com, free) ⭐

దీని తర్వాత **sandbox కి ఎలాంటి సంబంధం లేకుండా** app 24/7 online ఉంటుంది.
మీరు ఫోన్/ల్యాప్టాప్ ఏదైనా — link open చేస్తే app వస్తుంది.

### ✅ PR #2 merge అయింది
మొత్తం code ఇప్పుడు **`master`** లో ఉంది. Render `master` నుంచే deploy చేస్తుంది,
కాబట్టి ఇంక ఏమీ merge చేయాల్సిన అవసరం లేదు. ఇక మీరు చేయాల్సింది Render లో
4 క్లిక్‌లు మాత్రమే.

### Steps (4 clicks)

1. **https://render.com** → Sign up → **GitHub తో continue** (free, card అవసరం లేదు)
2. Dashboard → **New +** → **Blueprint**
3. మీ repo **`lakshmithanmai729-jpg/book_bridge`** select చేయండి → **Connect**
4. Render `render.yaml` చదివి అన్నీ సెటప్ చేస్తుంది → **Apply**

⏳ మొదటి build కి 3–5 నిమిషాలు పడుతుంది. తర్వాత:

```
https://bookbridge-XXXX.onrender.com      ← ఇది మీ శాశ్వత link
```

**మొదట admin account సృష్టించండి:** Render Dashboard → **Environment** → ఇవి add చేయండి:

```
DJANGO_SUPERUSER_USERNAME = మీ పేరు (ఉదా. thanmai)
DJANGO_SUPERUSER_EMAIL    = మీ ఇమెయిల్
DJANGO_SUPERUSER_PASSWORD = పొడవైన పాస్‌వర్డ్ (జాగ్రత్తగా దాచుకోండి)
```

తర్వాత **Manual Deploy → Deploy latest commit** నొక్కండి. అప్పుడు
`https://bookbridge-XXXX.onrender.com/admin/` లో మీరు login అవ్వవచ్చు.

> ⚠️ Public site లో `demo / bookbridge123` accounts **సృష్టించబడవు** —
> `seed_demo` production లో (DEBUG=False) కేవలం categories మాత్రమే create చేస్తుంది,
> ఎందుకంటే ఆ పాస్‌వర్డ్ అందరికీ తెలుసు.

### Render ఏమి చేస్తుంది (render.yaml లో ఉంది)

- `pip install -r requirements.txt`
- `collectstatic` (WhiteNoise static files serve చేస్తుంది — nginx అవసరం లేదు)
- `migrate` (database tables create)
- `seed_demo --if-empty` (production లో categories మాత్రమే — demo accounts కాదు)
- `ensure_admin` (`DJANGO_SUPERUSER_*` ఉంటే మీ admin account create/update)
- `gunicorn` తో app start
- `/healthz/` health check
- `SECRET_KEY` ను Render తనే generate చేస్తుంది
- **PostgreSQL free database** కూడా create అవుతుంది (`DATABASE_URL` ద్వారా connect)

### Free tier లో తెలుసుకోవాల్సిన విషయాలు

| విషయం | ఏమి జరుగుతుంది |
| --- | --- |
| 15 నిమిషాలు ఎవరూ open చేయకపోతే | app sleep అవుతుంది. తర్వాత మొదటి load కి ~30 sec |
| Book cover uploads | free disk ephemeral — redeploy కి పోతాయి (demo కి fine) |
| Database | free PostgreSQL — data **permanent** గా ఉంటుంది |
| Email | Render logs లో print అవుతుంది. Gmail SMTP కావాలంటే కింద చూడండి (password reset కి అవసరం) |
| Demo accounts | Production లో create అవ్వవు (భద్రత). మీ సొంత admin మాత్రమే |

### 🎭 Demo content మరియు శాశ్వత photos

`render.yaml` లో ఇవి ఇప్పటికే పెట్టి ఉన్నాయి:

| Variable | విలువ | ఏమి చేస్తుంది |
| --- | --- | --- |
| `DEMO_MODE` | `1` | 16 books + photos + chats ఆటోమేటిక్ (demo accounts **login అవ్వలేని** passwords తో) |
| `MEDIA_STORAGE` | `db` | Upload అయిన photos database లో — restart కి పోవు |

**Database 30 రోజులకు expire అవ్వకూడదంటే** → **`NEON.md`** చూడండి
(Neon free, ఎప్పటికీ expire అవ్వదు, card అవసరం లేదు).

Deploy అయ్యాక ఏమి connect అయిందో చూడాలంటే Logs లో `db_status` output ఉంటుంది.

### 📧 Email పనిచేయించడం (password reset కి కావాలి)

Default గా Render లో email **పంపబడదు** — logs లో మాత్రమే print అవుతుంది. అంటే
"Forgot password" పనిచేయదు. ఇది మార్చడానికి 3 నిమిషాలు:

1. Gmail → **Google Account → Security → 2-Step Verification ON** చేయండి
2. అదే page లో **App passwords** → "BookBridge" అని పేరు పెట్టి create చేయండి
3. 16 అక్షరాల password copy చేయండి
4. Render → **Environment** → ఇవి add చేయండి:

```
EMAIL_BACKEND       = django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST          = smtp.gmail.com
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = yourname@gmail.com
EMAIL_HOST_PASSWORD = <16-అక్షరాల app password>
DEFAULT_FROM_EMAIL  = BookBridge <yourname@gmail.com>
```

`Save, rebuild, and deploy` నొక్కండి. ఇక verification + password reset emails
నిజంగా వెళ్తాయి.

**Email లేకపోయినా పనిచేసే మార్గం:** `/admin/auth/user/` → user select చేయండి →
**Action: "Set a temporary password"** → password screen మీద కనిపిస్తుంది →
ఆ వ్యక్తికి ఇవ్వండి. వాళ్ళు login అయ్యాక `Change password` తో మార్చుకోవచ్చు.

### Media files permanent గా కావాలంటే (optional)
Render Dashboard → Environment → ఇవి add చేయండి:

```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
```

(దీనికి `django-storages` package కావాలి — చెప్పండి, నేను add చేస్తాను.)

---

## ఇతర hosts (same repo, same settings)

| Host | ఎలా |
| --- | --- |
| **Railway** | New Project → Deploy from GitHub → `Procfile` automatic గా పనిచేస్తుంది |
| **Fly.io** | `fly launch --no-deploy` → `fly deploy` (`fly.toml` సిద్ధంగా ఉంది) |
| **Docker (ఏ server అయినా)** | `docker compose up --build` → port 8000 |

అన్నిచోట్లా ఇవి మాత్రం సెట్ చేయండి: `DEBUG=False`, strong `SECRET_KEY`,
`ALLOWED_HOSTS` (మీ domain), మరియు `DATABASE_URL` (ఉంటే).

---

## ఏది ఎంచుకోవాలి?

- **ఇప్పుడే demo చూపించాలి / మీరు మాత్రమే test చేస్తున్నారు** → Option A సరిపోతుంది
- **ఇతరులకు link పంపాలి, ఎప్పుడైనా open అవ్వాలి** → **Option B** (Render)

Option B కోసం చెప్పండి — నేను PR merge చేసి, అవసరమైన configs సర్ది, step-by-step
సహాయం చేస్తాను.
