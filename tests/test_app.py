"""Streamlit AppTest による UI 結合テスト。"""

import pytest
from streamlit.testing.v1 import AppTest

pytestmark = pytest.mark.lean


@pytest.fixture
def app(lean_runner, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("VLLM_TIMEOUT_SEC", "1")
    at = AppTest.from_file("../app.py", default_timeout=120)
    at.run()
    assert not at.exception
    return at


def _button(at, key):
    return next(b for b in at.button if b.key == key)


def test_four_tabs(app):
    assert len(app.tabs) == 4


def test_lean_demos_work_when_vllm_is_down(app, monkeypatch):
    # vLLM を停止した状態（存在しないポート）でも Lean 単体デモは動く
    _button(app, "rbac_verify").click()
    app.run()
    assert not app.exception
    assert app.session_state["rbac_result"].status.value == "PASS"


def test_coding_violation_via_ui(app):
    next(n for n in app.number_input if n.key == "coding_amount").set_value(150)
    _button(app, "coding_verify").click()
    app.run()
    assert not app.exception
    assert app.session_state["coding_result"].status.value == "VIOLATION"
    assert "SafeTransfer" not in app.session_state["coding_result"].lean_source


def test_rbac_default_via_ui(app):
    _button(app, "rbac_verify").click()
    app.run()
    assert app.session_state["rbac_result"].status.value == "PASS"


def test_optimization_via_ui(app):
    _button(app, "opt_run").click()
    app.run()
    assert not app.exception
    state = app.session_state["opt_state"]
    assert state["solution"].status == "OPTIMAL"
    assert state["result"].status.value == "PASS"
