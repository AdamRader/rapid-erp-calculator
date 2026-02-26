"""Rapid ERP Budget Calculator
Interactive deal-sizing tool for AI Rapid Deployment engagements.
"""

import streamlit as st
import pandas as pd

# --- Page Config ---
st.set_page_config(
    page_title="Rapid ERP Budget Calculator",
    page_icon=":bar_chart:",
    layout="wide",
)

# --- Constants ---

ROLES = ["Architect", "Functional", "AI Enabler", "Offshore"]

DEFAULT_RATES = {
    "Architect": 285,
    "Functional": 200,
    "AI Enabler": 150,
    "Offshore": 75,
}

PHASES = ["Phase 0", "Phase 1", "Phase 2", "Phase 3", "Phase 4"]
PHASE_LABELS = {
    "Phase 0": "Mobilize (Wk 1-2)",
    "Phase 1": "Workshops (Wk 2-6)",
    "Phase 2": "Build (Wk 5-12)",
    "Phase 3": "Enablement (Wk 10-16)",
    "Phase 4": "Cutover (Wk 15-20)",
}

# Base staffing hours by role by phase (standard engagement: 170 hrs)
BASE_PHASE_HOURS = {
    "Architect":  [8,  12, 6,  2,  2],
    "Functional": [4,  20, 24, 20, 12],
    "AI Enabler": [6,  6,  4,  2,  2],
    "Offshore":   [0,  0,  24, 12, 4],
}

# Vertical definitions: base price + hour adjustments per role
VERTICALS = {
    "Professional Services": {"base": 25_000, "adj": [-10, -20, -5, -15]},
    "Wholesale Distribution": {"base": 30_000, "adj": [0, 0, 0, 0]},
    "SaaS / Software":        {"base": 35_000, "adj": [5, 10, 5, 5]},
    "Light Manufacturing":    {"base": 35_000, "adj": [3, 5, 2, 5]},
    "E-commerce / DTC":       {"base": 35_000, "adj": [2, 5, 2, 5]},
    "Nonprofit":              {"base": 25_000, "adj": [-10, -20, -5, -15]},
}

SCENARIOS = {
    "A": {
        "name": "QB Desktop → NetSuite (Logo Capture)",
        "profile": "$12M distributor, 15 users, 1 entity, QB Desktop, Shopify, minimal customization",
        "fee": "$25-28K",
        "margin": "15-22%",
        "strategy": "Logo capture, relationship-building, follow-on opportunity",
        "hours": [20, 60, 15, 25],
    },
    "B": {
        "name": "Dynamics GP → NetSuite (Core Offering)",
        "profile": "$30M pro services, 35 users, 1 entity, GP migration, Salesforce + Expensify",
        "fee": "$38-42K",
        "margin": "28-36%",
        "strategy": "Core engagement type. Leverage GP migration playbook.",
        "hours": [30, 80, 20, 35],
    },
    "C": {
        "name": "SaaS → NetSuite (Premium)",
        "profile": "$30M ARR SaaS, 25 users, 2 entities, QBO, Salesforce + Stripe, rev rec",
        "fee": "$45-50K",
        "margin": "32-40%",
        "strategy": "Premium positioning. Rev rec expertise justifies upper range.",
        "hours": [35, 90, 25, 45],
    },
    "D": {
        "name": "Distribution + E-commerce (Integration-Heavy)",
        "profile": "$20M distributor, 30 users, 1 entity, Sage 100, Shopify + ShipStation + Avalara",
        "fee": "$42-48K",
        "margin": "28-38%",
        "strategy": "Pre-built connectors keep hours down. Integration expertise is differentiator.",
        "hours": [30, 85, 20, 45],
    },
}


# --- Calculation Engine ---

