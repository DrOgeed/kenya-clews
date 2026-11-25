# Data sources and assumptions

Every input lives in [`scripts/kenya_inputs.py`](scripts/kenya_inputs.py), and every number there carries a source tag. This file explains the tags, records the reasoning behind each assumption, and lists the gaps that should be closed before the results are used in a formal policy submission.

**Assumption** means a value chosen by the author where no Kenyan official figure was found. These are defensible defaults, not official data, and each is a candidate for sensitivity analysis.

## Source tags

| Tag | Source |
|---|---|
| EPRA25 | Energy and Petroleum Regulatory Authority, *Energy & Petroleum Statistics Report FY2024/25* (Sept 2025) |
| WPP24 | United Nations, *World Population Prospects 2024*, medium variant (annual growth rates via database.earth republication; anchors 2050 = 83.59 M, 2075 = 100.06 M) |
| LCPDP | Ministry of Energy and Petroleum, *Least Cost Power Development Plan 2024-2043* |
| IRENA | IRENA, *Renewable Power Generation Costs in 2024* (2025) |
| ATB | NREL, *Annual Technology Baseline 2024*, moderate case |
| NWMP | JICA / WRMA, *National Water Master Plan 2030* (2013), basin water balance tables |
| KNBS | KNBS *Economic Survey 2025* and *National Agriculture Production Report 2025* |
| NIA | National Irrigation Authority; *National Irrigation Sector Investment Plan 2025-2035* (NISIP) |
| FAO | FAOSTAT land use; AQUASTAT irrigation; FAO-56 crop water guidance |
| IPCC | IPCC 2006 Guidelines, default CO2 emission factors |
| MAC21 | Macharia et al. 2021, *Energies* 14:2169, energy intensity of Kenyan water utilities |
| COMPACT | Kenya National Energy Compact, Mission 300 (Aug 2025) |

## Electricity

