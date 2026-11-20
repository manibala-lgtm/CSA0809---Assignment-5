# CSA08 – Assignment 5
## City Air-Quality Monitoring Network

**Student:** Manibala.I  
**Register Number:** 1924260190  
**Course:** CSA08 – Python Programming  
**Department:** B.Tech AI & DS  
**GitHub Repository:** [Add your Assignment 5 repository link here]

## Assignment contents
- Task06_B1: Cleaning pipeline, SQLite storage and charts; pandas benchmark.
- Task07_B2: Adversarial CSV tests, SQL parameterisation and sentiment edge cases.
- Task08_B3: Python loops, pandas groupby, SQL GROUP BY and cProfile comparison.
- Task09_B4: Sentiment scorer, extractive summariser, 50-complaint evaluation and index timing.
- Task01_A1 to Task05_A5: Design and theory answers are provided in the separate theory PDF.

## Software
- Python 3.10 or newer
- pandas
- matplotlib
- sqlite3, csv, statistics, cProfile, time, re (Python standard library)

Install libraries:
```bash
python -m pip install -r requirements.txt
```

## Run each program
Run commands from the repository root:

```bash
python Task06_B1/b1_cleaning_pipeline.py
python Task06_B1/b1_pandas_comparison.py
python Task07_B2/b2_adversarial_tests.py
python Task08_B3/b3_loops_pandas_sql.py
python Task09_B4/b4_ai_and_index.py
```

## Expected files after execution
- Task06_B1/output/cleaned_air_quality.csv
- Task06_B1/output/air_quality.sqlite
- Task06_B1/output/chart_*.png
- Task07_B2/output/: adversarial CSV files
- Task08_B3/output/: generated datasets, benchmark_results.txt and cprofile_loops.txt
- Task09_B4/output/complaint_results.csv

## Notes
- The B1 sample input intentionally contains missing, NA, negative, excessive, duplicate and Fahrenheit readings.
- The full B1 pipeline fills missing pollutant values with the station median, removes invalid readings and duplicates, and converts Fahrenheit to Celsius.
- The separate B1 Complete-the-Code function follows the supplied exercise's expected behaviour: it skips blank, NA, negative and above-999 PM2.5 values.
- B3 generates 8,760 hourly records per station for 1, 12 and 120 stations. Runtime measurements depend on the computer.
- B4 uses a small lexicon-based sentiment model. Its agreement score is an experiment on the included labelled sample, not a guarantee of real-world accuracy.
- Add your own execution screenshots to the relevant task output folders before submission.
- Record the Python and library versions on your computer using `python --version` and `python -m pip show pandas matplotlib`.

## Suggested GitHub commit sequence
1. Add Task06_B1 files and run outputs.
2. Add Task07_B2 files and run outputs.
3. Add Task08_B3 files and benchmark outputs.
4. Add Task09_B4 files and evaluation outputs.
5. Add README, requirements and final report.
