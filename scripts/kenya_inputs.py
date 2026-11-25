"""
Kenya CLEWs (KECLEWS) input assumptions, 2025-2075.

Every number here carries a source tag in its comment:
  [EPRA25]  EPRA Energy & Petroleum Statistics Report FY2024/25
  [WPP24]   UN World Population Prospects 2024, medium variant
  [LCPDP]   Least Cost Power Development Plan 2024-2043 (MoEP)
  [IRENA]   IRENA Renewable Power Generation Costs in 2024
  [ATB]     NREL Annual Technology Baseline 2024 (moderate)
  [NWMP]    National Water Master Plan 2030 (JICA/WRMA, 2013)
  [KNBS]    KNBS Economic Survey 2025 / National Agriculture Production Report 2025
  [NIA]     National Irrigation Authority / NISIP 2025-2035
  [FAO]     FAOSTAT / AQUASTAT / FAO-56 crop water guidance
  [IPCC]    IPCC 2006 default emission factors
  [MAC21]   Macharia et al. 2021, Energies 14:2169 (energy intensity of Kenyan water supply)
  [COMPACT] Kenya National Energy Compact, Aug 2025 (Mission 300)
  [ASSUMP]  Model assumption by the author; see DATA_SOURCES.md for reasoning

Units
  energy PJ, power capacity GW, money million USD (2025 real), water MCM (million m3),
  land kha (thousand hectares), crops kt, fertiliser kt N, emissions kt CO2.
"""

YEARS = list(range(2025, 2076))
REGION = "KEN"
DISCOUNT_RATE = 0.10                     # [ASSUMP] real social discount rate, close to LCPDP practice
GWh_PER_PJ = 277.7778
CAP2ACT_POWER = 31.536                   # PJ per GW-year

# ----------------------------------------------------------------------------------
# Time slices: 4 seasons x 1 day type x 3 daily brackets  [EPRA25 load shape]
# ----------------------------------------------------------------------------------
SEASONS = {1: ("S1", 90, "Jan-Mar hot/dry"), 2: ("S2", 91, "Apr-Jun long rains"),
           3: ("S3", 92, "Jul-Sep cool/dry"), 4: ("S4", 92, "Oct-Dec short rains")}
BRACKETS = {1: ("N", 8, "Night 22:00-06:00"), 2: ("D", 12, "Day 06:00-18:00"),
            3: ("P", 4, "Evening peak 18:00-22:00")}
# Average grid load by bracket (MW, FY2024/25) [EPRA25]: night ~1,350, day ~1,750, evening ~2,250
BRACKET_LOAD = {"N": 1350, "D": 1750, "P": 2250}
SEASON_LOAD = {"S1": 1.01, "S2": 0.99, "S3": 0.99, "S4": 1.01}   # flat monthly sales [EPRA25]

# ----------------------------------------------------------------------------------
# Population and the demand rule  [WPP24]
# ----------------------------------------------------------------------------------
POP_GROWTH_PCT = [
    1.916, 1.886, 1.863, 1.834, 1.809, 1.783, 1.761, 1.724, 1.691, 1.650,   # 2025-2034
    1.612, 1.573, 1.529, 1.495, 1.447, 1.410, 1.365, 1.325, 1.278, 1.236,   # 2035-2044
    1.191, 1.156, 1.121, 1.088, 1.061, 1.035, 1.008, 0.977, 0.952, 0.925,   # 2045-2054
    0.905, 0.883, 0.872, 0.851, 0.823, 0.799, 0.777, 0.750, 0.715, 0.689,   # 2055-2064
    0.658, 0.634, 0.603, 0.577, 0.546, 0.519, 0.494, 0.469, 0.434, 0.410,   # 2065-2074
    0.386]                                                                   # 2075
POP_2026_M = 58.64                        # [WPP24]
DEMAND_MULTIPLIER = 3.0                   # user rule: electricity growth = 3 x population growth

