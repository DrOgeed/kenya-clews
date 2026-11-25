"""
Build the Kenya CLEWs OSeMOSYS dataset (otoole CSV format) for one or all scenarios.

    python scripts/build_model.py            # all scenarios
    python scripts/build_model.py BASE       # one scenario

Output: data/csv/<SCENARIO>/*.csv, readable by `otoole convert csv datafile ...`
"""
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import yaml

import kenya_inputs as K

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "config.yaml"
Y = K.YEARS
R = K.REGION

SCENARIOS = {
    "BASE": "Demographic demand (3x population growth), least cost, current policy (no new coal)",
    "LCPDP": "As BASE but LCPDP 2024-2043 Reference demand growth (6.6%/yr) to 2043",
    "RE100": "As BASE plus 100% renewable generation from 2035 (NDC 3.0): no fossil generation, no nuclear; standby firm capacity allowed",
    "NZDRY": "As BASE plus net-zero power CO2 by 2050 and climate stress (drier hydro, runoff, rainfed yields)",
    "IRRIG": "As BASE plus NISIP irrigation expansion (690 kha by 2035, 1,000 kha by 2050) forced",
}


# ------------------------------------------------------------------ helpers
def interp(points, y):
    """Piecewise-linear interpolation of {year: value}; flat outside the keys."""
    if not points:
        return 0.0
    ks = sorted(points)
    if y <= ks[0]:
        return float(points[ks[0]])
    if y >= ks[-1]:
        return float(points[ks[-1]])
    for a, b in zip(ks, ks[1:]):
        if a <= y <= b:
            return points[a] + (points[b] - points[a]) * (y - a) / (b - a)


def nwmp(series, y):
    """NWMP values given for 2010/2030/2050; linear between, flat after 2050."""
    return interp({2010: series[0], 2030: series[1], 2050: series[2]}, y)


def population():
    pop = {2026: K.POP_2026_M}
    g = dict(zip(Y, K.POP_GROWTH_PCT))
    pop[2025] = K.POP_2026_M / (1 + g[2026] / 100)
    for y in range(2027, 2076):
        pop[y] = pop[y - 1] * (1 + g[y] / 100)
    return pop, g


class Model:
    def __init__(self):
        self.p = defaultdict(list)
        self.techs, self.fuels, self.emis, self.storage = {}, {}, {}, {}
        self.units = {}

    def tech(self, code, desc, capunit, actunit):
        self.techs[code] = desc
        self.units[code] = (capunit, actunit)

    def fuel(self, code, desc, unit):
        self.fuels[code] = (desc, unit)

    def add(self, param, *idx):
        self.p[param].append(idx)

    def yearly(self, param, prefix, fn):
        for y in Y:
            v = fn(y)
            if v is not None:
                self.add(param, *prefix, y, round(float(v), 8))


# ------------------------------------------------------------------ scenario switches
def switches(scen):
    s = dict(demand="rule", re100=False, netzero=False, dry=False, irrig=False)
    if scen == "LCPDP":
        s["demand"] = "lcpdp"
    if scen == "RE100":
        s["re100"] = True
    if scen == "NZDRY":
        s["netzero"] = True
        s["dry"] = True
    if scen == "IRRIG":
        s["irrig"] = True
    return s


def climate(sw, kind, y, basin=None):
    """Multipliers for the climate-stress scenario."""
    if not sw["dry"]:
        return 1.0
    if kind == "hydro":
        return interp({2025: 1.0, 2030: 0.9, 2040: 0.75, 2050: 0.7, 2075: 0.65}, y)
    if kind == "runoff":
        if basin in ("ATH", "TAN", "ENN", "RVB"):
            return interp({2025: 1.0, 2050: 0.85, 2075: 0.80}, y)
        return interp({2025: 1.0, 2050: 0.95, 2075: 0.92}, y)
    if kind == "yield":
        return interp({2025: 1.0, 2050: 0.90, 2075: 0.85}, y)
    return 1.0


