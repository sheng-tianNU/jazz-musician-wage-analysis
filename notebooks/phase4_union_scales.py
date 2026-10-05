# %% [markdown]
# # Phase 4: What does a union gig in New York pay?
#
# AFM Local 802 (the New York musicians' union) publishes minimum pay ("scale") for
# freelance classical concerts, chamber music and religious services. We parse that PDF,
# turn its per-service rates into hourly pay, and compare it to what BLS says payroll
# musicians in the New York metro actually earn per hour.
#
# Limits:
# - Local 802's club-date and Broadway scales (where most jazz work sits) are members only.
#   The classical scale is the closest public union rate, and church work ties back to
#   Phase 1 (religious organizations pay musicians well).
# - Scale is a minimum per service. Practice, travel and unpaid hours between gigs aren't in it.
# - We use the first contract year (Sep 2025 to Sep 2026), the closest to BLS's May 2025 data.
#
# Run: `python notebooks/phase4_union_scales.py` (needs pdfplumber; downloads the PDF once).

# %%
import re
import urllib.request

import matplotlib.pyplot as plt
import pandas as pd
import pdfplumber

from style import BLUE, GRAY, INK, MUTED, ROOT, save

DATA = ROOT / "data"
PDF_URL = ("https://www.local802afm.org/wp-content/uploads/2025/12/"
           "SINGLE-ENGAGEMENT-CLASSICAL-SCALES-2025-2028-v121625.pdf")
PDF = DATA / "local802_classical_scales_2025_2028.pdf"
if not PDF.exists():
    req = urllib.request.Request(PDF_URL, headers={"User-Agent": "Mozilla/5.0"})
    PDF.write_bytes(urllib.request.urlopen(req).read())

# %% [markdown]
# ## Data: every line in the PDF that ends in dollar amounts (saved to data/local802_scales.csv)
# Rate lines look like `Rehearsal per hour $71.46 $74.32 $77.29`, one column per contract
# year. The same label (e.g. "2 ½ hours or less") appears under several engagement types,
# so we track which section heading we are under.

# %%
SECTIONS = {"CLASSICAL CONCERT (": "concert", "CHAMBER MUSIC (": "chamber",
            "RELIGIOUS SERVICE (": "religious", "The Following Conditions": "all"}
rows, section = [], None
with pdfplumber.open(PDF) as pdf:
    text = "\n".join(page.extract_text() for page in pdf.pages)
for line in text.splitlines():
    section = next((s for h, s in SECTIONS.items() if line.startswith(h)), section)
    amounts = re.findall(r"\$([\d,]+\.\d\d)", line)
    if amounts:
        label = line[:line.index("$")].strip()
        rows.append([section, label] + [float(a.replace(",", "")) for a in amounts])
scales = pd.DataFrame(rows).rename(columns=lambda c: ["section", "item"][c] if c < 2 else f"rate{c - 1}")
scales.to_csv(DATA / "local802_scales.csv", index=False)


def rate(section, item, col=2):
    """First rate in `section` whose label contains `item`. col 2 = rate1 = first contract year."""
    hit = scales[(scales.section == section) & scales.item.str.contains(item, regex=False)]
    assert len(hit), f"no '{item}' in {section}"
    return float(hit.iloc[0, col])


PENSION = float(re.search(r"([\d.]+)% as per AFM-EPF", text).group(1)) / 100
# Health has 5 columns (it steps up on Jan 1); column 3 = Jan 1 to Sep 11, 2026.
HEALTH_SHOW = rate("all", "CONTRIBUTIONS", 3)
HEALTH_REH = rate("all", "PLUS, per musician each rehearsal", 3)

perf = {s: rate(s, "hours or less") for s in ["concert", "chamber"]}  # one show, up to 2½ hrs
reh_call = {s: rate(s, "minimum call") for s in ["concert", "chamber"]}  # 2½-hour rehearsal
church_service = rate("religious", "on the same day within 3 hours")
church_reh = rate("religious", "call of 2 hours")
print(f"pension {PENSION:.2%}, health ${HEALTH_SHOW}/show + ${HEALTH_REH}/rehearsal")
print("performance:", perf, "rehearsal call:", reh_call)
print("church service:", church_service, "church rehearsal:", church_reh)

# Sanity checks against numbers read by eye from the PDF.
assert perf["concert"] == 356.01 and reh_call["concert"] == 178.65
assert church_service == 356.01 and round(PENSION, 4) == 0.1799

# %% [markdown]
# ## A typical gig, end to end
# "Gig" = one booking, not a steady job. Our assumption (not the union's): a concert gig is
# two 2½-hour rehearsals plus one 2½-hour concert; a church gig is one 2-hour rehearsal on an
# earlier day plus a service of up to 3 hours. (A rehearsal on the same day, inside the 3-hour
# window, is already covered by the service fee, so it would not be paid separately.)
# Pension and health are paid by the employer on top of wages, into union funds.

