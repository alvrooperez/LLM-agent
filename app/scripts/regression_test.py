"""
regression_test.py — Ejecuta todos los evals y verifica que no haya regresiones.

Definimos thresholds para cada métrica. Si alguna cae por debajo, exit code != 0.

Uso:
  python scripts/regression_test.py

Esto debería correr en CI antes de cualquier merge.
"""
import sys
import subprocess
import json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
WORKDIR = SCRIPTS_DIR.parent

# Thresholds. Si una métrica cae por debajo, FAIL.
THRESHOLDS = {
    "multi_tool_chaining": {
        "min_pass_rate": 1.0,  # 100% PASS
        "min_chains_tested": 5,
    },
    "tool_call_rate": {
        "min": 0.5,  # 50% de las queries deben disparar al menos 1 tool
    },
}


def run_eval_chain() -> dict:
    """Ejecuta eval_chain.py y parsea resultados."""
    print("\n=== Multi-tool chaining eval ===")
    result = subprocess.run(
        ["python", "scripts/eval_chain.py", "--model", "qwen2.5-rag-ft"],
        cwd=WORKDIR, capture_output=True, text=True, timeout=900,
    )
    if result.returncode != 0:
        print(f"FAIL: eval_chain.py exited with {result.returncode}")
        print(result.stdout[-1000:])
        print(result.stderr[-1000:])
        return None
    # Parsea el JSON guardado
    json_path = WORKDIR / "data" / "eval_chain_results.json"
    if not json_path.exists():
        print(f"FAIL: {json_path} not found")
        return None
    with json_path.open() as f:
        return json.load(f)


def check_thresholds(chain_data: dict) -> list[str]:
    """Devuelve lista de fallos. Vacia si todo OK."""
    failures = []

    if not chain_data:
        return ["eval_chain no produjo datos"]

    summary = chain_data.get("summary", {})

    # Multi-tool chaining
    pass_rate = summary.get("chaining_rate", 0)
    if pass_rate < THRESHOLDS["multi_tool_chaining"]["min_pass_rate"]:
        failures.append(
            f"chaining_rate {pass_rate:.2f} < {THRESHOLDS['multi_tool_chaining']['min_pass_rate']}"
        )

    chains_tested = len(chain_data.get("results", []))
    if chains_tested < THRESHOLDS["multi_tool_chaining"]["min_chains_tested"]:
        failures.append(
            f"chains_tested {chains_tested} < {THRESHOLDS['multi_tool_chaining']['min_chains_tested']}"
        )

    # Tool call rate por task
    results = chain_data.get("results", [])
    if results:
        total_tcs = sum(r.get("chain_count", 0) for r in results)
        queries_with_tools = sum(1 for r in results if r.get("chain_count", 0) > 0)
        tool_rate = queries_with_tools / len(results)
        if tool_rate < THRESHOLDS["tool_call_rate"]["min"]:
            failures.append(
                f"tool_call_rate {tool_rate:.2f} < {THRESHOLDS['tool_call_rate']['min']}"
            )

    return failures


def main() -> int:
    print("=" * 60)
    print("REGRESSION TEST")
    print("=" * 60)

    chain_data = run_eval_chain()
    failures = check_thresholds(chain_data)

    print("\n" + "=" * 60)
    if failures:
        print("REGRESSION DETECTED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("ALL CHECKS PASSED")
        if chain_data:
            print(f"  chaining_rate: {chain_data['summary']['chaining_rate']:.2f}")
            print(f"  pass: {chain_data['summary']['pass']}")
            print(f"  partial: {chain_data['summary']['partial']}")
            print(f"  fail: {chain_data['summary']['fail']}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
