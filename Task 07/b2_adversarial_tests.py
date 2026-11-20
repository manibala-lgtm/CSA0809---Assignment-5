import csv
import io
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

def read_csv_safely(path):
    if Path(path).stat().st_size == 0:
        return "ERROR: empty file"
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"station", "date", "pm25"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                return f"ERROR: missing required columns; found {reader.fieldnames}"
            return list(reader)
    except UnicodeDecodeError:
        try:
            with open(path, newline="", encoding="cp1252") as f:
                return list(csv.DictReader(f))
        except Exception as exc:
            return f"ERROR: encoding/read failure: {exc}"
    except Exception as exc:
        return f"ERROR: {exc}"

def score(text):
    positive = {"good", "clean", "fast", "helpful", "improved"}
    negative = {"bad", "dirty", "slow", "rude", "smoke", "broken"}
    negators = {"not", "never", "no"}
    words = text.lower().replace(".", " ").replace(",", " ").split()
    total = 0
    for i, word in enumerate(words):
        value = 1 if word in positive else -1 if word in negative else 0
        if i > 0 and words[i-1] in negators:
            value *= -1
        total += value
    return total

def main():
    # Construct adversarial files.
    (OUT / "missing_column.csv").write_text("station,date\nAdyar,2026-10-01\n", encoding="utf-8")
    (OUT / "wrong_delimiter.csv").write_text("station;date;pm25\nAdyar;2026-10-01;48\n", encoding="utf-8")
    (OUT / "different_encoding.csv").write_bytes("station,date,pm25\nCafé,2026-10-01,48\n".encode("cp1252"))
    (OUT / "empty.csv").write_text("", encoding="utf-8")

    for filename in ("missing_column.csv", "wrong_delimiter.csv",
                     "different_encoding.csv", "empty.csv"):
        print(filename, "=>", read_csv_safely(OUT / filename))

    readings = [
        ("Adyar", "2026-10-01", 48.0), ("Guindy", "2026-10-01", 95.0),
        ("Guindy", "2026-10-03", 121.0), ("Adyar", "2026-10-04", 60.0)
    ]
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
    con.executemany("INSERT INTO aq VALUES (?, ?, ?)", readings)
    con.commit()

    def station_average(name):
        row = con.execute("SELECT AVG(pm25) FROM aq WHERE station = ?", (name,)).fetchone()
        return row[0]

    print("Parameterized averages:", station_average("Adyar"), station_average("Guindy"))
    print("Injection attempt with parameter:", station_average("Adyar' OR '1'='1"))

    injected = "Adyar' OR '1'='1"
    unsafe_sql = "SELECT AVG(pm25) FROM aq WHERE station = '" + injected + "'"
    print("Unsafe string-built query result:", con.execute(unsafe_sql).fetchone()[0])
    con.close()

    tests = [
        "The service is not good.",
        "The air is not bad.",
        "The service is not not good.",
        "The roads are clean but the factory smoke is bad.",
        "Great service, but the air is dirty."
    ]
    print("Sentiment adversarial tests:")
    for sentence in tests:
        print(score(sentence), "|", sentence)

if __name__ == "__main__":
    main()
