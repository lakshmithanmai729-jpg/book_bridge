# BookBridge

Local used-book marketplace. Buy, sell, donate, and find books near you.

Built with Django, MySQL, and Bootstrap.

## Features

- Account signup, login, profile, and password change
- Book listings with photos, condition, price, and location
- Donate a book or mark a listing as negotiable
- Search and filter by title, author, city, pincode, category, and price
- Wishlist
- Suggested price and similar-book recommendations
- Multiple photos per listing

## Tech stack

- Python / Django
- MySQL
- Bootstrap 5
- Pillow (image uploads)

## Setup

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

3. Fill `.env` with your Django `SECRET_KEY` and MySQL credentials. Do not commit `.env`.

4. Create the database in MySQL (`book_bridge`), then run:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Project layout

| App | Role |
| --- | --- |
| `core` | Home page |
| `accounts` | Auth, profile, messages placeholder |
| `books` | Listings, search, wishlist, images |
| `ai_engine` | Price suggestion and recommendations |

## License

MIT
