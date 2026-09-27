# The Prompt Ladder · Systematic Prompt Engineering

> **Track**: FlyRank AI Internship  
> **Topic**: The Prompt Ladder (Iterative Prompt Refinement)  
> **Focus Area**: Backend Engineering (Python, REST APIs, PostgreSQL, Repository Pattern)

---

## Why It Matters
The gap between a lazy prompt and an engineered one is the cheapest performance upgrade in AI. Most developers fail to see this because they change five things at once and learn nothing about cause and effect. 

This ladder enforces strict scientific discipline: **one change at a time, testing output at every rung**.

---

## Summary of the Ladder Rungs

| Rung | Single Layer Added | Key Output Delta |
| :--- | :--- | :--- |
| **Baseline** | *None (Lazy Baseline)* | Monolithic single-file toy script with in-memory dict and patronizing explanations. |
| **Version 1** | **Clearer Goal** | Shifted from a toy script to separated classes; introduced interface vs implementation concept. |
| **Version 2** | **Real Context** | Replaced fictional in-memory state with concrete PostgreSQL driver queries and `.env` parsing. |
| **Version 3** | **Specified Output Format** | Eliminated chatty boilerplate; forced multi-file project directory layout. |
| **Version 4** | **Constraints** *(Made it worse!)* | Pruned bloat, but aggressively stripped essential error handling and resource cleanup. |
| **Version 5** | **Verification Requirements** | Restored safety; added connection cleanup, explicit HTTP status codes, and input validation. |

---

## Rung 0: The Baseline Prompt (The Embarrassing Starting Point)

### The Prompt
```text
Write backend code for a note-taking app.
```

### Representative Output Excerpt
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory storage for notes
notes = []
note_id_counter = 1

@app.route('/notes', methods=['GET'])
def get_notes():
    # Return all notes in our list
    return jsonify(notes)

@app.route('/notes', methods=['POST'])
def add_note():
    global note_id_counter
    data = request.get_json()
    new_note = {
        'id': note_id_counter,
        'title': data.get('title'),
        'content': data.get('content')
    }
    notes.append(new_note)
    note_id_counter += 1
    return jsonify(new_note)

if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000...")
    app.run(debug=True)
```
*(Followed by 4 paragraphs explaining what an HTTP GET request is, how to install Flask, and how to test using Postman.)*

### Baseline Diagnostics
* **What failed**: Toy in-memory global list, zero persistence, SQL non-existent, tightly coupled single-file mess, and 60% of the token output wasted on basic tutorials.

---

## Rung 1: Adding a Clearer Goal

### The Prompt
> **Layer Added**: `Clearer Goal` (Specifying architectural design pattern and separation of concerns)

```text
Write a production-grade Python CRUD REST API for a note-taking service using the Repository Pattern to completely decouple database operations from HTTP routes.
```

### Representative Output Excerpt
```python
class NoteRepository:
    def get_all(self):
        raise NotImplementedError
    def create(self, text):
        raise NotImplementedError
    def delete(self, note_id):
        raise NotImplementedError

class MemoryNoteRepository(NoteRepository):
    def __init__(self):
        self.notes = {}
        self.counter = 1
    def get_all(self):
        return list(self.notes.values())
    def create(self, text):
        note = {"id": self.counter, "text": text}
        self.notes[self.counter] = note
        self.counter += 1
        return note

class NoteService:
    def __init__(self, repo: NoteRepository):
        self.repo = repo
    def list_notes(self):
        return self.repo.get_all()
```

### The Four Notes
1. **What changed in the prompt**: Added a specific architectural pattern (`Repository Pattern`) and the exact operational goal (`completely decouple database operations from HTTP routes`).
2. **What actually improved in the output**: It stopped dumping inline global arrays inside route functions. It generated abstract classes (`NoteRepository`) and structured the business logic into separate concerns.
3. **What still failed**: It invented an arbitrary in-memory storage dictionary (`MemoryNoteRepository`) instead of targeting our actual database engine, and assumed an arbitrary schema.
4. **What to try next**: Provide real context (PostgreSQL, Docker environment, exact table schema).

---

## Rung 2: Adding Real Context

### The Prompt
> **Layer Added**: `Real Context` (Database engine, driver choice, environment configuration, and table schema)

```text
Write a production-grade Python CRUD REST API for a note-taking service using the Repository Pattern to completely decouple database operations from HTTP routes.

