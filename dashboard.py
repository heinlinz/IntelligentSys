import os

import numpy as np
import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="Season Ticket Renewal Dashboard",
    page_icon="🎟️",
    layout="wide",
)

API_URL = os.environ.get("RENEWAL_API_URL", "http://localhost:5000")

# Definitions and effects come from Variable_Definitions.docx.
INPUT_VARIABLES = [
    {
        "Symbol": "X1",
        "Variable": "Seat quality",
        "Meaning (0–1)": "How good the holder's seat is (comfort, view, location). 0 = poor, 1 = excellent.",
        "Effect in the model": "Raises satisfaction (h1)",
        "Default": 0.7,
    },
    {
        "Symbol": "X2",
        "Variable": "Team performance",
        "Meaning (0–1)": "How well the team is doing on the field. 0 = poor, 1 = excellent.",
        "Effect in the model": "Raises satisfaction (h1), with a smaller weight because research shows a weaker effect",
        "Default": 0.6,
    },
    {
        "Symbol": "X3",
        "Variable": "Expensive price",
        "Meaning (0–1)": "How heavy the renewal price feels. 0 = cheap, 1 = very expensive. Higher is worse for the customer.",
        "Effect in the model": "Lowers satisfaction (h1) and lowers switching cost (h2)",
        "Default": 0.5,
    },
    {
        "Symbol": "X4",
        "Variable": "Package benefit",
        "Meaning (0–1)": "Perks that come with the ticket (discounts, exclusive benefits, priority). 0 = none, 1 = many.",
        "Effect in the model": "Raises switching cost (h2)",
        "Default": 0.6,
    },
    {
        "Symbol": "X5",
        "Variable": "Stadium access",
        "Meaning (0–1)": "How easy it is to get to the stadium. 0 = hard, 1 = easy.",
        "Effect in the model": "Raises switching cost (h2)",
        "Default": 0.5,
    },
]

HIDDEN_VARIABLES = [
    {
        "Symbol": "h1",
        "Variable": "Satisfaction",
        "Meaning (0–1)": "How happy the holder is with the season ticket experience. Built from seat quality and team performance, then reduced by high price.",
        "Effect in the model": "Lowers peer pressure (h3) and turnover (h4)",
    },
    {
        "Symbol": "h2",
        "Variable": "Switching cost",
        "Meaning (0–1)": "How locked-in the holder feels after buying. It comes from package benefit and access. If the renewal price is raised, the lock-in becomes weaker, so price is a negative factor here.",
        "Effect in the model": "Lowers peer pressure (h3) and turnover (h4)",
    },
    {
        "Symbol": "h3",
        "Variable": "Peer pressure",
        "Meaning (0–1)": "Pressure from other people to leave. When satisfaction and switching cost are both high, this is low because the holder no longer cares what others say.",
        "Effect in the model": "Lowers renewal (O)",
    },
    {
        "Symbol": "h4",
        "Variable": "Turnover",
        "Meaning (0–1)": "The tendency to leave (churn). It follows the same logic as peer pressure: low when satisfaction and switching cost are both high.",
        "Effect in the model": "Lowers renewal (O)",
    },
]

OUTPUT_VARIABLES = [
    {
        "Symbol": "O",
        "Variable": "Renewal rate",
        "Meaning (0–1)": "How likely the holder is to renew, from 0 (leaves) to 1 (renews). It depends on two negative factors, so it goes up when peer pressure and turnover go down.",
        "Effect in the model": "Final output",
    },
]

LAYER_COLORS = {
    "Input": ("#e8f1ff", "#2f6fdb"),
    "Hidden": ("#fff4e5", "#d97706"),
    "Output": ("#e9f8ef", "#18864b"),
}


def variable_frame(variables):
    return pd.DataFrame(variables)[
        ["Symbol", "Variable", "Meaning (0–1)", "Effect in the model"]
    ]


