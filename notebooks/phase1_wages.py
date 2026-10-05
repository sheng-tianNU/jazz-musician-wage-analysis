# %% [markdown]
# # Phase 1: What do musicians actually earn? (BLS OEWS, May 2025)
#
# Source: BLS Occupational Employment and Wage Statistics, `all_data_M_2025.xlsx`.
# Occupation of interest: SOC 27-2042, Musicians and Singers.
#
# Two limits to keep in mind:
# - OEWS only counts **employees**. Self-employed gig players are not in it, which is
#   most working jazz musicians. Treat these numbers as "musicians with a payroll job".
# - BLS publishes only **hourly** wages for musicians (they typically work fewer than
#   2,080 hours a year and are paid by the hour), so every figure here is hourly.
#
# Run as a script (`python notebooks/phase1_wages.py`) or cell by cell in VS Code.

# %%
import matplotlib.pyplot as plt
import pandas as pd

from style import BLUE, GRAY, INK, MUTED, ROOT, save

RAW = ROOT / "data" / "oesm25all" / "all_data_M_2025.xlsx"
SUBSET = ROOT / "data" / "creative_occ_2025.csv"

MUSICIANS = "27-2042"
CREATIVE = {
    "27-2042": "Musicians & singers",
    "27-2011": "Actors",
    "27-2031": "Dancers",
    "27-2041": "Music directors & composers",
    "27-2012": "Producers & directors",
    "00-0000": "All occupations",
}

# The raw file is ~413k rows and slow to read, so cache the rows we need.
if not SUBSET.exists():
    raw = pd.read_excel(RAW, dtype=str)
    raw[raw.OCC_CODE.isin(CREATIVE)].to_csv(SUBSET, index=False)

df = pd.read_csv(SUBSET, dtype=str)
# BLS markers: "*" / "**" = suppressed, "#" = above BLS's reporting cap (none in these rows).
num_cols = ["TOT_EMP", "H_PCT10", "H_PCT25", "H_MEDIAN", "H_PCT75", "H_PCT90", "LOC_QUOTIENT"]
for c in num_cols:
    df[c] = pd.to_numeric(df[c].str.replace(",", ""), errors="coerce")

national = df[(df.AREA_TYPE == "1") & (df.I_GROUP == "cross-industry")]
mus = df[df.OCC_CODE == MUSICIANS]

# %% [markdown]
# ## 1. The spread: musicians earn the highest median of any performing job, with a huge range
# Each line runs from the 10th to the 90th percentile hourly wage; the dot is the median.

# %%
spread = national.set_index("OCC_CODE").loc[list(CREATIVE)].assign(
    label=lambda d: d.index.map(CREATIVE)
).sort_values("H_MEDIAN")

fig, ax = plt.subplots(figsize=(8, 4))
for i, (code, r) in enumerate(spread.iterrows()):
    color = BLUE if code == MUSICIANS else GRAY
    ax.plot([r.H_PCT10, r.H_PCT90], [i, i], color=color, lw=2, solid_capstyle="round")
    ax.plot(r.H_MEDIAN, i, "o", ms=9, color=color, mec="#fcfcfb", mew=2)
    ax.annotate(f"${r.H_MEDIAN:.2f}", (r.H_MEDIAN, i), xytext=(0, 9),
                textcoords="offset points", ha="center", fontsize=9, color=MUTED)
ax.set_yticks(range(len(spread)), spread.label)
ax.margins(y=0.15)  # room for the top row's median label
ax.set_xlabel("Hourly wage, 10th to 90th percentile (dot = median)")
ax.xaxis.set_major_formatter("${x:.0f}")
ax.set_title("Musicians: high median, enormous spread", loc="left", color=INK)
save(fig, "01_creative_wage_spread.png", "Source: U.S. Bureau of Labor Statistics, OEWS, May 2025")

m = spread.loc[MUSICIANS]
print(f"Musicians P90/P10 ratio: {m.H_PCT90 / m.H_PCT10:.1f}x "
      f"(all occupations: {spread.loc['00-0000'].H_PCT90 / spread.loc['00-0000'].H_PCT10:.1f}x)")

# %% [markdown]
# ## 2. Who employs musicians, and who pays best
# National, 4-digit industries with at least 500 musicians on payroll.

# %%
ind = mus[(mus.AREA_TYPE == "1") & (mus.I_GROUP == "4-digit") & (mus.TOT_EMP >= 500)]
ind = ind.dropna(subset=["H_MEDIAN"]).sort_values("H_MEDIAN")
SHORT = {
    "Promoters of Performing Arts, Sports, and Similar Events": "Event promoters",
    "Religious Organizations": "Religious organizations",
    "Performing Arts Companies": "Performing arts companies",
    "Other Schools and Instruction": "Private lessons & other schools",
    "Colleges, Universities, and Professional Schools": "Colleges & universities",
    "Independent Artists, Writers, and Performers": "Independent artists",
    "Elementary and Secondary Schools": "K-12 schools",
}
ind_label = ind.NAICS_TITLE.map(SHORT).fillna(ind.NAICS_TITLE)

fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(ind_label, ind.H_MEDIAN, color=BLUE, height=0.6)
for y, (med, emp) in enumerate(zip(ind.H_MEDIAN, ind.TOT_EMP)):
    ax.annotate(f"${med:.2f}  ({emp:,.0f} jobs)", (med, y), xytext=(4, 0),
                textcoords="offset points", va="center", fontsize=9, color=MUTED)
