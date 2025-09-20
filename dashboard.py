import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from PIL import Image

# show image in sidebar
st.sidebar.image("streamlit_pic.png", use_container_width=True)


st.set_page_config(page_title="Lebanon Commercial,Service & Non-Banking Financial Institutions, by Governorate", layout="wide")

# === PATH TO CSV =============================================================
CSV_PATH = Path(__file__).parent / "Cleaned Data.csv"

# === COLUMN SETS =============================================================
COMMERCIAL_SIZE_COLS = [
    "Total number of commercial institutions by size - number of small institutions",
    "Total number of commercial institutions by size - number of medium-sized institutions",
    "Total number of commercial institutions by size - number of large-sized institutions",
]
OTHER_COLS = [
    "Total number of service institutions",
    "Total number of non banking financial institutions",
]
EXISTENCE_COLS = [
    "Existence of commercial and service activities by type - self employment",
    "Existence of commercial and service activities by type - public sector",
    "Existence of commercial and service activities by type - banking institutions",
    "Existence of commercial and service activities by type - service institutions",
    "Existence of commercial and service activities by type - commerce",
]
EXISTENCE_LABELS = {
    EXISTENCE_COLS[0]: "Self-employment",
    EXISTENCE_COLS[1]: "Public sector",
    EXISTENCE_COLS[2]: "Banking",
    EXISTENCE_COLS[3]: "Service institutions",
    EXISTENCE_COLS[4]: "Commerce",
}

# legend mapping for Visual 1
SIZE_MAP = {
    COMMERCIAL_SIZE_COLS[0]: "Commercial — Small",
    COMMERCIAL_SIZE_COLS[1]: "Commercial — Medium",
    COMMERCIAL_SIZE_COLS[2]: "Commercial — Large",
}
OTHER_MAP = {
    "Total number of service institutions": "Service institutions",
    "Total number of non banking financial institutions": "Non-banking financial institutions",
}

# colors
COLOR_MAP_V1 = {
    "Commercial — Small": "#1f77b4",    # dark blue
    "Commercial — Medium": "#3399e6",   # medium blue
    "Commercial — Large": "#99ccff",    # light blue
    "Commercial (total)": "#1f77b4",
    "Service institutions": "#e63946",  # red
    "Non-banking financial institutions": "#f7a6b9",  # pink
}
COLOR_MAP_V3 = {
    "Commerce":              "#f7a6b9",  # pink
    "Service institutions":  "#e63946",  # red
    "Self-employment":       "#0b3d91",  # dark blue
    "Public sector":         "#74b9ff",  # clear/light blue
    "Banking":               "#2e86de",  # medium blue
}
V3_ACTIVITY_ORDER = ["Commerce", "Service institutions", "Self-employment", "Public sector", "Banking"]

# === LOAD & PREP =============================================================
@st.cache_data
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    def clean_area(x: str) -> str:
        s = str(x)
        if "/" in s:
            s = s.rsplit("/", 1)[-1]
        s = s.replace("-", " ").replace("_", " ").strip().title()
        if "Governorate" not in s and "District" not in s:
            s = f"{s} Governorate"
        return s

    df["Governorate"] = df["refArea"].apply(clean_area)

    for col in COMMERCIAL_SIZE_COLS + OTHER_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Keeping NaN as NaN to reflect “no data”
    for col in EXISTENCE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

df = load_data(CSV_PATH)

st.title("Lebanon Trade 2023")

# === SIDEBAR ================================================================
with st.sidebar:
    st.header("Filters")
    govs = sorted(df["Governorate"].unique().tolist())
    sel_govs = st.multiselect("Governorates", govs, default=govs)

    top_n_gov = st.slider("Top N governorates (by total institutions)", 5, 25, 10, step=1)

    st.markdown("---")
    show_pct_comm = st.toggle("Show % within governorate (100% stacked)", value=True)
    split_commercial = st.checkbox("Split Commercial into Small / Medium / Large", value=True)


# === FILTER & AGG (for V1 & V2) =============================================
dff = df[df["Governorate"].isin(sel_govs)].copy()

