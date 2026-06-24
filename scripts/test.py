import pandas as pd
import pickle
import os
from scipy.sparse import load_npz 
import scipy.sparse as sp
from lightfm.evaluation import auc_score, precision_at_k, recall_at_k

train_matrix = sp.load_npz("Main_data/train_matrix.npz")
test_matrix = sp.load_npz("Main_data/test_matrix.npz")

path = "Main_data/lightfm_model.pkl"
with open(path, "rb") as f:
    data = pickle.load(f) 

model = data["model"]
user_list = data["users"]
item_list = data["items"]
num_users = len(user_list)
num_items = len(item_list)

print("Calculating evaluation metrics across threads...")
n = os.cpu_count()
print('Available Cores:', n)
precision = precision_at_k(
    model, test_matrix, train_interactions=train_matrix, k=10, num_threads=n
).mean()

recall = recall_at_k(
    model, test_matrix, train_interactions=train_matrix, k=10, num_threads=n
).mean()

auc = auc_score(
    model, test_matrix, train_interactions=train_matrix, num_threads=n
).mean()

print("\n" + "=" * 40)
print("             EVALUATION REPORT         ")
print("=" * 40)
print(f"Users: {num_users}")
print(f"Items: {num_items}")
print(f"Train interactions: {train_matrix.nnz}")
print(f"Test interactions: {test_matrix.nnz}")
print("-" * 40)
print(f"Precision@10: {precision:.4f}")
print(f"Recall@10:    {recall:.4f}")
print(f"AUC:          {auc:.4f}")
print("=" * 40)
