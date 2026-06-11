from repo_brain.parsers.node import (
    is_test_file,
    parse_imports,
    parse_routes,
    parse_symbols,
    parse_tests,
)

ES_MODULE = """
import express from 'express'
import { Router, Request, Response } from 'express'
import * as utils from './utils'
import type { User } from './types'
import './side-effect'

const router = Router()

export class UserController {
  getUser() {}
}

export async function createUser(req, res) {
  return res.json({})
}

const listUsers = (req, res) => {
  return res.json([])
}

const deleteUser = async (req, res) => {
  return res.json({})
}

router.get('/users', listUsers)
router.post('/users', createUser)
router.put('/users/:id', (req, res) => {})
router.delete('/users/:id', deleteUser)
"""

COMMONJS = """
const express = require('express')
const { Router } = require('express')
const path = require('path')

const app = express()

app.get('/health', (req, res) => res.json({ ok: true }))
app.post('/upload', uploadHandler)
"""

TEST_FILE = """
describe('UserController', () => {
  it('should return a user', async () => {
    expect(true).toBe(true)
  })

  test('should create a user', () => {
    expect(1).toBe(1)
  })
})
"""


# ---------------------------------------------------------------------------
# is_test_file
# ---------------------------------------------------------------------------

def test_is_test_file_spec_js():
    assert is_test_file("src/user.spec.js") is True

def test_is_test_file_test_ts():
    assert is_test_file("src/user.test.ts") is True

def test_is_not_test_file():
    assert is_test_file("src/user.js") is False
    assert is_test_file("src/router.ts") is False


# ---------------------------------------------------------------------------
# parse_imports — ES modules
# ---------------------------------------------------------------------------

def test_es_default_import():
    imports = parse_imports("app.ts", ES_MODULE)
    assert any(i.module == "express" and i.name == "express" for i in imports)

def test_es_named_imports():
    imports = parse_imports("app.ts", ES_MODULE)
    assert any(i.module == "express" and i.name == "Router" for i in imports)
    assert any(i.module == "express" and i.name == "Request" for i in imports)

def test_es_star_import():
    imports = parse_imports("app.ts", ES_MODULE)
    assert any(i.module == "./utils" and i.alias == "utils" for i in imports)

def test_es_side_effect_import():
    imports = parse_imports("app.ts", ES_MODULE)
    assert any(i.module == "./side-effect" for i in imports)

def test_commonjs_require():
    imports = parse_imports("app.js", COMMONJS)
    assert any(i.module == "express" and i.name == "express" for i in imports)

def test_commonjs_destructure():
    imports = parse_imports("app.js", COMMONJS)
    assert any(i.module == "express" and i.name == "Router" for i in imports)


# ---------------------------------------------------------------------------
# parse_symbols
# ---------------------------------------------------------------------------

def test_detects_class():
    symbols = parse_symbols("app.ts", ES_MODULE)
    assert any(s.name == "UserController" and s.symbol_type == "class" for s in symbols)

def test_detects_async_function():
    symbols = parse_symbols("app.ts", ES_MODULE)
    assert any(s.name == "createUser" and s.symbol_type == "async_function" for s in symbols)

def test_detects_arrow_function():
    symbols = parse_symbols("app.ts", ES_MODULE)
    assert any(s.name == "listUsers" and s.symbol_type == "arrow_function" for s in symbols)

def test_detects_async_arrow():
    symbols = parse_symbols("app.ts", ES_MODULE)
    assert any(s.name == "deleteUser" and s.symbol_type == "async_arrow_function" for s in symbols)


# ---------------------------------------------------------------------------
# parse_routes
# ---------------------------------------------------------------------------

def test_router_get():
    routes = parse_routes("router.ts", ES_MODULE)
    assert any(r.method == "get" and r.path == "/users" for r in routes)

def test_router_post():
    routes = parse_routes("router.ts", ES_MODULE)
    assert any(r.method == "post" and r.path == "/users" for r in routes)

def test_router_put_with_param():
    routes = parse_routes("router.ts", ES_MODULE)
    assert any(r.method == "put" and r.path == "/users/:id" for r in routes)

def test_app_get_commonjs():
    routes = parse_routes("app.js", COMMONJS)
    assert any(r.method == "get" and r.path == "/health" for r in routes)

def test_app_post_commonjs():
    routes = parse_routes("app.js", COMMONJS)
    assert any(r.method == "post" and r.path == "/upload" for r in routes)

def test_no_routes_in_plain_file():
    routes = parse_routes("utils.js", "export const add = (a, b) => a + b")
    assert routes == []


# ---------------------------------------------------------------------------
# parse_tests
# ---------------------------------------------------------------------------

def test_detects_describe_block():
    info = parse_tests("user.test.ts", TEST_FILE)
    assert "UserController" in info.test_classes

def test_detects_it_block():
    info = parse_tests("user.test.ts", TEST_FILE)
    assert any("should return a user" in fn for fn in info.test_functions)

def test_detects_test_block():
    info = parse_tests("user.test.ts", TEST_FILE)
    assert any("should create a user" in fn for fn in info.test_functions)