import streamlit as st
import pandas as pd
from datetime import date
import os
from users import USERS

st.set_page_config(page_title="Cash Tracker", layout="centered")

DENOMS = [100,200,500,1000,2000,5000,10000,20000,50000,100000]
DENOMS_STRING = {100: "100", 200: "200", 500: "500", 1000: "1,000", 2000: "2,000", 5000: "5,000", 10000: "10,000", 20000: "20,000", 50000: "50,000", 100000: "100,000"}
# ---------- LOGIN ----------
if "user" not in st.session_state:
    st.title("Cash Tracker Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = USERS.get(username)
        if user and user["password"] == password:
            st.session_state.user = {
                "username": username,
                "role": user["role"]
            }
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# ---------- LOGOUT ----------
st.sidebar.write(f"Logged in as **{st.session_state.user['username']}**")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

role = st.session_state.user["role"]
username = st.session_state.user["username"]


# ---------- FUNCTION TO LOAD EXISTING ENTRY FOR CASHIER ----------
def load_existing_entry(username, entry_date):
    filename = f"data/cash_{entry_date.strftime('%Y-%m')}.csv"
    if not os.path.exists(filename):
        return None

    df = pd.read_csv(filename)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    match = df[
        (df["cashier"] == username) &
        (df["date"] == entry_date)
    ]

    if match.empty:
        return None

    return match.iloc[0]

# ---------- CASHIER PAGE ----------
if role == "cashier":
    st.header("Daily Cash Entry")

    entry_date = st.date_input("Date", date.today())

    existing = load_existing_entry(username, entry_date)

    counts = {}
    total_cash = 0

    st.subheader("Cash Count")
    for d, s in DENOMS_STRING.items():
        default = int(existing[str(d)]) if existing is not None else 0

        count = st.number_input(f"Rp. {s},-",
                                min_value=0,
                                step=1,
                                value=default,
                                key=f"{entry_date}_{d}")
        counts[d] = count
        total_cash += d * count

    st.subheader("Other Entries")
    parking = st.number_input("Parking",
                              step=1000,
                              value=int(existing["parking"]) if existing is not None else 0,
                              key=f"{entry_date}_parking")
    saving = st.number_input("Saving",
                             step=1000,
                             value=int(existing["saving"]) if existing is not None else 0,
                             key=f"{entry_date}_saving")
    debt_credit = st.number_input("Debt / Credit",
                                  step=1000,
                                  value=int(existing["debt_credit"]) if existing is not None else 0,
                                  key=f"{entry_date}_debt_credit")
    st.metric("Total Cash", f"{total_cash:,}")

    if st.button("Save"):
        os.makedirs("data", exist_ok=True)
        filename = f"data/cash_{entry_date.strftime('%Y-%m')}.csv"

        row = {
            "date": entry_date,
            "cashier": username,
            **{str(d): counts[d] for d in DENOMS},
            "parking": parking,
            "saving": saving,
            "debt_credit": debt_credit
        }

        if os.path.exists(filename):
            df = pd.read_csv(filename)
            df["date"] = pd.to_datetime(df["date"]).dt.date

            df = df[
                ~((df["cashier"] == username) & (df["date"] == entry_date))
            ]

            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            df = pd.DataFrame([row])

        df.to_csv(filename, index=False)

        st.success("Saved successfully")

# ---------- MANAGER PAGE ----------
if role == "manager":
    st.header("Manager Dashboard")

    import glob

    files = glob.glob("data/cash_*.csv")
    if not files:
        st.info("No data yet")
        st.stop()

    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])

    start = st.date_input("From")
    end = st.date_input("To")

    filtered = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]

    if filtered.empty:
        st.warning("No records found for the selected date range")
        st.stop()

    # ---- AGGREGATE BY DATE ----
    summary = (
        filtered
        .groupby(filtered["date"].dt.date)[[str(d) for d in DENOMS]]
        .sum()
        .reset_index()
    )

    # Convert counts to Rupiah values
    for d in DENOMS:
        summary[f"Rp {DENOMS_STRING[d]}"] = summary[str(d)] * d
        summary.drop(columns=[str(d)], inplace=True)

    summary = summary.sort_values(by="date")

    st.subheader("Cash Breakdown (All Cashiers Combined)")

    st.dataframe(
        summary.style.format(
            {col: "{:,.0f}" for col in summary.columns if col != "date"}
        )
    )