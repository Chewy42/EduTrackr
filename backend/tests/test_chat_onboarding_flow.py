import pytest

from app.services.chat_service import (
    parse_and_save_user_response,
    check_onboarding_completeness,
    get_next_question_topic,
)


class DummyPrefsStore:
    def __init__(self):
        self.rows = {}

    def get(self, user_id):
        return self.rows.get(user_id, {})

    def save(self, user_id, data):
        self.rows[user_id] = {**self.rows.get(user_id, {}), **data}
        return self.rows[user_id]


@pytest.fixture
def prefs_store(monkeypatch):
    store = DummyPrefsStore()

    from app.services import chat_service

    def fake_get_scheduling_preferences(user_id: str):
        return store.get(user_id)

    def fake_save_scheduling_preference(user_id: str, field: str, value, collected_name: str | None = None):
        existing = store.get(user_id)
        collected = existing.get("collected_fields", []) or []
        name_to_add = collected_name if collected_name else field
        if name_to_add not in collected:
            collected.append(name_to_add)
        data = {"user_id": user_id, field: value, "collected_fields": collected}
        return store.save(user_id, data)

    monkeypatch.setattr(chat_service, "get_scheduling_preferences", fake_get_scheduling_preferences)
    monkeypatch.setattr(chat_service, "save_scheduling_preference", fake_save_scheduling_preference)

    return store


def test_onboarding_flow_reaches_complete(prefs_store):
    user_id = "test-user"
    prefs = {}

    # planning mode
    prefs, _ = parse_and_save_user_response(user_id, "Next semester", prefs)
    # credits
    prefs, _ = parse_and_save_user_response(user_id, "Standard (12-15)", prefs)
    # time preference
    prefs, _ = parse_and_save_user_response(user_id, "Afternoons", prefs)
    # work status
    prefs, _ = parse_and_save_user_response(user_id, "No work commitments", prefs)
    # summer
    prefs, _ = parse_and_save_user_response(user_id, "Yes to summer", prefs)

    is_complete, missing = check_onboarding_completeness(prefs)
    # Core fields should be complete after this sequence
    assert is_complete is True
    assert missing == []

    # We still expect the advisor to optionally ask about focus next
    next_topic = get_next_question_topic(prefs)
    assert next_topic in ("focus", "complete")
