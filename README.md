# Kenya CLEWs model (KECLEWS), 2025-2075

An OSeMOSYS Climate, Land, Energy and Water systems (CLEWs) model of Kenya, built to advise on which energy sectors to invest in over the next 50 years while accounting for crop production, irrigation water, land use and the six Water Resources Authority basins.

Status: model, data and pipeline are in place; scenario results and the full documentation are being finalised.

- Inputs and sources: [`scripts/kenya_inputs.py`](scripts/kenya_inputs.py), [`DATA_SOURCES.md`](DATA_SOURCES.md)
- Build and run: `pip install -r requirements.txt`, then `python scripts/run_scenarios.py` (needs GLPK `glpsol` on PATH)
- MUIO: import `muio/KenyaCLEWs_<SCENARIO>.xlsx` or restore `muio/KenyaCLEWs_<SCENARIO>.zip`
