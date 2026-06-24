import pickle
import numpy as np
import pandas as pd
from scipy.sparse import load_npz

playlist_id = int(input("Enter Playlist ID: "))
top_k = 20

with open("Main_data/lightfm_model.pkl", "rb") as f:
    data = pickle.load(f)

model = data["model"]
users = data["users"]
items = data["items"]

train_matrix = load_npz("train_matrix.npz").tocsr()
songs = pd.read_csv("Main_data/songs.csv")

user_idx = users.index(playlist_id)
scores = model.predict(user_idx, np.arange(len(items)))

known_items = train_matrix[user_idx].indices
scores[known_items] = -np.inf

top_item_indices = np.argsort(-scores)[:top_k]

recommended_uris = [items[idx] for idx in top_item_indices]
recommended_uris = [uri.replace("spotify:track:", "") for uri in recommended_uris]
scores_dict = {items[idx]: scores[idx] for idx in top_item_indices}

recommendations = songs[songs["track_uri"].isin(recommended_uris)].copy()
recommendations = recommendations.drop_duplicates(subset=["track_uri"])

recommendations["score"] = recommendations["track_uri"].map(scores_dict)
recommendations = recommendations.sort_values(by="score", ascending=False)

output_cols = ["track_name", "artist_name", "album_name"]
print(recommendations[output_cols].to_string(index=False))