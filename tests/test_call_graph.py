"""Tests for call graph extraction across all three language parsers."""
from repo_brain.parsers.python_ast import parse_calls as py_parse_calls
from repo_brain.parsers.node import parse_calls as node_parse_calls, parse_fetch_calls
from repo_brain.parsers.go import parse_calls as go_parse_calls

# ---------------------------------------------------------------------------
# Python call graph
# ---------------------------------------------------------------------------

PY_SOURCE = """
def helper():
    pass

def process_user(user_id):
    data = helper()
    return validate(data)

class UserService:
    def get(self, uid):
        return fetch_user(uid)
"""

def test_py_detects_call_in_function():
    calls = py_parse_calls("app.py", PY_SOURCE)
    callee_names = [c.callee_name for c in calls]
    assert "helper" in callee_names
    assert "validate" in callee_names

def test_py_caller_name_tracked():
    calls = py_parse_calls("app.py", PY_SOURCE)
    process_calls = [c for c in calls if c.caller_name == "process_user"]
    assert any(c.callee_name == "helper" for c in process_calls)

def test_py_method_calls_tracked():
    calls = py_parse_calls("app.py", PY_SOURCE)
    assert any(c.callee_name == "fetch_user" for c in calls)

def test_py_file_path_set():
    calls = py_parse_calls("app/users.py", PY_SOURCE)
    assert all(c.caller_file == "app/users.py" for c in calls)

def test_py_lineno_positive():
    calls = py_parse_calls("app.py", PY_SOURCE)
    assert all(c.lineno > 0 for c in calls)

def test_py_empty_source():
    assert py_parse_calls("app.py", "") == []

def test_py_syntax_error_returns_empty():
    assert py_parse_calls("app.py", "def broken(:\n    pass") == []


# ---------------------------------------------------------------------------
# Node.js call graph
# ---------------------------------------------------------------------------

NODE_SOURCE = """
function validateUser(user) {
    return checkEmail(user.email)
}

const processRequest = async (req, res) => {
    const user = await fetchUser(req.params.id)
    validateUser(user)
}
"""

def test_node_detects_function_call():
    calls = node_parse_calls("app.ts", NODE_SOURCE)
    callees = [c.callee_name for c in calls]
    assert "checkEmail" in callees or "validateUser" in callees

def test_node_caller_file_set():
    calls = node_parse_calls("src/app.ts", NODE_SOURCE)
    assert all(c.caller_file == "src/app.ts" for c in calls)


# ---------------------------------------------------------------------------
# fetch call detection (route linking)
# ---------------------------------------------------------------------------

FETCH_SOURCE = """
async function loadUser(id) {
    const res = await fetch('/api/users/' + id)
    return res.json()
}

function createDoc(data) {
    return axios.post('/api/documents', data)
}
"""

def test_fetch_call_detected():
    links = parse_fetch_calls("frontend/app.ts", FETCH_SOURCE)
    patterns = [l.pattern for l in links]
    assert "/api/users/" in patterns or any("/api/users" in p for p in patterns)

def test_axios_post_detected():
    links = parse_fetch_calls("frontend/app.ts", FETCH_SOURCE)
    post_links = [l for l in links if l.method == "post"]
    assert any("/api/documents" in l.pattern for l in post_links)

def test_fetch_link_has_frontend_file():
    links = parse_fetch_calls("src/client.ts", FETCH_SOURCE)
    assert all(l.frontend_file == "src/client.ts" for l in links)


# ---------------------------------------------------------------------------
# Go call graph
# ---------------------------------------------------------------------------

GO_SOURCE = """
package main

func processOrder(id int) {
    order := fetchOrder(id)
    validateOrder(order)
}

func fetchOrder(id int) Order {
    return db.Find(id)
}
"""

def test_go_detects_call():
    calls = go_parse_calls("main.go", GO_SOURCE)
    callees = [c.callee_name for c in calls]
    assert "fetchOrder" in callees or "validateOrder" in callees

def test_go_caller_file_set():
    calls = go_parse_calls("cmd/main.go", GO_SOURCE)
    assert all(c.caller_file == "cmd/main.go" for c in calls)
