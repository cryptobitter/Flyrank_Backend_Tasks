# Prompting Fundamentals on Real Tasks v2

> **Track**: FlyRank AI Internship — Foundations  
> **Topic**: Prompting Fundamentals on Real Tasks  
> **Target Task (from FL-01 Audit)**: Production-Grade PostgreSQL Repository Layer with Connection Pooling, Transaction Safety, and Clean Error Handling

---

## 1. Executive Summary & Why It Matters
The gap between a lazy prompt and an engineered one is the cheapest performance upgrade in AI. Practicing on toy examples ("write a poem about databases") teaches nothing about real-world software engineering constraints. 

This deliverable tracks the step-by-step engineering of a prompt for an actual, critical task from our FL-01 backend codebase: moving from raw single-connection scripts to an enterprise-grade PostgreSQL repository layer. Each iteration introduces exactly one named technique from the Anthropic & OpenAI best-practice guides, measures the concrete delta in the generated code, compares cross-model execution between **Claude** and **ChatGPT**, and distills the learnings into a reusable production template.

---

## 2. Iteration Log: The 6 Iterations

### Rung 0: The Naive Baseline

#### The Prompt
```text
Write a Python database class to connect to Postgres and save notes.
```

#### Representative Output Excerpt
```python
import psycopg2

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="testdb",
            user="postgres",
            password="password",
            host="localhost"
        )
        self.cursor = self.conn.cursor()

    def save_note(self, text):
        query = f"INSERT INTO notes (text) VALUES ('{text}')"
        self.cursor.execute(query)
        self.conn.commit()
        print("Note saved successfully!")
```

#### Diagnostic & Critique
* **Observed Output**: 
  - Catastrophic SQL injection vulnerability via f-string formatting (`f"INSERT INTO notes VALUES ('{text}')"`).
  - Hardcoded localhost credentials instead of environment variables.
  - Keeps a single global connection and persistent cursor open indefinitely in `__init__`, guaranteeing thread collisions and connection death in multi-worker WSGI servers.
  - Zero return value, raw `print()` statements instead of return types or exceptions.

---

### Iteration 1: Applying Role Assignment

#### The Prompt
> **Technique Added**: `Role Assignment` (Calibrating the AI's persona, experience level, and default architectural expectations)

```text
You are a Principal Database Infrastructure Engineer specializing in Python, PostgreSQL, and high-reliability distributed systems. Write a Python database class to connect to Postgres and save notes.
```

#### Representative Output Excerpt
```python
import os
import psycopg2
from typing import Dict, Any

class NoteDatabase:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is not set.")

    def save_note(self, text: str) -> Dict[str, Any]:
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO notes (text) VALUES (%s) RETURNING id, text;",
                    (text,)
                )
                record = cur.fetchone()
                return {"id": record[0], "text": record[1]}
```

#### Observed Output Differences (Prompt vs. Output Note)
* **What changed in prompt**: Assigned the role of a *Principal Database Infrastructure Engineer*.
* **Observed difference in output**: The role prompt immediately eradicated the two most egregious beginner mistakes: the f-string SQL injection was replaced with parameterized `%s` tuples, and hardcoded localhost credentials were replaced with `os.getenv("DATABASE_URL")`. It also added basic type hints and returned a dictionary instead of `print()`.
* **What still failed**: It opens and tears down a brand new physical TCP connection to PostgreSQL on every single method call (`with psycopg2.connect(...)`), which would immediately exhaust PostgreSQL connection limits under moderate traffic.

---

### Iteration 2: Adding Context and Motivation

#### The Prompt
> **Technique Added**: `Context and Motivation` (Explaining the operational environment, concurrency requirements, and why connection overhead matters)

```text
You are a Principal Database Infrastructure Engineer specializing in Python, PostgreSQL, and high-reliability distributed systems. Write a Python database class to connect to Postgres and save notes.

Context & Motivation:
This service runs inside a multi-worker Docker Compose environment handling concurrent HTTP requests. Opening a new TCP connection per request causes extreme latency and threatens connection starvation on our PostgreSQL server. The service must use connection pooling via `psycopg2.pool.SimpleConnectionPool`, manage connections safely across concurrent threads, and interact with the schema:
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Representative Output Excerpt
```python
import os
from contextlib import contextmanager
from psycopg2 import pool
from typing import Generator, Dict, Any

class NoteDatabase:
    def __init__(self, minconn: int = 1, maxconn: int = 20):
        database_url = os.getenv("DATABASE_URL")
        self._pool = pool.SimpleConnectionPool(minconn, maxconn, dsn=database_url)

    @contextmanager
    def get_connection(self) -> Generator:
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    def save_note(self, text: str) -> Dict[str, Any]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO notes (text) VALUES (%s) RETURNING id, text, created_at;",
                    (text,)
                )
                res = cur.fetchone()
                conn.commit()
                return {"id": res[0], "text": res[1], "created_at": res[2]}