# Grid baseline FY2024/25 [EPRA25]
SENT_OUT_GWH_2025 = 14472.0               # incl. imports
SALES_GWH_2025 = 11329.75                 # final grid consumption
PEAK_MW_2025 = 2316.2
# T&D delivery efficiency (sales / sent-out). 0.783 in 2025 [EPRA25];
# path to EPRA allowable losses (17.5%) by 2035 and 14% by 2050 [ASSUMP]
TD_EFF = {2025: 0.783, 2030: 0.80, 2035: 0.825, 2050: 0.86, 2075: 0.86}

# LCPDP Reference sensitivity: 6.6%/yr to 2043 [LCPDP], then the 3x rule
LCPDP_GROWTH_TO_2043 = 0.066

# ----------------------------------------------------------------------------------
# Basins  [NWMP]
# ----------------------------------------------------------------------------------
BASINS = ["LVN", "LVS", "RVB", "ATH", "TAN", "ENN"]
BASIN_NAMES = {"LVN": "Lake Victoria North", "LVS": "Lake Victoria South", "RVB": "Rift Valley",
               "ATH": "Athi", "TAN": "Tana", "ENN": "Ewaso Ng'iro North"}
BASIN_AREA_KHA = {"LVN": 1837.4, "LVS": 3173.4, "RVB": 13045.2, "ATH": 5863.9,
                  "TAN": 12602.6, "ENN": 21022.6}                       # [NWMP] km2/10
# Population share by basin, from 2019 county census mapped to basins [ASSUMP]
POP_SHARE = {"LVN": 0.17, "LVS": 0.20, "RVB": 0.14, "ATH": 0.25, "TAN": 0.18, "ENN": 0.06}

# Water resources (MCM/yr) at 2010 / 2030 / 2050 [NWMP Table: surface runoff, GW sustainable yield]
RUNOFF = {"LVN": (4626, 4969, 5455), "LVS": (4773, 5749, 7005), "RVB": (2457, 3045, 3794),
          "ATH": (1198, 1334, 1711), "TAN": (5858, 7261, 7383), "ENN": (1725, 2536, 1361)}
GW_YIELD = {"LVN": (116, 108, 140), "LVS": (203, 188, 190), "RVB": (102, 102, 109),
            "ATH": (305, 300, 332), "TAN": (675, 567, 508), "ENN": (526, 475, 449)}
ENV_RESERVE = 0.30          # share of runoff kept as ecological reserve [ASSUMP, NWMP gives reserve first priority]
ROR_SHARE = 0.25            # share of runoff abstractable without storage [ASSUMP]
# Existing regulated yield from dams and weirs, MCM/yr [ASSUMP]
DAM_RESIDUAL = {"LVN": 50, "LVS": 60, "RVB": 150, "ATH": 250, "TAN": 600, "ENN": 10}
TRANSFER_TAN_ATH_RESIDUAL = 230         # Thika/Ndakaini/Chania to Nairobi, MCM/yr [ASSUMP]
TRANSFER_TAN_ATH_MAX = 800              # incl. Northern Collector Tunnel phases [ASSUMP]

# Municipal + industrial + livestock water per person (m3/yr) [ASSUMP calibrated to NWMP sector totals]
MUN_WATER_PER_CAP = {2025: 35.0, 2050: 50.0, 2075: 50.0}
GW_SHARE_MUN_2025 = {"LVN": 0.20, "LVS": 0.20, "RVB": 0.30, "ATH": 0.55, "TAN": 0.20, "ENN": 0.80}

# Energy intensity of water [MAC21]
KWH_M3_TREAT_DIST = 0.15    # surface treatment + distribution
KWH_M3_GW = 0.60            # borehole pumping 150-200 m
KWH_M3_DESAL = {2025: 3.5, 2040: 3.0, 2075: 3.0}
KWH_M3_TRANSFER = 0.30      # [ASSUMP]
KWH_M3_IRR_SURFACE = 0.05   # gravity-fed with some lifting [ASSUMP]
KWH_M3_IRR_DRIP = 0.35      # pressurised [ASSUMP]
IRR_EFF_SURFACE = 0.50      # [FAO]
IRR_EFF_DRIP = 0.85         # [FAO]
MUN_DELIVERY_EFF = 0.80     # physical losses in networks [ASSUMP]

