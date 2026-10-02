"""
Assignment 1 Reference: In-Memory CRUD API (Before SQLite Migration)
Used to compare against our SQLite implementation and prove that the API layer
remains identical when swapping the storage layer from memory to SQLite.
"""

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(title="Task CRUD API (A1 In-Memory Reference)")

tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Learn SQLite fundamentals", "done": False},
    {"id": 3, "title": "Connect CRUD API to database", "done": False},
]
next_id = 4


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})


@app.get("/tasks")
def get_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return JSONResponse(status_code=404, content={"error": "Task not found"})


@app.post("/tasks", status_code=201)
async def create_task(request: Request):
    global next_id
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})

    done = body.get("done", False)
    if not isinstance(done, bool):
        return JSONResponse(status_code=400, content={"error": "Field 'done' must be a boolean"})

    new_task = {"id": next_id, "title": title.strip(), "done": done}
    next_id += 1
    tasks.append(new_task)
    return JSONResponse(status_code=201, content=new_task)


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    target = None
    for task in tasks:
        if task["id"] == task_id:
            target = task
            break

    if target is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})

    title = body.get("title", target["title"])
    done = body.get("done", target["done"])

    if not isinstance(title, str) or not title.strip():
        return JSONResponse(status_code=400, content={"error": "Title must be a non-empty string"})
    if not isinstance(done, bool):
        return JSONResponse(status_code=400, content={"error": "Field 'done' must be a boolean"})

    target["title"] = title.strip()
    target["done"] = done
    return target


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return Response(status_code=204)
    return JSONResponse(status_code=404, content={"error": "Task not found"})
