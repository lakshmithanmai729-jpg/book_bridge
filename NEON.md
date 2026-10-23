# BookBridge — Neon database, DEMO_MODE మరియు శాశ్వత photos

ఈ మూడూ **Render free plan** లోని మూడు లోపాలను తీసేస్తాయి:

| లోపం | పరిష్కారం |
| --- | --- |
| Render free Postgres **30 రోజులకు expire** (data పోతుంది) | **Neon** (ఉచితం, ఎప్పటికీ expire అవ్వదు) |
| Restart కి **photos పోతాయి** | `MEDIA_STORAGE=db` — photos database లో ఉంటాయి |
| Marketplace **ఖాళీగా** కనిపిస్తుంది | `DEMO_MODE=1` — 16 books, photos, chats ఆటోమేటిక్ |

**మూడూ కలిపి ఖర్చు: ₹0.**

---

## 1️⃣ DEMO_MODE — marketplace నిండుగా

ఇప్పుడు `render.yaml` లో ఇది ఇప్పటికే పెట్టి ఉంది:

```yaml
- key: DEMO_MODE
  value: "1"
```

### ఏమి చేస్తుంది

Deploy అయ్యే ప్రతిసారి ఇవి ఆటోమేటిక్ గా వస్తాయి:

| ఏమి | ఎన్ని |
| --- | --- |
| Books (photos తో) | **16** |
| Categories | 8 |
| Chat conversations | 6 |
| Book requests | 2 |
| Reviews | 4 |
| Wishlists | 3 |
| Notifications | 2 |

### 🔒 భద్రత — ఇది ముఖ్యం

DEMO_MODE లో demo accounts (`demo`, `arjun`, `priya`, `rahul`) create అవుతాయి,
కానీ వాటికి **password ఉండదు** (`unusable password`). అంటే:

- ✅ వాళ్ళ books, photos, chats **అందరికీ కనిపిస్తాయి**
- ❌ ఎవరూ ఆ accounts లోకి **login అవ్వలేరు** — README password (`bookbridge123`) పనిచేయదు
- ✅ మీకు మీ సొంత admin account మాత్రమే

### ఆపేయాలంటే (నిజమైన marketplace కి)

Render → **Environment** → `DEMO_MODE` → విలువ `0` → **Save, rebuild, and deploy**

> 📌 ఇప్పటికే seed అయిన 16 books **పోవు** — అవి database లో ఉన్నాయి. కావాలంటే
> `/admin/books/book/` లో ఒక్కొక్కటి delete చేయండి.

### మీరు మాన్యువల్ గా add చేసిన book

మీరు `admin` పేరుతో add చేసిన book **అలాగే ఉంటుంది** — demo seeding దాన్ని
ముట్టుకోదు. (`--if-empty` ఇప్పుడు "demo data ఉందా" అని చూస్తుంది, "books ఉన్నాయా"
అని కాదు — అందుకే మీ book ఉన్నా demo content వస్తుంది.)

---

## 2️⃣ Photos — restart కి పోకుండా

### సమస్య
Render free plan లో disk **తాత్కాలికం** (ephemeral). Restart / redeploy / sleep
నుంచి మేల్కొనడం జరిగినప్పుడల్లా `media/` folder ఖాళీ అవుతుంది. అప్పుడు
database లో `book_images/xyz.jpg` అని ఉన్నా, ఆ file ఉండదు → broken photos.

### పరిష్కారం
`render.yaml` లో ఇది ఇప్పటికే ఉంది:

```yaml
- key: MEDIA_STORAGE
  value: "db"
```

అంటే upload అయిన ప్రతి photo **database లోనే** (bytes గా) store అవుతుంది.

| అంశం | వివరం |
| --- | --- |
| Photo save అయ్యేది | `core_storedfile` table |
| URL | మారదు — `/media/book_images/...` |
| Thumbnails | కూడా database లో (`thumbs/...`) |
| Size అంశం | ఒక cover ~30 KB · thumbnail ~6 KB · **16 covers ≈ 0.6 MB** |
| Neon free limit | **0.5 GB** → దాదాపు **800 covers + thumbs** |

> పెద్ద scale కి (వేల books) S3 లేదా Cloudinary మంచిది. ఈ demo scale కి
> database పర్ఫెక్ట్ — మరియు ఇది **అదనపు account అవసరం లేదు**.

### ఇది పనిచేస్తోందా చూడండి

Render → **Logs** లో ఇలా కనిపిస్తుంది (deploy చివరలో):

```
Uploaded photos
  storage  : DatabaseStorage
  survives : yes — photos are rows in the database, so a restart or redeploy keeps them.
```

Local లో ట్రై చేయాలంటే:

```bash
MEDIA_STORAGE=db python manage.py db_status
```

---

## 3️⃣ Neon — శాశ్వత database

### ⚠️ ముందుగా తెలుసుకోండి

Render free Postgres **create చేసిన 30 రోజుల తర్వాత expire** అవుతుంది.
ఆ తర్వాత 14 రోజుల grace, ఆ తర్వాత **data తో సహా delete**. ఇది Render docs లోనే
ఉంది. Neon free plan కి ఈ limit **లేదు**.

