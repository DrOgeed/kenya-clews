"""
Export a scenario to MUIO (the OSeMOSYS user interface, github.com/OSeMOSYS/MUIO).

    python scripts/export_muio.py BASE [--muio /path/to/MUIO]

Produces, in muio/:
  KenyaCLEWs_<SCEN>.xlsx   MUIO import template (Case > Import from Excel template)
  KenyaCLEWs_<SCEN>.zip    ready-made MUIO case built by running MUIO's own importer
                           (Case > Upload/restore case), with time-slice mapping and the
                           reserve-margin user-defined constraint already set
  KenyaCLEWs_<SCEN>_reserve_margin_UDC.csv   the same constraint as a table, for manual entry

The template follows MUIO's ImportTemplate.py: one sheet per set and per parameter, sheet name =
parameter name without spaces (truncated to 31 characters), year-indexed parameters in wide format.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import yaml

import kenya_inputs as K

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load(open(ROOT / "config" / "config.yaml"))
YEARS = K.YEARS

# MUIO parameter groups (from MUIO WebAPP/DataStorage/Parameters.json)
MUIO_PARAMS = {
    "R": ["DiscountRate"],
    "RT": ["TotalTechnologyModelPeriodActivityUpperLimit", "TotalTechnologyModelPeriodActivityLowerLimit",
           "OperationalLife", "CapacityToActivityUnit", "DiscountRateIdv"],
    "RE": ["ModelPeriodEmissionLimit"],
    "RYTs": ["YearSplit"],
    "RYT": ["CapacityOfOneTechnologyUnit", "TotalTechnologyAnnualActivityUpperLimit",
            "TotalTechnologyAnnualActivityLowerLimit", "TotalAnnualMinCapacityInvestment", "TotalAnnualMinCapacity",
            "TotalAnnualMaxCapacityInvestment", "TotalAnnualMaxCapacity", "ResidualCapacity", "FixedCost",
            "CapitalCost", "AvailabilityFactor"],
    "RYTM": ["VariableCost"],
    "RYTCM": ["OutputActivityRatio", "InputActivityRatio"],
    "RS": ["StorageLevelStart", "OperationalLifeStorage"],
    "RYS": ["MinStorageCharge", "ResidualStorageCapacity", "CapitalCostStorage"],
    "RTSM": ["TechnologyFromStorage", "TechnologyToStorage"],
    "RYTTs": ["CapacityFactor"],
    "RYC": ["SpecifiedAnnualDemand", "AccumulatedAnnualDemand"],
    "RYCTs": ["SpecifiedDemandProfile"],
    "RYE": ["EmissionsPenalty", "AnnualEmissionLimit"],
    "RYTEM": ["EmissionActivityRatio"],
}
SHEET_ALIAS = {"TotalTechnologyModelPeriodActivityUpperLimit": "TotalTechnologyPeriodActivityUp",
               "TotalTechnologyModelPeriodActivityLowerLimit": "TotalTechnologyPeriodActivityLo"}

TECH_GROUPS = [
    ("PWR", "Power generation"), ("IMPELC", "Electricity imports"), ("STO", "Storage"), ("GRID", "Grid"),
    ("FUEL", "Fuel supply"), ("WATER", "Water supply"), ("IRR", "Irrigation"), ("LAND", "Land use"),
    ("CROP", "Crop production"), ("AGRI", "Agricultural inputs and imports"),
]


def tech_group(t):
    if t.startswith("IMPELC"): return "IMPELC"
    if t.startswith("PWR"): return "PWR"
    if t == "BATSTOR": return "STO"
    if t in ("TRNELC", "UNSELC"): return "GRID"
    if t in ("IMPHFO", "IMPDSL", "IMPLNG", "IMPURN"): return "FUEL"
    if t.startswith(("WIRS", "WIRD", "LIRS")): return "IRR"
    if t.startswith("W"): return "WATER"
    if t.startswith("L"): return "LAND"
    if len(t) == 8 and t.startswith("C"): return "CROP"
    return "AGRI"


def sheet_name(p):
    return SHEET_ALIAS.get(p, p)[:31]


def build_template(scen):
    src = ROOT / "data" / "csv" / scen
    techs = pd.read_csv(ROOT / "data" / "csv" / f"_{scen}_technologies.csv")
    comms = pd.read_csv(ROOT / "data" / "csv" / f"_{scen}_commodities.csv")
    sheets = {}
    techs = techs.rename(columns={"TECHNOLOGY": "VALUE"})
    techs["TECHGROUP"] = techs.VALUE.map(tech_group)
    sheets["TECHNOLOGY"] = techs
    sheets["TECHGROUP"] = pd.DataFrame(TECH_GROUPS, columns=["TECHGROUP", "DESCRIPTION"])
    sheets["FUEL"] = comms.rename(columns={"FUEL": "VALUE"}).assign(BALANCE_LEVEL="Ts")
    sheets["EMISSION"] = pd.DataFrame([("CO2", "Carbon dioxide (power fuels, minus afforestation removals)", "kt")],
                                      columns=["VALUE", "DESCRIPTION", "UNIT"])
    sheets["STORAGE"] = pd.DataFrame([("BATT", "Grid battery energy storage", "PJ")], columns=["VALUE", "DESCRIPTION", "UNIT"])
    sheets["YEAR"] = pd.DataFrame({"VALUE": YEARS})
    sheets["MODE_OF_OPERATION"] = pd.DataFrame({"VALUE": [1, 2]})
    ts = pd.read_csv(src / "TIMESLICE.csv")
    sdesc = {v[0]: v[2] for v in K.SEASONS.values()}
    bdesc = {v[0]: v[2] for v in K.BRACKETS.values()}
    ts["DESCRIPTION"] = ts.VALUE.map(lambda l: f"{sdesc[l[:2]]}, {bdesc[l[2:]]}")
    sheets["TIMESLICE"] = ts
    sheets["SEASON"] = pd.DataFrame({"VALUE": list(K.SEASONS), "DESCRIPTION": [v[2] for v in K.SEASONS.values()]})
    sheets["DAYTYPE"] = pd.DataFrame({"VALUE": [1], "DESCRIPTION": ["All days"]})
    sheets["DAILYTIMEBRACKET"] = pd.DataFrame({"VALUE": list(K.BRACKETS), "DESCRIPTION": [v[2] for v in K.BRACKETS.values()]})

    for grp, params in MUIO_PARAMS.items():
        for p in params:
            if p not in CONFIG:
                continue
            df = pd.read_csv(src / f"{p}.csv")
            idx = CONFIG[p]["indices"]
            default = CONFIG[p]["default"]
            if "YEAR" in idx and grp != "RYTs":
                keys = [i for i in idx if i != "YEAR"]
                if df.empty:
                    wide = pd.DataFrame(columns=keys + YEARS)
                else:
                    wide = df.pivot_table(index=keys, columns="YEAR", values="VALUE", aggfunc="last").reindex(columns=YEARS)
                    wide = wide.fillna(default).reset_index()
                    wide.columns = [str(c) for c in wide.columns]
                sheets[sheet_name(p)] = wide
            else:
                sheets[sheet_name(p)] = df
    out = ROOT / "muio" / f"KenyaCLEWs_{scen}.xlsx"
    out.parent.mkdir(exist_ok=True)
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
    return out


def reserve_margin_udc(scen):
    """MUIO has no ReserveMargin parameter; express it as a UDC:
       -sum(credit_t * TotalCapacity_t) <= -RM_y * peak_GW_y, with the peak taken from the solved otoole run."""
    res = ROOT / "results" / scen / "RateOfProductionByTechnology.csv"
    peak = {}
    if res.exists():
        r = pd.read_csv(res)
        r = r[(r.FUEL == "ELCFIN")]      # same basis as the otoole run: delivered electricity, grossed up for losses
        from build_model import interp as _i
        peak = (r.groupby(["YEAR", "TIMESLICE"]).VALUE.sum() / K.CAP2ACT_POWER).groupby("YEAR").max()
        peak = {y: v / _i(K.TD_EFF, y) for y, v in peak.items()}
    else:   # fall back to the exogenous demand peak at transmission level
        d = pd.read_csv(ROOT / "data" / "csv" / scen / "SpecifiedAnnualDemand.csv").set_index("YEAR").VALUE
        prof = pd.read_csv(ROOT / "data" / "csv" / scen / "SpecifiedDemandProfile.csv")
        ys = pd.read_csv(ROOT / "data" / "csv" / scen / "YearSplit.csv")
        f = prof.merge(ys, on=["TIMESLICE", "YEAR"]).assign(r=lambda x: x.VALUE_x / x.VALUE_y).groupby("YEAR").r.max()
        eff = {y: 1 / 0.85 for y in YEARS}
        peak = {y: d[y] * f[y] * eff[y] / K.CAP2ACT_POWER for y in YEARS}
    from build_model import interp
    rows = []
    for y in YEARS:
        rows.append(("RM", "CONSTANT", y, round(-interp(K.RESERVE_MARGIN, y) * peak.get(y, 0.0), 6)))
        for t, cc in K.CAPACITY_CREDIT.items():
            rows.append(("RM", t, y, -cc))
    df = pd.DataFrame(rows, columns=["UDC", "TECHNOLOGY", "YEAR", "VALUE"])
    out = ROOT / "muio" / f"KenyaCLEWs_{scen}_reserve_margin_UDC.csv"
    df.to_csv(out, index=False)
    return df


def muio_case(scen, xlsx, muio_dir, udc):
    """Run MUIO's own importer against the template, then patch time-slice mapping and the UDC."""
    work = Path(tempfile.mkdtemp())
    ds = work / "WebAPP" / "DataStorage"
    ds.mkdir(parents=True)
    for f in ("Parameters.json", "Variables.json"):
        shutil.copy(muio_dir / "WebAPP" / "DataStorage" / f, ds / f)
    for f in ("Duals.json", "Indicators.json"):
        p = muio_dir / "WebAPP" / "DataStorage" / f
        if p.exists():
            shutil.copy(p, ds / f)
    tpl = ds / xlsx.name
    shutil.copy(xlsx, tpl)
    case = f"KenyaCLEWs_{scen}"
    runner = f"""
import sys; sys.path.insert(0, r'{muio_dir / "API"}')
from Classes.Case.ImportTemplate import ImportTemplate
from Classes.Base import Config
from pathlib import Path
it = ImportTemplate('{xlsx.name}')
it.TEMPLATE_PATH = Path(Config.DATA_STORAGE, '{xlsx.name}')
r = it.importProcess({{'osy-template': '{xlsx.name}', 'osy-casename': '{case}', 'osy-currency': 'MUSD',
     'osy-version': '5.7', 'osy-desc': 'Kenya CLEWs {scen}', 'osy-date': '2026-11-25', 'osy-data': True}})
print(r['status_code'])
"""
    p = subprocess.run([sys.executable, "-c", runner], cwd=work, capture_output=True, text=True)
    if "success" not in p.stdout:
        print(p.stdout[-2000:], p.stderr[-3000:])
        raise RuntimeError("MUIO import failed")
    cdir = ds / case
    gpath = cdir / "genData.json"
    gen = json.load(open(gpath))
    # time-slice to season / day type / bracket mapping (needed for storage)
    se = {s["Se"]: s["SeId"] for s in gen["osy-se"]}
    dtb = {d["Dtb"]: d["DtbId"] for d in gen["osy-dtb"]}
    snum = {v[0]: k for k, v in K.SEASONS.items()}
    bnum = {v[0]: k for k, v in K.BRACKETS.items()}
    for t in gen["osy-ts"]:
        t["SE"] = se.get(snum[t["Ts"][:2]], se.get(str(snum[t["Ts"][:2]])))
        t["DTB"] = dtb.get(bnum[t["Ts"][2:]], dtb.get(str(bnum[t["Ts"][2:]])))
        t["DT"] = gen["osy-dt"][0]["DtId"]
    # reserve margin as UDC (Tag 0 = inequality, sum(mult x TotalCapacity) <= constant)
    tid = {t["Tech"]: t["TechId"] for t in gen["osy-tech"]}
    credit_techs = [t for t, c in K.CAPACITY_CREDIT.items() if c > 0 and t in tid]
    gen["osy-constraints"] = [{"ConId": "CO_0", "Con": "RM", "Desc": "Reserve margin: firm capacity >= RM x evening peak (GW)",
                               "Tag": 0, "CM": [tid[t] for t in credit_techs]}]
    json.dump(gen, open(gpath, "w"), indent=2)
    ys = [str(y) for y in YEARS]
    const = udc[udc.TECHNOLOGY == "CONSTANT"].set_index("YEAR").VALUE
    rycn = {"UCC": {"SC_0": [dict({"ConId": "CO_0"}, **{y: float(const[int(y)]) for y in ys})]}}
    rytcn = {"CAM": {"SC_0": []}, "CNCM": {"SC_0": []}, "CCM": {"SC_0": []}}
    for t in credit_techs:
        for key in rytcn:
            val = -K.CAPACITY_CREDIT[t] if key == "CCM" else 0
            rytcn[key]["SC_0"].append(dict({"TechId": tid[t], "ConId": "CO_0"}, **{y: val for y in ys}))
    json.dump(rycn, open(cdir / "RYCn.json", "w"))
    json.dump(rytcn, open(cdir / "RYTCn.json", "w"))
    udc.to_csv(cdir / "reserve_margin_UDC.csv", index=False)
    out = ROOT / "muio" / case
    shutil.make_archive(str(out), "zip", root_dir=ds, base_dir=case)
    shutil.rmtree(work)
    return Path(str(out) + ".zip")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenarios", nargs="*")
    ap.add_argument("--muio", default=os.environ.get("MUIO_DIR", str(Path.home() / "ext" / "MUIO")))
    a = ap.parse_args()
    from build_model import SCENARIOS
    for s in a.scenarios or list(SCENARIOS):
        x = build_template(s)
        udc = reserve_margin_udc(s)
        print(f"{s}: template {x.name}")
        if Path(a.muio).exists():
            z = muio_case(s, x, Path(a.muio), udc)
            print(f"{s}: MUIO case {z.name}")


if __name__ == "__main__":
    main()
