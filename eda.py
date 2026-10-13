from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "productivity_monthly.csv"

df = pd.read_csv(DATA)

print("Shape:", df.shape)
print()
print(df.dtypes)
print()
print("Total missing value:", df.isna().sum().sum())
print("Baris duplikat:", df.duplicated().sum())
print("Blok unik:", df["Block_ID"].nunique())
print("Rentang tahun:", df["Year"].min(), "-", df["Year"].max())

# Penanda baris yang sudah berproduksi (sama dengan kolom Is_Mature di Excel)
df["Is_Mature"] = (df["Plant_Status"] != "TBM").astype(int)
print()
print(df["Is_Mature"].value_counts().sort_index())
# Kelompok umur (sama dengan AgeGroup di Excel)
df["AgeGroup"] = pd.cut(
    df["Plant_Age_Years"],
    bins=[-1, 2, 5, 10, 16, 100],
    labels=["1) 0-2 TBM", "2) 3-5", "3) 6-10", "4) 11-16", "5) 17+"],
)

# Hanya blok yang sudah berproduksi
mature = df[df["Is_Mature"] == 1]

print()
print("Rata-rata produktivitas (blok berproduksi):", round(mature["Productivity_t_Ha"].mean(), 2))

print()
print("Rata-rata per tahun:")
print(mature.groupby("Year")["Productivity_t_Ha"].mean().round(2))

print()
print("Rata-rata per kelompok umur:")
print(mature.groupby("AgeGroup", observed=True)["Productivity_t_Ha"].mean().round(2))
import matplotlib.pyplot as plt
import seaborn as sns

CHARTS = BASE / "charts"
CHARTS.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid")

# Grafik 1: tren tahunan
yearly = mature.groupby("Year")["Productivity_t_Ha"].mean().reset_index()

fig, ax = plt.subplots(figsize=(9, 5))
sns.lineplot(data=yearly, x="Year", y="Productivity_t_Ha", marker="o", ax=ax)
ax.set_ylim(bottom=0)
ax.set_xticks(yearly["Year"])
ax.set_title("Rata-rata Produktivitas Bulanan per Tahun (blok berproduksi)")
ax.set_xlabel("Tahun")
ax.set_ylabel("t/ha per bulan")
fig.tight_layout()
fig.savefig(CHARTS / "01_tren_tahunan.png", dpi=150)
plt.close(fig)

# Grafik 2: kelompok umur
age = mature.groupby("AgeGroup", observed=True)["Productivity_t_Ha"].mean().reset_index()
age["AgeGroup"] = age["AgeGroup"].cat.remove_unused_categories()

fig, ax = plt.subplots(figsize=(8, 5))
sns.barplot(data=age, x="AgeGroup", y="Productivity_t_Ha", color="#4472C4", ax=ax)
ax.bar_label(ax.containers[0], fmt="%.2f")
ax.set_title("Produktivitas per Kelompok Umur Tanaman")
ax.set_xlabel("Umur tanaman (tahun)")
ax.set_ylabel("t/ha per bulan")
fig.tight_layout()
fig.savefig(CHARTS / "02_kelompok_umur.png", dpi=150)
plt.close(fig)

print()
print("Grafik tersimpan di:", CHARTS)
# Grafik 3: tren tahunan, dipisah per kelompok umur
by_age_year = (
    mature.groupby(["Year", "AgeGroup"], observed=True)["Productivity_t_Ha"]
    .mean()
    .reset_index()
)
by_age_year["AgeGroup"] = by_age_year["AgeGroup"].cat.remove_unused_categories()

print()
print("Rata-rata per tahun dan kelompok umur:")
print(by_age_year.pivot(index="Year", columns="AgeGroup", values="Productivity_t_Ha").round(2))

fig, ax = plt.subplots(figsize=(10, 5.5))
sns.lineplot(
    data=by_age_year, x="Year", y="Productivity_t_Ha",
    hue="AgeGroup", marker="o", ax=ax,
)
ax.set_ylim(bottom=0)
ax.set_xticks(sorted(by_age_year["Year"].unique()))
ax.set_title("Produktivitas Bulanan per Tahun, Dipisah per Kelompok Umur")
ax.set_xlabel("Tahun")
ax.set_ylabel("t/ha per bulan")
ax.legend(title="Umur tanaman (tahun)")
fig.tight_layout()
fig.savefig(CHARTS / "03_tren_per_umur.png", dpi=150)
plt.close(fig)
# Grafik 4: heatmap tahun x bulan
heat = mature.pivot_table(
    index="Year", columns="Month_Number",
    values="Productivity_t_Ha", aggfunc="mean",
)

print()
print("Heatmap tahun x bulan:")
print(heat.round(2))

fig, ax = plt.subplots(figsize=(11, 6))
sns.heatmap(
    heat, annot=True, fmt=".2f", cmap="YlGn",
    cbar_kws={"label": "t/ha per bulan"}, ax=ax,
)
ax.tick_params(axis="y", rotation=0)
ax.set_title("Produktivitas Bulanan: Tahun x Bulan (blok berproduksi)")
ax.set_xlabel("Bulan (1 = Januari, 12 = Desember)")
ax.set_ylabel("Tahun")
fig.tight_layout()
fig.savefig(CHARTS / "04_heatmap_tahun_bulan.png", dpi=150)
plt.close(fig)
# Indeks relatif blok: dibandingkan dengan blok lain pada tahun dan kelompok umur yang sama
mature = mature.copy()
cell = mature.groupby(["Year", "AgeGroup"], observed=True)
mature["Cell_Blocks"] = cell["Block_ID"].transform("nunique")
mature["Cell_Mean"] = cell["Productivity_t_Ha"].transform("mean")
mature["Rel_Index"] = mature["Productivity_t_Ha"] / mature["Cell_Mean"]

# Hanya bandingkan jika minimal ada 5 blok di kelompok tahun-umur tersebut
fair = mature[mature["Cell_Blocks"] >= 5]
print()
print("Baris dipakai:", len(fair), "dari", len(mature))

block_index = (
    fair.groupby("Block_ID")["Rel_Index"].mean().sort_values(ascending=False).round(3)
)
print()
print("5 blok teratas:")
print(block_index.head(5))
print()
print("5 blok terbawah:")
print(block_index.tail(5))

# Grafik 5: 8 blok teratas dan 8 blok terbawah, dalam persen terhadap rata-rata
extremes = pd.concat([block_index.head(8), block_index.tail(8)]).reset_index()
extremes.columns = ["Block_ID", "Rel_Index"]
extremes["Pct"] = (extremes["Rel_Index"] - 1) * 100
colors = ["#4472C4" if v >= 0 else "#C0504D" for v in extremes["Pct"]]

fig, ax = plt.subplots(figsize=(8, 7))
bars = ax.barh(extremes["Block_ID"], extremes["Pct"], color=colors)
ax.bar_label(bars, fmt="%+.1f%%", padding=3)
ax.axvline(0, color="black", linewidth=1)
ax.set_xlim(-28, 21)
ax.invert_yaxis()
ax.set_title("Produktivitas Blok vs Blok Sebaya (tahun dan kelompok umur sama)")
ax.set_xlabel("Selisih terhadap rata-rata blok sebaya (%)")
ax.set_ylabel("Blok")
fig.tight_layout()
fig.savefig(CHARTS / "05_indeks_relatif_blok.png", dpi=150)
plt.close(fig)