# %% [markdown]
# # Phase 3: Does a musician's pay cover the cost of living?
#
# Two views:
# - **Jazz cities:** add up a year of basic costs (MIT Living Wage Calculator, one adult,
#   no children) and compare them to what the median musician there earns.
# - **States:** adjust each state's median wage for local prices (BEA Regional Price
#   Parities) to see who earns the most in real terms.
#
# Wages are hourly (BLS publishes only hourly pay for musicians), so the honest question is
# "how many hours a week must a musician work to cover basic costs?" We also show the
# full-time (2,080 hr) annual figure for scale.
#
# Run: `python notebooks/phase3_cost_of_living.py` (needs phase 1's data cache;
# downloads BEA + MIT data on first run).

# %%
import io
import urllib.request
import zipfile

import matplotlib.pyplot as plt
import pandas as pd

from style import BLUE, GRAY, INK, MUTED, ROOT, save

DATA = ROOT / "data"
UA = {"User-Agent": "Mozilla/5.0"}  # both sites reject the default Python user agent
FULL_TIME_HOURS = 2080


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read()


def money(s):
    return pd.to_numeric(s.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")


oews = pd.read_csv(DATA / "creative_occ_2025.csv", dtype=str)
mus = oews[oews.OCC_CODE == "27-2042"].copy()
for c in ["TOT_EMP", "H_PCT25", "H_MEDIAN"]:
    mus[c] = pd.to_numeric(mus[c].str.replace(",", ""), errors="coerce")

# %% [markdown]
# ## Data: MIT living costs for the jazz cities (cached to data/mit_living_costs_2026.csv)

# %%
CITIES = {  # MIT metro code -> (short name, OEWS area title)
    35620: ("New York", "New York-Newark-Jersey City, NY-NJ"),
    41860: ("San Francisco", "San Francisco-Oakland-Fremont, CA"),
    31080: ("Los Angeles", "Los Angeles-Long Beach-Anaheim, CA"),
    16980: ("Chicago", "Chicago-Naperville-Elgin, IL-IN"),
    34980: ("Nashville", "Nashville-Davidson--Murfreesboro--Franklin, TN"),
    29820: ("Las Vegas", "Las Vegas-Henderson-North Las Vegas, NV"),
    35380: ("New Orleans", "New Orleans-Metairie, LA"),
}
MIT_CACHE = DATA / "mit_living_costs_2026.csv"
if not MIT_CACHE.exists():
    rows = []
    for code, (city, _) in CITIES.items():
        page = fetch(f"https://livingwage.mit.edu/metros/{code}").decode("utf-8", "replace")
        t = pd.read_html(io.StringIO(page), attrs={"class": "results_table table-striped expense_table"},
                         flavor="lxml")[0]
        # Column 1 = "1 adult, 0 children". Keep only that household type.
        rows.append(pd.Series(money(t.iloc[:, 1]).values, index=t.iloc[:, 0], name=city))
    pd.DataFrame(rows).rename_axis("city").to_csv(MIT_CACHE)
mit = pd.read_csv(MIT_CACHE, index_col="city")

# Group MIT's budget lines into a few readable stacks. Taxes are included because
# the musician wages we compare against are before tax.
STACK = {
    "Housing": ["Housing"],
    "Food": ["Food"],
    "Medical": ["Medical"],
    "Transportation": ["Transportation"],
    "Everything else": ["Civic", "Internet & Mobile", "Other", "Child Care"],
    "Taxes": ["Annual taxes"],
}
costs = pd.DataFrame({k: mit[v].sum(axis=1) for k, v in STACK.items()})
# The rounded parts add back up to MIT's own "before taxes" total (within $1 a part); show MIT's.
assert (costs.sum(axis=1) - mit["Required annual income before taxes"]).abs().max() <= len(STACK)
costs["Total"] = mit["Required annual income before taxes"]

pay = mus[mus.AREA_TYPE == "4"].set_index("AREA_TITLE")
costs["median_hourly"] = [pay.H_MEDIAN.get(t) for _, t in CITIES.values()]
costs["full_time_pay"] = costs.median_hourly * FULL_TIME_HOURS
costs["hours_per_week"] = costs.Total / costs.median_hourly / 52
costs = costs.sort_values("Total")
print(costs[["Total", "median_hourly", "full_time_pay", "hours_per_week"]].round(1).to_string())

# %% [markdown]
# ## 7. A year of basic costs vs. a year of median musician pay
# Bars = MIT's basic budget for one adult (pre-tax). Diamond = median musician wage x 2,080 hrs.

# %%
# Housing in blue (the cost that matters most); the rest step from dark to light gray.
shades = [BLUE, "#6f6e69", "#8f8e88", "#a8a7a0", "#c9c8c1", "#e2e1da"]
fig, ax = plt.subplots(figsize=(9, 4.6))
left = pd.Series(0.0, index=costs.index)
for part, color in zip(STACK, shades):
    ax.barh(costs.index, costs[part], left=left, color=color, height=0.6, label=part,
            edgecolor="#fcfcfb", linewidth=0.8)
    left += costs[part]
ax.plot(costs.full_time_pay, costs.index, "D", color=INK, ms=7, label="Median musician pay, full time")
xmax = costs[["Total", "full_time_pay"]].max().max() * 1.45
for y, r in enumerate(costs.itertuples()):
    text = ("wage suppressed by BLS" if pd.isna(r.median_hourly)
            else f"costs covered by ~{r.hours_per_week:.0f} hrs/week")
    ax.annotate(text, (max(r.Total, r.full_time_pay if pd.notna(r.full_time_pay) else 0), y),
                xytext=(8, 0), textcoords="offset points", va="center", fontsize=9, color=MUTED)
ax.set_xlim(0, xmax)
ax.xaxis.set_major_formatter(lambda x, _: f"${x / 1e3:.0f}k")
ax.set_xlabel("Per year, before tax (one adult, no children)")
ax.set_title("Where BLS reports a wage, 15 to 23 hrs/week covers basic costs", loc="left", color=INK)
ax.legend(ncol=4, fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18))
save(fig, "07_city_costs_vs_pay.png", "Sources: Living wage data sourced from the Living Wage Institute via https://livingwage.mit.edu, accessed Oct 3, 2026; "
     "BLS OEWS, May 2025")

