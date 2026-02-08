import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Dummy data consistent with the constraints in the prompt
data = {
    "TPDE":     {"compile_time": 1.0,   "runtime": 60.0},   # ~10x faster compile than O0, similar runtime
    "LLVM-O0":  {"compile_time": 10.0,  "runtime": 55.0},
    "LLVM-O1":  {"compile_time": 100.0, "runtime": 27.5},   # ~10x slower compile than O0, ~2x faster runtime
}

labels = list(data.keys())
x = np.array([data[k]["compile_time"] for k in labels])
y = np.array([data[k]["runtime"] for k in labels])

# Generate normal distribution of points around each category
np.random.seed(42)
n_points = 100
all_points = []

for label in labels:
    compile_mean = data[label]["compile_time"]
    runtime_mean = data[label]["runtime"]
    
    compile_samples = np.random.normal(compile_mean, compile_mean * 0.1, n_points)
    runtime_samples = np.random.normal(runtime_mean, runtime_mean * 0.1, n_points)
    
    for c, r in zip(compile_samples, runtime_samples):
        all_points.append({"compile_time": c, "runtime": r, "category": label})

# Find Pareto front (lower is better for both metrics)

df_all = pd.DataFrame(all_points)
df_all.to_csv("output/pareto/all.csv", index=False)

# Identify Pareto dominant points
dominated = np.zeros(len(df_all), dtype=bool)
for i in range(len(df_all)):
    for j in range(len(df_all)):
        if i != j:
            if (df_all.iloc[j]["compile_time"] <= df_all.iloc[i]["compile_time"] and
                df_all.iloc[j]["runtime"] <= df_all.iloc[i]["runtime"] and
                (df_all.iloc[j]["compile_time"] < df_all.iloc[i]["compile_time"] or
                 df_all.iloc[j]["runtime"] < df_all.iloc[i]["runtime"])):
                dominated[i] = True
                break

df_pareto = df_all[~dominated].sort_values(by="compile_time")
df_pareto.to_csv("output/pareto/dominators.csv", index=False)