agg = dff.groupby("Governorate", as_index=False)[COMMERCIAL_SIZE_COLS + OTHER_COLS].sum()
agg["Commercial (total)"] = agg[COMMERCIAL_SIZE_COLS].sum(axis=1)
agg["All total"] = (
    agg["Commercial (total)"]
    + agg["Total number of service institutions"]
    + agg["Total number of non banking financial institutions"]
)
agg = agg.sort_values("All total", ascending=False).head(top_n_gov)

dff = dff[dff["Governorate"].isin(agg["Governorate"].tolist())].copy()


# === VISUAL 1 ================================================================
st.subheader("Lebanon Commercial, Service & Non-Banking Financial Institutions, by Governorate")

if split_commercial:
    cols_to_use = COMMERCIAL_SIZE_COLS + OTHER_COLS
    long_v1 = agg.melt(id_vars="Governorate", value_vars=cols_to_use, var_name="Raw", value_name="Value")
    long_v1["Series"] = long_v1["Raw"].map({**SIZE_MAP, **OTHER_MAP})
    series_order = ["Commercial — Small", "Commercial — Medium", "Commercial — Large",
                    "Service institutions", "Non-banking financial institutions"]
else:
    tmp = agg[["Governorate", "Commercial (total)"] + OTHER_COLS].copy()
    tmp = tmp.rename(columns={"Commercial (total)": "Commercial"})
    long_v1 = tmp.melt(id_vars="Governorate", value_vars=["Commercial"] + OTHER_COLS,
                       var_name="Series", value_name="Value")
    long_v1["Series"] = long_v1["Series"].replace({
        "Commercial": "Commercial (total)",
        "Total number of service institutions": "Service institutions",
        "Total number of non banking financial institutions": "Non-banking financial institutions",
    })
    series_order = ["Commercial (total)", "Service institutions", "Non-banking financial institutions"]

if show_pct_comm:
    long_v1["RowSum"] = long_v1.groupby("Governorate")["Value"].transform(lambda s: max(s.sum(), 1))
    long_v1["Value"] = (long_v1["Value"] / long_v1["RowSum"]) * 100
    y_title = "Percent of institutions (%)"
else:
    y_title = "Number of institutions"

fig_v1 = px.bar(
    long_v1, x="Governorate", y="Value", color="Series",
    barmode="stack",
    category_orders={"Series": series_order},
    color_discrete_map=COLOR_MAP_V1,
    hover_data={"Governorate": True, "Series": True, "Value": ":,.2f"},
)
fig_v1.update_layout(xaxis_title="", yaxis_title=y_title, legend_title="", margin=dict(l=10, r=10, t=10, b=10), height=460)
st.plotly_chart(fig_v1, use_container_width=True)


# === VISUAL 2 ================================================================
st.subheader("Institution Composition within a Governorate")
if agg.empty:
    st.warning("No data for current filters.")
else:
    focus_gov = st.selectbox("Choose a governorate to inspect", agg["Governorate"].tolist())
    row = agg[agg["Governorate"] == focus_gov].iloc[0]
    values_pie = {
        "Commercial — Small": row[COMMERCIAL_SIZE_COLS[0]],
        "Commercial — Medium": row[COMMERCIAL_SIZE_COLS[1]],
        "Commercial — Large": row[COMMERCIAL_SIZE_COLS[2]],
        "Service institutions": row["Total number of service institutions"],
        "Non-banking financial institutions": row["Total number of non banking financial institutions"],
    }
    pie_df = pd.DataFrame({"Category": list(values_pie.keys()), "Value": list(values_pie.values())})
    fig_comp = px.pie(pie_df, names="Category", values="Value", hole=0.3,
                      color="Category", color_discrete_map=COLOR_MAP_V1)
    fig_comp.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=420)
    st.plotly_chart(fig_comp, use_container_width=True)


# === VISUAL 3: ACTIVITY EXISTENCE (stacked, 1 column per governorate) ========
st.subheader("Distribution of Activities Existence Across Governorates (by Number of Towns)")

# Work on a copy with only the needed cols
exist = dff[["Governorate", "Town"] + EXISTENCE_COLS].copy()

# Keep NaN as NaN; convert to numeric for safety
for col in EXISTENCE_COLS:
    exist[col] = pd.to_numeric(exist[col], errors="coerce")

