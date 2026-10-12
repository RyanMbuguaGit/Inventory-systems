import copy
from unittest.mock import MagicMock, patch

import pytest
import requests

import app as app_module


@pytest.fixture
def client():
    original = copy.deepcopy(app_module.inventory)
    app_module.app.config["TESTING"] = True
    yield app_module.app.test_client()
    app_module.inventory[:] = original


def mock_response(json_data, status=200):
    m = MagicMock()
    m.json.return_value = json_data
    m.status_code = status
    m.raise_for_status.return_value = None
    return m


def test_get_all(client):
    r = client.get("/inventory")
    assert r.status_code == 200 and len(r.get_json()) >= 3


def test_get_one_and_404(client):
    assert client.get("/inventory/1").status_code == 200
    assert client.get("/inventory/999").status_code == 404


def test_post_valid_and_invalid(client):
    r = client.post("/inventory", json={"product_name": "Tea", "price": 2, "stock": 5})
    assert r.status_code == 201 and "id" in r.get_json()
    assert client.post("/inventory", json={"price": 2}).status_code == 400
    assert client.post("/inventory", json={"product_name": "X", "price": "abc"}).status_code == 400


def test_patch(client):
    r = client.patch("/inventory/1", json={"price": 9.99, "stock": 3})
    assert r.get_json()["price"] == 9.99 and r.get_json()["stock"] == 3
    assert client.patch("/inventory/999", json={"price": 1}).status_code == 404
    assert client.patch("/inventory/1", json={"stock": -5}).status_code == 400


def test_delete(client):
    assert client.delete("/inventory/1").status_code == 200
    assert client.get("/inventory/1").status_code == 404
    assert client.delete("/inventory/1").status_code == 404


@patch("app.requests.get")
def test_external_barcode(mock_get, client):
    mock_get.return_value = mock_response(
        {"status": 1, "product": {"product_name": "Silk", "brands": "Silk", "ingredients_text": "water"}})
    r = client.get("/external/search?barcode=123")
    assert r.status_code == 200 and r.get_json()["product_name"] == "Silk"


@patch("app.requests.get")
def test_external_not_found(mock_get, client):
    mock_get.return_value = mock_response({"status": 0})
    assert client.get("/external/search?barcode=000").status_code == 404


@patch("app.requests.get")
def test_external_failure(mock_get, client):
    mock_get.side_effect = requests.ConnectionError("down")
    assert client.get("/external/search?name=milk").status_code == 502


def test_external_missing_params(client):
    assert client.get("/external/search").status_code == 400


@patch("app.requests.get")
def test_enrich(mock_get, client):
    mock_get.return_value = mock_response(
        {"status": 1, "product": {"product_name": "Nutella", "brands": "NewBrand", "ingredients_text": "new"}})
    r = client.post("/inventory/1/enrich")
    assert r.status_code == 200 and r.get_json()["brands"] == "NewBrand"