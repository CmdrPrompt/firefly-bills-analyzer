"""Tests for FireflyClient — HTTP session and connection validation."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from firefly_python_api import FireflyClient, FireflyConnectionError, load_config


class TestFireflyClientConstruction:
    def test_stores_base_url(self):
        client = FireflyClient(url="https://firefly.example.com", token="tok")
        assert client.url == "https://firefly.example.com"

    def test_strips_trailing_slash_from_url(self):
        client = FireflyClient(url="https://firefly.example.com/", token="tok")
        assert client.url == "https://firefly.example.com"

    def test_session_has_authorization_header(self):
        client = FireflyClient(url="https://firefly.example.com", token="mytoken")
        assert client.session.headers["Authorization"] == "Bearer mytoken"

    def test_session_has_accept_header(self):
        client = FireflyClient(url="https://firefly.example.com", token="tok")
        assert client.session.headers["Accept"] == "application/json"

    def test_session_has_content_type_header(self):
        client = FireflyClient(url="https://firefly.example.com", token="tok")
        assert client.session.headers["Content-Type"] == "application/json"

    def test_session_is_requests_session(self):
        client = FireflyClient(url="https://firefly.example.com", token="tok")
        assert isinstance(client.session, requests.Session)


class TestValidateConnection:
    def _make_client(self) -> FireflyClient:
        return FireflyClient(url="https://firefly.example.com", token="tok")

    def test_returns_true_on_200(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        with patch.object(client.session, "get", return_value=mock_response) as mock_get:
            result = client.validate_connection()
        mock_get.assert_called_once_with("https://firefly.example.com/api/v1/about")
        assert result is True

    def test_raises_on_http_error(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403")
        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(FireflyConnectionError):
                client.validate_connection()

    def test_raises_on_connection_error(self):
        client = self._make_client()
        with patch.object(client.session, "get", side_effect=requests.ConnectionError("refused")):
            with pytest.raises(FireflyConnectionError):
                client.validate_connection()

    def test_raises_on_timeout(self):
        client = self._make_client()
        with patch.object(client.session, "get", side_effect=requests.Timeout("timed out")):
            with pytest.raises(FireflyConnectionError):
                client.validate_connection()

    def test_error_message_contains_url(self):
        client = self._make_client()
        with patch.object(client.session, "get", side_effect=requests.ConnectionError("refused")):
            with pytest.raises(FireflyConnectionError, match="firefly.example.com"):
                client.validate_connection()


class TestLoadConfig:
    def test_reads_from_environment(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("")
        with patch.dict(
            os.environ,
            {"FIREFLY_URL": "https://env.example.com", "FIREFLY_TOKEN": "envtoken"},
        ):
            url, token = load_config(env_path=str(env_file))
        assert url == "https://env.example.com"
        assert token == "envtoken"

    def test_reads_from_dotenv_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FIREFLY_URL=https://dotenv.example.com\nFIREFLY_TOKEN=dotenvtoken\n")
        env = {k: v for k, v in os.environ.items() if k not in ("FIREFLY_URL", "FIREFLY_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            url, token = load_config(env_path=str(env_file))
        assert url == "https://dotenv.example.com"
        assert token == "dotenvtoken"

    def test_environment_takes_precedence_over_dotenv(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FIREFLY_URL=https://dotenv.example.com\nFIREFLY_TOKEN=dotenvtoken\n")
        with patch.dict(
            os.environ,
            {"FIREFLY_URL": "https://override.example.com", "FIREFLY_TOKEN": "overridetoken"},
        ):
            url, token = load_config(env_path=str(env_file))
        assert url == "https://override.example.com"
        assert token == "overridetoken"

    def test_raises_when_url_missing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FIREFLY_TOKEN=tok\n")
        env = {k: v for k, v in os.environ.items() if k not in ("FIREFLY_URL", "FIREFLY_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="FIREFLY_URL"):
                load_config(env_path=str(env_file))

    def test_raises_when_token_missing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FIREFLY_URL=https://example.com\n")
        env = {k: v for k, v in os.environ.items() if k not in ("FIREFLY_URL", "FIREFLY_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="FIREFLY_TOKEN"):
                load_config(env_path=str(env_file))

    def test_default_env_path_is_dot_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "FIREFLY_URL=https://cwd.example.com\nFIREFLY_TOKEN=cwdtoken\n"
        )
        env = {k: v for k, v in os.environ.items() if k not in ("FIREFLY_URL", "FIREFLY_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            url, token = load_config()
        assert url == "https://cwd.example.com"
        assert token == "cwdtoken"