def build_estimate(vertical, integrations, migration, customization, entities,
                   extra_workshops, extra_integrations, extra_hypercare, adv_rev_rec,
                   ai_rate):
    """Run all calculations and return a results dict."""

    # --- Price ---
    base = VERTICALS[vertical]["base"]
    adj_lo, adj_hi = 0, 0

    if integrations == 4:
        adj_lo += 3_000; adj_hi += 5_000
    elif integrations >= 5:
        adj_lo += 5_000; adj_hi += 8_000

    if migration == "2 sources, 3+ years history":
        adj_lo += 2_000; adj_hi += 3_000
    elif migration == "3+ source systems":
        adj_lo += 4_000; adj_hi += 6_000

    if customization == "Moderate (11-15 points)":
        adj_lo += 2_500; adj_hi += 7_500

    if entities == "2 subsidiaries":
        adj_lo += 3_000; adj_hi += 3_000
    elif entities == "3 subsidiaries":
        adj_lo += 5_000; adj_hi += 8_000

    addon_cost = (extra_workshops * 2_500
                  + extra_integrations * 4_000
                  + extra_hypercare * 2_500
                  + (6_500 if adv_rev_rec else 0))

    price_lo = base + adj_lo + addon_cost
    price_hi = base + adj_hi + addon_cost

    # --- Hours ---
    vert_adj = VERTICALS[vertical]["adj"]
    hours = []
    for i, role in enumerate(ROLES):
        base_hrs = sum(BASE_PHASE_HOURS[role])
        h = base_hrs + vert_adj[i]

        # Integration complexity (beyond 3)
        if integrations > 3 and role in ("Functional", "Offshore"):
            h += (integrations - 3) * 5

        # Migration complexity
        if migration == "2 sources, 3+ years history" and role in ("Functional", "Offshore"):
            h += 5
        elif migration == "3+ source systems" and role in ("Functional", "Offshore"):
            h += 10

        # Customization complexity
        if customization == "Moderate (11-15 points)" and role in ("Functional", "Offshore"):
            h += 5

        # Entity complexity
        if entities == "2 subsidiaries" and role in ("Functional", "Offshore"):
            h += 5
        elif entities == "3 subsidiaries" and role in ("Functional", "Offshore"):
            h += 10

        hours.append(max(h, 0))

    # Add-on hours
    if extra_workshops > 0:
        hours[0] += extra_workshops * 3   # Architect
        hours[1] += extra_workshops * 5   # Functional
        hours[2] += extra_workshops * 2   # AI Enabler
    if extra_integrations > 0:
        hours[1] += extra_integrations * 5
        hours[3] += extra_integrations * 8
    if extra_hypercare > 0:
        hours[1] += extra_hypercare * 8
    if adv_rev_rec:
        hours[0] += 5
        hours[1] += 15
        hours[3] += 5

    # --- Phase breakdown (proportional scaling from base) ---
    phase_table = []
    for i, role in enumerate(ROLES):
        base_total = sum(BASE_PHASE_HOURS[role])
        row = []
        for j in range(5):
            if base_total > 0:
                row.append(max(round(hours[i] * BASE_PHASE_HOURS[role][j] / base_total), 0))
            else:
                row.append(0)
        # Adjust rounding so row sums to hours[i]
        diff = hours[i] - sum(row)
        if diff != 0:
            # Add diff to the largest phase
            max_idx = row.index(max(row))
            row[max_idx] += diff
        phase_table.append(row)

    # --- Costs ---
    rates = {r: DEFAULT_RATES[r] for r in ROLES}
    rates["AI Enabler"] = ai_rate
    labor_cost = sum(hours[i] * rates[ROLES[i]] for i in range(4))
    total_hours = sum(hours)

    # --- Margins ---
    margin_lo = price_lo - labor_cost
    margin_hi = price_hi - labor_cost
    margin_pct_lo = margin_lo / price_lo * 100 if price_lo else 0
    margin_pct_hi = margin_hi / price_hi * 100 if price_hi else 0

    # --- Scenario match ---
    best_key, best_diff = "B", float("inf")
    for key, sc in SCENARIOS.items():
        diff = abs(sum(sc["hours"]) - total_hours)
        if diff < best_diff:
            best_diff = diff
            best_key = key

    # --- Warnings ---
    warnings = []
    if integrations >= 5:
        warnings.append("5+ integrations exceeds base scope — requires custom scoping")
    if entities == "4+ subsidiaries":
        warnings.append("4+ subsidiaries exceeds methodology scope")
    if customization == "Heavy (15+ points)":
        warnings.append("Heavy customization exceeds rapid deployment scope — consider traditional engagement")
    if migration == "3+ source systems":
        warnings.append("3+ source systems adds significant migration complexity")

    return {
        "price_lo": price_lo,
        "price_hi": price_hi,
        "addon_cost": addon_cost,
        "hours": hours,
        "phase_table": phase_table,
        "total_hours": total_hours,
        "rates": rates,
        "labor_cost": labor_cost,
        "margin_lo": margin_lo,
        "margin_hi": margin_hi,
        "margin_pct_lo": margin_pct_lo,
        "margin_pct_hi": margin_pct_hi,
        "scenario_key": best_key,
        "warnings": warnings,
    }


