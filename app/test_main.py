import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db
from models import Base
from schemas import UserCreate

# --- Setup test DB ---
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


# Dependency override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# --- Fixtures ---
@pytest.fixture
def new_user():
    unique_email = f"rocky_{uuid.uuid4().hex[:6]}@example.com"
    return {
        "username": "Rocky",
        "email": unique_email
    }


# --- Tests ---

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Streaming Chatbot API is running!"}


def test_create_user(new_user):
    response = client.post("/users/", json=new_user)
    print("++++++++++++++++++++++++", response)
    assert response.status_code == 200
    assert response.json()["email"] == new_user["email"]
    assert "id" in response.json()


def test_create_conversation(new_user):
    # Create user
    user_resp = client.post("/users/", json=new_user)
    user_id = user_resp.json()["id"]

    # Create conversation
    response = client.post(f"/users/{user_id}/conversations/", json={"title": "Test Chat"})
    assert response.status_code == 200
    assert response.json()["title"] == "Test Chat"


def test_get_user_conversations(new_user):
    user_resp = client.post("/users/", json=new_user)
    print(user_resp.json())
    user_id = user_resp.json()["id"]

    # Create two conversations
    client.post(f"/users/{user_id}/conversations/", json={"title": "Conv1"})
    client.post(f"/users/{user_id}/conversations/", json={"title": "Conv2"})

    response = client.get(f"/users/{user_id}/conversations/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_regular_chat(new_user):
    user_resp = client.post("/users/", json=new_user)
    user_id = user_resp.json()["id"]

    response = client.post(
        f"/chat/{user_id}",
        json={"message": "Hello"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "conversation_id" in data