# Water infrastructure costs, M$ per MCM/yr of capacity [ASSUMP from Kenyan project costs]
CAPEX_DAM = 1.5; CAPEX_GW = 0.5; CAPEX_WTP = 1.0; CAPEX_TRANSFER = 1.5
CAPEX_DESAL = {2025: 5.5, 2040: 4.0, 2075: 4.0}
CAPEX_IRR_SURFACE = 0.15; CAPEX_IRR_DRIP = 0.35
DESAL_MAX = {2025: 0, 2029: 0, 2030: 50, 2035: 150, 2050: 500, 2075: 700}   # MCM/yr, Mombasa [ASSUMP]
UNSERVED_WATER_COST = 20.0  # M$/MCM = 20 $/m3 backstop

# ----------------------------------------------------------------------------------
# Land  [FAO, KNBS, KFS]
# ----------------------------------------------------------------------------------
FOREST_2025 = {"LVN": 250, "LVS": 400, "RVB": 1100, "ATH": 350, "TAN": 950, "ENN": 560}   # kha, sums to FAO 3.61 Mha
BUILT_2025_TOTAL = 300.0       # kha [ASSUMP]
CROPLAND_MAX = {"LVN": 1500, "LVS": 2000, "RVB": 3500, "ATH": 2000, "TAN": 2800, "ENN": 800}   # suitable kha [ASSUMP; replace with GAEZ]
OTHER_CROPS_2025 = 1000.0      # cassava, peas, groundnut etc. held fixed, kha [ASSUMP]
AFF_MAX = {"LVN": 50, "LVS": 150, "RVB": 800, "ATH": 400, "TAN": 700, "ENN": 900}         # restorable kha [ASSUMP]
AFF_CAPEX = 0.6                # M$/kha (600 $/ha) [ASSUMP]
AFF_REMOVAL = -5.0             # kt CO2 per kha per yr [IPCC Tier 1 range]

# Irrigation infrastructure (kha)
IRR_RESIDUAL = {"LVN": 2.5, "LVS": 30.0, "RVB": 60.0, "ATH": 76.5, "TAN": 104.0, "ENN": 15.0}   # sums to 288 [NIA, FAO]
IRR_POTENTIAL = {"LVN": 60, "LVS": 200, "RVB": 180, "ATH": 250, "TAN": 500, "ENN": 150}         # sums to 1,340 [NWMP total; split ASSUMP]
IRR_CAPEX = 10.0               # M$/kha = 10,000 $/ha [NIA/NISIP cost range]
IRR_MAX_NEW_NATIONAL = 40.0    # kha/yr [NIA pace]

# ----------------------------------------------------------------------------------
# Crops [KNBS 2024 production; yields derived]
#   code: (name, rainfed yield t/ha, irrigated yield t/ha, cost rainfed $/ha, cost irrigated $/ha,
#          N rainfed kg/ha, N irrigated kg/ha, net irrigation mm, demand 2025 kt, import cost $/t, demand type)
# ----------------------------------------------------------------------------------
CROPS = {
    "MAI": ("Maize", 1.7, 5.0, 450, 1200, 25, 120, 300, 4500, 320, "food"),
    "BEA": ("Beans", 0.8, 1.5, 350, 900, 10, 20, 250, 1000, 850, "food"),
    "WHT": ("Wheat", 2.5, 4.5, 600, 1100, 60, 100, 250, 2300, 330, "food"),
    "RIC": ("Rice (paddy)", 2.0, 5.0, 700, 1500, 30, 120, 1000, 1200, 450, "food"),
    "POT": ("Irish potato", 10.0, 20.0, 1200, 2500, 60, 120, 300, 2200, 400, "food"),
    "SUG": ("Sugarcane", 50.0, 100.0, 900, 1800, 80, 120, 900, 11000, 60, "food"),
    "TEA": ("Tea (green leaf)", 11.8, 11.8, 2500, 2500, 150, 150, 0, 2700, 3000, "export"),
    "COF": ("Coffee", 0.45, 0.8, 1500, 2500, 80, 100, 0, 50, 8000, "export"),
    "HOR": ("Horticulture & flowers", 12.0, 25.0, 2500, 5000, 80, 150, 450, 7800, 2000, "export"),
    "SOR": ("Sorghum & millet", 0.9, 2.5, 300, 900, 10, 50, 250, 450, 350, "food"),
}
# Rainfed area 2025 (kha) and basin shares [KNBS national areas; basin split ASSUMP]
RAINFED_AREA_2025 = {"MAI": 2350, "BEA": 1100, "WHT": 120, "RIC": 15, "POT": 220, "SUG": 137,
                     "TEA": 228, "COF": 110, "HOR": 330, "SOR": 450}
