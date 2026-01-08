# Excel Natural Language Query Backend

This backend powers a **privacy-first web app** that allows users to upload an Excel/CSV file, ask questions in natural language, and receive results — **without storing any data permanently**.

All uploaded data is processed **in memory only** and wiped when the session ends.

---

## 🧠 What This Backend Does

1. Accepts an Excel (`.xlsx`) or CSV (`.csv`) file
2. Loads the file into an **in-memory DuckDB database**
3. Infers table schema automatically
4. Converts **natural language questions → safe SQL** using an LLM
5. Executes the SQL and returns results
6. Wipes all data when the user exits or the session expires

There is:

* ❌ No authentication
* ❌ No persistent storage
* ❌ No query history
* ❌ No background jobs

This is intentional.

---

## 🏗️ Architecture Overview

```
Client (Frontend)
   |
   |  POST /upload
   v
FastAPI Backend
   |
   |  Excel → Pandas → DuckDB (:memory:)
   |
   |  Schema inference
   |
User asks question
   |
   |  POST /query
   v
LLM (Gemini / Ollama)
   |
   |  SQL (SELECT only)
   v
SQL Validator → DuckDB
   |
   v
Result → Client
```

---

## 📁 Folder Structure

```
backend/
│
├── app/
│   ├── main.py                 # FastAPI app entry point
│   │
│   ├── routes/                 # API endpoints
│   │   ├── upload.py           # File upload + session creation
│   │   ├── query.py            # NL → SQL → execution
│   │   └── exit.py             # Session cleanup
│   │
│   ├── services/               # Core logic
│   │   ├── excel_loader.py     # Load Excel/CSV into DuckDB
│   │   ├── schema_infer.py     # Infer table schema
│   │   ├── ollama_client.py    # LLM client (Gemini/Ollama)
│   │   └── sql_executor.py     # SQL validation + execution
│   │
│   ├── prompts/
│   │   └── nl_to_sql.txt       # LLM system prompt
│   │
│   └── session/
│       └── manager.py          # Session + DB lifecycle
│
├── requirements.txt
└── README.md
```

---

## 🚀 Running the Backend

### 1️⃣ Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Set up LLM access

#### Option A: Gemini (current setup)

Set your API key as an environment variable:

```.env
GEMINI_KEY=your_api_key_here
```

(or configure it directly in code during development)

#### Option B: Ollama (local, later)

Make sure Ollama is running on:

```
http://localhost:11434
```

---

### 4️⃣ Start the server

```bash
uvicorn app.main:app --reload
```

Server will be available at:

```
http://localhost:8000
```

---

## 🔌 API Endpoints

### `POST /upload`

Uploads a file and creates a new session.

**Response**

```json
{
  "session_id": "uuid",
  "table": "data",
  "schema": {
    "column1": "VARCHAR",
    "column2": "INTEGER"
  }
}
```

---

### `POST /query`

Runs a natural language query against the uploaded data.

**Inputs**

* `session_id`
* `question`
* `table`
* `schema`

**Response**

```json
{
  "sql": "SELECT ...",
  "result": [[...], [...]]
}
```

---

### `POST /exit`

Explicitly deletes session data and wipes memory.

**Response**

```json
{
  "status": "deleted"
}
```

---

## 🔐 Security & Safety Guarantees

* DuckDB runs in `:memory:` mode only
* One database per session
* SQL is validated before execution
* Only `SELECT` queries are allowed
* No filesystem writes
* Server restart = total data wipe

This backend is **stateless by design**.

---

## ⚠️ Known Limitations (by choice)

* Single table only (no joins yet)
* No charts
* No multi-turn conversations
* No authentication
* No concurrency optimization

These are **deliberate MVP constraints**, not oversights.

---

## 🧭 Future Improvements (Optional)

* Column disambiguation
* Clarifying follow-up questions
* Chart generation
* Multi-sheet Excel support
* Better SQL parsing (AST-based)

---

## 🧠 Design Philosophy

> Excel is not a database.
> Natural language is ambiguous.
> Privacy beats convenience.

This backend embraces those realities instead of pretending otherwise.

