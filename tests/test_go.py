from repo_brain.parsers.go import (
    is_test_file,
    parse_imports,
    parse_routes,
    parse_symbols,
    parse_tests,
)

GO_SOURCE = '''
package main

import (
    "fmt"
    "net/http"
    "github.com/gin-gonic/gin"
    log "github.com/sirupsen/logrus"
)

type UserService struct {
    db *DB
}

type Repository interface {
    FindByID(id int) (*User, error)
}

func NewUserService(db *DB) *UserService {
    return &UserService{db: db}
}

func (s *UserService) GetUser(id int) (*User, error) {
    return s.db.Find(id)
}

func HealthCheck(c *gin.Context) {
    c.JSON(200, gin.H{"status": "ok"})
}
'''

GIN_ROUTES = '''
package main

import "github.com/gin-gonic/gin"

func setupRouter() *gin.Engine {
    r := gin.Default()
    r.GET("/users", listUsers)
    r.POST("/users", createUser)
    r.PUT("/users/:id", updateUser)
    r.DELETE("/users/:id", deleteUser)
    return r
}
'''

CHI_ROUTES = '''
package main

import "github.com/go-chi/chi/v5"

func main() {
    r := chi.NewRouter()
    r.Get("/documents", listDocuments)
    r.Post("/documents/upload", uploadDocument)
}
'''

HTTP_ROUTES = '''
package main

import "net/http"

func main() {
    http.HandleFunc("/health", healthHandler)
    http.HandleFunc("/api/users", usersHandler)
}
'''

TEST_FILE = '''
package user_test

import "testing"

func TestGetUser(t *testing.T) {
    t.Run("returns user", func(t *testing.T) {})
}

func TestCreateUser(t *testing.T) {}

func BenchmarkGetUser(b *testing.B) {}
'''

SINGLE_IMPORT = '''
package main

import "fmt"
import "os"

func main() {}
'''


# ---------------------------------------------------------------------------
# is_test_file
# ---------------------------------------------------------------------------

def test_is_test_file():
    assert is_test_file("service/user_test.go") is True

def test_is_not_test_file():
    assert is_test_file("service/user.go") is False
    assert is_test_file("main.go") is False


# ---------------------------------------------------------------------------
# parse_imports
# ---------------------------------------------------------------------------

def test_group_import_stdlib():
    imports = parse_imports("main.go", GO_SOURCE)
    assert any(i.module == "fmt" for i in imports)
    assert any(i.module == "net/http" for i in imports)

def test_group_import_external():
    imports = parse_imports("main.go", GO_SOURCE)
    assert any(i.module == "github.com/gin-gonic/gin" for i in imports)

def test_group_import_with_alias():
    imports = parse_imports("main.go", GO_SOURCE)
    assert any(i.module == "github.com/sirupsen/logrus" and i.alias == "log" for i in imports)

def test_single_import():
    imports = parse_imports("main.go", SINGLE_IMPORT)
    assert any(i.module == "fmt" for i in imports)
    assert any(i.module == "os" for i in imports)


# ---------------------------------------------------------------------------
# parse_symbols
# ---------------------------------------------------------------------------

def test_detects_struct():
    symbols = parse_symbols("main.go", GO_SOURCE)
    assert any(s.name == "UserService" and s.symbol_type == "struct" for s in symbols)

def test_detects_interface():
    symbols = parse_symbols("main.go", GO_SOURCE)
    assert any(s.name == "Repository" and s.symbol_type == "interface" for s in symbols)

def test_detects_function():
    symbols = parse_symbols("main.go", GO_SOURCE)
    assert any(s.name == "NewUserService" and s.symbol_type == "function" for s in symbols)

def test_detects_method():
    symbols = parse_symbols("main.go", GO_SOURCE)
    assert any(s.name == "GetUser" and s.symbol_type == "function" for s in symbols)

def test_detects_handler_function():
    symbols = parse_symbols("main.go", GO_SOURCE)
    assert any(s.name == "HealthCheck" for s in symbols)


# ---------------------------------------------------------------------------
# parse_routes
# ---------------------------------------------------------------------------

def test_gin_get_route():
    routes = parse_routes("router.go", GIN_ROUTES)
    assert any(r.method == "get" and r.path == "/users" for r in routes)

def test_gin_post_route():
    routes = parse_routes("router.go", GIN_ROUTES)
    assert any(r.method == "post" and r.path == "/users" for r in routes)

def test_gin_put_with_param():
    routes = parse_routes("router.go", GIN_ROUTES)
    assert any(r.method == "put" and r.path == "/users/:id" for r in routes)

def test_gin_delete_route():
    routes = parse_routes("router.go", GIN_ROUTES)
    assert any(r.method == "delete" and r.path == "/users/:id" for r in routes)

def test_chi_get_route():
    routes = parse_routes("router.go", CHI_ROUTES)
    assert any(r.method == "get" and r.path == "/documents" for r in routes)

def test_chi_post_route():
    routes = parse_routes("router.go", CHI_ROUTES)
    assert any(r.method == "post" and r.path == "/documents/upload" for r in routes)

def test_net_http_handlefunc():
    routes = parse_routes("main.go", HTTP_ROUTES)
    assert any(r.path == "/health" for r in routes)
    assert any(r.path == "/api/users" for r in routes)

def test_no_routes_plain_file():
    routes = parse_routes("service.go", GO_SOURCE)
    assert routes == []


# ---------------------------------------------------------------------------
# parse_tests
# ---------------------------------------------------------------------------

def test_detects_test_functions():
    info = parse_tests("user_test.go", TEST_FILE)
    assert "TestGetUser" in info.test_functions
    assert "TestCreateUser" in info.test_functions

def test_detects_benchmark():
    info = parse_tests("user_test.go", TEST_FILE)
    assert "BenchmarkGetUser" in info.test_functions

def test_no_test_classes_in_go():
    info = parse_tests("user_test.go", TEST_FILE)
    assert info.test_classes == []