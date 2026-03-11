import time
import subprocess
from pathlib import Path
import pytest
from src.contextanchor.cli import main
from click.testing import CliRunner

def test_benchmark_cli_dispatch_latency():
    runner = CliRunner()
    start = time.time()
    result = runner.invoke(main, ["--help"])
    end = time.time()
    
    latency_ms = (end - start) * 1000
    print(f"\nCLI dispatch latency: {latency_ms:.2f}ms")
    # Target < 500ms
    assert latency_ms < 500

def test_benchmark_git_hook_overhead(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        subprocess.run(["git", "init", "-q"])
        # Mock hook to see how fast the cli returns when invoked as hook
        start = time.time()
        result = runner.invoke(main, ["save-context", "--hook"])
        end = time.time()
        
        latency_ms = (end - start) * 1000
        print(f"Git hook execution time: {latency_ms:.2f}ms")

def test_benchmark_context_restoration():
    runner = CliRunner()
    start = time.time()
    # Mock branch switch
    result = runner.invoke(main, ["_hook-branch-switch", "0000", "0000"])
    end = time.time()
    latency_ms = (end - start) * 1000
    print(f"Context restoration latency: {latency_ms:.2f}ms")
    # Target < 2 seconds
    assert latency_ms < 2000
