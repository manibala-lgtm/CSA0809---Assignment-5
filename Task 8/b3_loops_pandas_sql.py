import csv
import cProfile
import io
import sqlite3
import statistics
import pstats
import time
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

def generate_csv(path, stations):
    # One year of hourly observations: 365 * 24 = 8,760 rows per station.
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["station", "day", "pm25"])
        for s in range(stations):
            station = f"Station{s+1:03d}"
            for day in range(365):
                day_text = (date(2026, 1, 1) + timedelta(days=day)).isoformat()
                for hour in range(24):
                    value = float((s * 7 + day * 3 + hour) % 180 + 1)
                    w.writerow([station, day_text, value])

def loops_csv(path):
    sums, counts = {}, {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["station"], row["day"])
            value = float(row["pm25"])
            sums[key] = sums.get(key, 0.0) + value
            counts[key] = counts.get(key, 0) + 1
    return {k: sums[k] / counts[k] for k in sums}

def pandas_groupby(path):
    df = pd.read_csv(path)
    result = df.groupby(["station", "day"], as_index=False)["pm25"].mean()
    return {(r.station, r.day): r.pm25 for r in result.itertuples(index=False)}

def sql_groupby(path, db_path):
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE readings (station TEXT, day TEXT, pm25 REAL)")
    with open(path, newline="", encoding="utf-8") as f:
        batch = []
        for row in csv.DictReader(f):
            batch.append((row["station"], row["day"], float(row["pm25"])))
            if len(batch) >= 10000:
                con.executemany("INSERT INTO readings VALUES (?, ?, ?)", batch)
                batch.clear()
        if batch:
            con.executemany("INSERT INTO readings VALUES (?, ?, ?)", batch)
    con.commit()
    start = time.perf_counter()
    rows = con.execute("""SELECT station, day, AVG(pm25)
                          FROM readings GROUP BY station, day""").fetchall()
    query_time = time.perf_counter() - start
    con.close()
    return {(s, d): v for s, d, v in rows}, query_time

def profile_loops(path):
    profiler = cProfile.Profile()
    profiler.enable()
    loops_csv(path)
    profiler.disable()
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).sort_stats("cumulative").print_stats()
    return stream.getvalue()

def main():
    summary_lines = []
    for stations in (1, 12, 120):
        csv_path = OUT / f"air_{stations}_stations.csv"
        db_path = OUT / f"air_{stations}_stations.sqlite"
        generate_csv(csv_path, stations)
        rows = stations * 8760

        t0 = time.perf_counter()
        loop_result = loops_csv(csv_path)
        loop_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        pandas_result = pandas_groupby(csv_path)
        pandas_time = time.perf_counter() - t0

        sql_result, sql_query_time = sql_groupby(csv_path, db_path)
        agree = (loop_result.keys() == pandas_result.keys() == sql_result.keys()
                 and all(abs(loop_result[k] - pandas_result[k]) < 1e-9
                         and abs(loop_result[k] - sql_result[k]) < 1e-9
                         for k in loop_result))
        line = (f"stations={stations}, readings={rows:,}, groups={len(loop_result):,}, "
                f"loops={loop_time:.4f}s, pandas={pandas_time:.4f}s, "
                f"SQL_query_only={sql_query_time:.4f}s, all_agree={agree}")
        print(line)
        summary_lines.append(line)

        if stations == 1:
            profile = profile_loops(csv_path)
            (OUT / "cprofile_loops.txt").write_text(profile, encoding="utf-8")

    (OUT / "benchmark_results.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print("Profile saved to output/cprofile_loops.txt")
    print("Benchmark results saved to output/benchmark_results.txt")

if __name__ == "__main__":
    main()
