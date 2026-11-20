import csv
import sqlite3
import time
from pathlib import Path
from collections import Counter
import re

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

POSITIVE = {"good", "clean", "fast", "helpful", "improved"}
NEGATIVE = {"bad", "dirty", "slow", "rude", "smoke", "broken"}
NEGATORS = {"not", "never", "no"}
STOP = {"the", "a", "an", "is", "are", "was", "were", "and", "but",
        "to", "of", "in", "on", "for", "it", "this", "that", "with",
        "from", "very", "my", "our", "i", "we", "they", "today"}

def score(text):
    words = re.findall(r"[a-z']+", text.lower())
    total = 0
    for i, word in enumerate(words):
        value = 1 if word in POSITIVE else -1 if word in NEGATIVE else 0
        if i > 0 and words[i-1] in NEGATORS:
            value *= -1
        total += value
    return total

def label(text):
    s = score(text)
    return "positive" if s > 0 else "negative" if s < 0 else "neutral"

def summarise(text, k=2):
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    words = re.findall(r"[a-z']+", text.lower())
    freq = Counter(w for w in words if w not in STOP and len(w) > 2)
    ranked = sorted(enumerate(sentences),
                    key=lambda item: (-sum(freq[w] for w in re.findall(r"[a-z']+", item[1].lower())), item[0]))
    chosen = sorted(i for i, _ in ranked[:k])
    return " ".join(sentences[i] for i in chosen)

COMPLAINTS = [
("The road air is clean and the buses are fast.", "positive"),
("Factory smoke makes the neighbourhood dirty.", "negative"),
("The response team was helpful and fast.", "positive"),
("The monitoring station is broken and slow.", "negative"),
("Air quality improved near the park.", "positive"),
("The street is dirty because of smoke.", "negative"),
("The new bus service is good.", "positive"),
("The complaint staff were rude.", "negative"),
("The area is clean today.", "positive"),
("The sensor is broken and gives bad readings.", "negative"),
("The response was not helpful.", "negative"),
("The air is not bad near the lake.", "positive"),
("Traffic smoke is making the air dirty.", "negative"),
("The new filter improved air quality.", "positive"),
("The service is slow and the staff are rude.", "negative"),
("The park is clean but traffic is bad.", "negative"),
("The bus is fast and helpful.", "positive"),
("The factory smoke is bad.", "negative"),
("The monitoring service improved.", "positive"),
("The road is dirty and broken.", "negative"),
("Air quality is good near the school.", "positive"),
("The sensor response is slow.", "negative"),
("The staff were helpful.", "positive"),
("Smoke levels are high and the air is bad.", "negative"),
("The new system is fast and clean.", "positive"),
("The complaint was ignored and the service is rude.", "negative"),
("The air has improved after traffic control.", "positive"),
("The road is not clean.", "negative"),
("The station gives good updates.", "positive"),
("The factory releases smoke every evening.", "negative"),
("The bus is not slow today.", "positive"),
("The air is dirty near the market.", "negative"),
("The response team is good and helpful.", "positive"),
("The sensor is not broken.", "positive"),
("The area has bad smoke and dirty roads.", "negative"),
("The clean-up work improved the street.", "positive"),
("The service is bad but the staff are helpful.", "neutral"),
("The air is good but traffic is slow.", "neutral"),
("No improvement in the dirty air.", "negative"),
("The station is fast and reliable.", "positive"),
("The complaint process is slow.", "negative"),
("The park air is clean.", "positive"),
("The factory smoke is not good.", "negative"),
("The new service is helpful.", "positive"),
("The readings are broken and the display is slow.", "negative"),
("The air is not dirty near the coast.", "positive"),
("The road is clean but the bus is slow.", "neutral"),
("The station update is improved.", "positive"),
("Smoke is bad for the neighbourhood.", "negative"),
("The team was helpful but the air remains dirty.", "negative")
]

def measure_index():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE readings (station TEXT, day TEXT, pm25 REAL)")
    rows = [(f"Station{i%100:03d}", f"2026-10-{i%30+1:02d}", float(i%150))
            for i in range(100_000)]
    con.executemany("INSERT INTO readings VALUES (?, ?, ?)", rows)
    con.commit()
    query = "SELECT AVG(pm25) FROM readings WHERE station=? AND day=?"
    params = ("Station042", "2026-10-12")
    def run_many():
        for _ in range(30):
            con.execute(query, params).fetchone()
    t0 = time.perf_counter()
    run_many()
    before = time.perf_counter() - t0
    con.execute("CREATE INDEX idx_station_day ON readings(station, day)")
    con.commit()
    t0 = time.perf_counter()
    run_many()
    after = time.perf_counter() - t0
    con.close()
    return before, after

def main():
    correct = 0
    rows = []
    for text, human in COMPLAINTS:
        predicted = label(text)
        correct += predicted == human
        rows.append((text, human, predicted, summarise(text)))
    with open(OUT / "complaint_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["complaint", "human_label", "model_label", "extractive_summary"])
        w.writerows(rows)
    print(f"Human-label agreement: {correct}/{len(COMPLAINTS)} = {correct/len(COMPLAINTS)*100:.1f}%")
    print("Example summaries:")
    for text, human, predicted, summary in rows[:5]:
        print(f"{predicted:8} | {summary}")
    before, after = measure_index()
    print(f"30 query runs before index: {before:.6f}s")
    print(f"30 query runs after index:  {after:.6f}s")
    print("Complaint results saved to output/complaint_results.csv")

if __name__ == "__main__":
    main()
