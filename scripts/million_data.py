import glob
import json
import os
import pandas as pd

input_folder = "Data/raw/spotify_million_playlist_dataset/data/mpd.slice.*.json"
output_csv = "Main_data/combined_output.csv"

json_files = sorted(glob.glob(input_folder))

with open(json_files[0], "r", encoding="utf-8") as f:
    first_slice = json.load(f)["playlists"]
    pd.DataFrame(first_slice).iloc[0:0].to_csv(
        output_csv, index=False, encoding="utf-8"
    )

print(f"Found {len(json_files)} files. Appending to CSV...")

for index, file_path in enumerate(json_files, start=1):
    print(
        f"[{index}/{len(json_files)}] Appending: {os.path.basename(file_path)}"
    )

    with open(file_path, "r", encoding="utf-8") as f:
        df_chunk = pd.DataFrame(json.load(f)["playlists"])
        df_chunk.to_csv(
            output_csv, mode="a", header=False, index=False, encoding="utf-8"
        )

print(f"\nSuccess! All data appended cleanly to '{output_csv}'.")