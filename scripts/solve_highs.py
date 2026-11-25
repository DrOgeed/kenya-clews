"""
Solve an OSeMOSYS LP with HiGHS (interior point, no crossover) and write a solution file that
`otoole results highs ...` can read.

    python scripts/solve_highs.py build/BASE.lp build/BASE.sol
"""
import sys
import time

import highspy


def solve(lp, sol, threads=2):
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("threads", threads)
    h.setOptionValue("solver", "ipm")
    h.setOptionValue("run_crossover", "off")
    t = time.time()
    h.readModel(lp)
    h.run()
    status = h.modelStatusToString(h.getModelStatus())
    obj = h.getInfo().objective_function_value
    s = h.getSolution()
    lpm = h.getLp()
    names = lpm.col_names_
    # HiGHS "style 1" text layout; without crossover there is no basis, so status is reported as BS
    with open(sol, "w") as f:
        f.write("Columns\n    Index Status        Lower        Upper       Primal         Dual  Name\n")
        for i, (n, v, d) in enumerate(zip(names, s.col_value, s.col_dual)):
            f.write(f"{i:9d}     BS {lpm.col_lower_[i]:12.6g} {lpm.col_upper_[i]:12.6g} {v:12.6g} {d:12.6g}  {n}\n")
        f.write("Rows\n    Index Status        Lower        Upper       Primal         Dual  Name\n")
        for i, (n, v, d) in enumerate(zip(lpm.row_names_, s.row_value, s.row_dual)):
            f.write(f"{i:9d}     BS {lpm.row_lower_[i]:12.6g} {lpm.row_upper_[i]:12.6g} {v:12.6g} {d:12.6g}  {n}\n")
        f.write(f"\nModel status: {status}\n\n# Primal solution values\nFeasible\nObjective {obj}\n")
    print(f"{lp}: {status}, objective {obj:,.1f} MUSD, {time.time() - t:.0f}s", flush=True)
    return status, obj


if __name__ == "__main__":
    solve(sys.argv[1], sys.argv[2])
