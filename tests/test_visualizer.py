import os
import json
import socket
import urllib.request
import threading
import time
import pytest
from http.server import HTTPServer
from eval_factory.visualize import VisualizerHTTPHandler
from eval_factory import config, save_run

@pytest.fixture
def temp_eval_dir(tmp_path):
    original_base = config.base_dir
    config.base_dir = str(tmp_path)
    yield tmp_path
    config.base_dir = original_base

def find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def test_visualizer_endpoints(temp_eval_dir):
    dataset_name = "test_visualizer_dataset"
    run_data = {
        "run_id": "uuid-123",
        "timestamp": "2026-05-22T18:00:00Z",
        "inputs": "Input visualizer test",
        "outputs": "Output visualizer test",
        "evaluation": {"correct": True, "ground_truth": "GT text"}
    }
    save_run(dataset_name, run_data)
    
    port = find_free_port()
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, VisualizerHTTPHandler)
    httpd.dataset_name = dataset_name
    httpd.dataset_file = os.path.join(str(temp_eval_dir), f"{dataset_name}.jsonl")
    httpd.base_dir = str(temp_eval_dir)
    
    # Spin up in a background thread
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()
    
    # Wait briefly for server to boot
    time.sleep(0.2)
    
    try:
        # Test GET /
        url_root = f"http://127.0.0.1:{port}/"
        with urllib.request.urlopen(url_root) as response:
            assert response.status == 200
            html = response.read().decode("utf-8")
            assert "eval-factory Dashboard" in html
            assert "Export JSONL" in html  # Our new button is present!
            
        # Test GET /api/runs
        url_runs = f"http://127.0.0.1:{port}/api/runs"
        with urllib.request.urlopen(url_runs) as response:
            assert response.status == 200
            runs = json.loads(response.read().decode("utf-8"))
            assert len(runs) == 1
            assert runs[0]["run_id"] == "uuid-123"
            
        # Test GET /api/download
        url_download = f"http://127.0.0.1:{port}/api/download"
        with urllib.request.urlopen(url_download) as response:
            assert response.status == 200
            assert "application/x-jsonlines" in response.headers.get("Content-Type", "")
            assert f"attachment; filename={dataset_name}.jsonl" in response.headers.get("Content-Disposition", "")
            lines = response.read().decode("utf-8").strip().split("\n")
            assert len(lines) == 1
            loaded = json.loads(lines[0])
            assert loaded["run_id"] == "uuid-123"
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join()