def node_card(symbol, name, layer):
    background, border = LAYER_COLORS[layer]
    st.markdown(
        f"""
        <div style="background:{background}; border:1px solid {border};
                    border-radius:12px; padding:0.65rem 0.5rem;
                    text-align:center; min-height:96px;">
            <div style="font-size:0.7rem; letter-spacing:0.08em;
                        text-transform:uppercase; color:#6b7280;">{layer}</div>
            <div style="font-size:1.25rem; font-weight:700; color:#111827;
                        line-height:1.2;">{symbol}</div>
            <div style="font-size:0.85rem; color:#374151;">{name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def arrow():
    st.markdown(
        "<div style='text-align:center; font-size:1.5rem; color:#9ca3af;'>↓</div>",
        unsafe_allow_html=True,
    )


def simulate(x1, x2, x3, x4, x5, alpha, alpha2, w3, w4, eta, dt, o0, steps):
    """Run the model exactly as described on the Numerical sheet."""
    h1 = (alpha * x2 + (1 - alpha) * x1) * (1 - x3)
    h2 = (alpha2 * x4 + (1 - alpha2) * x5) * (1 - x3)
    h3 = (1 - h1) * (1 - h2)
    h4 = (1 - h1) * (1 - h2)
    aggregated = w3 * (1 - h3) + w4 * (1 - h4)

    trajectory = np.zeros(steps + 1)
    trajectory[0] = o0
    for t in range(1, steps + 1):
        trajectory[t] = (
            trajectory[t - 1]
            + eta * (aggregated - trajectory[t - 1]) * dt
        )

    return {
        "h1": float(h1),
        "h2": float(h2),
        "h3": float(h3),
        "h4": float(h4),
        "aggregated": float(aggregated),
        "trajectory": trajectory,
        "final": float(trajectory[-1]),
    }


with st.sidebar:
    st.header("About this model")
    st.markdown(
        "This dashboard explains the **season ticket renewal model** "
        "from the Week 5 ABMS material."
    )
    st.markdown(
        "- **Inputs:** X1–X5\n"
        "- **Hidden nodes:** h1–h4\n"
        "- **Output:** O (renewal rate)"
    )
    st.warning(
        "All weights and input values are **assumptions**, not values taken "
        "from the research papers. Evidence supports direction and relative "
        "importance only."
    )
    st.caption(
        "Sources: Renewal_Model_Conceptual_Numerical.xlsx and "
        "Variable_Definitions.docx"
    )

st.title("🎟️ Season Ticket Renewal Model")
st.caption(
    "ICT 338 Intelligent Systems · Week 5 · All variables use a 0–1 scale"
)

overview_tab, dictionary_tab, simulator_tab, saved_tab = st.tabs(
    ["Model overview", "Variable dictionary", "What-if simulator", "Saved scenarios"]
)


with overview_tab:
    st.subheader("How the model flows")
    st.write(
        "Inputs (X1–X5) feed two hidden nodes: satisfaction (h1) and switching "
        "cost (h2). Those two feed peer pressure (h3) and turnover (h4). The "
        "last two drive the output, the renewal rate (O). **Less peer pressure "
        "and less turnover mean more renewal.**"
    )

    input_columns = st.columns(5)
    for column, variable in zip(input_columns, INPUT_VARIABLES):
        with column:
            node_card(variable["Symbol"], variable["Variable"], "Input")

    arrow()

    first_hidden = st.columns([1, 1, 1])
    with first_hidden[0]:
        node_card("h1", "Satisfaction", "Hidden")
    with first_hidden[2]:
        node_card("h2", "Switching cost", "Hidden")

    arrow()

    second_hidden = st.columns([1, 1, 1, 1, 1])
    with second_hidden[1]:
        node_card("h3", "Peer pressure", "Hidden")
    with second_hidden[3]:
        node_card("h4", "Turnover", "Hidden")

    arrow()

    output_column = st.columns([2, 1, 2])
    with output_column[1]:
        node_card("O", "Renewal rate", "Output")

    st.divider()
    st.subheader("Equations")

    left_equations, right_equations = st.columns(2)
    with left_equations:
        st.latex(r"h_1 = (\alpha X_2 + (1-\alpha) X_1)(1-X_3)")
        st.latex(r"h_2 = (\alpha_2 X_4 + (1-\alpha_2) X_5)(1-X_3)")
        st.latex(r"h_3 = (1-h_1)(1-h_2)")
    with right_equations:
        st.latex(r"h_4 = (1-h_1)(1-h_2)")
        st.latex(r"\text{impact} = w_3(1-h_3) + w_4(1-h_4)")
        st.latex(
            r"O(t+1) = O(t) + \eta \,(\text{impact} - O(t))\,\Delta t"
        )

    st.info(
        "The (1 − value) parts flip a **negative factor**. For example, "
        "(1 − X3) means a high price lowers both satisfaction and switching "
        "cost. h3 and h4 currently use the same formula, so they always have "
        "equal values."
    )


with dictionary_tab:
    st.subheader("What each variable means")
    st.write(
        "All values are on a **0–1 scale**. The tables below use the "
        "definitions from Variable_Definitions.docx."
    )

    st.markdown("#### Input layer — X1 to X5")
    st.dataframe(
        variable_frame(INPUT_VARIABLES),
        hide_index=True,
        width="stretch",
    )

    st.markdown("#### Hidden layer — h1 to h4")
    st.dataframe(
        variable_frame(HIDDEN_VARIABLES),
        hide_index=True,
        width="stretch",
    )

    st.markdown("#### Output layer — O")
    st.dataframe(
        variable_frame(OUTPUT_VARIABLES),
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "α = weight of team performance in h1 · α₂ = weight of package "
        "benefit in h2 · w3/w4 = weights of peer pressure and turnover in the "
        "output · η = adaptation rate · Δt = time step."
    )


with simulator_tab:
    st.subheader("What-if simulator")
    st.write(
        "Move the inputs and watch how the hidden nodes and the renewal rate "
        "change. The defaults match the worked example on the Numerical sheet."
    )

    controls, results = st.columns([1, 1.4])

    with controls:
        st.markdown("##### Inputs (0–1)")
        x1 = st.slider(
            "X1 · Seat quality", 0.0, 1.0, 0.7, 0.01,
            help="0 = poor seat, 1 = excellent seat",
        )
        x2 = st.slider(
            "X2 · Team performance", 0.0, 1.0, 0.6, 0.01,
            help="0 = poor on-field performance, 1 = excellent",
        )
        x3 = st.slider(
            "X3 · Expensive price", 0.0, 1.0, 0.5, 0.01,
            help="0 = cheap, 1 = very expensive (higher is worse)",
        )
        x4 = st.slider(
            "X4 · Package benefit", 0.0, 1.0, 0.6, 0.01,
            help="0 = no perks, 1 = many perks",
        )
        x5 = st.slider(
            "X5 · Stadium access", 0.0, 1.0, 0.5, 0.01,
            help="0 = hard to reach, 1 = easy to reach",
        )

        with st.expander("Model parameters (assumptions)"):
            alpha = st.slider(
                "α · team performance weight in h1", 0.0, 1.0, 0.4, 0.05
            )
            alpha2 = st.slider(
                "α₂ · package benefit weight in h2", 0.0, 1.0, 0.6, 0.05
            )
            w3 = st.slider(
                "w3 · weight of (1 − peer pressure)", 0.0, 1.0, 0.4, 0.05
            )
            w4 = st.slider(
                "w4 · weight of (1 − turnover)", 0.0, 1.0, 0.6, 0.05
            )
            eta = st.slider(
                "η · adaptation rate", 0.0, 1.0, 0.5, 0.05
            )
            dt = st.slider("Δt · time step", 0.1, 2.0, 1.0, 0.1)
            o0 = st.slider(
                "O(0) · starting renewal rate", 0.0, 1.0, 0.5, 0.01
            )
            steps = st.slider("Time steps", 5, 100, 20, 1)

    outcome = simulate(
        x1, x2, x3, x4, x5,
        alpha, alpha2, w3, w4, eta, dt, o0, steps,
    )

    with results:
        st.markdown("##### Hidden nodes and output")
        metric_columns = st.columns(3)
        with metric_columns[0]:
            st.metric("h1 · Satisfaction", f"{outcome['h1']:.3f}")
        with metric_columns[1]:
            st.metric("h2 · Switching cost", f"{outcome['h2']:.3f}")
        with metric_columns[2]:
            st.metric("h3 · Peer pressure", f"{outcome['h3']:.3f}")

        metric_columns = st.columns(3)
        with metric_columns[0]:
            st.metric("h4 · Turnover", f"{outcome['h4']:.3f}")
        with metric_columns[1]:
            st.metric(
                "Aggregated impact",
                f"{outcome['aggregated']:.3f}",
                help="The target the renewal rate moves toward.",
            )
        with metric_columns[2]:
            st.metric(
                f"O({steps}) · Renewal rate",
                f"{outcome['final']:.3f}",
                delta=f"{outcome['final'] - o0:+.3f} vs O(0)",
            )

        trajectory_frame = pd.DataFrame(
            {
                "t": np.arange(steps + 1),
                "Renewal rate O(t)": outcome["trajectory"],
                "Aggregated impact (target)": np.full(
                    steps + 1, outcome["aggregated"]
                ),
            }
        )
        st.line_chart(
            trajectory_frame,
            x="t",
            y=["Renewal rate O(t)", "Aggregated impact (target)"],
            y_label="Rate (0–1)",
            height=320,
        )

        if outcome["aggregated"] > o0:
            st.success(
                "Aggregated impact is above O(0), so the renewal rate rises "
                "toward the target."
            )
        elif outcome["aggregated"] < o0:
            st.warning(
                "Aggregated impact is below O(0), so the renewal rate falls "
                "toward the target."
            )
        else:
            st.info(
                "Aggregated impact equals O(0), so the renewal rate stays "
                "unchanged."
            )

    with st.expander("Price sensitivity: what happens when X3 rises?"):
        price_levels = sorted(
            {
                round(min(1.0, x3 + bump), 2)
                for bump in (0.0, 0.2, 0.4)
            }
        )
        price_curves = {"t": np.arange(steps + 1)}
        for level in price_levels:
            price_outcome = simulate(
                x1, x2, level, x4, x5,
                alpha, alpha2, w3, w4, eta, dt, o0, steps,
            )
            price_curves[f"X3 = {level:.2f}"] = price_outcome["trajectory"]

        st.line_chart(
            pd.DataFrame(price_curves),
            x="t",
            y=[f"X3 = {level:.2f}" for level in price_levels],
            y_label="Renewal rate O(t)",
            height=300,
        )
        st.caption(
            "A higher price lowers both satisfaction and switching cost, so "
            "peer pressure and turnover rise and the renewal rate falls."
        )


with saved_tab:
    st.subheader("Saved scenarios")
    st.write(
        "These scenarios come from the `renewal_rates` collection in "
        "Firestore, read through the Flask API."
    )
    st.caption(
        "The simulator uses the Excel defaults (η = 0.5, Δt = 1, O(0) = 0.5). "
        "Saved scenarios were calculated by the API with its own defaults, so "
        "their renewal rates can differ from the simulator's."
    )

    api_url = st.text_input("API base URL", value=API_URL)

    if st.button("Load saved scenarios", type="primary"):
        try:
            response = requests.get(
                f"{api_url.rstrip('/')}/renewal_rates", timeout=5
            )
            response.raise_for_status()
            st.session_state["saved_scenarios"] = response.json()
            st.session_state["saved_error"] = None
        except requests.RequestException as exc:
            st.session_state["saved_scenarios"] = None
            st.session_state["saved_error"] = str(exc)

    saved_error = st.session_state.get("saved_error")
    saved_scenarios = st.session_state.get("saved_scenarios")

    if saved_error:
        st.error(f"Could not reach the API at {api_url}: {saved_error}")
        st.code("myenv/bin/python main.py", language="bash")
    elif saved_scenarios is None:
        st.info(
            "Click **Load saved scenarios** to fetch the data from Firestore. "
            "The Flask API must be running."
        )
    elif not saved_scenarios:
        st.info(
            "The Firestore collection is empty. Create a scenario with a POST "
            "to `/renewal_rates` first."
        )
    else:
        rows = []
        for scenario_id, payload in saved_scenarios.items():
            inputs = payload.get("inputs", {})
            intermediates = payload.get("intermediates", {})
            row = {"Scenario": scenario_id}
            for name in ["X1", "X2", "X3", "X4", "X5"]:
                row[name] = payload.get(name, inputs.get(name))
            for name in ["h1", "h2", "h3", "h4", "s"]:
                row[name] = intermediates.get(name)
            row["Renewal rate"] = payload.get("renewal_rate")
            rows.append(row)

        saved_frame = pd.DataFrame(rows)
        saved_frame["_order"] = (
            saved_frame["Scenario"].str.extract(r"(\d+)$").astype(float)
        )
        saved_frame = saved_frame.sort_values("_order").drop(columns="_order")

        st.dataframe(saved_frame, hide_index=True, width="stretch")

        st.markdown("##### Renewal rate by scenario")
        st.bar_chart(
            saved_frame.set_index("Scenario")[["Renewal rate"]],
            y_label="Renewal rate",
            height=300,
        )