# ------------------------------------------------------------------ build
def build(scen):
    sw = switches(scen)
    m = Model()
    pop, g = population()
    ts = [(s, b) for s in K.SEASONS for b in K.BRACKETS]
    tsname = {(s, b): K.SEASONS[s][0] + K.BRACKETS[b][0] for s, b in ts}
    yearsplit = {(s, b): K.SEASONS[s][1] / 365 * K.BRACKETS[b][1] / 24 for s, b in ts}

    # ---- time structure
    for (s, b) in ts:
        l = tsname[(s, b)]
        for y in Y:
            m.add("YearSplit", l, y, round(yearsplit[(s, b)], 8))
        m.add("Conversionls", l, s, 1)
        m.add("Conversionld", l, 1, 1)
        m.add("Conversionlh", l, b, 1)
    for b, (_, hrs, _) in K.BRACKETS.items():
        for y in Y:
            m.add("DaySplit", b, y, round(hrs / 8760, 8))
    for s in K.SEASONS:
        for y in Y:
            m.add("DaysInDayType", s, 1, y, 7)
    m.add("DiscountRate", R, K.DISCOUNT_RATE)
    m.add("DepreciationMethod", R, 1)

    # ---- generic tech setter
    def setup(t, desc, capunit="GW", actunit="PJ", c2a=K.CAP2ACT_POWER, life=99, residual=None,
              capex=None, fom=None, vom=None, maxcap=None, maxinv=None, first=None,
              cf=None, avail=None, act_up=None, act_lo=None, mincap=None):
        m.tech(t, desc, capunit, actunit)
        m.add("CapacityToActivityUnit", R, t, c2a)
        m.add("OperationalLife", R, t, life)
        if residual is not None:
            m.yearly("ResidualCapacity", (R, t), residual if callable(residual) else (lambda y, r=residual: r))
        if capex is not None:
            m.yearly("CapitalCost", (R, t), capex if callable(capex) else (lambda y, c=capex: c))
        if fom:
            m.yearly("FixedCost", (R, t), fom if callable(fom) else (lambda y, c=fom: c))
        if vom is not None:
            m.yearly("VariableCost", (R, t, 1), vom if callable(vom) else (lambda y, c=vom: c))
        if maxcap is not None:
            m.yearly("TotalAnnualMaxCapacity", (R, t), maxcap if callable(maxcap) else (lambda y, c=maxcap: c))
        if mincap is not None:
            m.yearly("TotalAnnualMinCapacity", (R, t), mincap)
        if maxinv is not None or first is not None:
            def mi(y, maxinv=maxinv, first=first):
                if first is not None and y < first:
                    return 0.0
                if maxinv is None:
                    return None
                return maxinv(y) if callable(maxinv) else maxinv
            m.yearly("TotalAnnualMaxCapacityInvestment", (R, t), mi)
        if avail is not None:
            m.yearly("AvailabilityFactor", (R, t), avail if callable(avail) else (lambda y, c=avail: c))
        if cf is not None:
            for (s, b) in ts:
                l = tsname[(s, b)]
                m.yearly("CapacityFactor", (R, t, l), (lambda y, s=s, b=b: cf(s, b, y)) if callable(cf) else (lambda y, c=cf: c))
        if act_up is not None:
            m.yearly("TotalTechnologyAnnualActivityUpperLimit", (R, t), act_up)
        if act_lo is not None:
            m.yearly("TotalTechnologyAnnualActivityLowerLimit", (R, t), act_lo)

    def io(param, t, f, fn, mode=1):
        m.yearly(param, (R, t, f, mode), fn if callable(fn) else (lambda y, c=fn: c))

    # ---- commodities
    m.fuel("ELCTX", "Electricity at transmission level", "PJ")
    m.fuel("ELCFIN", "Electricity delivered to final users", "PJ")
    for f, d in [("HFO", "Heavy fuel oil"), ("DSL", "Diesel/kerosene"), ("LNG", "Imported LNG"),
                 ("URN", "Nuclear fuel (thermal PJ)"), ("BAG", "Bagasse available for export power")]:
        m.fuel(f, d, "PJ")
    m.emis["CO2"] = "Carbon dioxide (power fuels, minus afforestation removals)"

    # ---- electricity demand under the rule
    td_eff = lambda y: interp(K.TD_EFF, y)
    sales_pj_2025 = K.SALES_GWH_2025 / K.GWh_PER_PJ

    mun2025 = {b: K.MUN_WATER_PER_CAP[2025] * pop[2025] * K.POP_SHARE[b] for b in K.BASINS}
    irr_net_2025 = {b: 0.0 for b in K.BASINS}
    for c, bas in K.IRRIGATED_AREA_2025.items():
        for b, a in bas.items():
            irr_net_2025[b] += a * K.CROPS[c][7] / 100
    water_elec_2025 = sum(
        mun2025[b] * (K.KWH_M3_TREAT_DIST + K.GW_SHARE_MUN_2025[b] * K.KWH_M3_GW) * 0.0036
        + irr_net_2025[b] / K.IRR_EFF_SURFACE * K.KWH_M3_IRR_SURFACE * 0.0036 for b in K.BASINS)
    base_nonwater = sales_pj_2025 - water_elec_2025

    demand = {2025: base_nonwater}
    for y in Y[1:]:
        if sw["demand"] == "lcpdp" and y <= 2043:
            gr = K.LCPDP_GROWTH_TO_2043
        else:
            gr = K.DEMAND_MULTIPLIER * g[y] / 100
        demand[y] = demand[y - 1] * (1 + gr)
    m.yearly("SpecifiedAnnualDemand", (R, "ELCFIN"), lambda y: demand[y])
    raw = {(s, b): K.SEASONS[s][1] * K.SEASON_LOAD[K.SEASONS[s][0]] * K.BRACKET_LOAD[K.BRACKETS[b][0]] * K.BRACKETS[b][1]
           for s, b in ts}
    tot = sum(raw.values())
    for (s, b) in ts:
        m.yearly("SpecifiedDemandProfile", (R, "ELCFIN", tsname[(s, b)]), lambda y, v=raw[(s, b)] / tot: v)

    # ---- grid
    setup("TRNELC", "Transmission and distribution network", residual=3.2, capex=800, fom=16, life=40, first=2026)
    io("InputActivityRatio", "TRNELC", "ELCTX", lambda y: 1 / td_eff(y))
    io("OutputActivityRatio", "TRNELC", "ELCFIN", 1)
    setup("UNSELC", "Unserved electricity (value of lost load backstop)", residual=99, vom=K.UNSERVED_ELEC_COST)
    io("OutputActivityRatio", "UNSELC", "ELCFIN", 1)

    # ---- fuels
    for f in ["HFO", "DSL", "LNG", "URN"]:
        t = "IMP" + f
        setup(t, f"Import of {m.fuels[f][0]}", capunit="PJ/yr", c2a=1, residual=9999,
              vom=lambda y, f=f: interp(K.FUELS_PRICE[f], y))
        io("OutputActivityRatio", t, f, 1)
        if f in K.EMISSION_FACTOR:
            m.yearly("EmissionActivityRatio", (R, t, "CO2", 1), lambda y, f=f: K.EMISSION_FACTOR[f])
    if sw["re100"]:
        m.yearly("TotalTechnologyAnnualActivityUpperLimit", (R, "IMPLNG"), lambda y: None if y < 2035 else 0.0)

    # ---- power plants
    fossil = {"PWRDSL", "PWROCGDSL", "PWROCGLNG", "PWRCCGLNG"}
    for t, d in K.POWER.items():
        res = (lambda y, r=d["residual"]: interp(r, y)) if d.get("residual") else None
        capex = (lambda y, c=d["capex"]: interp(c, y)) if d.get("capex") else None
        maxcap = (lambda y, c=d["maxcap"]: interp(c, y)) if d.get("maxcap") else None
        maxinv = (lambda y, c=d["maxinv"]: interp(c, y)) if d.get("maxinv") else None
        first = d.get("first") if d.get("capex") else 2999
        if t in ("PWRNUC",) and sw["re100"]:
            maxcap = lambda y: 0.0
        is_hydro = t.startswith("PWRHYD")
        if is_hydro:
            ecf = d["energy_cf"]
            def cf(s, b, y, ecf=ecf):
                sf = K.HYDRO_SEASON[K.SEASONS[s][0]] * climate(sw, "hydro", y)
                return min(0.95, 2.0 * ecf * sf) if K.BRACKETS[b][0] == "P" else min(0.95, ecf * sf * 0.92)
            capsrc = d["residual"] if d.get("residual") else d["maxcap"]
            act_up = lambda y, c=capsrc, ecf=ecf: interp(c, y) * ecf * K.CAP2ACT_POWER * climate(sw, "hydro", y)
            setup(t, d["name"], residual=res, capex=capex, fom=d["fom"], life=d["life"], maxcap=maxcap,
                  first=first, cf=cf, act_up=act_up)
            water_in = d["evap"] + d.get("water_yield", 0.0)
            io("OutputActivityRatio", t, "ELCTX", 1)
            if water_in > 0:
                io("InputActivityRatio", t, "WTRRAW" + d["basin"], water_in)
            if d.get("water_yield"):
                io("OutputActivityRatio", t, "WTRSUP" + d["basin"], d["water_yield"])
            continue
        if t.startswith("PWRWND"):
            sc = d.get("cf_scale", 1.0)
            cf = lambda s, b, y, sc=sc: min(0.95, K.WIND_SEASON[K.SEASONS[s][0]] * K.WIND_BRACKET[K.BRACKETS[b][0]] * sc)
        elif t.startswith("PWRSOL"):
            cf = lambda s, b, y: {"N": 0.0, "D": K.SOLAR_DAY[K.SEASONS[s][0]], "P": K.SOLAR_PEAK}[K.BRACKETS[b][0]]
        else:
            cf = d.get("cf", 0.90)
        avail = 0.85 if t in fossil else (0.95 if t in ("PWRGEO",) else None)
        if t == "PWRGEO":
            cf = 0.82
        setup(t, d["name"], residual=res, capex=capex, fom=d.get("fom"), vom=d.get("vom"), life=d["life"],
              maxcap=maxcap, maxinv=maxinv, first=first, cf=cf, avail=avail)
        out = "ELCFIN" if t == "PWRSOLDG" else "ELCTX"
        io("OutputActivityRatio", t, out, 1)
        if d.get("fuel"):
            io("InputActivityRatio", t, d["fuel"], 1 / d["eff"])
        if sw["re100"] and t in fossil:
            m.yearly("TotalTechnologyAnnualActivityUpperLimit", (R, t), lambda y: None if y < 2035 else 0.0)
            # Standby firm capacity may still be built: a strict no-new-fossil variant is infeasible at the
            # 18% reserve margin (geothermal drilling pace and zero battery firm credit), see README.

    # ---- battery storage
    B = K.BATTERY
    m.storage["BATT"] = "Grid battery energy storage"
    setup("BATSTOR", "Grid battery (charge mode 1, discharge mode 2)", residual=0.0,
          capex=lambda y: interp(B["capex_power"], y), fom=B["fom"], life=B["life"],
          maxinv=lambda y: interp(B["maxinv"], y), first=B["first"])
    m.yearly("InputActivityRatio", (R, "BATSTOR", "ELCTX", 1), lambda y: 1.0)
    m.yearly("OutputActivityRatio", (R, "BATSTOR", "ELCTX", 2), lambda y: B["rte"])
    m.add("TechnologyToStorage", R, "BATSTOR", "BATT", 1, 1)
    m.add("TechnologyFromStorage", R, "BATSTOR", "BATT", 2, 1)
    m.yearly("CapitalCostStorage", (R, "BATT"), lambda y: interp(B["capex_energy"], y) * K.GWh_PER_PJ)
    m.add("OperationalLifeStorage", R, "BATT", B["life"])
    m.add("DiscountRateStorage", R, "BATT", K.DISCOUNT_RATE)
    m.add("StorageLevelStart", R, "BATT", 0)
    m.add("StorageMaxChargeRate", R, "BATT", 999)
    m.add("StorageMaxDischargeRate", R, "BATT", 999)
    m.yearly("ResidualStorageCapacity", (R, "BATT"), lambda y: 0.0)
    m.yearly("MinStorageCharge", (R, "BATT"), lambda y: 0.0)

    # ---- reserve margin
    # OSeMOSYS compares firm capacity with the PRODUCTION of the tagged fuel in each time slice. Tagging
    # transmission-level electricity would let surplus wind/solar output raise the requirement (and make
    # load shedding a way to lower it). Tagging delivered electricity (ELCFIN: grid deliveries, rooftop PV
    # and any unserved energy) ties the margin to demand; dividing by T&D efficiency grosses it up for losses.
    m.yearly("ReserveMargin", (R,), lambda y: interp(K.RESERVE_MARGIN, y) / td_eff(y))
    m.yearly("ReserveMarginTagFuel", (R, "ELCFIN"), lambda y: 1)
    for t, cc in K.CAPACITY_CREDIT.items():
        if cc > 0:
            m.yearly("ReserveMarginTagTechnology", (R, t), lambda y, cc=cc: cc)

    # ---- Ethiopia contract floor (take-or-pay)
    m.yearly("TotalTechnologyAnnualActivityLowerLimit", (R, "IMPELCETH"),
             lambda y: None if (y < 2027 or y > K.ETH_CONTRACT_END) else 0.4 * K.ETH_TAKE_OR_PAY_CF * K.CAP2ACT_POWER)

    # ---- base-year calibration
    for t, (kind, gwh) in K.CALIB_2025_GWH.items():
        par = "TotalTechnologyAnnualActivityUpperLimit" if kind == "up" else "TotalTechnologyAnnualActivityLowerLimit"
        m.add(par, R, t, 2025, round(gwh / K.GWh_PER_PJ, 6))

    # ---- emissions policy
    if sw["netzero"]:
        m.yearly("AnnualEmissionLimit", (R, "CO2"),
                 lambda y: None if y < 2030 else interp({2030: 1500.0, 2050: 0.0, 2075: 0.0}, y))

    # ---- WATER, per basin
    E = 0.0036   # PJ per (kWh/m3 x MCM)
    mun = lambda y, b: interp(K.MUN_WATER_PER_CAP, y) * pop[y] * K.POP_SHARE[b]
    for b in K.BASINS:
        for f, d, u in [("WTRRAW", "Renewable surface water", "MCM"), ("WTRSUP", "Bulk water supply", "MCM"),
                        ("WTRMUN", "Municipal, industrial and livestock water delivered", "MCM"),
                        ("WTRIRR", "Irrigation water at field", "MCM")]:
            m.fuel(f + b, f"{d}, {K.BASIN_NAMES[b]} basin", u)
        runoff = lambda y, b=b: nwmp(K.RUNOFF[b], y) * climate(sw, "runoff", y, b)

        setup("WSRF" + b, f"Surface runoff net of ecological reserve, {b}", capunit="MCM/yr", actunit="MCM",
              c2a=1, residual=1e5, act_up=lambda y, r=runoff: (1 - K.ENV_RESERVE) * r(y))
        io("OutputActivityRatio", "WSRF" + b, "WTRRAW" + b, 1)

        setup("WROR" + b, f"Run-of-river abstraction, {b}", capunit="MCM/yr", actunit="MCM", c2a=1,
              residual=1e5, act_up=lambda y, r=runoff: K.ROR_SHARE * r(y))
        io("InputActivityRatio", "WROR" + b, "WTRRAW" + b, 1)
        io("OutputActivityRatio", "WROR" + b, "WTRSUP" + b, 1)

        setup("WDAM" + b, f"Dam storage yield, {b}", capunit="MCM/yr", actunit="MCM", c2a=1, life=80,
              residual=K.DAM_RESIDUAL[b], capex=K.CAPEX_DAM, fom=0.02, first=2027,
              maxcap=lambda y, r=runoff, b=b: max(K.DAM_RESIDUAL[b], (1 - K.ENV_RESERVE - K.ROR_SHARE) * r(y)))
        io("InputActivityRatio", "WDAM" + b, "WTRRAW" + b, 1)
        io("OutputActivityRatio", "WDAM" + b, "WTRSUP" + b, 1)

        gwy = lambda y, b=b: nwmp(K.GW_YIELD[b], y) * (climate(sw, "runoff", y, b) if sw["dry"] else 1.0)
        gw_res = min(K.GW_SHARE_MUN_2025[b] * mun2025[b] / K.MUN_DELIVERY_EFF, nwmp(K.GW_YIELD[b], 2025))
        setup("WGWT" + b, f"Groundwater abstraction, {b}", capunit="MCM/yr", actunit="MCM", c2a=1, life=25,
              residual=gw_res, capex=K.CAPEX_GW, fom=0.02,
              maxcap=lambda y, f=gwy, r=gw_res: max(r, f(y)), act_up=gwy, first=2026)
        io("InputActivityRatio", "WGWT" + b, "ELCFIN", K.KWH_M3_GW * E)
        io("OutputActivityRatio", "WGWT" + b, "WTRSUP" + b, 1)

        setup("WTRT" + b, f"Municipal treatment and distribution, {b}", capunit="MCM/yr", actunit="MCM", c2a=1,
              life=40, residual=1.05 * mun2025[b], capex=K.CAPEX_WTP, fom=0.03, first=2026)
        io("InputActivityRatio", "WTRT" + b, "WTRSUP" + b, 1 / K.MUN_DELIVERY_EFF)
        io("InputActivityRatio", "WTRT" + b, "ELCFIN", K.KWH_M3_TREAT_DIST * E)
        io("OutputActivityRatio", "WTRT" + b, "WTRMUN" + b, 1)
        m.yearly("AccumulatedAnnualDemand", (R, "WTRMUN" + b), lambda y, b=b: mun(y, b))

        setup("WUNS" + b, f"Unserved municipal water (backstop), {b}", capunit="MCM/yr", actunit="MCM", c2a=1,
              residual=1e5, vom=K.UNSERVED_WATER_COST)
        io("OutputActivityRatio", "WUNS" + b, "WTRMUN" + b, 1)

        setup("WIRS" + b, f"Surface/furrow irrigation conveyance, {b}", capunit="MCM/yr", actunit="MCM", c2a=1,
              life=30, residual=1.1 * irr_net_2025[b] + 1, capex=K.CAPEX_IRR_SURFACE, fom=0.01, first=2026)
        io("InputActivityRatio", "WIRS" + b, "WTRSUP" + b, 1 / K.IRR_EFF_SURFACE)
        io("InputActivityRatio", "WIRS" + b, "ELCFIN", K.KWH_M3_IRR_SURFACE / K.IRR_EFF_SURFACE * E)
        io("OutputActivityRatio", "WIRS" + b, "WTRIRR" + b, 1)

        setup("WIRD" + b, f"Drip/sprinkler irrigation, {b}", capunit="MCM/yr", actunit="MCM", c2a=1, life=15,
              residual=0.0, capex=K.CAPEX_IRR_DRIP, fom=0.02, first=2026)
        io("InputActivityRatio", "WIRD" + b, "WTRSUP" + b, 1 / K.IRR_EFF_DRIP)
        io("InputActivityRatio", "WIRD" + b, "ELCFIN", K.KWH_M3_IRR_DRIP / K.IRR_EFF_DRIP * E)
        io("OutputActivityRatio", "WIRD" + b, "WTRIRR" + b, 1)

        setup("WIRU" + b, f"Irrigation water deficit (backstop), {b}", capunit="MCM/yr", actunit="MCM", c2a=1,
              residual=1e5, vom=K.IRRIGATION_DEFICIT_COST)
        io("OutputActivityRatio", "WIRU" + b, "WTRIRR" + b, 1)

    setup("WTRFTA", "Inter-basin transfer Tana to Athi (Nairobi supply)", capunit="MCM/yr", actunit="MCM", c2a=1,
          life=60, residual=K.TRANSFER_TAN_ATH_RESIDUAL, capex=K.CAPEX_TRANSFER, fom=0.01,
          maxcap=K.TRANSFER_TAN_ATH_MAX, first=2027)
    io("InputActivityRatio", "WTRFTA", "WTRSUPTAN", 1)
    io("InputActivityRatio", "WTRFTA", "ELCFIN", K.KWH_M3_TRANSFER * E)
    io("OutputActivityRatio", "WTRFTA", "WTRSUPATH", 1)

    setup("WDESATH", "Seawater desalination, Mombasa (Athi basin)", capunit="MCM/yr", actunit="MCM", c2a=1,
          life=25, residual=0.0, capex=lambda y: interp(K.CAPEX_DESAL, y), fom=0.15,
          maxcap=lambda y: interp(K.DESAL_MAX, y), first=2030)
    io("InputActivityRatio", "WDESATH", "ELCFIN", lambda y: interp(K.KWH_M3_DESAL, y) * E)
    io("OutputActivityRatio", "WDESATH", "WTRSUPATH", 1)

    # ---- LAND, per basin
    built = lambda y, b: K.BUILT_2025_TOTAL * K.POP_SHARE[b] * pop[y] / pop[2025] * 1.01 ** (y - 2025)
    irr_target = {2025: 288.0, 2035: 690.0, 2050: 1000.0, 2075: 1000.0}   # kha, NISIP
    pot_total = sum(K.IRR_POTENTIAL.values())
    irr_base = sum(K.IRR_RESIDUAL.values())
    rem_total = sum(K.IRR_POTENTIAL[b] - K.IRR_RESIDUAL[b] for b in K.BASINS)
    irr_new = {}   # IRRIG only: new scheme area per basin, which must be cropped
    for b in K.BASINS:
        for f, d in [("LND", "Total land"), ("LCRP", "Cropland"), ("LIRR", "Irrigated cropland (equipped)")]:
            m.fuel(f + b, f"{d}, {K.BASIN_NAMES[b]} basin", "kha")
        area = K.BASIN_AREA_KHA[b]
        setup("LSUP" + b, f"Land supply, {b}", capunit="kha", actunit="kha", c2a=1, residual=area,
              act_up=lambda y, a=area: a)
        io("OutputActivityRatio", "LSUP" + b, "LND" + b, 1)

        setup("LCRS" + b, f"Cropland (suitable land converted), {b}", capunit="kha", actunit="kha", c2a=1,
              residual=K.CROPLAND_MAX[b], act_up=lambda y, c=K.CROPLAND_MAX[b]: c)
        io("InputActivityRatio", "LCRS" + b, "LND" + b, 1)
        io("OutputActivityRatio", "LCRS" + b, "LCRP" + b, 1)

        share = K.IRR_POTENTIAL[b] / pot_total
        mincap, maxinv = None, K.IRR_MAX_NEW_NATIONAL * share
        if sw["irrig"]:
            # new area allocated by each basin's remaining potential, with build pace to match the national target
            rem = (K.IRR_POTENTIAL[b] - K.IRR_RESIDUAL[b]) / rem_total
            req = lambda y, b=b, rem=rem: K.IRR_RESIDUAL[b] + max(0.0, interp(irr_target, y) - irr_base) * rem
            mincap = req
            irr_new[b] = lambda y, b=b, rem=rem: max(0.0, interp(irr_target, y) - irr_base) * rem
            maxinv = 1.10 * max(interp(irr_target, y) - interp(irr_target, y - 1) for y in Y[1:]) * rem
        setup("LIRS" + b, f"Irrigation scheme development, {b}", capunit="kha", actunit="kha", c2a=1, life=30,
              residual=K.IRR_RESIDUAL[b], capex=K.IRR_CAPEX, fom=0.15, maxcap=K.IRR_POTENTIAL[b],
              maxinv=maxinv, first=2026, mincap=mincap,
              act_lo=(lambda y, f=mincap: 0.9 * f(y)) if sw["irrig"] else None)
        io("InputActivityRatio", "LIRS" + b, "LCRP" + b, 1)
        io("OutputActivityRatio", "LIRS" + b, "LIRR" + b, 1)

        setup("LFOR" + b, f"Existing forest (protected), {b}", capunit="kha", actunit="kha", c2a=1,
              residual=K.FOREST_2025[b], act_lo=lambda y, f=K.FOREST_2025[b]: f * 0.999)
        io("InputActivityRatio", "LFOR" + b, "LND" + b, 1)

        setup("LAFF" + b, f"Afforestation and restoration, {b}", capunit="kha", actunit="kha", c2a=1, life=40,
              residual=0.0, capex=K.AFF_CAPEX, fom=0.03, maxcap=K.AFF_MAX[b], first=2027)
        io("InputActivityRatio", "LAFF" + b, "LND" + b, 1)
        m.yearly("EmissionActivityRatio", (R, "LAFF" + b, "CO2", 1), lambda y: K.AFF_REMOVAL)

        setup("LBLT" + b, f"Built-up land, {b}", capunit="kha", actunit="kha", c2a=1, residual=area,
              act_lo=lambda y, b=b: built(y, b))
        io("InputActivityRatio", "LBLT" + b, "LND" + b, 1)

        ocr = K.OTHER_CROPS_2025 * K.POP_SHARE[b]
        setup("LOCR" + b, f"Other crops (cassava, pulses etc., fixed), {b}", capunit="kha", actunit="kha", c2a=1,
              residual=ocr, act_lo=lambda y, a=ocr: a * 0.999)
        io("InputActivityRatio", "LOCR" + b, "LCRP" + b, 1)

    # ---- CROPS
    def retain(base, y):
        """Existing crop area can shrink by at most CROP_AREA_MAX_DECLINE of its 2025 level per year."""
        if y == 2025:
            return 0.98 * base
        return base * max(0.5, 1 - K.CROP_AREA_MAX_DECLINE * (y - 2025)) * 0.98
    m.fuel("FERTN", "Nitrogen fertiliser", "kt N")
    setup("IMPFERT", "Imported nitrogen fertiliser", capunit="kt/yr", actunit="kt N", c2a=1, residual=1e5,
          vom=K.FERT_IMPORT_COST)
    io("OutputActivityRatio", "IMPFERT", "FERTN", 1)
    setup("GNH3", "Green ammonia fertiliser plant (electrolysis + Haber-Bosch)", capunit="kt N/yr",
          actunit="kt N", c2a=1, life=25, residual=0.0, capex=lambda y: interp(K.GNH3_CAPEX, y),
          fom=lambda y: 0.03 * interp(K.GNH3_CAPEX, y), first=2028)
    io("InputActivityRatio", "GNH3", "ELCFIN", K.GNH3_PJ_PER_KTN)
    io("InputActivityRatio", "GNH3", "WTRSUPRVB", K.GNH3_WATER_MCM_PER_KTN)
    io("OutputActivityRatio", "GNH3", "FERTN", 1)

    for c, (name, yr, yi, cr, ci, nr, ni, mm, dem, impc, kind) in K.CROPS.items():
        m.fuel("CRP" + c, name, "kt")
        if kind == "food":
            dfn = lambda y, dem=dem: dem * pop[y] / pop[2025]
        else:
            dfn = lambda y, dem=dem: dem * interp(K.EXPORT_DEMAND_GROWTH, y)
        m.yearly("AccumulatedAnnualDemand", (R, "CRP" + c), dfn)
        t = "IMP" + c
        setup(t, f"Import of {name}" + (" (slack for export crops)" if kind == "export" else ""),
              capunit="kt/yr", actunit="kt", c2a=1, residual=1e5, vom=impc / 1000)   # < MUIO's 999,999 cap
        io("OutputActivityRatio", t, "CRP" + c, 1)

        for b in K.BASINS:
            base = K.RAINFED_AREA_2025[c] * K.RAINFED_SHARE[c].get(b, 0.0)
            if base > 0:
                t = f"C{c}R{b}"
                cap = base * K.RAINFED_EXPANSION_CAP
                setup(t, f"{name}, rainfed, {b}", capunit="kha", actunit="kha", c2a=1, residual=cap,
                      vom=cr / 1000, act_up=lambda y, c_=cap: c_,
                      act_lo=lambda y, bs=base: retain(bs, y))
                io("InputActivityRatio", t, "LCRP" + b, 1)
                io("InputActivityRatio", t, "FERTN", nr / 1000)
                yld = lambda y, yr=yr: yr * interp(K.RAINFED_YIELD_GROWTH, y) * climate(sw, "yield", y)
                io("OutputActivityRatio", t, "CRP" + c, yld)
                if c == "SUG":
                    io("OutputActivityRatio", t, "BAG", lambda y, f=yld: f(y) * K.BAGASSE_PJ_PER_KT_CANE)
            ibase = K.IRRIGATED_AREA_2025.get(c, {}).get(b, 0.0)
            allowed = c in K.IRRIGABLE_CROPS and (ibase > 0 or c in ("HOR", "MAI"))
            if allowed:
                t = f"C{c}I{b}"
                lo = (lambda y, bs=ibase: retain(bs, y)) if ibase else None
                if b in irr_new and c in ("MAI", "RIC", "HOR"):
                    # NISIP: 85% of new scheme area cropped, split maize 40%, rice 30% (where rice schemes
                    # exist, otherwise horticulture), horticulture the rest [ASSUMP]
                    has_rice = K.IRRIGATED_AREA_2025.get("RIC", {}).get(b, 0) > 0
                    sh = {"MAI": 0.40, "RIC": 0.30 if has_rice else 0.0, "HOR": 0.30 if has_rice else 0.60}[c]
                    lo = lambda y, bs=ibase, sh=sh, nw=irr_new[b]: (retain(bs, y) if bs else 0.0) + 0.85 * sh * nw(y)
                setup(t, f"{name}, irrigated, {b}", capunit="kha", actunit="kha", c2a=1, residual=1e4,
                      vom=ci / 1000, act_lo=lo)
                io("InputActivityRatio", t, "LIRR" + b, 1)
                io("InputActivityRatio", t, "WTRIRR" + b, mm / 100)
                io("InputActivityRatio", t, "FERTN", ni / 1000)
                yld = lambda y, yi=yi: yi * interp(K.IRRIGATED_YIELD_GROWTH, y)
                io("OutputActivityRatio", t, "CRP" + c, yld)
                if c == "SUG":
                    io("OutputActivityRatio", t, "BAG", lambda y, f=yld: f(y) * K.BAGASSE_PJ_PER_KT_CANE)

    meta = dict(base_nonwater_PJ=base_nonwater, water_elec_2025_PJ=water_elec_2025,
                demand_PJ={y: demand[y] for y in (2025, 2030, 2050, 2075)})
    return m, ts, tsname, meta


