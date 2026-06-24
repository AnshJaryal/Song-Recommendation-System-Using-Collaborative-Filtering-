import pickle
import numpy as np
import pandas as pd

from scipy.sparse import coo_matrix, save_npz
from lightfm import LightFM
from lightfm.cross_validation import random_train_test_split
from lightfm.evaluation import (precision_at_k,recall_at_k,auc_score)

df = pd.read_csv("Main_data/200k_interactions.csv",usecols=["pid", "track_uri"])
df = df.drop_duplicates()
df["pid"] = df["pid"].astype("category")
df["track_uri"] = df["track_uri"].astype("category")

num_users = len(df["pid"].cat.categories)
num_items = len(df["track_uri"].cat.categories)

rows = df["pid"].cat.codes.values
cols = df["track_uri"].cat.codes.values

interaction_matrix = coo_matrix(
    (
        np.ones(len(df), dtype=np.float32),
        (rows, cols)
    ),
    shape=(num_users, num_items)
)

train_matrix, test_matrix = random_train_test_split(interaction_matrix,test_percentage=0.2,random_state=np.random.RandomState(42))
save_npz("Main_data/train_matrix.npz", train_matrix)
save_npz("Main_data/test_matrix.npz", test_matrix)
print(test_matrix.shape)
print(train_matrix.shape)
model = LightFM(no_components=16,loss="warp",random_state=42)
for epoch in range(1,31):
    model.fit(train_matrix,epochs = 1, num_threads = 20)
    if epoch % 5 == 0 or epoch == 1:
        print(f"--------------Epoch{epoch}/30 completed---------------")
        
with open("Main_data/lightfm_model.pkl", "wb") as f:
    pickle.dump(
        {
            "model": model,
            "users": df["pid"].cat.categories.tolist(),
            "items": df["track_uri"].cat.categories.tolist()
        },
        f
    )

print(model.user_embeddings.shape)
print(model.item_embeddings.shape)