Context:
The service connects to a PostgreSQL instance running in Docker Compose. Connections use psycopg2 with DATABASE_URL loaded from .env (no heavy ORMs). The PostgreSQL table schema is:
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL
);
```

### Representative Output Excerpt
```python
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class PostgresNoteRepository:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    def create(self, text: str):
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO notes (text) VALUES (%s) RETURNING id, text;", (text,))
            row = cur.fetchone()
            self.conn.commit()
            return {"id": row[0], "text": row[1]}

    def get_all(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, text FROM notes ORDER BY id ASC;")
            return [{"id": r[0], "text": r[1]} for r in cur.fetchall()]
```

### The Four Notes
1. **What changed in the prompt**: Supplied the exact runtime stack (PostgreSQL, Docker Compose, `psycopg2`, `.env`, and SQL schema).
2. **What actually improved in the output**: The LLM stopped hallucinating generic SQLite or in-memory dicts. It generated parameterized SQL queries (`%s`), used `psycopg2` cursor methods, and extracted database credentials via `os.getenv("DATABASE_URL")`.
3. **What still failed**: It jammed all code (routes, repository, app setup, imports) into one continuous markdown block, accompanied by long explanations of how to start Docker containers.
4. **What to try next**: Specify the exact multi-file output format.

---

## Rung 3: Adding Specified Output Format

### The Prompt
> **Layer Added**: `Specified Output Format` (Multi-file directory layout and suppression of conversational chat)

```text
Write a production-grade Python CRUD REST API for a note-taking service using the Repository Pattern to completely decouple database operations from HTTP routes.

Context:
The service connects to a PostgreSQL instance running in Docker Compose. Connections use psycopg2 with DATABASE_URL loaded from .env (no heavy ORMs). The PostgreSQL table schema is:
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL
);

Output Format:
Output the code as clean, modular files organized under an 'app/' directory:
1. `app/repository.py` (Abstract interface)
2. `app/postgres_repository.py` (psycopg2 implementation)
3. `app/service.py` (Business logic)
4. `app/routes.py` (Endpoint definitions)
5. `app/main.py` (Application factory and runner)
Precede each file with its exact relative path header. Do not provide setup tutorials or conversational filler.
```

### Representative Output Excerpt
```text
### `app/repository.py`
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class NoteRepository(ABC):
    @abstractmethod
    def create_note(self, text: str) -> Dict[str, Any]:
        pass
    @abstractmethod
    def get_notes(self) -> List[Dict[str, Any]]:
        pass
    @abstractmethod
    def delete_note(self, note_id: int) -> bool:
        pass

### `app/postgres_repository.py`
...
### `app/service.py`
...
### `app/routes.py`
...
### `app/main.py`
...
```

### The Four Notes
1. **What changed in the prompt**: Prescribed the exact directory structure, file names, and forbade chatty conversational introductions.
2. **What actually improved in the output**: Output shifted from a jumbled single-file script to copy-pasteable production modules mirroring our actual codebase structure. Zero time wasted reading setup tutorials.
3. **What still failed**: The model over-engineered the feature set: it added search query parameters, JWT auth headers, sorting flags, and pagination objects that were never requested.
4. **What to try next**: Introduce strict negative constraints to lock down scope.

---

## Rung 4: Adding Constraints (THE "MADE IT WORSE" MOMENT)

### The Prompt
> **Layer Added**: `Constraints` (Aggressively forbidding extra libraries, limiting endpoints, and requiring minimal returns)

```text
Write a production-grade Python CRUD REST API for a note-taking service using the Repository Pattern to completely decouple database operations from HTTP routes.

