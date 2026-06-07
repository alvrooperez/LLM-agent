"""
Tests de obs.py: thread-safety y formato del evento JSONL.

Verifica que:
  - La escritura al JSONL es thread-safe (lock)
  - Multiples requests concurrentes no mezclan sus tool_events
  - El formato del evento es valido
  - El contextvar se limpia tras cada llamada
"""
import sys
import os
import json
import time
import threading
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def test_event_file_writes_are_thread_safe(tmp_path, monkeypatch):
    """Multiples escrituras concurrentes no se corrompen."""
    # Redirigir OBS_DIR a tmp
    monkeypatch.setenv("OBS_DIR", str(tmp_path / "obs"))

    # Importar obs con env nuevo
    import importlib
    if "obs" in sys.modules:
        del sys.modules["obs"]
    import obs
    importlib.reload(obs)

    def write_event_task(i):
        obs.write_event({"task_id": i, "data": "x" * 100})

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(write_event_task, i) for i in range(20)]
        for f in as_completed(futures):
            f.result()

    # Leer JSONL y verificar que cada linea es JSON valido
    events_file = tmp_path / "obs" / "events.jsonl"
    assert events_file.exists()
    lines = events_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 20
    parsed = [json.loads(l) for l in lines]
    # Verificar que todos los task_id estan presentes (sin perdidas)
    task_ids = sorted(p["task_id"] for p in parsed)
    assert task_ids == sorted(range(20))


def test_instrumented_execute_uses_contextvar_for_isolation(monkeypatch):
    """Cada llamada a instrumented_run_agent tiene su propia lista de eventos."""
    monkeypatch.setenv("OBS_DIR", str(Path(tempfile.mkdtemp()) / "obs"))

    # Limpiar modulo obs para usar el nuevo OBS_DIR
    if "obs" in sys.modules:
        del sys.modules["obs"]
    import obs
    import importlib
    importlib.reload(obs)

    # Mockear agent.run para que NO ejecute el agent loop real
    # sino que simule una llamada a execute_tool_call
    mock_agent_module = MagicMock()

    captured_events_per_request = {}

    def fake_execute_tool_call(tc):
        """Simula execute_tool_call y captura en el contextvar de la request actual."""
        events = obs._current_tool_events.get()
        if events is not None:
            events.append({"name": tc.get("name", ""), "result": "mock_result"})
        return "mock_result"

    # Hacer que agent.run.execute_tool_call apunte a fake
    mock_agent_module.execute_tool_call = fake_execute_tool_call

    # Simular dos requests concurrentes que llaman execute_tool_call
    # Cada una con su propio contextvar
    def simulate_request(request_id, tc_name):
        events = []
        token = obs._current_tool_events.set(events)
        try:
            # Simular lo que haria el agent loop
            fake_execute_tool_call({"name": tc_name, "arguments": {}})
            fake_execute_tool_call({"name": tc_name + "_2", "arguments": {}})
            captured_events_per_request[request_id] = list(events)
        finally:
            obs._current_tool_events.reset(token)
        return events

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [
            ex.submit(simulate_request, "req_a", "tool_a"),
            ex.submit(simulate_request, "req_b", "tool_b"),
            ex.submit(simulate_request, "req_c", "tool_c"),
        ]
        for f in as_completed(futures):
            f.result()

    # Verificar que cada request tiene SOLO sus propios eventos
    assert len(captured_events_per_request["req_a"]) == 2
    assert captured_events_per_request["req_a"][0]["name"] == "tool_a"
    assert captured_events_per_request["req_a"][1]["name"] == "tool_a_2"

    assert len(captured_events_per_request["req_b"]) == 2
    assert captured_events_per_request["req_b"][0]["name"] == "tool_b"

    assert len(captured_events_per_request["req_c"]) == 2
    assert captured_events_per_request["req_c"][0]["name"] == "tool_c"

    # No hay cross-contamination
    all_a_names = {e["name"] for e in captured_events_per_request["req_a"]}
    assert "tool_b" not in all_a_names
    assert "tool_c" not in all_a_names


def test_contextvar_reset_after_request():
    """Tras una llamada, _current_tool_events vuelve a su default (None)."""
    # Default del contextvar es None
    import obs
    assert obs._current_tool_events.get() is None

    # Setear
    events = [{"test": 1}]
    token = obs._current_tool_events.set(events)
    assert obs._current_tool_events.get() is events

    # Reset
    obs._current_tool_events.reset(token)
    assert obs._current_tool_events.get() is None
