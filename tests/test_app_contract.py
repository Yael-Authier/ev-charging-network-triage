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
        "new_demo_state(", "select_incident_closures(", "record_visit_change(",
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


def test_public_app_has_no_shared_filesystem_writes():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "save_interventions(" not in source
    assert "record_event(" not in source
    assert "load_interventions(" not in source
    assert "read_history(" not in source
    assert "st.session_state.history" in source


def test_public_tables_use_static_cards_not_dynamic_dataframe():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.dataframe(" not in source
    assert "st.table(" not in source
    assert "render_static_records(" in source
    assert "escape(shown)" in source


def test_static_cards_have_responsive_styles():
    css = (ROOT / "demo" / "voltora.css").read_text(encoding="utf-8")
    assert ".voltora-record" in css
    assert "minmax(145px, 1fr)" in css
