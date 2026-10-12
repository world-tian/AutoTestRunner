"""CLI behavior when the optional AutoTestHub service is unavailable."""

import sys

import pytest
import requests

from autotest_runner import cli


def test_run_continues_locally_when_preflight_cloud_sync_times_out(monkeypatch, caplog):
    calls = {}

    def timeout_sync(*args, **kwargs):
        raise requests.exceptions.ConnectTimeout("hub unavailable")

    def local_run(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return 0

    monkeypatch.setenv("AUTOTEST_HUB_URL", "http://120.79.207.52:15173")
    monkeypatch.setenv("AUTOTEST_PROJECT_ID", "camera-project")
    monkeypatch.setattr("autotest_runner.core.sync.sync_cases", timeout_sync)
    monkeypatch.setattr(cli, "run_tests_locally", local_run)
    monkeypatch.setattr(sys, "argv", ["autotest_runner", "run", "testcases"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 0
    assert calls["args"][0] == "testcases"
    assert calls["args"][1] is False
    assert calls["args"][2] == "http://120.79.207.52:15173"
    assert "将继续本地测试" in caplog.text
    assert "本次结果仅保存在本地" in caplog.text
