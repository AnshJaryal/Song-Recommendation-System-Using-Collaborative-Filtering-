Music Recommendation System

An end-to-end music recommendation engine using the **LightFM architecture** (Collaborative Filtering via Matrix Factorization) paired with a responsive, multi-threaded **Neumorphism (Soft UI)** desktop application built with `customtkinter`.

---

##  Project Architecture & Data Constraints

> ⚠️ **IMPORTANT DATA NOTE:** Due to GitHub's file size limitations, large datasets (`combined_output.csv`), sparse matrices, and trained models (`.pkl`) are **not** committed to this repository. You must either compile them from scratch using the provided script sequence or download them via the external link below.

👉 [**Click Here to Download Pre-Trained Models & Datasets via Google Drive**](https://drive.google.com/file/d/1Xx1rA6W_j_8X40fOpQtATotwFivXcpDr/view?usp=sharing)

If downloading, extract the contents directly into a folder named `Main_data` at the root of this project repository.

---

## Repository Workspace Structure

Ensure your local directory aligns with this structure before execution:

```
├── Data/
│   └── raw/
│       └── spotify_million_playlist_dataset/
│           └── data/                     # Drop raw mpd.slice.*.json files here
├── Main_data/                            
│   ├── lightfm_model.pkl
│   ├── train_matrix.npz
│   └── songs.csv
├── scripts/
|   ├── interactions.py
|   ├── million_data.py
│   ├── subset.py
|   ├── test.py
│   └── train.py                          # Script that builds your LightFM models
├── app/
|   └──  app.py                           # Main UI wrapper application
├── requirements.txt
└── .gitignore