# %% [markdown]
# ## Data: BEA Regional Price Parities by state, 2024 (cached to data/bea_rpp_state.csv)
# RPP = how expensive a state is vs. the US average (100). 110 = 10% pricier.

# %%
RPP_CACHE = DATA / "bea_rpp_state.csv"
if not RPP_CACHE.exists():
    z = zipfile.ZipFile(io.BytesIO(fetch("https://apps.bea.gov/regional/zip/SARPP.zip")))
    RPP_CACHE.write_bytes(z.read("SARPP_STATE_2008_2024.csv"))
rpp = pd.read_csv(RPP_CACHE, dtype=str)
rpp = rpp[rpp.LineCode == "1"]  # line 1 = all items; also drops the footer notes
rpp = pd.Series(rpp["2024"].astype(float).values, index=rpp.GeoName.str.strip())

# %% [markdown]
# ## 8. States: what the median wage is worth after local prices
# Gray = paycheck as reported; blue = adjusted to US-average prices (wage / RPP x 100).

# %%
states = mus[(mus.AREA_TYPE == "2")].dropna(subset=["H_MEDIAN"]).set_index("AREA_TITLE")
states = states.assign(rpp=states.index.map(rpp))
assert states.rpp.notna().all(), "a state name didn't match BEA's list"
states["real"] = states.H_MEDIAN / states.rpp * 100
states["rank_nominal"] = states.H_MEDIAN.rank(ascending=False).astype(int)
states["rank_real"] = states.real.rank(ascending=False).astype(int)
states = states.sort_values("real")

fig, ax = plt.subplots(figsize=(8, 8))
y = range(len(states))
ax.hlines(y, states.H_MEDIAN, states.real, color=GRAY, lw=2)
ax.plot(states.H_MEDIAN, y, "o", color=GRAY, ms=6, label="Reported")
ax.plot(states.real, y, "o", color=BLUE, ms=7, label="Adjusted for local prices")
for i, r in enumerate(states.itertuples()):
    ax.annotate(f"${r.real:.2f}", (max(r.real, r.H_MEDIAN), i), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=8, color=MUTED)
ax.set_yticks(list(y), states.index)
ax.xaxis.set_major_formatter("${x:.0f}")
ax.set_xlabel("Median hourly wage, musicians & singers")
ax.set_title("After local prices: Iowa climbs 6 places, Hawaii drops 5", loc="left", color=INK)
ax.legend(frameon=False, loc="lower right")
save(fig, "08_states_real_wage.png", "Sources: BLS OEWS, May 2025; "
     "U.S. Bureau of Economic Analysis, Regional Price Parities, 2024")

moves = (states.rank_nominal - states.rank_real).sort_values()
print(f"{len(states)} states. Biggest climbers (rank change):\n{moves.tail(4).to_string()}")
print(f"Biggest fallers:\n{moves.head(4).to_string()}")
print(states.sort_values("real", ascending=False)[["H_MEDIAN", "rpp", "real"]].round(2).head(5).to_string())
