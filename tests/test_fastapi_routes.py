from repo_brain.parsers.fastapi import parse_routes

APP_ROUTES = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/users")
def list_users():
    pass

@app.post("/users")
async def create_user():
    pass

@app.put("/users/{user_id}")
def update_user(user_id: int):
    pass

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    pass
"""

ROUTER_ROUTES = """
from fastapi import APIRouter

router = APIRouter()

@router.get("/items/{item_id}")
def get_item(item_id: int):
    pass

@router.post("/compare")
async def compare_items():
    pass
"""

NO_ROUTES = """
def plain_function():
    pass

class SomeClass:
    def method(self):
        pass
"""

DYNAMIC_PATH = """
from fastapi import APIRouter
router = APIRouter()

PREFIX = "/api"

@router.get(PREFIX + "/users")
def dynamic():
    pass
"""


def test_app_get_route():
    routes = parse_routes("app.py", APP_ROUTES)
    assert any(r.method == "get" and r.path == "/users" and r.function_name == "list_users" for r in routes)


def test_app_post_route():
    routes = parse_routes("app.py", APP_ROUTES)
    assert any(r.method == "post" and r.path == "/users" and r.function_name == "create_user" for r in routes)


def test_app_put_route():
    routes = parse_routes("app.py", APP_ROUTES)
    assert any(r.method == "put" and r.path == "/users/{user_id}" for r in routes)


def test_app_delete_route():
    routes = parse_routes("app.py", APP_ROUTES)
    assert any(r.method == "delete" and r.path == "/users/{user_id}" for r in routes)


def test_router_get():
    routes = parse_routes("router.py", ROUTER_ROUTES)
    assert any(r.method == "get" and r.path == "/items/{item_id}" for r in routes)


def test_router_post():
    routes = parse_routes("router.py", ROUTER_ROUTES)
    assert any(r.method == "post" and r.path == "/compare" for r in routes)


def test_no_routes():
    routes = parse_routes("plain.py", NO_ROUTES)
    assert routes == []


def test_dynamic_path_skipped():
    routes = parse_routes("dyn.py", DYNAMIC_PATH)
    assert routes == []


def test_syntax_error_returns_empty():
    assert parse_routes("bad.py", "def (broken:") == []