RAINFED_SHARE = {
    "MAI": {"LVN": .30, "LVS": .18, "RVB": .30, "ATH": .07, "TAN": .13, "ENN": .02},
    "BEA": {"LVN": .18, "LVS": .17, "RVB": .20, "ATH": .15, "TAN": .27, "ENN": .03},
    "WHT": {"LVN": .05, "RVB": .70, "TAN": .10, "ENN": .15},
    "RIC": {"LVN": .30, "LVS": .50, "ATH": .20},
    "POT": {"LVN": .10, "LVS": .10, "RVB": .35, "TAN": .35, "ENN": .10},
    "SUG": {"LVN": .55, "LVS": .35, "RVB": .05, "TAN": .05},
    "TEA": {"LVN": .10, "LVS": .45, "RVB": .05, "TAN": .40},
    "COF": {"LVN": .05, "LVS": .15, "RVB": .05, "ATH": .15, "TAN": .60},
    "HOR": {"LVN": .10, "LVS": .15, "RVB": .20, "ATH": .20, "TAN": .30, "ENN": .05},
    "SOR": {"LVN": .10, "LVS": .25, "RVB": .20, "ATH": .20, "TAN": .20, "ENN": .05},
}
# Irrigated crop area 2025 by basin (kha) [NIA schemes; ASSUMP split]
IRRIGATED_AREA_2025 = {
    "RIC": {"LVN": 2.5, "LVS": 15.0, "ATH": 5.0, "TAN": 27.5},
    "MAI": {"RVB": 12.0, "ATH": 24.0, "TAN": 24.0},
    "SUG": {"LVS": 7.5, "ATH": 10.0, "TAN": 7.5},
    "HOR": {"LVS": 7.5, "RVB": 45.0, "ATH": 37.5, "TAN": 45.0, "ENN": 15.0},
    "WHT": {"RVB": 3.0},
}
IRRIGABLE_CROPS = ["RIC", "MAI", "SUG", "HOR", "WHT"]
RAINFED_EXPANSION_CAP = 1.6       # max rainfed area per crop-basin vs 2025 [ASSUMP]
RAINFED_YIELD_GROWTH = {2025: 1.0, 2050: 1.28, 2075: 1.36}   # [ASSUMP] ~1%/yr to 2050
IRRIGATED_YIELD_GROWTH = {2025: 1.0, 2050: 1.13, 2075: 1.18}
EXPORT_DEMAND_GROWTH = {2025: 1.0, 2050: 1.45, 2075: 1.65}   # tea/coffee/horticulture [ASSUMP]
FERT_IMPORT_COST = 1.1            # M$/kt N (urea ~500 $/t product) [ASSUMP]
BAGASSE_PJ_PER_KT_CANE = 0.3 * 7.5e-3 * 0.5   # 0.3 t bagasse/t cane, 7.5 GJ/t, half available for export [ASSUMP]

