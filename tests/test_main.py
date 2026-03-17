import pytest
from app.main import app, items


@pytest.fixture(autouse=True)
def clear_items():
    items.clear()
    yield
    items.clear()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Hello, World!"
    assert data["status"] == "ok"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_get_items_empty(client):
    response = client.get("/items")
    assert response.status_code == 200
    assert response.get_json() == {"items": []}


def test_add_item(client):
    response = client.post("/items", json={"name": "widget"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "widget"
    assert data["id"] == 1


def test_get_items_after_add(client):
    client.post("/items", json={"name": "widget"})
    response = client.get("/items")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "widget"


def test_add_item_missing_name(client):
    response = client.post("/items", json={"foo": "bar"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_add_multiple_items(client):
    client.post("/items", json={"name": "widget"})
    client.post("/items", json={"name": "gadget"})
    response = client.get("/items")
    data = response.get_json()
    assert len(data["items"]) == 2
    assert data["items"][1]["id"] == 2
