"""B-706 – Safe Error Handling tests."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.middleware.error_handler import global_exception_handler, http_exception_handler


def _build_test_app() -> FastAPI:
    """Build an app with a route that raises an unhandled exception."""
    test_app = FastAPI()

    app_exception_handler = global_exception_handler
    app_http_handler = http_exception_handler

    test_app.add_exception_handler(HTTPException, app_http_handler)
    test_app.add_exception_handler(Exception, app_exception_handler)

    @test_app.get("/v1/crash")
    def crash():
        raise RuntimeError("Database connection refused at /var/run/postgres.sock")

    @test_app.get("/v1/http-error")
    def http_error():
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Resource missing"})

    @test_app.get("/v1/ok")
    def ok():
        return {"status": "ok"}

    return test_app


class TestUnhandledExceptionReturnsSafe500:
    def test_unhandled_exception_returns_safe_500(self):
        app = _build_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/crash")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert body["error"]["message"] == "An unexpected error occurred"


class TestNoStackTraceInResponse:
    def test_no_stack_trace_in_response(self):
        app = _build_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/crash")
        text = resp.text
        assert "Traceback" not in text
        assert "RuntimeError" not in text
        assert "postgres.sock" not in text
        assert "/var/run" not in text

    def test_no_file_paths_in_response(self):
        app = _build_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/crash")
        text = resp.text
        assert ".py" not in text
        assert "backend/" not in text


class TestValidationErrorStructured:
    def test_validation_error_structured(self):
        """The main app's validation handler returns structured 422."""
        from app.config import get_settings

        from app.main import app as main_app

        settings = get_settings()
        main_app.dependency_overrides[get_settings] = lambda: settings

        client = TestClient(main_app)
        resp = client.post("/v1/query", json={"employee_id": "", "question": "dental"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"


class TestHTTPExceptionStructured:
    def test_http_exception_passes_through(self):
        app = _build_test_app()
        client = TestClient(app)
        resp = client.get("/v1/http-error")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"
