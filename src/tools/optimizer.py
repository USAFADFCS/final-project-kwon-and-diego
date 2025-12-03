from scipy.optimize import linprog

def optimize_daily_hours(tasks, sleep_min=8):
    """
    tasks = [("Gym", 2), ("Work", 8), ("Leisure", 2)]
    """
    # Objective: minimize idle time
    c = [1] * len(tasks)

    # Constraint: sum(task hours) + sleep ≥ 24
    A_eq = [ [1]*len(tasks) ]
    b_eq = [24 - sleep_min]

    result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=[(hours, hours+4) for _, hours in tasks])

    # Output optimized hours for each task
    return result.x
