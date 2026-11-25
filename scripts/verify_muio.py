"""
Check that an exported MUIO case is usable: unpack it into a scratch MUIO data store, let MUIO's own
DataFile class write the model data file, then build (and optionally solve) the LP with MUIO's model.

    python scripts/verify_muio.py BASE [--solve] [--muio /path/to/MUIO]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--solve", action="store_true")
    ap.add_argument("--muio", default=os.environ.get("MUIO_DIR", str(Path.home() / "ext" / "MUIO")))
    a = ap.parse_args()
    muio = Path(a.muio)
    case = f"KenyaCLEWs_{a.scenario}"
    work = Path(tempfile.mkdtemp())
    ds = work / "WebAPP" / "DataStorage"
    ds.mkdir(parents=True)
    for f in ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json"):
        if (muio / "WebAPP" / "DataStorage" / f).exists():
            shutil.copy(muio / "WebAPP" / "DataStorage" / f, ds / f)
        else:   # generated at runtime by the MUIO app; an empty registry is enough to write the data file
            (ds / f).write_text("{}")
    zipfile.ZipFile(ROOT / "muio" / f"{case}.zip").extractall(ds)
    runner = f"""
import sys; sys.path.insert(0, r'{muio / "API"}')
from Classes.Case.DataFileClass import DataFile
d = DataFile('{case}')
run = {{'Case': 'check', 'Desc': 'verification run', 'Scenarios': [{{'ScenarioId': 'SC_0', 'Scenario': 'SC_0', 'Active': True}}]}}
print(d.createCaseRun('check', run)['status_code'])
d = DataFile('{case}')
d.generateDatafile('check')
from pathlib import Path
src = Path('WebAPP/DataStorage/{case}/res/check/data.txt')
d.preprocessData(src, src.with_name('data_processed.txt'))
print('datafile written')
"""
    # MUIO checks that a CBC executable exists at start-up; only the data file is needed here,
    # so a placeholder on PATH is enough when CBC is not installed
    env = dict(os.environ)
    if not shutil.which("cbc"):
        fake = work / "bin"
        fake.mkdir()
        (fake / "cbc").write_text("#!/bin/sh\nexit 1\n")
        (fake / "cbc").chmod(0o755)
        env["PATH"] = f"{fake}{os.pathsep}{env['PATH']}"
    p = subprocess.run([sys.executable, "-c", runner], cwd=work, capture_output=True, text=True, env=env)
    print(p.stdout.strip())
    if "datafile written" not in p.stdout:
        print(p.stderr[-3000:])
        sys.exit(1)
    data = ds / case / "res" / "check" / "data_processed.txt"
    model = muio / "WebAPP" / "SOLVERs" / "model.v.5.7.txt"
    out = ROOT / "build" / f"muio_{a.scenario}"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(data, out / "data.txt")
    (out / "csv").mkdir(exist_ok=True)
    # MUIO's model writes results relative to its own folder layout; point it at a scratch folder
    txt = (out / "data.txt").read_text()
    g = subprocess.run(["glpsol", "-m", str(model), "-d", str(out / "data.txt"), "--wlp", str(out / "muio.lp"), "--check"],
                       cwd=out, capture_output=True, text=True)
    tail = [l for l in g.stdout.splitlines() if "rows" in l.lower() or "columns" in l.lower() or "error" in l.lower()]
    print("\n".join(tail[-6:]))
    if g.returncode != 0:
        print(g.stdout[-2000:])
        sys.exit(1)
    if a.solve:
        import highspy
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("solver", "ipm")
        h.setOptionValue("run_crossover", "off")
        h.readModel(str(out / "muio.lp"))
        h.run()
        res = {"status": h.modelStatusToString(h.getModelStatus()), "objective": h.getInfo().objective_function_value}
        print(res)
        json.dump(res, open(out / "muio_solution.json", "w"))
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
