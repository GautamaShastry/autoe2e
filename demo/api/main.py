"""Demo FastAPI application for E2E testing."""

import os
from contextlib import asynccontextmanager
from typing import Any

import psycopg2
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# Database connection
def get_db_connection():
    return psycopg2.connect(os.environ.get(
        "DATABASE_URL",
        "postgresql://demo:demo@localhost:5432/demo"
    ))


# Redis connection
def get_redis_client():
    return redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    yield


app = FastAPI(title="Demo API", lifespan=lifespan)


class ItemCreate(BaseModel):
    name: str
    description: str | None = None


class Item(BaseModel):
    id: int
    name: str
    description: str | None = None


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/ready")
def readiness_check() -> dict[str, Any]:
    """Readiness check - verifies DB and Redis connections."""
    status = {"db": "unknown", "redis": "unknown"}

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        status["db"] = "connected"
    except Exception as e:
        status["db"] = f"error: {str(e)}"

    try:
        r = get_redis_client()
        r.ping()
        status["redis"] = "connected"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

    all_ok = status["db"] == "connected" and status["redis"] == "connected"
    return {"ready": all_ok, "services": status}


@app.post("/items", response_model=Item, status_code=201)
def create_item(item: ItemCreate) -> Item:
    """Create a new item."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO items (name, description) VALUES (%s, %s) RETURNING id",
        (item.name, item.description)
    )
    item_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    # Cache in Redis
    r = get_redis_client()
    r.set(f"item:{item_id}", item.name, ex=3600)

    return Item(id=item_id, name=item.name, description=item.description)


@app.get("/items", response_model=list[Item])
def list_items() -> list[Item]:
    """List all items."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description FROM items ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [Item(id=r[0], name=r[1], description=r[2]) for r in rows]


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    """Get a single item by ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description FROM items WHERE id = %s", (item_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    return Item(id=row[0], name=row[1], description=row[2])


@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: ItemCreate) -> Item:
    """Update an existing item."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE items SET name = %s, description = %s WHERE id = %s RETURNING id",
        (item.name, item.description, item_id)
    )
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Item not found")

    # Update cache
    r = get_redis_client()
    r.set(f"item:{item_id}", item.name, ex=3600)

    return Item(id=item_id, name=item.name, description=item.description)


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int) -> None:
    """Delete an item."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE id = %s RETURNING id", (item_id,))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Item not found")

    # Remove from cache
    r = get_redis_client()
    r.delete(f"item:{item_id}")