```

#### Observed Output Differences (Prompt vs. Output Note)
* **What changed in prompt**: Provided runtime context (Docker Compose multi-worker concurrency) and explained the motivation (prevent TCP exhaustion and server starvation).
* **Observed difference in output**: The model engineered a `SimpleConnectionPool` and introduced a generator-based context manager (`@contextmanager def get_connection()`) to guarantee that connections are checked back into the pool via `putconn` even if exceptions occur.
* **What still failed**: The output is still a monolithic class that mixes connection pool lifecycle with domain queries, lacking clear interface boundaries, domain entity structures, or standardized error wrappers.

---

### Iteration 3: Adding Few-Shot Examples

#### The Prompt
> **Technique Added**: `Few-Shot Examples` (Providing concrete input/output exemplars of clean architecture and custom exception handling)

```text
You are a Principal Database Infrastructure Engineer specializing in Python, PostgreSQL, and high-reliability distributed systems. Write a Python database class to connect to Postgres and save notes.

Context & Motivation:
This service runs inside a multi-worker Docker Compose environment handling concurrent HTTP requests. Opening a new TCP connection per request causes extreme latency and threatens connection starvation. The service must use connection pooling (`SimpleConnectionPool`) and interact with schema `notes (id SERIAL PRIMARY KEY, text TEXT NOT NULL)`.

Exemplar of Expected Architectural Pattern:
```python
# Interface Example
class AbstractRepository(ABC):
    @abstractmethod
    def add(self, item: Any) -> Any: pass

# Method Signature & Exception Handling Example
def get_entity_or_fail(self, entity_id: int) -> EntityRecord:
    try:
        with self.get_cursor() as cur:
            cur.execute("SELECT id, name FROM items WHERE id = %s;", (entity_id,))
            row = cur.fetchone()
            if not row:
                raise RecordNotFoundError(f"Item {entity_id} does not exist.")
            return EntityRecord(id=row[0], name=row[1])
    except psycopg2.DatabaseError as e:
        logger.error("Query failed: %s", e)
        raise RepositoryError("Persistence failure") from e
```
```

#### Representative Output Excerpt
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import psycopg2

class RepositoryException(Exception): pass
class RecordNotFoundError(RepositoryException): pass

@dataclass(frozen=True)
class NoteRecord:
    id: int
    text: str

class NoteRepositoryInterface(ABC):
    @abstractmethod
    def save_note(self, text: str) -> NoteRecord: pass
    @abstractmethod
    def get_note(self, note_id: int) -> NoteRecord: pass

class PostgresNoteRepository(NoteRepositoryInterface):
    ...
    def get_note(self, note_id: int) -> NoteRecord:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, text FROM notes WHERE id = %s;", (note_id,))
                    row = cur.fetchone()
                    if not row:
                        raise RecordNotFoundError(f"Note {note_id} not found.")
                    return NoteRecord(id=row[0], text=row[1])
        except psycopg2.DatabaseError as exc:
            raise RepositoryException("Database access error") from exc
```

#### Observed Output Differences (Prompt vs. Output Note)
* **What changed in prompt**: Injected concrete few-shot examples demonstrating abstract base classes, immutable dataclasses, and custom layered exception wrapping (`RepositoryException` catching `psycopg2.DatabaseError`).
* **Observed difference in output**: The generated code adopted typed domain objects (`@dataclass(frozen=True) NoteRecord`) and domain-level exceptions (`RecordNotFoundError`). Raw database exceptions no longer leak to higher layers.
* **What still failed**: The output formatting is unpredictable—the model alternated between inline comments, scattered narrative explanations, and incomplete snippet stubs (`...`).

---

### Iteration 4: Adding Strict Output Structure

#### The Prompt
> **Technique Added**: `Output Structure` (Explicit tag-based encapsulation, file partitioning, and suppression of discursive conversational filler)

