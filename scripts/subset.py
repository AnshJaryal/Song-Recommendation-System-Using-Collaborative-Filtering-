import pandas as pd

limit = 200_00

chunks = []
seen = set()

for chunk in pd.read_csv('Main_data/interactions.csv',chunksize = 2_000_000):
    chunk = chunk[chunk["pid"] < limit]
    chunks.append(chunk)
    if len(chunk):
        seen.update(chunk["pid"])
    
    if len(seen) >= limit:
        break

df = pd.concat(chunks,ignore_index = True)

df.to_csv(
    "Main_data/200k_interactions.csv",index = False
)
print(df.shape)