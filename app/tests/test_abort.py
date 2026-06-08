"""
Test del AbortController: cliente cancela la request a mitad del stream.
El backend (FastAPI) debe cerrar la conexion limpiamente.
"""
import pytest
import socket
import time
import json

pytestmark = pytest.mark.e2e


HOST = "localhost"
PORT = 8090


def server_alive() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((HOST, PORT))
        s.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not server_alive(), reason="chat server not running on :8090")
def test_client_abort_does_not_break_server():
    """Cliente cancela request a mitad del stream, server sigue OK."""
    data = json.dumps({
        'message': 'Busca en los docs como configurar RAG y dame el estado de la GPU',
        'model': 'qwen2.5-rag-ft',
    }).encode()

    # Iniciar una request lenta
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(30)
    s.connect((HOST, PORT))
    req = (
        b"POST /api/chat/stream HTTP/1.1\r\n"
        b"Host: localhost:8090\r\n"
        b"Content-Type: application/json\r\n"
        b"User-Agent: abort-test/1.0\r\n"
        b"Content-Length: " + str(len(data)).encode() + b"\r\n"
        b"\r\n" + data
    )
    s.send(req)

    # Leer un poco y luego abortar
    time.sleep(2)
    s.close()
    time.sleep(2)

    # Verificar que el server sigue respondiendo
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2.settimeout(3)
    s2.connect((HOST, PORT))
    s2.send(b"GET /api/health HTTP/1.1\r\nHost: localhost\r\nUser-Agent: abort-test/1.0\r\n\r\n")
    try:
        resp = s2.recv(4096).decode('utf-8', errors='replace')
        status_line = resp.split('\r\n')[0]
        assert '200' in status_line, f"Expected 200, got {status_line}"
    finally:
        s2.close()