# Long form to compute counts robustly
exist_long = exist.melt(
    id_vars=["Governorate", "Town"],
    value_vars=EXISTENCE_COLS,
    var_name="ActivityRaw",
    value_name="Val",
)

# Numerator: towns with activity present (Val == 1)
exist_long["IsOne"] = (exist_long["Val"] == 1).astype(int)
abs_counts = (
    exist_long.groupby(["Governorate", "ActivityRaw"])["IsOne"]
    .sum()
    .reset_index(name="NumTowns")
)

# Denominator: towns that actually have data for that activity (non-null)
den_counts = (
    exist_long.groupby(["Governorate", "ActivityRaw"])["Val"]
    .count()  # counts non-null
    .reset_index(name="Denom")
)

# Merge numerator & denominator
exist_counts = abs_counts.merge(den_counts, on=["Governorate", "ActivityRaw"], how="left")

# Map clean labels
exist_counts["Activity"] = exist_counts["ActivityRaw"].map(EXISTENCE_LABELS)

# Top-N by “# towns with data” (largest Denom across activities)
gov_rank = (
    exist_counts.groupby("Governorate")["Denom"]
    .max()
    .sort_values(ascending=False)
    .index.tolist()
)
exist_counts = exist_counts[exist_counts["Governorate"].isin(gov_rank)]

# Percent or absolute
exist_counts["Value"] = exist_counts["NumTowns"]
y_title_exist = "# towns with activity"

# --- Colors (your request): pink, red, dark blue, clear blue, medium blue ---
activity_order = ["Commerce", "Service institutions", "Self-employment", "Public sector", "Banking"]
exist_color_map = {
    "Commerce":              "#f7a6b9",  # pink
    "Service institutions":  "#e63946",  # red
    "Self-employment":       "#0b3d91",  # dark blue
    "Public sector":         "#74b9ff",  # clear/light blue
    "Banking":               "#2e86de",  # medium blue
}

# Stacked columns (one column per governorate)
fig_exist = px.bar(
    exist_counts,
    x="Governorate",
    y="Value",
    color="Activity",
    barmode="stack",
    category_orders={"Activity": activity_order},
    color_discrete_map=exist_color_map,
    hover_data={
        "Governorate": True,
        "Activity": True,
        "Value": ":,.2f",
        "NumTowns": True,
        "Denom": True,
    },
)
fig_exist.update_layout(
    xaxis_title="",
    yaxis_title=y_title_exist,
    legend_title="",
    margin=dict(l=10, r=10, t=10, b=10),
    height=460,
)
st.plotly_chart(fig_exist, use_container_width=True)



# === DRILL DOWN (no change to the chart above) ===============================
st.markdown("####  Name of towns inside a governorate")

# Make sure the long table has clean Activity labels to filter on
_exist_long = exist_long.copy()
_exist_long["Activity"] = _exist_long["ActivityRaw"].map(EXISTENCE_LABELS)

# Order governorates as they appear in your aggregated table
gov_options = exist_counts["Governorate"].drop_duplicates().tolist()
act_options = ["Commerce", "Service institutions", "Self-employment", "Public sector", "Banking"]

c1, c2 = st.columns([1.2, 1])
with c1:
    dd_gov = st.selectbox("Governorate", gov_options, index=0)
with c2:
    dd_act = st.selectbox("Activity", act_options, index=0)

# Build towns list for the chosen (gov, activity), value == 1
towns_with_act = (
    _exist_long[
        (_exist_long["Governorate"] == dd_gov) &
        (_exist_long["Activity"] == dd_act) &
        (_exist_long["IsOne"] == 1)
    ]["Town"]
    .dropna()
    .drop_duplicates()
    .sort_values()
    .tolist()
)

st.markdown(f"**Towns with _{dd_act}_ in _{dd_gov}_** — {len(towns_with_act)} town(s)")
if towns_with_act:
    # neat multi-column list (all towns, no Top-N)
    cols = st.columns(4)
    for i, t in enumerate(towns_with_act):
        with cols[i % 4]:
            st.markdown(f"- {t}")
else:
    st.info("No towns found with this activity == 1 for the selected governorate.")