# Green ammonia (electrolytic hydrogen + Haber-Bosch)
GNH3_PJ_PER_KTN = 14.6 * 3.6e-3   # 14.6 MWh per t N [ASSUMP from 12 MWh/t NH3]
GNH3_WATER_MCM_PER_KTN = 0.0022
GNH3_CAPEX = {2025: 6.5, 2035: 4.0, 2050: 2.4, 2075: 2.2}   # M$ per kt N/yr: PEM ~2,000 $/kW falling to ~600, plus ASU/HB [ASSUMP]

# ----------------------------------------------------------------------------------
# Power technologies
#   residual capacity (GW) as {year: value} (linearly interpolated, 0 after last key unless held)
#   capex $/kW == M$/GW, fixed O&M $/kW/yr == M$/GW/yr, variable M$/PJ, life yr, efficiency
# ----------------------------------------------------------------------------------
FUELS_PRICE = {          # $/GJ == M$/PJ  [ASSUMP from World Bank CMO / IEA WEO trajectories]
    "HFO": {2025: 13.0, 2075: 13.0},
    "DSL": {2025: 20.0, 2075: 20.0},
    "LNG": {2025: 11.0, 2075: 11.5},
    "URN": {2025: 0.8, 2075: 0.8},
}
EMISSION_FACTOR = {"HFO": 77.4, "DSL": 74.1, "LNG": 56.1}   # kt CO2/PJ [IPCC]