# --- UI ---

st.title("Rapid ERP Budget Calculator")
st.caption("AI Rapid Deployment — Deal Sizing & Margin Analysis")

# Sidebar inputs
with st.sidebar:
    st.header("Deal Parameters")

    vertical = st.selectbox("1. Vertical", list(VERTICALS.keys()), index=1)

    integrations = st.slider("2. Integration Count", 0, 6, 2)

    migration = st.selectbox("3. Data Migration Scope", [
        "1 source, <2 years history",
        "2 sources, 2 years history",
        "2 sources, 3+ years history",
        "3+ source systems",
    ], index=1)

    customization = st.selectbox("4. Customization Level", [
        "Leading practices (0 extra points)",
        "Standard (5-10 points)",
        "Moderate (11-15 points)",
        "Heavy (15+ points)",
    ], index=1)

    entities = st.selectbox("5. Entity Structure", [
        "Single entity",
        "2 subsidiaries",
        "3 subsidiaries",
        "4+ subsidiaries",
    ])

    st.divider()
    st.subheader("Add-Ons")
    extra_workshops = st.number_input("Additional workshops", 0, 5, 0)
    extra_integrations = st.number_input("Additional integration points", 0, 5, 0)
    extra_hypercare = st.number_input("Extended hypercare (weeks)", 0, 8, 0)
    adv_rev_rec = st.checkbox("Advanced revenue recognition")

    st.divider()
    st.subheader("Rate Card")
    ai_rate = st.number_input(
        "AI Enabler rate ($/hr)", 0, 500, 150,
        help="Default $150/hr — adjust when rate is finalized",
    )

# Run calculations
r = build_estimate(
    vertical, integrations, migration, customization, entities,
    extra_workshops, extra_integrations, extra_hypercare, adv_rev_rec,
    ai_rate,
)

# Warnings
for w in r["warnings"]:
    st.error(f"**Out of Scope:** {w}")

# Key metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Fee (Low)", f"${r['price_lo']:,.0f}")
c2.metric("Fee (High)", f"${r['price_hi']:,.0f}")
c3.metric("Total Hours", f"{r['total_hours']}")
c4.metric("Labor Cost", f"${r['labor_cost']:,.0f}")

st.divider()

# Detail tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "Staffing Model", "Margin Analysis", "Scenario Match", "Add-On Reference",
])

