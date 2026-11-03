"""Smoke checks for the Streamlit entrypoint without launching a server."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_entrypoint_compiles():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    ast.parse(source, filename="app.py")


def test_brand_stylesheet_exists_and_contains_identity():
    css = (ROOT / "demo" / "voltora.css").read_text(encoding="utf-8")
    assert "#55e0c4" in css
    assert ".stApp" in css


def test_operational_sections_still_present():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    for feature in (
        "tab_queue", "tab_work", "tab_incidents", "tab_history",
        "save_interventions(", "select_incident_closures(", "record_event(",
    ):
        assert feature in source


def test_streamlit_native_dark_theme():
    import tomllib

    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["theme"]["base"] == "dark"
    assert config["theme"]["backgroundColor"] == "#101923"
    assert config["theme"]["textColor"] == "#E9F1F5"


def test_queue_shows_current_visit_status_without_redundant_incident_metric():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"Visit status"' in source
    assert 'st.session_state.interventions[station]["status"]' in source
    assert 'st.metric("Active incidents after confirmed closures"' not in source
