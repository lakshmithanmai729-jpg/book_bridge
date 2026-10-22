# BookBridge — run it on your own computer (VS Code)

This is the "no assistant needed" guide. Once set up, you can start BookBridge
any time with one command and open it at:

> **http://127.0.0.1:8000/**

Demo login: **demo** / **bookbridge123**

---

## 0. Which branch has the latest work?

All the latest features (AI layer, bug fixes, deploy config) live on the
branch **`arena/2fb4088e-book-bridge`**. `master` is older until that branch is
merged. In VS Code, click the branch name in the bottom-left corner and pick:

```
origin/arena/2fb4088e-book-bridge
```

(Or in the terminal: `git checkout arena/2fb4088e-book-bridge && git pull`)

---

## 1. Fastest way — one click (Windows)

1. Open the `book_bridge` folder in VS Code.
2. In the file list, double-click **`BookBridge-Start.bat`**.

That script creates the virtual environment, installs requirements, applies
migrations, loads demo data, and starts the server — then opens your browser
at `http://127.0.0.1:8000`.

Stop the server with **Ctrl + C** in the window it opened.

---

## 2. Manual way — VS Code terminal (Windows)

Open **Terminal → New Terminal** in VS Code (Ctrl + `), then run these five
lines one time only:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --if-empty
```

After that, every time you want to start the app:

```bat
venv\Scripts\activate
python manage.py runserver
```

Then open **http://127.0.0.1:8000/** in your browser.

> If VS Code says `python` is not recognised, install Python 3.11+ from
> <https://www.python.org/downloads/> and tick **"Add python.exe to PATH"**
> during setup, then close and reopen VS Code.

---

## 3. Manual way — macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --if-empty
python manage.py runserver
```

There is also a shortcut script:

```bash
./scripts/dev_up.sh            # start
./scripts/dev_up.sh --fresh    # reset the demo data first
```

On Windows the equivalent is `scripts\dev_up.bat`.

---

## 4. Open it on your phone (same Wi-Fi)

The default `runserver` only listens on your own computer. To test on a phone,
run it on all interfaces:

```bash
python manage.py runserver 0.0.0.0:8000
```

Then find your computer's local IP:

* **Windows:** `ipconfig` → look for *IPv4 Address* (e.g. `192.168.1.5`)
* **macOS/Linux:** `ifconfig` or `ip addr`

Open `http://192.168.1.5:8000` on the phone (same Wi-Fi). If it does not load,
allow Python through your firewall, or add the IP to `.env`:

```
ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.5
```

---

## 5. What you can change without touching code

| Change | Where | Restart needed? |
| --- | --- | --- |
| Books, users, categories, reports, prices | `/admin/` or the app itself | No — saves instantly |
| Text, colours, layout, logic | edit the file → save | **Yes** — `runserver` auto-reloads on save |
| New model / field | edit `models.py` → `python manage.py makemigrations` → `python manage.py migrate` | Yes |
| Environment settings (email, domain, database) | `.env` file | Yes |

`runserver` reloads automatically whenever you save a Python or template file,
so you normally just refresh the browser.

---

## 6. Useful commands

```bat
python manage.py runserver                :: start the app
python manage.py migrate                  :: apply database changes
python manage.py makemigrations           :: create a migration after editing models
python manage.py seed_demo --reset        :: wipe and reload the demo data
python manage.py createsuperuser          :: make your own admin account
python manage.py test                     :: run all 161 tests
python manage.py shell                    :: Python console with the app loaded
python manage.py collectstatic            :: rebuild static files (needed for production only)
```

---

## 7. Logins that already exist

| Username | Password | Notes |
| --- | --- | --- |
| `demo` | `bookbridge123` | Staff account — sees `/staff/` and the AI admin panels |
| `arjun` | `bookbridge123` | Public profile, Telegram contact |
| `priya` | `bookbridge123` | Public profile, WhatsApp contact |
| `rahul` | `bookbridge123` | Private profile, in-app chat only |

Create your own with `python manage.py createsuperuser` and use `/admin/`.

---

## 8. Common problems

**"That port is already in use"**
Another server is still running. Press Ctrl + C in the other terminal, or use a
different port: `python manage.py runserver 8002`.

**Styles look broken / icons missing**
Only happens when `DEBUG=False`. For local work keep `DEBUG=True` in `.env`
(the `.env.example` default) and `runserver` serves static files by itself.

**"no such table" errors**
You forgot to migrate. Run `python manage.py migrate`.

**The pages load but there are no books**
Run `python manage.py seed_demo --if-empty` (or `--reset` to start clean).

**`ModuleNotFoundError: No module named 'django'`**
The virtual environment is not active. Run `venv\Scripts\activate`
(Windows) or `source venv/bin/activate` (Mac/Linux) first.

**Password reset / verification emails do not arrive**
By default they are printed in the terminal where the server runs — look there.
To send real email, fill in the SMTP values in `.env`.

---

## 9. Where the data lives

* **Database:** `db.sqlite3` in the project root. Delete it and re-run
  `migrate` + `seed_demo` for a completely fresh start.
* **Uploaded photos:** the `media/` folder.
* Nothing is sent anywhere — the AI features run inside this project.

---

## 10. When you are ready for a public link

Deploying gives you a permanent `https://...` URL that works even when your
laptop is off. See **`DEPLOY.md`** (Render blueprint is already in
`render.yaml`). Until then, `http://127.0.0.1:8000` is your local link.
