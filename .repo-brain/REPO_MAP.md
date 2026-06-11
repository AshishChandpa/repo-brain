# Repository Map

## Summary

- Python files: 27
- Classes: 12
- Functions: 240
- FastAPI routes: 0
- Test files: 9

## Top-level Modules

- `src`
- `tests`

## FastAPI Routes

| Method | Path | Handler | File |
|--------|------|---------|------|

## Important Files

- `src/repo_brain/__init__.py` (1 lines)
- `src/repo_brain/cli.py` (449 lines)
- `src/repo_brain/config.py` (53 lines)
- `src/repo_brain/context.py` (174 lines)
- `src/repo_brain/impact.py` (140 lines)
- `src/repo_brain/mcp_server.py` (250 lines)
- `src/repo_brain/models.py` (93 lines)
- `src/repo_brain/parsers/__init__.py` (1 lines)
- `src/repo_brain/parsers/fastapi.py` (59 lines)
- `src/repo_brain/parsers/go.py` (142 lines)
- `src/repo_brain/parsers/node.py` (158 lines)
- `src/repo_brain/parsers/pytest.py` (42 lines)
- `src/repo_brain/parsers/python_ast.py` (93 lines)
- `src/repo_brain/scanner.py` (148 lines)
- `src/repo_brain/writers/__init__.py` (1 lines)
- `src/repo_brain/writers/json_writer.py` (25 lines)
- `src/repo_brain/writers/markdown_writer.py` (60 lines)
- `tests/__init__.py` (1 lines)

## Tests

### `tests/test_context.py`

- `test_keywords_lowercased`
- `test_keywords_removes_stopwords`
- `test_keywords_splits_camelcase`
- `test_keywords_splits_underscores`
- `test_keywords_deduplicates`
- `test_keywords_empty_task`
- `test_keywords_all_stopwords`
- `test_tokenize_root_route`
- `test_tokenize_route_with_path_param`
- `test_tokenize_route_with_dotted_param`
- `test_tokenize_file_path_strips_py`
- `test_tokenize_camelcase`
- `test_tokenize_empty_string`
- `test_tokenize_plain_function_name`
- `test_score_files_matches_relevant`
- `test_score_files_excludes_unrelated`
- `test_score_files_sorted_by_score`
- `test_score_files_score_positive`
- `test_score_symbols_matches_name`
- `test_score_symbols_excludes_unrelated`
- `test_score_symbols_sorted_descending`
- `test_match_routes_by_path`
- `test_match_routes_by_function`
- `test_match_routes_excludes_unrelated`
- `test_match_routes_root_path_does_not_crash`
- `test_match_routes_path_param_does_not_crash`
- `test_match_tests_by_filename`
- `test_match_tests_by_function_name`
- `test_match_tests_excludes_unrelated`
- `test_match_tests_sorted`
- `test_build_context_returns_keywords`
- `test_build_context_suggests_relevant_files`
- `test_build_context_suggests_relevant_symbols`
- `test_build_context_suggests_routes`
- `test_build_context_suggests_tests`
- `test_build_context_empty_task`
- `test_build_context_caps_files_at_ten`
- `test_build_context_caps_symbols_at_ten`

### `tests/test_fastapi_routes.py`

- `test_app_get_route`
- `test_app_post_route`
- `test_app_put_route`
- `test_app_delete_route`
- `test_router_get`
- `test_router_post`
- `test_no_routes`
- `test_dynamic_path_skipped`
- `test_syntax_error_returns_empty`

### `tests/test_go.py`

- `test_is_test_file`
- `test_is_not_test_file`
- `test_group_import_stdlib`
- `test_group_import_external`
- `test_group_import_with_alias`
- `test_single_import`
- `test_detects_struct`
- `test_detects_interface`
- `test_detects_function`
- `test_detects_method`
- `test_detects_handler_function`
- `test_gin_get_route`
- `test_gin_post_route`
- `test_gin_put_with_param`
- `test_gin_delete_route`
- `test_chi_get_route`
- `test_chi_post_route`
- `test_net_http_handlefunc`
- `test_no_routes_plain_file`
- `test_detects_test_functions`
- `test_detects_benchmark`
- `test_no_test_classes_in_go`