| Input | Value | Source |
|---|---|---|
| Sent-out energy 2025 | 14,472 GWh (incl. imports) | EPRA25 |
| Final grid sales 2025 | 11,330 GWh | EPRA25 |
| Peak demand | 2,316 MW (Feb 2025) | EPRA25 |
| T&D delivery efficiency | 0.783 (2025), 0.825 (2035), 0.86 (2050) | EPRA25 for 2025; path to EPRA allowable losses is an assumption |
| Installed capacity by technology | geothermal 940, hydro 839.5, MSD 512.8, gas turbines 52, wind 435.5, solar 210.3 MW; Ethiopia import 200 MW (400 MW from 2027) | EPRA25 |
| Daily load shape | night ~1,350 MW, day ~1,750 MW, evening peak ~2,250 MW (18:00-22:00) | EPRA25 weekday profile |
| Hydro, wind, solar seasonal shapes | from EPRA monthly generation | EPRA25 |
| Geothermal capex | 3,500 $/kW (2025) to 3,000 (2050) | LCPDP candidates 3,500-3,808; IRENA global 4,015 |
| Wind capex | 1,600 to 1,150 $/kW | LCPDP 1,886 (100 MW candidate); IRENA global 1,041 |
| Utility solar capex | 900 to 450 $/kW | LCPDP 1,128-1,277; IRENA global 691 |
| Battery | converter 300 $/kW + cells 250 $/kWh (2025) to 150 + 120 (2050), sized separately; round trip 0.85 | ATB moderate |
| High Grand Falls | 693 MW, 3,708 $/kW, earliest 2033, plus 150 MCM of regulated Tana water per PJ generated | LCPDP cost; PPP terminated July 2025, so treated as an option only |
| Karura | 90 MW, 3,889 $/kW | LCPDP |
| Nuclear | 7,000 to 6,000 $/kW, earliest 2035, max 1 GW to 2040 | Assumption (NuPEA's official 3,600-5,000 $/kW judged optimistic) |
| LNG CCGT / OCGT | 1,380 / 800 $/kW, earliest 2030 | LEAP Kenya study 2021; Dongo Kundu LCPDP candidate |
| Fuel prices | HFO 13, diesel 20, LNG 11, uranium 0.8 $/GJ, flat real | Assumption from World Bank / IEA trajectories |
| Ethiopia import | 6.5 USc/kWh; 60% take-or-pay floor on 400 MW to 2045 | Price from EPRA25 and Ecofin 2026; floor is an assumption |
| Emission factors | HFO 77.4, diesel 74.1, gas 56.1 kt CO2/PJ | IPCC |
| Reserve margin | 0.95 (2025) rising to 1.18 from 2032, on the evening-peak slice | Assumption, LCPDP practice is about 15% on instantaneous peak |
| Capacity credits | geothermal 0.9, existing hydro 0.6-0.8, thermal 0.9, Ethiopia 0.8, wind 0.10-0.15, solar 0, batteries 0.25 | Assumption |

### Demand rule

Final grid demand grows each year at 3 times the UN WPP 2024 population growth rate for that year. The rule is applied to non-water final demand: 2025 sales (11,330 GWh) minus the electricity the model's water sector uses in 2025 (about 870 GWh), so the water-energy link is not double counted. Electricity for water supply, irrigation pumping, desalination and green ammonia is endogenous and comes on top.

## Water (six WRA basins)

| Input | Value | Source |
|---|---|---|
| Surface runoff and groundwater sustainable yield, 2010 / 2030 / 2050 | basin tables | NWMP |
| Ecological reserve | 30% of runoff | Assumption (NWMP gives the reserve first priority but no single share) |
| Run-of-river abstraction without storage | 25% of runoff | Assumption |
| Existing regulated yield of dams | LVN 50, LVS 60, RVB 150, ATH 250, TAN 600, ENN 10 MCM/yr | Assumption |
| Tana to Athi transfer | 230 MCM/yr existing, up to 800 | Assumption (Thika/Ndakaini plus Northern Collector) |
| Municipal + industrial + livestock water | 35 m3/person/yr (2025) to 50 (2050) | Assumption calibrated to NWMP sector totals |
| Energy intensity | treatment + distribution 0.15, boreholes 0.60, desalination 3.5 to 3.0, transfer 0.30, surface irrigation 0.05, drip 0.35 kWh/m3 | MAC21; irrigation values are assumptions |
| Irrigation efficiency | surface 0.50, drip 0.85 | FAO |
| Infrastructure costs | dams 1.5, boreholes 0.5, treatment 1.0, transfer 1.5, desalination 5.5 to 4.0, surface irrigation 0.15, drip 0.35 M$ per MCM/yr | Assumption |
| Backstops | unserved municipal water 20 $/m3; irrigation deficit 5 $/m3 | Model device; any use is reported |

## Land and crops

| Input | Value | Source |
|---|---|---|
| Basin areas | NWMP km2 | NWMP |
| Forest 2025 | 3.61 Mha total, split by basin; protected from net loss | FAO total; basin split is an assumption |
| Suitable cropland by basin | LVN 1.5, LVS 2.0, RVB 3.5, ATH 2.0, TAN 2.8, ENN 0.8 Mha | Assumption (replace with GAEZ v4) |
| Crop areas and production 2024 | maize 2.41 Mha / 4.03 Mt; tea 228 kha; horticulture 477 kha / 7.77 Mt; others by production | KNBS |
| Basin split of crop areas | by main growing counties | Assumption |
| Irrigated area | 288 kha (2025); potential 1.34 Mha | NIA, FAO, NWMP |
| Irrigation development cost | 10,000 $/ha; max 40 kha/yr nationally | NIA / NISIP cost range |
| Yield growth | rainfed +28% by 2050; irrigated +13% | Assumption |
| Net irrigation requirement | rice 1,000, sugarcane 900, horticulture 450, maize 300, wheat 250 mm | FAO-56 typical values |
| Food demand | constant per person, scaled by population; export crops +45% by 2050 | Assumption |
| Import prices | maize 320, wheat 330, rice (paddy equiv.) 450, beans 850 $/t | Assumption |
| Crop area change limit | at most 2% of the 2025 area per year (floor 50%) | Assumption, avoids unrealistic one-year switches |
| Nitrogen fertiliser | import 1,100 $/t N; green ammonia 14.6 MWh/t N, 6,500 $/(t N/yr) falling to 2,400 | Assumption |
| Bagasse | 0.3 t/t cane, 7.5 GJ/t, half available for export power | Assumption |
| Afforestation | 600 $/ha, removes 5 t CO2/ha/yr | IPCC Tier 1 range |

## Scenario switches

| Scenario | Change from BASE |
|---|---|
| LCPDP | demand grows 6.6%/yr to 2043 (LCPDP Reference), then by the 3x rule |
| RE100 | no fossil generation and no nuclear from 2035 (NDC 3.0 100% renewable grid) |
| NZDRY | power CO2 falls linearly from 1.5 Mt (2030) to zero (2050); hydro availability down to 70% by 2050; runoff down 15% in Athi, Tana, ENN and Rift Valley by 2050; rainfed yields down 10% by 2050 |
| IRRIG | irrigated area must reach 690 kha by 2035 and 1,000 kha by 2050 (NISIP), split by basin potential, and be at least 90% used |

## Known gaps

1. Land cover by basin should come from a GIS overlay (ESA WorldCover or KFS/SLEEK with WRA basin shapefiles) or GAEZ v4 clustering.
2. Kenya-specific forward fuel prices, especially delivered LNG.
3. Plant-level hydro inflows from KenGen; the model uses an aggregate seasonal shape.
4. FAOSTAT areas for beans, sorghum, millet, wheat and sugarcane.
5. The official UN WPP 2024 CSV should replace the republished growth series.
6. Surface water is balanced per time slice without seasonal river flow; seasonal runoff shares would sharpen dry-season results.
7. The LCPDP 2024-2043 cost table was extracted from a tender annex whose columns are ambiguous; nuclear, MSD and CCGT costs come from other sources.
