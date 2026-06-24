import os
import json
import csv
import glob

raw_dir = "Data/raw/spotify_million_playlist_dataset/data"
output_csv = "Main_data/combined_output.csv"

os.makedirs("Main_data", exist_ok=True)
json_files = sorted(glob.glob(os.path.join(raw_dir, "mpd.slice.*.json")))

out_file = open(output_csv, mode="w", newline="", encoding="utf-8")
writer = csv.writer(out_file)
writer.writerow(["pid", "track_uri", "track_name", "artist_name", "album_name"])

for file_path in json_files:
    f = open(file_path, "r", encoding="utf-8")
    chunk_data = json.load(f)
    f.close()

    for playlist in chunk_data["playlists"]:
        pid = playlist["pid"]
        for track in playlist["tracks"]:
            writer.writerow([
                pid,
                track["track_uri"],
                track["track_name"],
                track["artist_name"],
                track["album_name"]
            ])

out_file.close()
print("Done! combined_output.csv created.")