### Steps (5 నిమిషాలు)

**1.** `https://neon.com` → **Sign up** (GitHub / Google / email — **card అవసరం లేదు**)

**2.** **Create project**
- Name: `bookbridge`
- Region: **Singapore** (Render service కూడా Singapore లో ఉంది → వేగం బాగుంటుంది)
- Postgres version: default ఉంచండి
→ **Create**

**3.** Dashboard లో **Connect** (లేదా **Connection string**) నొక్కండి

**4.** **Connection pooling** ఉన్న URL copy చేయండి. ఇలా ఉంటుంది:

```
postgresql://neondb_owner:AbCdEf123456@ep-cool-name-123456-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

> ⚠️ `?sslmode=require` తో **మొత్తం** copy చేయండి. మా code ఇప్పుడు ఆ భాగాన్ని
> చదువుతుంది (ఇంతకుముందు drop అయ్యేది → connection fail).

**5.** Render → `bookbridge` service → **Environment** → **Edit** →
`DATABASE_URL` విలువను **Neon URL తో replace** చేయండి

**6.** **`Save, rebuild, and deploy`** → 3 నిమిషాలు ఆగండి

**7.** **Logs** లో `db_status` output చూడండి — ఇలా ఉండాలి:

```
Database
  engine   : postgresql
  host     : ep-cool-name-123456-pooler.ap-southeast-1.aws.neon.tech
  sslmode  : require
  status   : connected (server 16.x)
```

`host` లో **neon.tech** కనిపిస్తే — ✅ మీరు ఇప్పుడు Neon లో ఉన్నారు.

### ఏమి జరుగుతుంది (data విషయం)

Neon కొత్తది కాబట్టి database **ఖాళీగా** ఉంటుంది. Deploy లో ఇవి ఆటోమేటిక్:

1. `migrate` → tables create
2. `seed_demo --if-empty` → **16 books + photos + chats** (DEMO_MODE వల్ల)
3. `ensure_demo_media` → covers
4. `ensure_admin` → మీ admin account

అంటే **మీకు ఏమీ చేయాల్సిన అవసరం లేదు** — site మళ్ళీ నిండుగా వస్తుంది.

> మీరు మాన్యువల్ గా add చేసిన ఆ ఒక్క book మాత్రం రాదు (అది పాత database లో ఉంది).
> `/admin/books/book/add/` లో 1 నిమిషంలో మళ్ళీ add చేయవచ్చు.

### 🔴 ఒక ముఖ్యమైన హెచ్చరిక

`render.yaml` లో ఇప్పటికీ ఇది ఉంది:

```yaml
- key: DATABASE_URL
  fromDatabase:
    name: bookbridge-db
```

అంటే **render.yaml ను edit చేసి sync చేస్తే**, `DATABASE_URL` తిరిగి Render
Postgres కి మారిపోతుంది. మీరు Neon లో శాశ్వతంగా ఉండాలంటే ఆ block తీసేయాలి.

**నాకు చెప్పండి — నేను ఆ మార్పు చేసి ఇస్తాను** (అప్పుడు `DATABASE_URL` ను Render
"secret" గా అడుగుతుంది, మీరు Neon URL paste చేయాలి).

అంతవరకూ: **`Manual sync` బటన్ నొక్కకండి** — సాధారణ deploys కి problem ఉండదు.

### ఇప్పటి Render DB data ను Neon కి తరలించాలంటే (optional)

మీ laptop లో (repo folder లో):

```bash
# 1. Render ఇప్పటి data దించుకోండి
pg_dump "<Render External Database URL>" --no-owner --no-privileges > bookbridge.sql

# 2. Neon కి ఎక్కించండి
psql "<Neon connection string>" < bookbridge.sql
```

> Render Dashboard → `bookbridge-db` → **Connect** → **External Database URL**.
> ఇది demo data కాబట్టి ఇది అవసరం లేదు — కేవలం పూర్తి జాగ్రత్త కోసం.

---

## ✅ మొత్తం అయ్యాక check list

Render → **Logs** లో ఇవి కనిపించాలి:

```
Demo data ready: 4 users, 16 books, 6 chat messages, ...
Demo accounts have unusable passwords on purpose...
Recreated N demo cover image(s).        (లేదా) All demo cover images are present.
Created superuser "admin".
Database ... status : connected
Uploaded photos  storage : DatabaseStorage
```

Browser లో:

| URL | ఏమి కనిపించాలి |
| --- | --- |
| `/` | books, categories |
| `/books/` | **16 books available** |
| `/books/1/` | photo + details |
| `/admin/` | 13 tables + live counts |

---

## సారాంశం

| Setting | విలువ | ఎందుకు |
| --- | --- | --- |
| `DEMO_MODE` | `1` | Marketplace నిండుగా (accounts lock అయి) |
| `MEDIA_STORAGE` | `db` | Photos restart కి పోకుండా |
| `DATABASE_URL` | Neon URL | Data శాశ్వతం (30 రోజుల limit లేదు) |

**మూడూ ₹0.** ఏదైనా అడుగు దగ్గర ఆగిపోతే — ఆ screen ఫోటో పండి.