with tab1:
    st.subheader("Hours by Role by Phase")

    rows = []
    for i, role in enumerate(ROLES):
        row = {"Role": f"{role} (${r['rates'][role]}/hr)"}
        for j, phase in enumerate(PHASES):
            row[PHASE_LABELS[phase]] = r["phase_table"][i][j]
        row["Total"] = r["hours"][i]
        row["Cost"] = f"${r['hours'][i] * r['rates'][role]:,.0f}"
        rows.append(row)

    # Totals
    totals_row = {"Role": "Total"}
    for j, phase in enumerate(PHASES):
        totals_row[PHASE_LABELS[phase]] = sum(r["phase_table"][i][j] for i in range(4))
    totals_row["Total"] = r["total_hours"]
    totals_row["Cost"] = f"${r['labor_cost']:,.0f}"
    rows.append(totals_row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.caption(
        "Hours assume pre-built SDF bundles (saves 40-60 hrs) and intake-first model "
        "(saves 30-40% discovery time). Phase breakdown is proportionally scaled."
    )

with tab2:
    st.subheader("Margin Analysis")

    mc1, mc2 = st.columns(2)

    with mc1:
        st.metric("Labor Cost", f"${r['labor_cost']:,.0f}")
        st.metric("Margin at Low Fee", f"${r['margin_lo']:,.0f}",
                  f"{r['margin_pct_lo']:.1f}%")
        st.metric("Margin at High Fee", f"${r['margin_hi']:,.0f}",
                  f"{r['margin_pct_hi']:.1f}%")

    with mc2:
        st.caption("Margin Sensitivity")
        sens = []
        for fee in [25_000, 30_000, 35_000, 40_000, 45_000, 50_000]:
            m = fee - r["labor_cost"]
            pct = m / fee * 100 if fee else 0
            if pct < 20:
                v = "Logo capture"
            elif pct < 28:
                v = "Minimum sustainable"
            elif pct < 33:
                v = "Core"
            elif pct < 38:
                v = "Sweet spot"
            else:
                v = "Premium"
            sens.append({"Fee": f"${fee:,.0f}", "Margin $": f"${m:,.0f}",
                         "Margin %": f"{pct:.0f}%", "Viability": v})
        st.dataframe(pd.DataFrame(sens), use_container_width=True, hide_index=True)

    st.caption("AI Enabler cost included at configured rate. Margins improve as "
               "bundles and pre-population reduce hours over time.")

with tab3:
    sc = SCENARIOS[r["scenario_key"]]
    st.subheader(f"Closest Match: Scenario {r['scenario_key']}")
    st.markdown(f"**{sc['name']}**")
    st.caption(sc["profile"])

    sc1, sc2 = st.columns(2)
    sc1.metric("Reference Fee", sc["fee"])
    sc2.metric("Reference Margin", sc["margin"])

    st.info(f"**Strategy:** {sc['strategy']}")

    ref_rows = []
    for i, role in enumerate(ROLES):
        ref_rows.append({
            "Role": role,
            "Ref Hours": sc["hours"][i],
            "Your Hours": r["hours"][i],
            "Delta": r["hours"][i] - sc["hours"][i],
        })
    ref_rows.append({
        "Role": "Total",
        "Ref Hours": sum(sc["hours"]),
        "Your Hours": r["total_hours"],
        "Delta": r["total_hours"] - sum(sc["hours"]),
    })
    st.dataframe(pd.DataFrame(ref_rows), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Add-On Pricing Reference")
    st.dataframe(pd.DataFrame([
        {"Add-On": "Additional discovery workshop", "Price": "$2,000-$3,000",
         "Included": "1.5-2 hrs Architect + Functional, AI processing"},
        {"Add-On": "Additional integration point", "Price": "$3,000-$5,000",
         "Included": "Scoping, configuration, testing"},
        {"Add-On": "Additional customization points", "Price": "$1,500-$2,500/point",
         "Included": "Development, testing, deployment per point"},
        {"Add-On": "Additional data migration source", "Price": "$4,000-$6,000",
         "Included": "Mapping, cleansing, loading, validation"},
        {"Add-On": "Extended hypercare", "Price": "$2,500/week",
         "Included": "Functional consultant stabilization time"},
        {"Add-On": "Additional subsidiary", "Price": "$3,000-$5,000",
         "Included": "Configuration, testing, elimination setup"},
        {"Add-On": "Advanced rev rec setup", "Price": "$5,000-$8,000",
         "Included": "ASC 606 config beyond basic"},
    ]), use_container_width=True, hide_index=True)

    if r["addon_cost"] > 0:
        st.success(f"**Selected add-ons total:** ${r['addon_cost']:,.0f}")

# Footer
st.divider()
st.caption(
    "Internal tool — Centric Consulting | NetSuite & Oracle Practice. "
    "Rates and assumptions per AI Rapid Deployment methodology v1.0."
)
