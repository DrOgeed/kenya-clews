"""
Full pipeline for each scenario:
  build CSVs -> otoole datafile -> GLPK matrix (LP) -> HiGHS solve -> otoole result CSVs -> MUIO export

    python scripts/run_scenarios.py              # all scenarios
    python scripts/run_scenarios.py BASE RE100   # selected
Then: python scripts/analyse_results.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import build_model
from solve_highs import solve

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
CFG = ROOT / "config" / "config.yaml"
MODEL = ROOT / "model" / "osemosys_fast.txt"


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        print(p.stdout[-3000:], p.stderr[-3000:])
        raise RuntimeError(" ".join(map(str, cmd)))
    return p.stdout


def main(scens):
    BUILD.mkdir(exist_ok=True)
    log = {}
    for s in scens:
        build_model.main([s])
        dat, lp, sol = BUILD / f"{s}.txt", BUILD / f"{s}.lp", BUILD / f"{s}.sol"
        run(["otoole", "convert", "csv", "datafile", str(ROOT / "data" / "csv" / s), str(dat), str(CFG)])
        run(["glpsol", "-m", str(MODEL), "-d", str(dat), "--wlp", str(lp), "--check"])
        status, obj = solve(str(lp), str(sol))
        out = ROOT / "results" / s
        shutil.rmtree(out, ignore_errors=True)
        run(["otoole", "results", "highs", "csv", str(sol), str(out), "datafile", str(dat), str(CFG)])
        log[s] = {"status": status, "objective_MUSD": obj}
        json.dump(log[s], open(out / "_solve.json", "w"), indent=1)
        lp.unlink()          # matrices are large (~180 MB); keep the datafile and solution only
        run([sys.executable, str(ROOT / "scripts" / "export_muio.py"), s])
        print(f"{s} done: {status}", flush=True)
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or list(build_model.SCENARIOS))
