import time
import pandas as pd
from pathlib import Path

def benchmark(n):
    # Reproducible synthetic data for the pandas alternative.
    df = pd.DataFrame({
        "station": ["Adyar" if i % 2 == 0 else "Guindy" for i in range(n)],
        "pm25": [float((i % 150) + 1) for i in range(n)]
    })
    start = time.perf_counter()
    df["pm25"] = df["pm25"].replace(["NA", ""], pd.NA)
    df = df.dropna(subset=["pm25"])
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")
    df = df[(df["pm25"] >= 0) & (df["pm25"] <= 999)]
    low, high = df["pm25"].min(), df["pm25"].max()
    df["pm25_minmax"] = 0.0 if high == low else (df["pm25"] - low) / (high - low)
    elapsed = time.perf_counter() - start
    return elapsed, len(df)

if __name__ == "__main__":
    print("Pandas cleaning and vectorised normalisation benchmark")
    for size in (1_000, 100_000, 1_000_000):
        seconds, kept = benchmark(size)
        print(f"rows={size:,} kept={kept:,} elapsed_seconds={seconds:.6f}")
