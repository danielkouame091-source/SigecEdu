# SigecEdu

**Smart attendance management and anti-corruption control for education in Côte d'Ivoire.**
*(French: "Système intelligent de gestion de l'assiduité et de contrôle anti-corruption pour l'éducation en Côte d'Ivoire".)*

**Author:** Kouassi Kouame Daniel · UID 25MDA10119 · MBA Data Science & AI, Chandigarh University, India

---

## 1. What is this project? (in simple words)

In many schools, attendance is written on paper, and it can be changed, forgotten or sold. SigecEdu is the **back-end** (the "engine behind the screen") of a system that:

1. keeps one **record per student** with an **attendance rate** (for example 82.5 %);
2. decides automatically whether a student is **allowed to sit the exam** (the rule: at least **75 %** attendance);
3. exposes this data through a small **web API**, so a phone app or a website can read and update it.

The longer-term goal is to make attendance **hard to falsify** (teacher identification by biometrics, audit trail) and so reduce corruption around exam eligibility. This repository contains the first working building blocks.

> **Honest status:** this is a school/prototype back-end. The student API works end to end; teachers, users and attendance sessions exist as data models and enumerations but have no API endpoints yet. See section 8.

## 2. Vocabulary (the code keeps French domain words)

| In the code | In English |
| --- | --- |
| `eleve` | student |
| `enseignant` | teacher |
| `matricule` | student ID number (unique) |
| `numero_te` | teacher ID number (unique) |
| `nom` / `prenoms` | last name / first names |
| `assiduite` | attendance |
| `taux_assiduite` | attendance rate, in % |
| `eligible_examen` | allowed to sit the exam (true/false) |
| `seance` | class session |
| `utilisateur` | user (a person who can log in) |

## 3. Files, one by one

```
SigecEdu/
├── main.py              ← the web API (Flask). THIS is what you run.
├── models.py            ← the database tables: students, teachers, users
├── enums.py             ← fixed lists of values (attendance status, presence, session status)
├── schemas.py           ← the shape of the data going in/out of the API (Pydantic)
├── crud.py              ← small helpers: find / create a student or a teacher
├── database.py          ← connection to the database (SQLite by default)
├── check_assiduite.py   ← the attendance rules (rate calculation, 75 % threshold)
├── seed_assiduite.py    ← puts 4 fictional students in the database for testing
├── creer_admin.py       ← creates the first administrator account
├── test_api.py          ← quick automatic test of the API
├── requirements.txt     ← the Python libraries needed
└── .gitignore           ← files Git must ignore (.env, *.db, ...)
```

## 4. How to run it (macOS Terminal)

Open the **Terminal** app and type these lines one by one (the `#` lines are only comments).

```bash
# 1. Go into the project folder (adapt the path to where you cloned it)
cd ~/SigecEdu

# 2. Create an isolated Python environment (once)
python3 -m venv .venv
source .venv/bin/activate

# 3. Install the libraries (once)
pip install -r requirements.txt

# 4. Put 4 fictional students in the database (optional, once)
python seed_assiduite.py

# 5. Start the API
python main.py
```

The API is now alive at **http://127.0.0.1:5000**. Open that address in your browser: you will see the list of endpoints.

**Settings (optional)** — create a file named `.env` next to `main.py`:

```
DATABASE_URL=sqlite:///sigecedu.db     # or a PostgreSQL address in production
PORT=5000                              # port used by the API
FLASK_DEBUG=0                          # 1 only on your own computer, never in production
```

## 5. The API

All answers are JSON with a `"status"` field (`"success"` or `"error"`).

| Method | Address | What it does |
| --- | --- | --- |
| GET | `/` | Name, version and list of endpoints |
| GET | `/health` | Checks the API and the database connection |
| GET | `/api/eleves` | List all students |
| GET | `/api/eleves/<id>` | One student |
| POST | `/api/eleves` | Create a student |
| PUT | `/api/eleves/<id>` | Update a student (only the fields you send) |
| DELETE | `/api/eleves/<id>` | Delete a student |

**Required fields to create a student:** `matricule`, `nom`, `prenoms`.
**Optional:** `taux_assiduite` (default 100), `eligible_examen` (default true), `statut_assiduite` (one of `Regular`, `Irregular`, `Absent`, `Excluded`; default `Regular`).

Example (second Terminal window, while the API is running):

```bash
# Create a student
curl -X POST http://127.0.0.1:5000/api/eleves \
  -H "Content-Type: application/json" \
  -d '{"matricule":"eleve005","nom":"Yao","prenoms":"kouadio marie","taux_assiduite":88}'

# List the students
curl http://127.0.0.1:5000/api/eleves
```

The API cleans the input: the matricule and last name are saved in CAPITAL LETTERS, first names in Title Case.

**HTTP codes:** 200 OK · 201 created · 400 missing data · 404 not found · 409 this matricule already exists · 422 invalid value · 500 server error.

## 6. The attendance rules

Written in `check_assiduite.py`:

- **Attendance rate** = sessions attended ÷ total sessions × 100 (rounded to 2 decimals; 100 % if there is no session yet).
- **Eligible for the exam** if the rate is **75 % or more**. The 75 % threshold is an example value and can be changed.

Try it: `python check_assiduite.py`.

## 7. Security: administrator account

`creer_admin.py` creates the first administrator. The password is asked in the terminal (12 characters minimum) and saved **hashed**, never in clear text:

```bash
python creer_admin.py admin@example.com
```

## 8. Limits and next steps (honest list)

- **No login protection on the API yet.** Anyone who can reach the server can create or delete students. Before any real use: add authentication (the `Utilisateur` table is ready for it) and role checks.
- Teachers (`Enseignant`), users (`Utilisateur`) and presence/session enums exist in the data model but have **no API endpoints yet**.
- No automatic computation of `taux_assiduite` from real sessions yet: today the rate is entered or sent by the client.
- No real data: the seed students are fictional.
- Only two automatic checks exist (`test_api.py`, `check_assiduite.py`). Unit tests with `pytest` are a good next step.

## 9. Technologies

Python 3 · Flask (web API) · SQLAlchemy (database) · Pydantic (data shapes) · SQLite (default database) · Gunicorn (production server).
