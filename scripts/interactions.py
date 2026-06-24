import pandas as pd
import ast
import csv

INPUT_FILE =     "Main_data/combined_output.csv"
OUTPUT_FILE = "Main_data/interactions.csv"

chunksize = 1000

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["pid", "track_uri"])

    for chunk in pd.read_csv(
        INPUT_FILE,
        chunksize=chunksize
    ):

        for _, row in chunk.iterrows():

            pid = row["pid"]

            try:
                tracks = ast.literal_eval(
                    row["tracks"]
                )

                for track in tracks:

                    writer.writerow([
                        pid,
                        track["track_uri"]
                    ])

            except Exception:
                continue

print("Done")