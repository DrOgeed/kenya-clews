"""
Summarise solved scenarios into tables and figures.

    python scripts/analyse_results.py            # all scenarios with results/<SCEN>/
Outputs: results/summary/*.csv, results/figures/*.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import kenya_inputs as K
from build_model import SCENARIOS

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
SUM = RES / "summary"
FIG = RES / "figures"
GWH = K.GWh_PER_PJ

# Fixed categorical order, reference palette (validated, adjacent pairs) - colour follows the group
GEN_GROUPS = [
    ("Geothermal", ["PWRGEO"], "#257de0"),
    ("Hydro", ["PWRHYDTAN", "PWRHYDRVB", "PWRHYDLVS", "PWRHYDLVN", "PWRHYDHGF", "PWRHYDKAR", "PWRHYDNEW", "PWRHYDSML"], "#f47230"),
    ("Wind", ["PWRWNDT1", "PWRWNDT2"], "#00b894"),
    ("Solar", ["PWRSOL", "PWRSOLDG"], "#f2a600"),
    ("Battery discharge", ["BATSTOR"], "#ee7fac"),
    ("Imports", ["IMPELCETH", "IMPELCEAP"], "#008a17"),
    ("Gas (LNG)", ["PWROCGLNG", "PWRCCGLNG"], "#6a4ce2"),
    ("Other (oil, nuclear, bagasse)", ["PWRDSL", "PWROCGDSL", "PWRNUC", "PWRBAG"], "#ec4647"),
]
INV_SECTORS = {
    "Geothermal": ["PWRGEO"], "Wind": ["PWRWNDT1", "PWRWNDT2"], "Solar PV": ["PWRSOL", "PWRSOLDG"],
    "Battery storage": ["BATSTOR"], "Hydropower": [g for g in GEN_GROUPS[1][1]],
    "Gas (LNG)": ["PWROCGLNG", "PWRCCGLNG"], "Nuclear": ["PWRNUC"], "Bagasse cogeneration": ["PWRBAG"],
    "Grid (T&D)": ["TRNELC"],
    "Water supply (dams, boreholes, treatment, transfer, desalination)":
        [f"{p}{b}" for p in ("WDAM", "WGWT", "WTRT") for b in K.BASINS] + ["WTRFTA", "WDESATH"],
    "Irrigation (schemes and on-farm)": [f"{p}{b}" for p in ("LIRS", "WIRS", "WIRD") for b in K.BASINS],
    "Green ammonia fertiliser": ["GNH3"],
    "Afforestation": [f"LAFF{b}" for b in K.BASINS],
}


def load(scen, name):
    p = RES / scen / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["REGION", "TECHNOLOGY", "FUEL", "YEAR", "VALUE"])


def group_of(t, groups):
    for g, techs, *_ in groups:
        if t in techs:
            return g
    return None


def summarise(scen):
    out = {}
    prod = load(scen, "ProductionByTechnologyAnnual")
    use = load(scen, "UseByTechnology")
    cap = load(scen, "TotalCapacityAnnual")
    inv = load(scen, "CapitalInvestment")
    invs = load(scen, "CapitalInvestmentStorage")
    emi = load(scen, "AnnualEmissions")
    tdc = load(scen, "TotalDiscountedCost")

    el = prod[prod.FUEL.isin(["ELCTX", "ELCFIN"]) & ~prod.TECHNOLOGY.isin(["TRNELC"])].copy()
    el["GROUP"] = el.TECHNOLOGY.map(lambda t: group_of(t, GEN_GROUPS) or ("Unserved" if t == "UNSELC" else None))
    gen = el.dropna(subset=["GROUP"]).pivot_table(index="YEAR", columns="GROUP", values="VALUE", aggfunc="sum").fillna(0) * GWH / 1000
    out["generation_TWh"] = gen

    c = cap[cap.TECHNOLOGY.map(lambda t: group_of(t, GEN_GROUPS) is not None)].copy()
    c["GROUP"] = c.TECHNOLOGY.map(lambda t: group_of(t, GEN_GROUPS))
    out["capacity_GW"] = c.pivot_table(index="YEAR", columns="GROUP", values="VALUE", aggfunc="sum").fillna(0)

    inv = inv.copy()
    sec = {t: s for s, ts in INV_SECTORS.items() for t in ts}
    inv["SECTOR"] = inv.TECHNOLOGY.map(sec)
    if not invs.empty:
        invs = invs.assign(SECTOR="Battery storage")
        inv = pd.concat([inv, invs.rename(columns={"STORAGE": "TECHNOLOGY"})])
    inv = inv.dropna(subset=["SECTOR"])
    rows = {}
    for label, (a, b) in {"2026-2035": (2026, 2035), "2036-2050": (2036, 2050), "2051-2075": (2051, 2075)}.items():
        rows[label] = inv[(inv.YEAR >= a) & (inv.YEAR <= b)].groupby("SECTOR").VALUE.sum() / 1000
    out["investment_bnUSD"] = pd.DataFrame(rows).fillna(0).round(2)

    # electricity used by water and agriculture
    eu = use[use.FUEL == "ELCFIN"].copy()
    def wsec(t):
        if t.startswith(("WGWT", "WTRT")): return "Municipal water supply"
        if t.startswith(("WIRS", "WIRD")): return "Irrigation pumping"
        if t == "WDESATH": return "Desalination"
        if t == "WTRFTA": return "Inter-basin transfer"
        if t == "GNH3": return "Green ammonia"
        return None
    eu["SECTOR"] = eu.TECHNOLOGY.map(wsec)
    out["nexus_electricity_TWh"] = eu.dropna(subset=["SECTOR"]).pivot_table(
        index="YEAR", columns="SECTOR", values="VALUE", aggfunc="sum").fillna(0) * GWH / 1000

    # water supply by source and basin
    ws = prod[prod.FUEL.str.startswith("WTRSUP")].copy()
    ws["BASIN"] = ws.FUEL.str[-3:]
    ws["SOURCE"] = ws.TECHNOLOGY.map(lambda t: {"WROR": "Run-of-river", "WDAM": "Dams", "WGWT": "Groundwater",
                                                "WTRF": "Transfer", "WDES": "Desalination"}.get(t[:4], "Multipurpose hydro"))
    out["water_supply_MCM"] = ws.pivot_table(index=["BASIN", "YEAR"], columns="SOURCE", values="VALUE", aggfunc="sum").fillna(0)
    wu = use[use.FUEL.str.startswith("WTRSUP")].copy()
    wu["BASIN"] = wu.FUEL.str[-3:]
    wu["USE"] = wu.TECHNOLOGY.map(lambda t: "Irrigation" if t.startswith("WIR") else "Municipal" if t.startswith("WTRT")
                                  else "Transfer out" if t == "WTRFTA" else "Green ammonia" if t == "GNH3" else "Other")
    out["water_use_MCM"] = wu.pivot_table(index=["BASIN", "YEAR"], columns="USE", values="VALUE", aggfunc="sum").fillna(0)
    uns = prod[prod.TECHNOLOGY.str.startswith(("WUNS", "WIRU"))]
    out["unserved_water_MCM"] = uns.pivot_table(index="YEAR", columns="TECHNOLOGY", values="VALUE", aggfunc="sum").fillna(0)

    # land and crops
    act = load(scen, "TotalTechnologyAnnualActivity")
    crop = act[act.TECHNOLOGY.str.match(r"^C[A-Z]{3}[RI][A-Z]{3}$")].copy()
    crop["CROP"] = crop.TECHNOLOGY.str[1:4]
    crop["WATER"] = crop.TECHNOLOGY.str[4].map({"R": "rainfed", "I": "irrigated"})
    crop["BASIN"] = crop.TECHNOLOGY.str[5:]
    out["crop_area_kha"] = crop.pivot_table(index="YEAR", columns=["CROP", "WATER"], values="VALUE", aggfunc="sum").fillna(0)
    out["irrigated_area_by_basin_kha"] = crop[crop.WATER == "irrigated"].pivot_table(
        index="YEAR", columns="BASIN", values="VALUE", aggfunc="sum").fillna(0)
    cp = prod[prod.FUEL.str.startswith("CRP")].copy()
    cp["CROP"] = cp.FUEL.str[3:]
    cp["SRC"] = cp.TECHNOLOGY.map(lambda t: "Imports" if t.startswith("IMP") else "Domestic")
    out["crop_supply_kt"] = cp.pivot_table(index="YEAR", columns=["CROP", "SRC"], values="VALUE", aggfunc="sum").fillna(0)
    aff = act[act.TECHNOLOGY.str.startswith("LAFF")]
    out["afforestation_kha"] = aff.pivot_table(index="YEAR", columns="TECHNOLOGY", values="VALUE", aggfunc="sum").fillna(0)
    fert = prod[prod.FUEL == "FERTN"]
    out["fertiliser_ktN"] = fert.pivot_table(index="YEAR", columns="TECHNOLOGY", values="VALUE", aggfunc="sum").fillna(0)

    out["emissions_ktCO2"] = emi.pivot_table(index="YEAR", columns="EMISSION", values="VALUE", aggfunc="sum").fillna(0)
    out["total_discounted_cost_MUSD"] = pd.DataFrame({"VALUE": [tdc.VALUE.sum()]})
    lirs = cap[cap.TECHNOLOGY.str.startswith("LIRS")].copy()
    lirs["BASIN"] = lirs.TECHNOLOGY.str[4:]
    out["irrigation_schemes_kha"] = lirs.pivot_table(index="YEAR", columns="BASIN", values="VALUE", aggfunc="sum").fillna(0)
    return out


def headline(scen, o):
    g = o["generation_TWh"]
    def at(df, y, col):
        return float(df.loc[y, col]) if (y in df.index and col in df.columns) else 0.0
    row = {"Scenario": scen}
    for y in (2035, 2050, 2075):
        tot = g.loc[y].drop("Unserved", errors="ignore").sum() if y in g.index else 0
        row[f"Generation {y} (TWh)"] = round(tot, 1)
        row[f"Geothermal share {y}"] = f"{100 * at(g, y, 'Geothermal') / tot:.0f}%" if tot else ""
        row[f"Wind+solar share {y}"] = f"{100 * (at(g, y, 'Wind') + at(g, y, 'Solar')) / tot:.0f}%" if tot else ""
    inv = o["investment_bnUSD"]
    row["Investment 2026-2050 (bn USD)"] = round(inv[["2026-2035", "2036-2050"]].sum().sum(), 1)
    row["Irrigation schemes 2050 (kha)"] = round(o["irrigation_schemes_kha"].loc[2050].sum(), 0) if 2050 in o["irrigation_schemes_kha"].index else 0
    row["Irrigated cropped area 2050 (kha)"] = round(o["irrigated_area_by_basin_kha"].loc[2050].sum(), 0) if 2050 in o["irrigated_area_by_basin_kha"].index else 0
    row["Nexus electricity 2050 (TWh)"] = round(o["nexus_electricity_TWh"].loc[2050].sum(), 2) if 2050 in o["nexus_electricity_TWh"].index else 0
    e = o["emissions_ktCO2"]
    row["CO2 2050 (Mt)"] = round(e.loc[2050].sum() / 1000, 2) if 2050 in e.index else 0
    row["Unserved water 2050 (MCM)"] = round(o["unserved_water_MCM"].loc[2050].sum(), 0) if 2050 in o["unserved_water_MCM"].index else 0
    import json
    sol = json.load(open(RES / scen / "_solve.json"))
    row["Total discounted system cost (bn USD)"] = round(sol["objective_MUSD"] / 1000, 2)
    g2 = o["generation_TWh"]
    row["Unserved electricity 2026-2075 (TWh)"] = round(g2.get("Unserved", pd.Series(dtype=float)).sum(), 2)
    return row


def style(ax, title, ylabel):
    ax.set_title(title, loc="left", fontsize=11, color="#191919")
    ax.set_ylabel(ylabel, color="#666666", fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#cccccc")
    ax.tick_params(colors="#666666", labelsize=8)
    ax.grid(axis="y", color="#eeeeee", linewidth=0.8)
    ax.set_axisbelow(True)


def figures(allres):
    FIG.mkdir(parents=True, exist_ok=True)
    order = [g for g, *_ in GEN_GROUPS]
    colors = {g: c for g, _, c in GEN_GROUPS}
    scens = list(allres)
    # generation mix, small multiples on a shared scale
    ymax = max(o["generation_TWh"].drop(columns="Unserved", errors="ignore").sum(axis=1).max() for o in allres.values())
    fig, axes = plt.subplots(1, len(scens), figsize=(3.2 * len(scens), 3.6), sharey=True)
    axes = [axes] if len(scens) == 1 else axes
    for ax, s in zip(axes, scens):
        g = allres[s]["generation_TWh"]
        cols = [c for c in order if c in g.columns]
        ax.stackplot(g.index, [g[c] for c in cols], colors=[colors[c] for c in cols], labels=cols,
                     edgecolor="white", linewidth=0.6)
        style(ax, s, "TWh" if ax is axes[0] else "")
        ax.set_ylim(0, ymax * 1.05)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=8)
    fig.suptitle("Electricity generation by source, 2025-2075", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.12, 1, 0.95))
    fig.savefig(FIG / "generation_mix.png", dpi=160)
    plt.close(fig)

    # investment 2026-2050 by sector, horizontal grouped bars per scenario (BASE first)
    inv = pd.DataFrame({s: o["investment_bnUSD"][["2026-2035", "2036-2050"]].sum(axis=1) for s, o in allres.items()}).fillna(0)
    inv = inv.loc[inv.max(axis=1) > 0.05].sort_values(scens[0])
    fig, ax = plt.subplots(figsize=(8.5, 0.42 * len(inv) + 1.5))
    pal = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17", "#6a4ce2", "#ec4647"]
    h = 0.8 / len(scens)
    for i, s in enumerate(scens):
        ax.barh([k + i * h for k in range(len(inv))], inv[s], height=h * 0.9, color=pal[i], label=s)
    ax.set_yticks([k + h * (len(scens) - 1) / 2 for k in range(len(inv))])
    ax.set_yticklabels([x if len(x) < 38 else x[:36] + "..." for x in inv.index], fontsize=8)
    style(ax, "Capital investment 2026-2050 by sector", "")
    ax.set_xlabel("billion USD (2025, undiscounted)", color="#666666", fontsize=9)
    ax.grid(axis="x", color="#eeeeee"); ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "investment_by_sector.png", dpi=160)
    plt.close(fig)

    # water use by basin in 2050, BASE vs others
    fig, axes = plt.subplots(1, len(scens), figsize=(3.2 * len(scens), 3.4), sharey=True)
    axes = [axes] if len(scens) == 1 else axes
    wcol = {"Municipal": "#257de0", "Irrigation": "#f47230", "Transfer out": "#00b894", "Green ammonia": "#f2a600"}
    for ax, s in zip(axes, scens):
        wu = allres[s]["water_use_MCM"]
        d = wu.xs(2050, level="YEAR") if 2050 in wu.index.get_level_values("YEAR") else pd.DataFrame()
        d = d.reindex(K.BASINS).fillna(0)
        left = pd.Series(0.0, index=d.index)
        for col in [c for c in wcol if c in d.columns]:
            ax.barh(d.index, d[col], left=left, color=wcol[col], label=col, height=0.6, edgecolor="white", linewidth=1)
            left += d[col]
        style(ax, s, "")
        ax.grid(axis="x", color="#eeeeee"); ax.grid(axis="y", visible=False)
        ax.set_xlabel("MCM", color="#666666", fontsize=8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=8)
    fig.suptitle("Bulk water withdrawals by basin in 2050", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    fig.savefig(FIG / "water_use_2050.png", dpi=160)
    plt.close(fig)


def main():
    SUM.mkdir(parents=True, exist_ok=True)
    allres, heads = {}, []
    for s in SCENARIOS:
        if not (RES / s / "TotalDiscountedCost.csv").exists():
            continue
        o = summarise(s)
        allres[s] = o
        for k, df in o.items():
            df.round(4).to_csv(SUM / f"{s}_{k}.csv")
        heads.append(headline(s, o))
    pd.DataFrame(heads).to_csv(SUM / "headline_comparison.csv", index=False)
    if "BASE" in allres:   # base-year check against EPRA FY2024/25 (GWh)
        g = allres["BASE"]["generation_TWh"].loc[2025] * 1000
        obs = {"Geothermal": 5718.2, "Hydro": 3503.5, "Wind": 1907.6, "Solar": 473.3, "Imports": 1533.9,
               "Other (oil, nuclear, bagasse)": 1247.9}
        cal = pd.DataFrame({"Model 2025 (GWh)": g.reindex(obs.keys()).round(0), "EPRA FY2024/25 (GWh)": pd.Series(obs)})
        cal.loc["Total"] = cal.sum()
        cal["Difference"] = (cal.iloc[:, 0] / cal.iloc[:, 1] - 1).map(lambda x: f"{100 * x:+.1f}%")
        cal.to_csv(SUM / "calibration_2025.csv")
        print(cal.to_string())
    print(pd.DataFrame(heads).T.to_string())
    figures(allres)


if __name__ == "__main__":
    main()
