from __future__ import annotations

import json

import pytest

from api.pipeline.stt import MockSTTProvider, TranscriptionError, get_stt_provider


def test_mock_stt_parses_word_list() -> None:
    payload = json.dumps(
        [
            {"text": "We", "start_ms": 0, "end_ms": 200, "confidence": 0.98},
            {"text": "should", "start_ms": 210, "end_ms": 400},
        ]
    ).encode("utf-8")

    words = MockSTTProvider().transcribe(payload, sample_rate=16_000)

    assert [w.text for w in words] == ["We", "should"]
    assert words[0].confidence == 0.98
    assert words[1].confidence == 1.0  # default applied


def test_mock_stt_rejects_non_json_payload() -> None:
    with pytest.raises(TranscriptionError):
        MockSTTProvider().transcribe(b"\x00\x01\x02not-json-audio-bytes", sample_rate=16_000)


def test_mock_stt_rejects_malformed_entries() -> None:
    payload = json.dumps([{"text": "hi"}]).encode("utf-8")  # missing timestamps
    with pytest.raises(TranscriptionError):
        MockSTTProvider().transcribe(payload, sample_rate=16_000)


def test_get_stt_provider_mock() -> None:
    assert isinstance(get_stt_provider("mock"), MockSTTProvider)


def test_get_stt_provider_unknown_raises() -> None:
    with pytest.raises(NotImplementedError):
        get_stt_provider("deepgram")