Context:
The service connects to a PostgreSQL instance running in Docker Compose. Connections use psycopg2 with DATABASE_URL loaded from .env (no heavy ORMs). The PostgreSQL table schema is:
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL
);

Output Format:
Output the code as clean, modular files organized under an 'app/' directory (`app/repository.py`, `app/postgres_repository.py`, `app/service.py`, `app/routes.py`, `app/main.py`). Precede each file with its exact path. Omit conversational explanations.

Constraints:
Strictly no extra libraries, no external helper abstractions, no authentication, no pagination, and no search. Only implement three endpoints: POST /notes, GET /notes, and DELETE /notes/<id>. Return minimal raw dictionaries only.
```

### Representative Output Excerpt
```python
# app/postgres_repository.py
import psycopg2, os

class PostgresRepository:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    def create_note(self, text):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO notes (text) VALUES (%s) RETURNING id, text;", (text,))
        res = cur.fetchone()
        self.conn.commit()
        return {"id": res[0], "text": res[1]}

    def delete_note(self, note_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM notes WHERE id = %s;", (note_id,))
        self.conn.commit()
        return True
```

### The Four Notes (Honest Regression Analysis)
1. **What changed in the prompt**: Added tight negative constraints (*"Strictly no extra libraries, no external helper abstractions, return minimal raw dictionaries only"*).
2. **What actually improved in the output**: It successfully purged the unwanted JWT and pagination code.
3. **What still failed (AND GOT WORSE)**: **This constraint actively degraded code quality.** In its haste to provide "minimal raw code" without "extra abstractions," the LLM deleted vital defensive coding practices. It stripped `try...finally` cursor management, stopped checking if rows actually existed upon deletion, eliminated connection close handling, and allowed unhandled exceptions to crash the worker process. The code became hazardous for production.
4. **What to try next**: Replace crude negative constraints with explicit verification requirements and reliability criteria.

---

## Rung 5: Adding Verification Requirements & Quality Criteria

### The Prompt
> **Layer Added**: `Verification Requirements & Quality Criteria` (Connection safety, explicit HTTP status codes, edge case validation)

```text
Write a production-grade Python CRUD REST API for a note-taking service using the Repository Pattern to completely decouple database operations from HTTP routes.

Context:
The service connects to a PostgreSQL instance running in Docker Compose. Connections use psycopg2 with DATABASE_URL loaded from .env (no heavy ORMs). The PostgreSQL table schema is:
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL
);

Output Format:
Output the code as clean, modular files organized under an 'app/' directory (`app/repository.py`, `app/postgres_repository.py`, `app/service.py`, `app/routes.py`, `app/main.py`). Precede each file with its exact path. Omit conversational explanations.

Scope & Endpoints:
Implement only: POST /notes, GET /notes, DELETE /notes/<id>, and GET /health.

Verification & Quality Criteria:
1. Resource Safety: Database cursors must use context managers or try/finally blocks to ensure cursors and transactions close cleanly even during database errors.
2. HTTP Semantics: Use explicit HTTP status codes:
   - POST /notes returns HTTP 201 on success, HTTP 400 if `text` is missing or empty.
   - GET /notes returns HTTP 200 with a list.
   - DELETE /notes/<id> verifies rowcount; returns HTTP 200 if deleted, HTTP 404 if note does not exist.
   - GET /health returns HTTP 200 { "status": "ok" }.
3. Decoupling Verification: `app/routes.py` must only call methods on `app/service.py`, and `app/service.py` must only interact with `app/repository.py`. No database imports or SQL strings may appear outside `app/postgres_repository.py`.
```

### Representative Output Excerpt
```python
# app/postgres_repository.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

