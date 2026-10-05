# %% [markdown]
# # Phase 2: Could streaming replace a musician's paycheck?
#
# Question: how many Spotify streams per year would it take to earn what the median
# payroll musician earns (Phase 1), and how many artists actually get there?
#
# Inputs (all published, see README for links):
# - Median musician wage: $47.80/hr, BLS OEWS May 2025 (read from the Phase 1 cache).
# - Per-stream payout to rights holders: about $0.003 to $0.005 (industry estimates;
#   Spotify pays from a revenue pool, not a fixed rate per stream).
# - Spotify Loud & Clear 2025: how many artists generated at least $X on Spotify.
#
# Assumptions (ours, change them below):
# - 2,080 hours = a full-time year. BLS won't publish annual pay for musicians because
#   most don't work full-time, so this is a "full-time equivalent", not a typical income.
# - The artist's cut of what the rights holder receives depends on the deal. 20% is close to
#   the UK CMA's figures: 19.7% to 23.3% average royalty in new major contracts (2012 to 2021),
#   and 25.0% to 26.3% of majors' streaming income for all their UK artists, before recoupment.
# - Songwriting/publishing royalties are left out; this models the recording only.
#
# Run: `python notebooks/phase2_streaming.py` (needs phase 1's data/creative_occ_2025.csv).

# %%
import matplotlib.pyplot as plt
import pandas as pd

from style import BLUE, GRAY, INK, MUTED, ROOT, save

oews = pd.read_csv(ROOT / "data" / "creative_occ_2025.csv", dtype=str)
row = oews[(oews.OCC_CODE == "27-2042") & (oews.AREA_TYPE == "1")
           & (oews.I_GROUP == "cross-industry")].iloc[0]
MEDIAN_HOURLY = float(row.H_MEDIAN)
FULL_TIME_HOURS = 2080
TARGET = MEDIAN_HOURLY * FULL_TIME_HOURS

RATE_LOW, RATE_MID, RATE_HIGH = 0.003, 0.004, 0.005  # $ per stream to rights holders
# Share of the rights-holder payout that reaches the artist (assumed typical deals).
DEALS = {
    "DIY via distributor\n(keeps 100%)": 1.0,
    "Indie label\n(50/50 split)": 0.5,
    "Major label\n(20% royalty)": 0.2,
}


def streams_needed(target, rate, artist_share):
    return target / (rate * artist_share)


print(f"Target: ${MEDIAN_HOURLY:.2f}/hr x {FULL_TIME_HOURS:,} hrs = ${TARGET:,.0f}/yr")
assert round(streams_needed(1000, 0.004, 0.5)) == 500_000

# %% [markdown]
# ## 5. Streams per year to match the median musician's full-time pay
# Bar = $0.004 per stream; whisker = $0.005 (fewer streams) to $0.003 (more streams).

# %%
labels = list(DEALS)
mid = [streams_needed(TARGET, RATE_MID, s) / 1e6 for s in DEALS.values()]
low = [streams_needed(TARGET, RATE_HIGH, s) / 1e6 for s in DEALS.values()]
high = [streams_needed(TARGET, RATE_LOW, s) / 1e6 for s in DEALS.values()]

fig, ax = plt.subplots(figsize=(8, 3.6))
ax.barh(labels, mid, color=BLUE, height=0.55)
ax.errorbar(mid, labels, xerr=[[m - l for m, l in zip(mid, low)],
                               [h - m for h, m in zip(high, mid)]],
            fmt="none", ecolor=INK, elinewidth=1, capsize=4)
for y, (m, h) in enumerate(zip(mid, high)):
    ax.annotate(f"{m:,.0f}M a year (~{m * 1e6 / 365 / 1e3:,.0f}k a day)", (h, y), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=9, color=MUTED)
ax.set_xlim(0, max(high) * 1.6)
ax.invert_yaxis()
ax.xaxis.set_major_formatter("{x:.0f}M")
ax.set_xlabel(f"Spotify streams per year to earn ${TARGET:,.0f} (median musician, full time)")
ax.set_title("A label deal multiplies the streams you need by 5", loc="left", color=INK)
save(fig, "05_streams_needed.png", "Sources: BLS OEWS, May 2025; per-stream estimate via Royalty Exchange. "
     "Deal shares are our assumptions.")

for label, m in zip(labels, mid):
    print(f"{label.splitlines()[0]:<22} {m:6.1f}M streams/yr")

# %% [markdown]
# ## 6. How many artists actually get there? (Spotify Loud & Clear, 2025)
# "Generated" = paid to the rights holder (label or distributor), before the artist's cut.

# %%
LADDER = {  # minimum generated on Spotify in 2025 -> number of artists (worldwide)
    7_300: 100_000,
    100_000: 13_800,
    1_000_000: 1_500,
    10_000_000: 80,
}
ladder = pd.Series(LADDER)
tick = [f"${k / 1e6:.0f}M+" if k >= 1e6 else f"${k / 1e3:,.1f}k+".replace(".0k", "k")
        for k in ladder.index]
# Highlight the rung closest to the full-time median musician.
near = min(LADDER, key=lambda k: abs(k - TARGET))

fig, ax = plt.subplots(figsize=(8, 3.6))
ax.barh(tick, ladder.values, color=[BLUE if k == near else GRAY for k in ladder.index],
        height=0.55)
ax.set_xscale("log")
ax.set_xlim(10, 1e6)
for y, n in enumerate(ladder.values):
    ax.annotate(f"{n:,} artists", (n, y), xytext=(6, 0), textcoords="offset points",
                va="center", fontsize=9, color=MUTED)
ax.invert_yaxis()
ax.xaxis.set_major_formatter(lambda x, _: f"{x:,.0f}")
ax.set_xlabel("Artists worldwide (log scale)")
ax.set_ylabel("Generated on Spotify, 2025")
ax.set_title(f"More than {LADDER[near]:,} artists on Earth gross one median musician's pay",
             loc="left", color=INK)
save(fig, "06_spotify_ladder.png", "Source: Spotify Loud & Clear, 2025. Counts are minimums (\"more than\").")

hours = 7_300 / MEDIAN_HOURLY
print(f"100,000th artist: $7,300 gross = {hours:.0f} hours at the median wage "
      f"(~{hours / 40:.1f} full-time weeks), before any label split")