### `tests/test_impact.py`

- `test_module_path_simple`
- `test_module_path_init`
- `test_module_path_root`
- `test_module_path_non_py`
- `test_module_variants`
- `test_module_variants_init`
- `test_symbols_in_target`
- `test_routes_in_target`
- `test_imported_by_finds_importers`
- `test_imported_by_excludes_target_itself`
- `test_imported_by_excludes_unrelated`
- `test_related_tests_by_import`
- `test_related_tests_by_name_heuristic`
- `test_unrelated_tests_excluded`
- `test_likely_affected_union`
- `test_likely_affected_excludes_target`
- `test_likely_affected_is_sorted`
- `test_no_importers`
- `test_no_symbols_in_file`
- `test_module_path_in_result`

### `tests/test_mcp_server.py`

- `test_six_tools_defined`
- `test_tool_names`
- `test_all_tools_have_description`
- `test_all_tools_have_input_schema`
- `test_status_returns_file_count`
- `test_status_returns_project_name`
- `test_status_returns_modules`
- `test_status_returns_routes_count`
- `test_status_missing_index`
- `test_search_symbol_finds_class`
- `test_search_symbol_case_insensitive`
- `test_search_symbol_substring`
- `test_search_symbol_type_filter`
- `test_search_symbol_no_match`
- `test_search_symbol_includes_file_and_line`
- `test_related_files_finds_test`
- `test_related_files_finds_importer`
- `test_related_files_likely_affected_union`
- `test_related_files_excludes_self`
- `test_impact_returns_symbols`
- `test_impact_returns_routes`
- `test_impact_has_all_keys`
- `test_tests_returns_all_when_no_file`
- `test_tests_filtered_by_file`
- `test_tests_includes_functions`
- `test_task_context_returns_keywords`
- `test_task_context_suggests_files`
- `test_task_context_suggests_routes`
- `test_task_context_has_all_keys`
- `test_make_server_returns_server`
- `test_make_server_name`

### `tests/test_node.py`

- `test_is_test_file_spec_js`
- `test_is_test_file_test_ts`
- `test_is_not_test_file`
- `test_es_default_import`
- `test_es_named_imports`
- `test_es_star_import`
- `test_es_side_effect_import`
- `test_commonjs_require`
- `test_commonjs_destructure`
- `test_detects_class`
- `test_detects_async_function`
- `test_detects_arrow_function`
- `test_detects_async_arrow`
- `test_router_get`
- `test_router_post`
- `test_router_put_with_param`
- `test_app_get_commonjs`
- `test_app_post_commonjs`
- `test_no_routes_in_plain_file`
- `test_detects_describe_block`
- `test_detects_it_block`
- `test_detects_test_block`

### `tests/test_pytest_detection.py`

- `test_is_test_file_prefix`
- `test_is_test_file_suffix`
- `test_is_not_test_file`
- `test_detects_test_functions`
- `test_detects_test_class`
- `test_detects_methods_in_test_class`
- `test_ignores_helper_function`
- `test_ignores_non_test_class`
- `test_syntax_error_returns_empty`

### `tests/test_python_ast.py`

- `test_imports_absolute`
- `test_imports_relative`
- `test_symbols_class`
- `test_symbols_methods`
- `test_symbols_async_method`
- `test_symbols_top_level_function`
- `test_symbols_async_top_level`
- `test_syntax_error_returns_empty`

### `tests/test_scanner.py`

- `test_scan_finds_py_files`
- `test_scan_marks_test_files`
- `test_scan_detects_route`
- `test_scan_detects_class`
- `test_scan_detects_test_function`
- `test_scan_excludes_dirs`
- `test_top_level_modules`

## Notes

This file is generated by repo-brain. Do not manually edit.

Generated at: 2026-06-11T13:11:49.242301+00:00