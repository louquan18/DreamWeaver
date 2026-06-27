from src.models import provider


def test_stage_model_overrides_legacy_agent_model(monkeypatch):
    monkeypatch.setattr(provider.settings, "model_blueprint", "stage-blueprint")
    monkeypatch.setattr(provider.settings, "model_blueprint_fallback", "stage-blueprint-fallback")
    monkeypatch.setattr(provider.settings, "model_planner", "legacy-planner")
    monkeypatch.setattr(provider.settings, "model_planner_fallback", "legacy-planner-fallback")

    assert provider.agent_model_chain("blueprint") == [
        "stage-blueprint",
        "stage-blueprint-fallback",
    ]


def test_stage_model_falls_back_to_legacy_agent_model(monkeypatch):
    monkeypatch.setattr(provider.settings, "model_outline", "")
    monkeypatch.setattr(provider.settings, "model_outline_fallback", "")
    monkeypatch.setattr(provider.settings, "model_planner", "legacy-planner")
    monkeypatch.setattr(provider.settings, "model_planner_fallback", "legacy-planner-fallback")

    assert provider.agent_model_chain("outline") == [
        "legacy-planner",
        "legacy-planner-fallback",
    ]


def test_legacy_alias_uses_stage_model_when_configured(monkeypatch):
    monkeypatch.setattr(provider.settings, "model_draft", "stage-draft")
    monkeypatch.setattr(provider.settings, "model_draft_fallback", "stage-draft-fallback")
    monkeypatch.setattr(provider.settings, "model_writer", "legacy-writer")
    monkeypatch.setattr(provider.settings, "model_writer_fallback", "legacy-writer-fallback")

    assert provider.agent_model_chain("writer") == [
        "stage-draft",
        "stage-draft-fallback",
    ]


def test_memory_extract_has_separate_stage_model(monkeypatch):
    monkeypatch.setattr(provider.settings, "model_memory_extract", "stage-memory")
    monkeypatch.setattr(provider.settings, "model_memory_extract_fallback", "stage-memory-fallback")
    monkeypatch.setattr(provider.settings, "model_reviewer", "legacy-reviewer")
    monkeypatch.setattr(provider.settings, "model_reviewer_fallback", "legacy-reviewer-fallback")

    assert provider.agent_model_chain("memory_extract") == [
        "stage-memory",
        "stage-memory-fallback",
    ]
    assert provider.agent_temperature("memory_extract") == 0.1