```text
You are a Principal Database Infrastructure Engineer specializing in Python, PostgreSQL, and high-reliability distributed systems.

Task:
Implement the complete PostgreSQL data persistence layer for a note-taking service using connection pooling and the Repository Pattern.

Context:
- Multi-worker Docker Compose setup; must use `psycopg2.pool.ThreadedConnectionPool`.
- Database URL parsed from `os.getenv("DATABASE_URL")`.
- Table schema: `notes (id SERIAL PRIMARY KEY, text TEXT NOT NULL)`.

Format & Structure Requirements:
Output the solution strictly across two clean sections using the following markdown format:
### SECTION 1: DOMAIN & INTERFACE
Contains custom exceptions, frozen dataclasses, and the abstract repository ABC.
### SECTION 2: POSTGRESQL IMPLEMENTATION
Contains connection pool lifecycle management and the concrete `PostgresNoteRepository`.

Rules:
- Include full imports and complete implementations (no `pass`, no `...`, no placeholders).
- Omit conversational preambles, apologies, and basic CLI installation guides.
```

#### Representative Output Excerpt
```markdown
### SECTION 1: DOMAIN & INTERFACE
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

class RepositoryError(Exception):
    pass

class NoteNotFoundError(RepositoryError):
    pass

@dataclass(frozen=True)
class NoteEntity:
    id: int
    text: str
...
```

### SECTION 2: POSTGRESQL IMPLEMENTATION
```python
import os
from contextlib import contextmanager
from psycopg2 import pool
...
```
```

#### Observed Output Differences (Prompt vs. Output Note)
* **What changed in prompt**: Dictated exact section headers (`### SECTION 1`, `### SECTION 2`) and prohibited conversational intros or placeholder comments (`...`).
* **Observed difference in output**: Output became completely copy-pasteable and production-ready. No time spent scrolling past AI pleasantries. Every method was written out in full with zero ellipses.
* **What still failed**: It lacked transaction rollback safety on unexpected errors—if an insert query failed midway, the connection remained in an aborted transaction state before returning to the pool.

---

### Iteration 5: Adding Step Decomposition (Chain-of-Thought / Sequential Planning)

#### The Prompt
> **Technique Added**: `Step Decomposition` (Forcing the model to sequentially reason through pool initialization, transactional context boundaries, and error recovery before outputting the final implementation)

```text
You are a Principal Database Infrastructure Engineer specializing in Python, PostgreSQL, and high-reliability distributed systems.

Task:
Implement the production-grade PostgreSQL data access layer for a note-taking service.

Context:
- High-concurrency Docker environment. Must use `psycopg2.pool.ThreadedConnectionPool`.
- Reads `DATABASE_URL` from environment.
- Table: `notes(id SERIAL PRIMARY KEY, text TEXT NOT NULL)`.

Step-by-Step Decomposition:
Follow these sequential execution steps in your generation:
Step 1: Define domain types and layered exceptions (`RepositoryError`, `NoteNotFoundError`, `DatabaseConnectionError`).
Step 2: Implement a robust, thread-safe connection pool manager with explicit health check and shutdown hooks (`closeall`).
Step 3: Implement an atomic transaction context manager that automatically issues `conn.commit()` on success and `conn.rollback()` on exception before returning the connection to the pool.
Step 4: Implement `PostgresNoteRepository` satisfying `NoteRepositoryInterface` covering:
  - `create(text: str) -> NoteEntity` (validates non-empty input)
  - `get_all() -> list[NoteEntity]`
  - `delete(note_id: int) -> bool` (verifies deletion via cursor.rowcount)
Step 5: Provide a quick verification snippet demonstrating clean initialization and rollback behavior.

Output Structure:
Precede each step with a clear `## Step X: [Name]` header. Provide full executable Python code with complete type annotations and docstrings. No conversational filler.
```

#### Representative Output Excerpt
```python
## Step 2: Thread-Safe Pool & Transactional Context
class DatabasePool:
    def __init__(self, minconn: int = 2, maxconn: int = 10):
        url = os.getenv("DATABASE_URL")
        if not url:
            raise DatabaseConnectionError("DATABASE_URL environment variable is missing")
        self._pool = pool.ThreadedConnectionPool(minconn, maxconn, dsn=url)

    @contextmanager
    def transaction(self) -> Generator:
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def close(self) -> None:
        self._pool.closeall()