ax.set_xlim(0, ind.H_MEDIAN.max() * 1.45)
ax.xaxis.set_major_formatter("${x:.0f}")
ax.set_xlabel("Median hourly wage, musicians & singers")
ax.set_title("Churches outpay schools; event promoters pay the most", loc="left", color=INK)
save(fig, "02_industry_median.png", "Source: U.S. Bureau of Labor Statistics, OEWS, May 2025")

# %% [markdown]
# ## 3. Jazz cities
# New Orleans' wage is suppressed and only ~110 musicians are on payroll. That reflects
# BLS methodology (cash gigs, self-employment) more than the size of the scene.

# %%
HUBS = {
    "New York-Newark-Jersey City, NY-NJ": "New York",
    "San Francisco-Oakland-Fremont, CA": "San Francisco",
    "Las Vegas-Henderson-North Las Vegas, NV": "Las Vegas",
    "Los Angeles-Long Beach-Anaheim, CA": "Los Angeles",
    "Chicago-Naperville-Elgin, IL-IN": "Chicago",
    "Nashville-Davidson--Murfreesboro--Franklin, TN": "Nashville",
    "New Orleans-Metairie, LA": "New Orleans",
}
metro = mus[(mus.AREA_TYPE == "4") & mus.AREA_TITLE.isin(HUBS)].copy()
metro["city"] = metro.AREA_TITLE.map(HUBS)
metro = metro.sort_values("H_MEDIAN", na_position="first")

fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(metro.city, metro.H_MEDIAN.fillna(0), color=BLUE, height=0.6)
for y, r in enumerate(metro.itertuples()):
    text = (f"${r.H_MEDIAN:.2f}" if pd.notna(r.H_MEDIAN) else "wage suppressed") \
        + f"  ({r.TOT_EMP:,.0f} jobs)"
    ax.annotate(text, (0 if pd.isna(r.H_MEDIAN) else r.H_MEDIAN, y), xytext=(4, 0),
                textcoords="offset points", va="center", fontsize=9, color=MUTED)
ax.set_xlim(0, metro.H_MEDIAN.max() * 1.45)
ax.xaxis.set_major_formatter("${x:.0f}")
ax.set_xlabel("Median hourly wage, musicians & singers")
ax.set_title("New York leads; New Orleans is invisible to BLS", loc="left", color=INK)
save(fig, "03_jazz_cities.png", "Source: U.S. Bureau of Labor Statistics, OEWS, May 2025")

# %% [markdown]
# ## 4. States: top and bottom 8 by median hourly wage
# BLS lists only 41 of the 50 states + DC, and suppresses 13 of those (including New York
# and Tennessee), so just 28 have a median.

# %%
states = mus[mus.AREA_TYPE == "2"].dropna(subset=["H_MEDIAN"]).sort_values("H_MEDIAN")
ends = pd.concat([states.head(8), states.tail(8)])

fig, ax = plt.subplots(figsize=(8, 5.5))
colors = [GRAY] * 8 + [BLUE] * 8
ax.barh(ends.AREA_TITLE, ends.H_MEDIAN, color=colors, height=0.6)
for y, med in enumerate(ends.H_MEDIAN):
    ax.annotate(f"${med:.2f}", (med, y), xytext=(4, 0), textcoords="offset points",
                va="center", fontsize=9, color=MUTED)
ax.xaxis.set_major_formatter("${x:.0f}")
ax.set_xlabel("Median hourly wage, musicians & singers")
ax.set_title(f"{ends.AREA_TITLE.iloc[-1]} pays {ends.H_MEDIAN.iloc[-1] / ends.H_MEDIAN.iloc[0]:.1f}x "
             f"{ends.AREA_TITLE.iloc[0]}", loc="left", color=INK)
save(fig, "04_states.png", "Source: U.S. Bureau of Labor Statistics, OEWS, May 2025")
print(f"States with a reported median: {len(states)} of {(mus.AREA_TYPE == '2').sum()}")

# %% [markdown]
# ## Why some states pay more: concentration (location quotient, 1.0 = US average) and
# BLS's relative standard error of the mean wage (MEAN_PRSE, %), plus casino-adjacent industries.

# %%
st = mus[mus.AREA_TYPE == "2"].assign(
    LQ=lambda d: d.LOC_QUOTIENT, PRSE=lambda d: pd.to_numeric(d.MEAN_PRSE, errors="coerce"))
print(st.sort_values("LQ", ascending=False)[["AREA_TITLE", "TOT_EMP", "LQ", "H_MEDIAN"]].head(3).to_string(index=False))
print(st.dropna(subset=["H_MEDIAN"]).sort_values("PRSE", ascending=False)[["AREA_TITLE", "TOT_EMP", "PRSE"]].head(3).to_string(index=False))
nat = mus[(mus.AREA_TYPE == "1")]
print(nat[nat.NAICS.isin(["721000", "713000", "711300"])][["NAICS_TITLE", "TOT_EMP", "H_MEDIAN"]].to_string(index=False))

# %% Summary table for the README.
summary = mus[(mus.AREA_TYPE == "1") & (mus.I_GROUP == "cross-industry")][
    ["TOT_EMP", "H_PCT10", "H_PCT25", "H_MEDIAN", "H_PCT75", "H_PCT90"]]
print(summary.to_string(index=False))
