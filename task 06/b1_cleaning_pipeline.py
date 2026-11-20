import csv
import sqlite3
import statistics
from pathlib import Path
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
INPUT = HERE / "input" / "raw_air_quality.csv"
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

def load_clean(text):
    """Complete-the-code version: retain valid nonnegative PM2.5 values <= 999."""
    rows = []
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        value = (row.get("pm25") or "").strip()
        if value.upper() in ("", "NA"):
            continue
        try:
            pm25 = float(value)
        except ValueError:
            continue
        if pm25 < 0 or pm25 > 999:
            continue
        rows.append((row["station"].strip().title(), row["date"].strip(), pm25))
    return rows

def min_max(values):
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [0.0 for _ in values]
    return [round((v - low) / (high - low), 3) for v in values]

def to_float_or_none(value):
    value = (value or "").strip()
    if value.upper() in ("", "NA", "N/A", "NULL"):
        return None
    try:
        return float(value)
    except ValueError:
        return None

def clean_full_pipeline(input_path):
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        raw = list(csv.DictReader(f))

    cleaned = []
    seen = set()
    for r in raw:
        station = (r.get("station") or "").strip().title()
        date = (r.get("date") or "").strip()
        try:
            hour = int(r.get("hour", ""))
        except (TypeError, ValueError):
            continue
        if not station or not date or not 0 <= hour <= 23:
            continue
        key = (station, date, hour)
        if key in seen:
            continue
        seen.add(key)

        values = {}
        for col in ("pm25", "pm10", "no2"):
            v = to_float_or_none(r.get(col))
            values[col] = None if v is not None and (v < 0 or v > 999) else v

        temp = to_float_or_none(r.get("temperature"))
        unit = (r.get("temp_unit") or "C").strip().upper()
        if temp is not None and unit in ("F", "FAHRENHEIT"):
            temp = (temp - 32) * 5 / 9

        cleaned.append({
            "station": station, "date": date, "hour": hour,
            "pm25": values["pm25"], "pm10": values["pm10"],
            "no2": values["no2"], "temperature": temp
        })

    # Fill missing pollutant values with the station median; preserve NULL if no valid median exists.
    for col in ("pm25", "pm10", "no2"):
        by_station = {}
        for r in cleaned:
            if r[col] is not None:
                by_station.setdefault(r["station"], []).append(r[col])
        medians = {s: statistics.median(vals) for s, vals in by_station.items()}
        for r in cleaned:
            if r[col] is None and r["station"] in medians:
                r[col] = medians[r["station"]]
    return cleaned

def save_csv(rows, path):
    fields = ["station", "date", "hour", "pm25", "pm10", "no2", "temperature"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def store_and_query(rows):
    db = OUT / "air_quality.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE stations (
        station_id INTEGER PRIMARY KEY,
        station_name TEXT UNIQUE NOT NULL
    )""")
    con.execute("""CREATE TABLE readings (
        reading_id INTEGER PRIMARY KEY,
        station_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        hour INTEGER NOT NULL,
        pm25 REAL, pm10 REAL, no2 REAL, temperature REAL,
        FOREIGN KEY(station_id) REFERENCES stations(station_id),
        UNIQUE(station_id, day, hour)
    )""")
    names = sorted({r["station"] for r in rows})
    con.executemany("INSERT INTO stations(station_name) VALUES (?)",
                    [(n,) for n in names])
    ids = dict(con.execute("SELECT station_name, station_id FROM stations"))
    payload = [(ids[r["station"]], r["date"], r["hour"], r["pm25"],
                r["pm10"], r["no2"], r["temperature"]) for r in rows]
    con.executemany("""INSERT INTO readings
        (station_id, day, hour, pm25, pm10, no2, temperature)
        VALUES (?, ?, ?, ?, ?, ?, ?)""", payload)
    con.commit()

    q1 = con.execute("""SELECT AVG(r.pm25) FROM readings r
        JOIN stations s USING(station_id)
        WHERE s.station_name=? AND r.day LIKE '2026-10-%'""", ("Adyar",)).fetchone()[0]
    q2 = con.execute("SELECT MAX(pm10) FROM readings").fetchone()[0]
    q3 = con.execute("""SELECT day, AVG(temperature) FROM readings
        WHERE temperature IS NOT NULL GROUP BY day ORDER BY day""").fetchall()
    con.close()
    return db, q1, q2, q3

def make_charts(rows):
    valid = [r for r in rows if r["pm25"] is not None]
    if not valid:
        return
    # 1. Monthly trend
    daily = {}
    for r in valid:
        daily.setdefault(r["date"], []).append(r["pm25"])
    dates = sorted(daily)
    means = [sum(daily[d])/len(daily[d]) for d in dates]
    plt.figure()
    plt.plot(dates, means, marker="o")
    plt.title("Daily Mean PM2.5 Trend")
    plt.xlabel("Date")
    plt.ylabel("PM2.5")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(OUT / "chart_pm25_trend.png")
    plt.close()

    # 2. Station comparison
    stations = sorted({r["station"] for r in valid})
    station_means = [sum(r["pm25"] for r in valid if r["station"] == s) /
                     sum(1 for r in valid if r["station"] == s) for s in stations]
    plt.figure()
    plt.bar(stations, station_means)
    plt.title("Average PM2.5 by Station")
    plt.xlabel("Station")
    plt.ylabel("Average PM2.5")
    plt.tight_layout()
    plt.savefig(OUT / "chart_station_comparison.png")
    plt.close()

    # 3. Temperature vs PM2.5
    pairs = [(r["temperature"], r["pm25"]) for r in valid if r["temperature"] is not None]
    plt.figure()
    if pairs:
        plt.scatter([x for x, y in pairs], [y for x, y in pairs])
    plt.title("Temperature vs PM2.5")
    plt.xlabel("Temperature (°C)")
    plt.ylabel("PM2.5")
    plt.tight_layout()
    plt.savefig(OUT / "chart_temperature_pm25.png")
    plt.close()

    # 4. Hourly pollution pattern
    hours = sorted({r["hour"] for r in valid})
    hourly = [sum(r["pm25"] for r in valid if r["hour"] == h) /
              sum(1 for r in valid if r["hour"] == h) for h in hours]
    plt.figure()
    plt.bar(hours, hourly)
    plt.title("Mean PM2.5 by Hour")
    plt.xlabel("Hour of Day")
    plt.ylabel("Mean PM2.5")
    plt.tight_layout()
    plt.savefig(OUT / "chart_hourly_pm25.png")
    plt.close()

def main():
    text = INPUT.read_text(encoding="utf-8")
    print("Complete-the-code output:")
    clean = load_clean(text)
    print(clean)
    print(min_max([pm for _, _, pm in clean]))

    rows = clean_full_pipeline(INPUT)
    save_csv(rows, OUT / "cleaned_air_quality.csv")
    db, avg, max_pm10, daily_temp = store_and_query(rows)
    make_charts(rows)
    print("\nFull pipeline: raw rows =", sum(1 for _ in csv.DictReader(text.splitlines())))
    print("Cleaned rows =", len(rows))
    print("Average PM2.5 for Adyar in October =", round(avg, 3) if avg is not None else None)
    print("Maximum PM10 =", max_pm10)
    print("Daily average temperature =", daily_temp)
    print("Database =", db.name)
    print("Charts saved in", OUT)

if __name__ == "__main__":
    main()