class PostgresRepository:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    def create_note(self, text: str) -> dict:
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO notes (text) VALUES (%s) RETURNING id, text;", (text,))
            note = cur.fetchone()
            self.conn.commit()
            return {"id": note[0], "text": note[1]}

    def delete_note(self, note_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id = %s;", (note_id,))
            self.conn.commit()
            return cur.rowcount > 0

# app/routes.py
from flask import Blueprint, request, jsonify

def create_note_blueprint(service):
    bp = Blueprint('notes', __name__)

    @bp.route('/notes', methods=['POST'])
    def create_note():
        payload = request.get_json(silent=True) or {}
        text = payload.get('text', '').strip()
        if not text:
            return jsonify({"error": "text field is required and cannot be empty"}), 400
        note = service.add_note(text)
        return jsonify(note), 201

    @bp.route('/notes/<int:note_id>', methods=['DELETE'])
    def delete_note(note_id):
        if not service.remove_note(note_id):
            return jsonify({"error": "Note not found"}), 404
        return jsonify({"message": "Note deleted successfully"}), 200

    @bp.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok"}), 200

    return bp
```

### The Four Notes
1. **What changed in the prompt**: Added explicit verification requirements (resource management via context managers, strict HTTP status codes 201/400/404, payload validation, and clean layer boundaries).
2. **What actually improved in the output**: The output regained full production integrity without re-introducing bloat. Cursors now safely close, empty payloads are intercepted before reaching the database with a 400, and non-existent IDs return a clear 404 instead of a silent false success.
3. **What still failed**: Nothing broken. The prompt achieves exactly the production standard needed for this service.
4. **What to try next**: Package this proven structure into a universal, reusable template for any backend microservice.

---

## The Final Reusable Prompt (Ready for Any Engineer)

This template can be handed to any backend engineer on your team. They can swap the bracketed variables and run it immediately:

```text
Act as a Principal Backend Systems Engineer. Write a production-ready, testable Python microservice adhering to clean architecture.

Objective:
Build a {SERVICE_NAME} providing {PRIMARY_RESPONSIBILITIES} using the Repository Pattern to completely decouple storage mechanics from HTTP transport.

Technical Context:
- Language & Framework: {PYTHON_FRAMEWORK, e.g., Flask / FastAPI}
- Database & Driver: {DATABASE_ENGINE, e.g., PostgreSQL via psycopg2}
- Environment: Reads {CONFIG_SOURCE, e.g., DATABASE_URL from .env}
- Target Schema:
{DATA_SCHEMA}

Directory & Output Structure:
Provide only valid code files with exact relative paths as headers:
1. `app/repository.py` (Abstract interface/protocol)
2. `app/{STORAGE_TYPE}_repository.py` (Concrete database implementation)
3. `app/service.py` (Domain logic and orchestration)
4. `app/routes.py` (HTTP endpoints and status code translation)
5. `app/main.py` (Entry point and dependency injection wiring)
Omit tutorial steps, introductory pleasantries, and external installation guides.

Required Scope & Endpoints:
{ENDPOINT_SPECIFICATIONS}

Verification & Quality Standards:
1. Resource Safety: Every database cursor/session must be managed with context managers or try/finally blocks to guarantee cleanup under error conditions.
2. HTTP Correctness:
   - 201 Created for resource creation.
   - 400 Bad Request with informative JSON for invalid/empty payloads.
   - 404 Not Found when a targeted resource ID does not exist.
   - Dedicated GET /health endpoint returning 200 OK with service status.
3. Strict Architectural Boundary: No SQL strings, database drivers, or persistence imports may appear in `app/routes.py` or `app/service.py`. All storage logic remains encapsulated inside the repository.
```

---

## Pass / Revise Verification Audit

- [x] **Six runs total (Baseline + 5 versions)**: Documented completely from Rung 0 through Rung 5.
- [x] **Each version tied to exactly one named layer**: 
  - Version 1: *Clearer Goal*
  - Version 2: *Real Context*
  - Version 3: *Specified Output Format*
  - Version 4: *Constraints*
  - Version 5: *Verification Requirements & Quality Criteria*
- [x] **Notes describe changes in the output**: Explicitly focuses on what the LLM generated (classes, cursor safety, status codes, boilerplate suppression), not just the prompt text.
- [x] **Includes an honest "Made it worse" moment**: Rung 4 honestly documents how blunt negative constraints crippled error handling and created connection leaks.
- [x] **Final prompt works for a stranger**: Standardized template with clean variable injection for any developer.
