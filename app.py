import streamlit as st
import pandas as pd
from datetime import date
from users import USERS
from db import init_db, get_connection

# ---------- INIT ----------
init_db()

st.set_page_config(page_title="Cash Tracker", layout="centered")

DENOMS = [100,200,500,1000,2000,5000,10000,20000,50000,100000]
DENOMS_STRING = {
    100: "100", 200: "200", 500: "500", 1000: "1,000",
    2000: "2,000", 5000: "5,000", 10000: "10,000",
    20000: "20,000", 50000: "50,000", 100000: "100,000"
}

# ---------- DB FUNCTIONS ----------
def save_entry(entry_date, cashier, denom, count, parking, saving, debt_credit):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO cash_entries
        (date, cashier, denomination, count, parking, saving, debt_credit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        entry_date.isoformat(),
        cashier,
        denom,
        count,
        parking,
        saving,
        debt_credit
    ))

    conn.commit()
    conn.close()


def load_entries():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM cash_entries", conn)
    conn.close()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    return df


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

# ---------- SIDEBAR ----------
st.sidebar.write(f"Logged in as **{st.session_state.user['username']}**")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

role = st.session_state.user["role"]
username = st.session_state.user["username"]

df_all = load_entries()

# =========================
# ===== CASHIER PAGE ======
# =========================
if role == "cashier":
    st.header("Daily Cash Entry")

    entry_date = st.date_input("Date", date.today())

    existing = df_all[
        (df_all["cashier"] == username) &
        (df_all["date"] == entry_date)
    ]

    counts = {}
    total_cash = 0

    st.subheader("Cash Count")
    for d in DENOMS:
        row = existing[existing["denomination"] == d]
        default = int(row["count"].iloc[0]) if not row.empty else 0

        count = st.number_input(
            f"Rp. {DENOMS_STRING[d]},-",
            min_value=0,
            step=1,
            value=default,
            key=f"{entry_date}_{d}"
        )

        counts[d] = count
        total_cash += d * count

    st.subheader("Other Entries")
    parking = int(existing["parking"].iloc[0]) if not existing.empty else 0
    saving = int(existing["saving"].iloc[0]) if not existing.empty else 0
    debt_credit = int(existing["debt_credit"].iloc[0]) if not existing.empty else 0

    parking = st.number_input("Parking", step=1000, value=parking)
    saving = st.number_input("Saving", step=1000, value=saving)
    debt_credit = st.number_input("Debt / Credit", step=1000, value=debt_credit)

    st.metric("Total Cash", f"{total_cash:,}")

    if st.button("Save"):
        for d in DENOMS:
            save_entry(
                entry_date,
                username,
                d,
                counts[d],
                parking,
                saving,
                debt_credit
            )

        st.success("Saved successfully")

# =========================
# ===== MANAGER PAGE ======
# =========================
if role == "manager":
    st.header("Manager Dashboard")

    if df_all.empty:
        st.info("No data yet")
        st.stop()

    start = st.date_input("From")
    end = st.date_input("To")

    filtered = df_all[
        (df_all["date"] >= start) &
        (df_all["date"] <= end)
    ]

    if filtered.empty:
        st.warning("No records found")
        st.stop()

    summary = (
        filtered
        .groupby(["date", "denomination"])["count"]
        .sum()
        .reset_index()
        .pivot(index="date", columns="denomination", values="count")
        .fillna(0)
        .reset_index()
    )

    for d in DENOMS:
        summary[f"Rp {DENOMS_STRING[d]}"] = summary.get(d, 0) * d
        if d in summary:
            summary.drop(columns=[d], inplace=True)

    summary = summary.sort_values("date")

    st.subheader("Cash Breakdown (All Cashiers Combined)")
    st.dataframe(
        summary.style.format(
            {col: "{:,.0f}" for col in summary.columns if col != "date"}
        )
    )