# %%
gigs = pd.DataFrame({
    "Orchestra concert\n(15+ players)": [perf["concert"], 2 * reh_call["concert"], 7.5, 2],
    "Chamber concert\n(14 or fewer)": [perf["chamber"], 2 * reh_call["chamber"], 7.5, 2],
    "Church service": [church_service, church_reh, 5, 1],
}, index=["show", "rehearsals", "hours", "n_reh"]).T
gigs["wages"] = gigs.show + gigs.rehearsals
gigs["pension"] = gigs.wages * PENSION
gigs["health"] = HEALTH_SHOW + gigs.n_reh * HEALTH_REH
gigs["hourly"] = gigs.wages / gigs.hours

mit = pd.read_csv(DATA / "mit_living_costs_2026.csv", index_col="city")
NYC_BUDGET = mit.loc["New York", "Required annual income before taxes"]
gigs["gigs_for_budget"] = NYC_BUDGET / gigs.wages  # wages only: benefits aren't spendable cash
print(gigs.round(2).to_string())

# %% [markdown]
# ## 9. Union scale per hour vs. what New York payroll musicians earn
# Gray = BLS wage percentiles for musicians in the New York metro (May 2025).
# Blue = Local 802 minimums turned into hourly pay. A flat performance fee is divided by
# the longest time it covers, so the real hourly rate is at least this.

# %%
oews = pd.read_csv(DATA / "creative_occ_2025.csv", dtype=str)
nyc = oews[(oews.OCC_CODE == "27-2042")
           & (oews.AREA_TITLE == "New York-Newark-Jersey City, NY-NJ")].iloc[0]
bars = pd.Series({
    "BLS NYC 25th percentile": float(nyc.H_PCT25),
    "BLS NYC median": float(nyc.H_MEDIAN),
    "BLS NYC 75th percentile": float(nyc.H_PCT75),
    "BLS NYC 90th percentile": float(nyc.H_PCT90),
    "Union rehearsal, per hour": rate("concert", "Rehearsal per hour"),
    "Union full concert gig (7.5 hrs)": gigs.hourly.iloc[0],
    "Union church service (3 hrs)": church_service / 3,
    "Union orchestra concert (2.5 hrs)": perf["concert"] / 2.5,
    "Union chamber concert (2.5 hrs)": perf["chamber"] / 2.5,
}).sort_values()

fig, ax = plt.subplots(figsize=(9, 4.8))
colors = [BLUE if k.startswith("Union") else GRAY for k in bars.index]
ax.barh(bars.index, bars, color=colors, height=0.6)
for y, v in enumerate(bars):
    ax.annotate(f"${v:.2f}", (v, y), xytext=(5, 0), textcoords="offset points",
                va="center", fontsize=9, color=MUTED)
ax.axvline(float(nyc.H_MEDIAN), color=INK, lw=0.8, ls=":")
ax.xaxis.set_major_formatter("${x:.0f}")
ax.set_xlim(0, bars.max() * 1.15)
ax.set_xlabel("Dollars per hour, before tax")
ax.set_title("Union minimums beat what most NYC musicians earn per hour", loc="left", color=INK)
save(fig, "09_union_vs_bls_hourly.png", "Sources: AFM Local 802 Single Engagement Classical Scales 2025 to 2028; BLS OEWS, May 2025")

# %% [markdown]
# ## 10. One gig's full pay, and how many it takes to cover a year in New York
# Wages are cash. Pension and health go to union funds, so they don't pay rent.

# %%
parts = {"Concert or service": ("show", BLUE), "Rehearsals": ("rehearsals", "#7fb0ea"),
         "Pension (employer)": ("pension", "#8f8e88"), "Health (employer)": ("health", "#c9c8c1")}
fig, ax = plt.subplots(figsize=(9, 3.6))
left = pd.Series(0.0, index=gigs.index)
for label, (col, color) in parts.items():
    ax.barh(gigs.index, gigs[col], left=left, color=color, height=0.6, label=label,
            edgecolor="#fcfcfb", linewidth=0.8)
    left += gigs[col]
for y, r in enumerate(gigs.itertuples()):
    ax.annotate(f"${r.wages:,.0f} cash. {r.gigs_for_budget:.0f} a year cover NYC basics",
                (left.iloc[y], y), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=9, color=MUTED)
ax.set_xlim(0, left.max() * 1.8)
ax.xaxis.set_major_formatter("${x:,.0f}")
ax.set_xlabel(f"Per gig at union minimum (NYC basic budget: ${NYC_BUDGET:,.0f}/yr, MIT)")
ax.invert_yaxis()
ax.set_title("Covering a New York budget takes about 2 union gigs every week",
             loc="left", color=INK)
ax.legend(ncol=4, fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.3))
save(fig, "10_union_job_breakdown.png", "Sources: AFM Local 802 Single Engagement Classical Scales 2025 to 2028.\n"
     "Living wage data sourced from the Living Wage Institute via https://livingwage.mit.edu, accessed Oct 3, 2026. Gig structures are our assumptions.")