POWER = {
    # code: dict
    "PWRGEO": dict(name="Geothermal (flash)", residual={2025: 0.940, 2040: 0.940, 2055: 0.45, 2070: 0.0},
                   capex={2025: 3500, 2050: 3000, 2075: 2900}, fom=110, vom=0.0, life=30, cf=0.80,
                   avail=0.95, maxcap={2025: 10.0}, maxinv={2025: 0.0, 2027: 0.15, 2035: 0.25},
                   first=2027),
    "PWRHYDTAN": dict(name="Hydro Tana cascade (existing)", residual={2025: 0.600, 2075: 0.600},
                      capex=None, fom=45, life=60, basin="TAN", evap=45.0, energy_cf=0.476),
    "PWRHYDRVB": dict(name="Hydro Turkwel and Rift Valley (existing)", residual={2025: 0.126, 2075: 0.126},
                      capex=None, fom=45, life=60, basin="RVB", evap=60.0, energy_cf=0.476),
    "PWRHYDLVS": dict(name="Hydro Sondu Miriu and LVS small (existing)", residual={2025: 0.100, 2075: 0.100},
                      capex=None, fom=45, life=60, basin="LVS", evap=2.0, energy_cf=0.476),
    "PWRHYDLVN": dict(name="Hydro small LVN (existing)", residual={2025: 0.0135, 2075: 0.0135},
                      capex=None, fom=45, life=60, basin="LVN", evap=2.0, energy_cf=0.476),
    "PWRHYDHGF": dict(name="High Grand Falls multipurpose (Tana)", residual={}, capex={2025: 3708, 2075: 3708},
                      fom=40, life=60, basin="TAN", evap=30.0, energy_cf=0.45, maxcap={2025: 0, 2032: 0, 2033: 0.693},
                      first=2033, water_yield=150.0),
    "PWRHYDKAR": dict(name="Karura hydro (Tana)", residual={}, capex={2025: 3889, 2075: 3889},
                      fom=40, life=60, basin="TAN", evap=2.0, energy_cf=0.50, maxcap={2025: 0, 2030: 0, 2031: 0.09}, first=2031),
    "PWRHYDNEW": dict(name="Other multipurpose hydro (Magwagwa, Nandi Forest, Arror)", residual={},
                      capex={2025: 4000, 2075: 4000}, fom=40, life=60, basin="LVS", evap=20.0, energy_cf=0.45,
                      maxcap={2025: 0, 2031: 0, 2032: 0.25}, first=2032),
    "PWRHYDSML": dict(name="New small hydro", residual={}, capex={2025: 3000, 2075: 3000}, fom=60, life=40,
                      basin="TAN", evap=0.0, energy_cf=0.45, maxcap={2025: 0, 2027: 0, 2028: 0.30}, first=2028),
    "PWRWNDT1": dict(name="Wind, Turkana-Marsabit corridor", residual={2025: 0.4355, 2045: 0.4355, 2050: 0.0},
                     capex={2025: 1600, 2050: 1150, 2075: 1100}, fom=40, vom=0.0, life=25, maxcap={2025: 3.0},
                     maxinv={2025: 0.0, 2027: 0.4}, first=2027),
    "PWRWNDT2": dict(name="Wind, other sites", residual={}, capex={2025: 1600, 2050: 1150, 2075: 1100},
                     fom=40, vom=0.0, life=25, maxcap={2025: 8.0}, maxinv={2025: 0.0, 2027: 0.4}, first=2027,
                     cf_scale=0.70),
    "PWRSOL": dict(name="Utility solar PV", residual={2025: 0.2103, 2043: 0.2103, 2045: 0.0},
                   capex={2025: 900, 2050: 450, 2075: 400}, fom=15, vom=0.0, life=25, maxcap={2025: 30.0},
                   maxinv={2025: 0.0, 2027: 0.6, 2035: 1.5}, first=2027),
    "PWRSOLDG": dict(name="Distributed rooftop PV (grid-connected)", residual={},
                     capex={2025: 1000, 2050: 550, 2075: 500}, fom=18, vom=0.0, life=25,
                     maxcap={2025: 0.0, 2026: 0.2, 2050: 4.0, 2075: 6.0}, maxinv={2025: 0.0, 2026: 0.3}, first=2026),
    "PWRDSL": dict(name="Medium-speed diesel/HFO (existing)", residual={2025: 0.5128, 2030: 0.25, 2040: 0.0},
                   capex={2025: 1200, 2075: 1200}, fom=30, vom=2.2, life=25, eff=0.40, fuel="HFO",
                   first=2099),
    "PWROCGDSL": dict(name="Gas turbines on diesel (existing)", residual={2025: 0.052, 2035: 0.052, 2040: 0.0},
                      capex=None, fom=21.5, vom=3.0, life=25, eff=0.30, fuel="DSL"),
    "PWROCGLNG": dict(name="Open-cycle gas turbine, LNG", residual={}, capex={2025: 800, 2075: 750},
                      fom=20, vom=3.0, life=30, eff=0.35, fuel="LNG", maxcap={2025: 0, 2029: 0, 2030: 2.0}, first=2030),
    "PWRCCGLNG": dict(name="Combined-cycle gas turbine, LNG (Dongo Kundu)", residual={},
                      capex={2025: 1380, 2075: 1250}, fom=33, vom=1.0, life=30, eff=0.55, fuel="LNG",
                      maxcap={2025: 0, 2029: 0, 2030: 3.0}, first=2030),
    "PWRNUC": dict(name="Nuclear (large PWR)", residual={}, capex={2025: 7000, 2050: 6000, 2075: 6000},
                   fom=120, vom=0.6, life=60, eff=0.33, fuel="URN",
                   maxcap={2025: 0, 2034: 0, 2035: 1.0, 2040: 1.0, 2045: 2.0, 2075: 4.0}, first=2035, cf=0.88),
    "PWRBAG": dict(name="Bagasse cogeneration (sugar mills)", residual={2025: 0.002, 2075: 0.002},
                   capex={2025: 2000, 2075: 1800}, fom=60, vom=1.0, life=25, eff=0.25, fuel="BAG",
                   maxcap={2025: 0.002, 2026: 0.002, 2027: 1.0}, first=2027, cf=0.65),
    "IMPELCETH": dict(name="Electricity import, Ethiopia (EEP contract)", residual={2025: 0.2, 2026: 0.2, 2027: 0.4, 2075: 0.4},
                      capex=None, fom=0, vom=18.06, life=99, cf=0.85),   # 6.5 USc/kWh [EPRA25, Ecofin 2026]
    "IMPELCEAP": dict(name="Electricity import, Uganda/Tanzania", residual={2025: 0.20, 2075: 0.20},
                      capex=None, fom=0, vom=27.8, life=99, cf=0.60),     # 10 USc/kWh [ASSUMP]
}
# OSeMOSYS sizes storage energy (PJ) and converter power (GW) separately, so each is priced at its own
# real cost; the firm credit below is kept modest because energy duration is not tied to power.
BATTERY = dict(capex_power={2025: 300, 2050: 150, 2075: 140},          # $/kW converter/inverter [ATB]
               capex_energy={2025: 250, 2050: 120, 2075: 110},         # $/kWh cells [ATB moderate]
               fom=8, life=15, rte=0.85, maxinv={2025: 0.0, 2026: 0.3, 2035: 1.0}, first=2026)