def write(m, ts, tsname, outdir):
    cfg = yaml.safe_load(open(CONFIG))
    outdir.mkdir(parents=True, exist_ok=True)
    sets = {
        "REGION": [R], "YEAR": Y, "TECHNOLOGY": list(m.techs), "FUEL": list(m.fuels),
        "EMISSION": list(m.emis), "MODE_OF_OPERATION": [1, 2], "TIMESLICE": [tsname[x] for x in ts],
        "SEASON": list(K.SEASONS), "DAYTYPE": [1], "DAILYTIMEBRACKET": list(K.BRACKETS), "STORAGE": list(m.storage),
    }
    for name, vals in sets.items():
        pd.DataFrame({"VALUE": vals}).to_csv(outdir / f"{name}.csv", index=False)
    for name, spec in cfg.items():
        if spec["type"] != "param":
            continue
        cols = spec["indices"] + ["VALUE"]
        rows = m.p.get(name, [])
        df = pd.DataFrame(rows, columns=cols)
        if not df.empty:
            df = df.drop_duplicates(subset=spec["indices"], keep="last")
        df.to_csv(outdir / f"{name}.csv", index=False)
    unknown = set(m.p) - set(cfg)
    if unknown:
        raise ValueError(f"parameters not in config: {unknown}")


def main(args):
    scens = args or list(SCENARIOS)
    for s in scens:
        m, ts, tsname, meta = build(s)
        out = ROOT / "data" / "csv" / s
        write(m, ts, tsname, out)
        # descriptive registry used by the MUIO exporter and the README
        pd.DataFrame([(t, d, *m.units[t]) for t, d in m.techs.items()],
                     columns=["TECHNOLOGY", "DESCRIPTION", "UNITOFCAPACITY", "UNITOFACTIVITY"]).to_csv(
            out.parent / f"_{s}_technologies.csv", index=False)
        pd.DataFrame([(f, d, u) for f, (d, u) in m.fuels.items()], columns=["FUEL", "DESCRIPTION", "UNIT"]).to_csv(
            out.parent / f"_{s}_commodities.csv", index=False)
        print(f"{s}: {len(m.techs)} technologies, {len(m.fuels)} commodities | "
              f"non-water grid demand 2025 {meta['base_nonwater_PJ']:.2f} PJ, water-sector electricity 2025 "
              f"{meta['water_elec_2025_PJ']:.2f} PJ | demand PJ {', '.join(f'{k}:{v:.1f}' for k, v in meta['demand_PJ'].items())}")


if __name__ == "__main__":
    main(sys.argv[1:])
