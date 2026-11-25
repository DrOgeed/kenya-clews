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
    names = list(lpm.col_names_)
    cl, cu = list(lpm.col_lower_), list(lpm.col_upper_)
    rl, ru, rn = list(lpm.row_lower_), list(lpm.row_upper_), list(lpm.row_names_)
    cv, cd, rv, rd = list(s.col_value), list(s.col_dual), list(s.row_value), list(s.row_dual)
    # HiGHS "style 1" text layout; without crossover there is no basis, so status is reported as BS
    with open(sol, "w") as f:
        f.write("Columns\n    Index Status        Lower        Upper       Primal         Dual  Name\n")
        for i, (n, v, d) in enumerate(zip(names, cv, cd)):
            f.write(f"{i:9d}     BS {cl[i]:12.6g} {cu[i]:12.6g} {v:12.6g} {d:12.6g}  {n}\n")
        f.write("Rows\n    Index Status        Lower        Upper       Primal         Dual  Name\n")
        for i, (n, v, d) in enumerate(zip(rn, rv, rd)):
            f.write(f"{i:9d}     BS {rl[i]:12.6g} {ru[i]:12.6g} {v:12.6g} {d:12.6g}  {n}\n")
        f.write(f"\nModel status: {status}\n\n# Primal solution values\nFeasible\nObjective {obj}\n")
    print(f"{lp}: {status}, objective {obj:,.1f} MUSD, {time.time() - t:.0f}s", flush=True)
    return status, obj


if __name__ == "__main__":
    solve(sys.argv[1], sys.argv[2])