# Hydro seasonal shape (relative availability; long rains high, Jan-Mar low) [EPRA25 monthly hydro]
HYDRO_SEASON = {"S1": 0.85, "S2": 1.08, "S3": 1.10, "S4": 0.97}
# Wind shape: Feb strong, May weak; night windier [EPRA25]
WIND_SEASON = {"S1": 0.60, "S2": 0.40, "S3": 0.54, "S4": 0.48}
WIND_BRACKET = {"N": 1.10, "D": 0.92, "P": 1.05}
# Solar capacity factor by season during the day bracket; evening bracket gets the 18:00-19:00 tail
SOLAR_DAY = {"S1": 0.56, "S2": 0.48, "S3": 0.47, "S4": 0.52}
SOLAR_PEAK = 0.03

UNSERVED_ELEC_COST = 277.8   # M$/PJ = 1,000 $/MWh value of lost load backstop [ASSUMP]

# Reserve margin on the evening-peak time slice (firm capacity / peak load) [LCPDP planning practice ~15%;
# 18% here because the peak slice is a 4-hour average, below the instantaneous peak]
RESERVE_MARGIN = {2025: 0.95, 2026: 0.95, 2027: 1.0, 2028: 1.05, 2030: 1.15, 2032: 1.18, 2075: 1.18}
CAPACITY_CREDIT = {   # share of capacity counted as firm at the evening peak [ASSUMP]
    "PWRGEO": 0.90, "PWRHYDTAN": 0.80, "PWRHYDRVB": 0.80, "PWRHYDLVS": 0.70, "PWRHYDLVN": 0.60,
    "PWRHYDHGF": 0.70, "PWRHYDKAR": 0.60, "PWRHYDNEW": 0.60, "PWRHYDSML": 0.40,
    "PWRWNDT1": 0.15, "PWRWNDT2": 0.10, "PWRSOL": 0.0, "PWRSOLDG": 0.0,
    "PWRDSL": 0.90, "PWROCGDSL": 0.90, "PWROCGLNG": 0.90, "PWRCCGLNG": 0.90, "PWRNUC": 0.90,
    "PWRBAG": 0.40, "IMPELCETH": 0.80, "IMPELCEAP": 0.50, "BATSTOR": 0.0,
    # batteries: no firm credit. OSeMOSYS sizes storage energy separately from converter power, and any
    # credit was taken up by converters with ~1 h of energy. Storage still earns its peak-shifting value.
}
# Base-year (2025) calibration to observed dispatch, GWh [EPRA25]
CALIB_2025_GWH = {
    "PWRGEO": ("up", 5718.2),            # observed after 668.7 GWh curtailment
    "PWRDSL": ("lo", 1150.0),            # MSD/HFO share of 1,247.9 GWh thermal
    "IMPELCETH": ("lo", 1274.4),
    "IMPELCEAP": ("lo", 259.4),
}
ETH_TAKE_OR_PAY_CF = 0.60      # minimum use of the 400 MW EEP contract to 2045 [ASSUMP]
ETH_CONTRACT_END = 2045
CROP_AREA_MAX_DECLINE = 0.02   # crop-basin areas fall at most 2% of the 2025 area per year (floor 50%) [ASSUMP]
IRRIGATION_DEFICIT_COST = 5.0  # M$/MCM = 5 $/m3, backstop so forced irrigation never makes the model infeasible
