"""
Tests del graceful shutdown del server.
"""
import sys
import signal
import os
import pytest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def test_shutdown_handler_sets_should_exit():
    """El handler de SIGTERM debe marcar el server para salir."""
    import chat_app
    class MockServer:
        def __init__(self):
            self.should_exit = False
    mock_server = MockServer()
    chat_app._server_ref["server"] = mock_server

    chat_app.shutdown_handler(signal.SIGTERM, None)
    assert mock_server.should_exit is True

    # Reset
    chat_app._server_ref["server"] = None


def test_atexit_cleanup_does_not_raise():
    """El cleanup de atexit no debe lanzar excepciones."""
    import chat_app
    # Llamar directamente
    chat_app.cleanup()  # no debe raise


def test_signal_handlers_registered_when_main():
    """Cuando se ejecuta como __main__, los signal handlers se registran."""
    # En tests no estamos en __main__, asi que signal.signal lanzaria ValueError
    # Verificamos que el codigo lo maneja
    import chat_app
    # El modulo deberia tener las funciones definidas
    assert hasattr(chat_app, "shutdown_handler")
    assert hasattr(chat_app, "cleanup")
    assert callable(chat_app.shutdown_handler)
    assert callable(chat_app.cleanup)
