# BookBridge AI

BookBridge ships with an **offline AI layer** that runs inside Django. No GPU,
no model download, no paid API key, no personal data leaving the server. It is
classical machine learning (TF‑IDF, Naive Bayes, collaborative filtering) and
explainable scoring — which is exactly what a student marketplace needs: fast,
free, private and easy to reason about.

> Design rule: **the human is always the last reviewer.** Every AI output is a
> draft, a hint or a suggestion that the user can edit or ignore.

---

## 1. What the AI does

| Feature | Where it appears | How it works |
|---|---|---|
| **Fair price suggestion** | Sell form → *Suggest a fair price* | Finds comparable listings in the same category, normalises each to a "good" condition baseline, takes the **median** (robust to outliers), applies the seller's condition, clips to the MRP, and reports a range + confidence |
| **Description writer** | Sell form → *Draft description* | Extractive natural-language generation from facts the seller already typed. It never invents condition claims |
| **Category detection** | Sell form → *Guess category* | Multinomial **Naive Bayes** trained on existing listings, blended with a keyword prior so it works on a brand-new catalogue |
| **AI recommendations** | Book detail page, home page | **TF‑IDF cosine similarity** + wishlist co-occurrence ("readers who saved this also saved…"), with a human-readable reason on each card |
| **Assistant search** | `/ai/` | Rule-based NLP: budget, category, condition, free-only, area and sort parsed from a sentence such as *"NEET books under ₹300 near Madhapur"* |
| **Trust / risk score** | Sell form → *Check listing*, staff dashboard | Explainable rules: phone numbers or links in the description, duplicate reposts (fuzzy title match), price far from the category median, missing photo or thin description |
| **AI usage analytics** | Staff dashboard | `AIEvent` rows count feature usage per week — never the user's text |

---

## 2. Code map

```
ai_engine/
├── text.py        tokenising, TF-IDF vectors, cosine & fuzzy similarity
├── pricing.py     comparable-based price suggestion + confidence
├── classify.py    Naive Bayes category model (cached, retrains when the catalogue changes)
├── describe.py    listing copywriter (template NLG, deterministic variations)
├── recommend.py   content + collaborative recommendations, taste profile
├── assistant.py   natural-language query parsing and search
├── trust.py       listing risk scoring for moderation
├── models.py      AIEvent (feature usage analytics)
├── views.py       JSON endpoints + the /ai/ page
└── urls.py        routes
```

Templates:

* `ai_engine/templates/ai_engine/ai_hub.html` — the AI page (assistant + picks + explainer)
* `books/templates/books/book_form.html` — the seller-facing AI helper panel
* `books/templates/books/book_detail.html` — "AI recommendations" with reasons
* `core/templates/core/staff_dashboard.html` — AI usage + risk check on reports

---

## 3. HTTP API

All endpoints return JSON and are safe to call with partial or garbage input.

| Method | Endpoint | Returns |
|---|---|---|
| `GET` | `/ai/api/price/?category=&condition=&title=&original_price=` | `suggested_price`, `low`, `high`, `confidence`, `explanation`, `comparables[]` |
| `POST` | `/ai/api/describe/` | `description` |
| `POST` | `/ai/api/classify/` | `categories[]` with confidences |
| `POST` | `/ai/api/risk/` (login required) | `score`, `level`, `reasons[]`, `checks[]` |
| `GET` | `/ai/api/search/?q=...` | parsed `filters`, `understood[]`, `count`, `results[]` |
| `GET` | `/ai/api/similar/<book_id>/` | similar books with `score` + `reason` |
| `GET` | `/ai/api/parse/?q=...` | how the assistant understood a query (debugging) |

The old `/ai/suggest-price/` URL still works as an alias.

Rate limit: **120 AI calls per user/IP per hour** (`RATE_LIMITS['ai']`).

---

## 4. How the models work

### Price suggestion (`pricing.py`)

```
baseline = median(price_of_comparable / condition_factor[its_condition])
suggestion = baseline * condition_factor[seller_condition]
```

Condition factors: `new 1.45 · like_new 1.18 · good 1.00 · fair 0.72 · poor 0.45`.

Confidence combines sample size and price spread (IQR ÷ median). With fewer
than 3 comparables the suggestion falls back to the printed MRP (45 % resale)
and says so in `basis`.

### Category detection (`classify.py`)

Multinomial Naive Bayes with Laplace smoothing, trained in memory on every
book that has a category. A keyword prior (`CATEGORY_KEYWORDS`) adds evidence
for known exam terms, so the classifier is useful even with 5 listings. The
model is cached for 2 minutes and retrains automatically when the catalogue
changes.

### Recommendations (`recommend.py`)

```
score = cosine(tfidf(book), tfidf(candidate))
      + 0.18 (same category) + 0.22 (same author)
      + 0.12 + 0.05 * shared_readers (collaborative)
      + 0.06 (similar price)
```

`picks_for_user()` blends wishlist similarity, category interest from book
requests, the student's area and a light popularity prior, then attaches a
reason to every card. Blocked sellers are excluded from **every** AI path.

### Assistant (`assistant.py`)

Ordered rule parsing: budget → free → category → condition → area → sort. Each
signal is removed from the text before the next step, so "neet under 300 in
madhopur" leaves no leftover keywords. If a strict area filter returns nothing,
the area (never the budget) is relaxed and the answer says so.

### Risk score (`trust.py`)

Weights: phone number 60, off-platform link 45, email 45, external URL 40,
duplicate listing 30, price ≥ 3× median 18, price ≤ 0.25× median 10, missing
photo 6, no/short description 8/4, all-caps title 5, excessive punctuation 4.
Levels: high ≥ 60, medium ≥ 30, low otherwise. Every point comes with a reason.

---

## 5. Privacy

* Everything runs on the BookBridge server — no third-party API calls.
* `AIEvent` stores the feature name, the user (nullable) and aggregate numbers
  (sample size, result count, risk level). It never stores the seller's text.
* Blocked sellers are filtered out of recommendations, similar books and
  assistant search.
* Suggestions are drafts: nothing is published or priced without the user's
  explicit action.

---

## 6. Tests

```bash
python manage.py test ai_engine
```

41 tests cover the maths (cosine, median pricing, Naive Bayes, risk weights),
the guardrails (empty marketplace, garbage parameters, blocked sellers, no
invented facts) and every JSON endpoint.

---

## 7. Optional: plugging in an LLM later

The AI layer is deliberately provider-agnostic. If you later want richer copy
or a chat assistant, add a provider client and keep the existing modules as the
fallback:

```python
# ai_engine/llm.py  (not included — needs an API key)
def complete(prompt: str) -> str: ...
```

Then in `describe_api` / `assistant_search_api`, try `llm.complete(...)` first
and fall back to `draft_description()` / `search()` when the key is missing or
the call fails. Two rules matter:

1. **Never send personal data** (names, phone numbers, exact addresses) to a
   third-party model.
2. **Never let the model write prices or risk verdicts** — those must stay
   deterministic and auditable.

That keeps the current behaviour free and private by default, with an upgrade
path that does not rewrite the product.