```

#### Observed Output Differences (Prompt vs. Output Note)
* **What changed in prompt**: Enforced a 5-step decomposition pipeline requiring explicit transaction atomicity (`commit` on exit, `rollback` on exception) and connection pool lifecycle shutdown.
* **Observed difference in output**: This produced the most architecturally sound code of any iteration. The model decoupled the transactional cursor manager from the domain repository methods. If a SQL constraint or network blip occurs, `conn.rollback()` is guaranteed to execute before the connection returns to the pool, preventing dirty connection states from poisoning subsequent queries.

---

## 3. Cross-Model Comparison: Claude vs. ChatGPT

We executed the final Step-Decomposed prompt on both **Claude 3.7 Sonnet** and **ChatGPT (GPT-4o)**. Here is the objective, granular comparison:

| Evaluation Dimension | Claude 3.7 Sonnet | ChatGPT (GPT-4o) | Advantage / Takeaway |
| :--- | :--- | :--- | :--- |
| **1. Tone & Persona** | Pragmatic, engineering-focused, zero fluff. Directly opened with code and architectural docstrings. | Polite and slightly conversational; added a friendly 2-sentence intro and concluding "Next Steps" tips. | **Claude**: Fits automated CI/development pipelines better with zero discursive chatter. |
| **2. Defensive Transaction Management** | Used `ThreadedConnectionPool` and separated the transaction block into a nested context manager with explicit `rollback()` and re-raise. Also handled `psycopg2.InterfaceError`. | Implemented `commit()` and `rollback()` cleanly, but caught generic `Exception` rather than isolating database-specific driver exceptions. | **Claude**: Superior defensive rigor and database-specific exception taxonomy. |
| **3. Type Purity & Structural Adherence** | Followed the 5 requested step headers exactly (`## Step 1` to `## Step 5`). Used modern `list[NoteEntity]` and `Generator[psycopg2.extensions.cursor, None, None]`. | Followed step structure well, but imported `typing.List` instead of built-in generics, and used looser type annotations on context managers. | **Claude**: Modern Python 3.10+ typing precision. |
| **4. Edge Cases & Subtleties** | In `delete()`, explicitly checked `cur.rowcount > 0` and correctly returned a boolean status. Also added an empty string guard on `create()`. | Implemented `delete()`, but assumed success without checking `rowcount`, returning `True` even if the targeted note ID did not exist in the table. | **Claude**: Handled silent failure modes accurately without prompting. |

---

## 4. The Final Reusable Prompt Template

This prompt template has been generalized so any backend engineer or teammate can use it for database services without needing your personal context:

```text
Act as a Principal Infrastructure and Backend Engineer. 

Task:
Implement a robust, production-grade database repository layer for {SERVICE_NAME} adhering to Clean Architecture principles.

Context & Constraints:
- Language & Driver: Python with {DATABASE_DRIVER, e.g., psycopg2 / asyncpg}
- Concurrency & Environment: Multi-worker service deployed via Docker. Must manage connection limits using {POOL_TYPE, e.g., ThreadedConnectionPool}.
- Environment Configuration: Read connection parameters from `{ENV_VAR_NAME}`.
- Data Schema:
{TABLE_SCHEMA}

Execution Steps (Chain-of-Thought Decomposition):
1. Domain Layer: Define frozen domain dataclasses and custom domain exceptions ({DOMAIN_EXCEPTIONS}).
2. Storage Abstraction: Define an abstract repository interface ({INTERFACE_NAME}) with typed method contracts.
3. Connection & Transaction Safety: Implement a connection pool manager providing a context manager that ensures:
   - Safe connection acquisition and check-in back to the pool under all conditions.
   - Atomic transactions (`commit()` on success, `rollback()` on any failure).
   - Graceful pool shutdown method.
4. Concrete Implementation: Implement {CONCRETE_REPO_NAME} covering:
{REQUIRED_METHODS_LIST}
   - Validate inputs before database calls.
   - Verify affected row counts for mutations.
   - Wrap low-level driver errors into domain exceptions.

Output Requirements:
- Organize output into sequential markdown sections matching the execution steps.
- Provide complete, fully implemented Python code with full type hints and docstrings.
- Suppress conversational intros, installation tutorials, and placeholders.
```

---

## 5. Pass / Revise Self-Audit Checklist

- [x] **Five+ iterations beyond naive baseline**: Documented completely across 6 total stages (Rung 0 baseline + Rungs 1 to 5).
- [x] **Each iteration tied to a named technique**:
  - Iteration 1: *Role Assignment*
  - Iteration 2: *Context and Motivation*
  - Iteration 3: *Few-Shot Examples*
  - Iteration 4: *Output Structure*
  - Iteration 5: *Step Decomposition*
- [x] **Notes explain observed output differences**: Every rung details what concrete code changes occurred in the LLM's response (e.g. elimination of SQL injection, addition of connection pool context managers, transaction rollback handling), not just what was added to the prompt.
- [x] **Cross-model comparison is specific and honest**: Thoroughly compares Claude vs ChatGPT across 4 technical dimensions (tone, defensive transactions, typing purity, edge-case rowcount handling).
- [x] **Final template is reusable**: Modular `{TEMPLATE_VARIABLES}` allowing any team member to adapt it to their own microservices.
- [x] **Work is on a real task from FL-01**: Directly models our FlyRank backend note-taking database infrastructure.
