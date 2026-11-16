import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

sns.set_theme(style="whitegrid")
BIRU, ORANYE, ABU_MUDA, ABU = "#1f6fb2", "#e08a1e", "#9bb8d3", "#c8d3dd"
URUTAN_MUSIM = ["Spring", "Summer", "Fall", "Winter"]
URUTAN_CUACA = ["Cerah", "Berkabut/Mendung", "Hujan/Salju Ringan"]
URUTAN_SEGMEN = ["Dini Hari", "Rush Pagi", "Siang", "Rush Sore", "Malam"]
URUTAN_SUHU = ["Dingin (<=10C)", "Sejuk (10-20C)", "Hangat (20-30C)", "Panas (>30C)"]
URUTAN_DEMAND = ["Rendah", "Sedang", "Tinggi", "Sangat Tinggi"]
URUTAN_BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

st.set_page_config(page_title="Dashboard Bike Sharing", page_icon="🚲", layout="wide")


@st.cache_data
def load_data():
    base = os.path.dirname(os.path.abspath(__file__))
    hour = pd.read_csv(os.path.join(base, "main_data.csv"), parse_dates=["dteday"])
    day = pd.read_csv(os.path.join(base, "main_day_data.csv"), parse_dates=["dteday"])
    return hour, day


hour_df, day_df = load_data()

# ---------------- Sidebar ----------------
st.sidebar.title("🚲 Filter Data")
min_d, max_d = day_df["dteday"].min().date(), day_df["dteday"].max().date()
rentang = st.sidebar.date_input("Rentang tanggal", value=(min_d, max_d), min_value=min_d, max_value=max_d)
if isinstance(rentang, tuple) and len(rentang) == 2:
    tgl_awal, tgl_akhir = rentang
else:
    tgl_awal, tgl_akhir = min_d, max_d

musim = st.sidebar.multiselect("Musim", URUTAN_MUSIM, default=URUTAN_MUSIM)
cuaca = st.sidebar.multiselect("Cuaca", URUTAN_CUACA, default=URUTAN_CUACA)
tipe_hari = st.sidebar.multiselect("Jenis hari", ["Hari Kerja", "Akhir Pekan/Libur"],
                                   default=["Hari Kerja", "Akhir Pekan/Libur"])


def filter_df(df):
    m = (
        (df["dteday"].dt.date >= tgl_awal) & (df["dteday"].dt.date <= tgl_akhir)
        & df["season_label"].isin(musim) & df["weather_label"].isin(cuaca) & df["day_type"].isin(tipe_hari)
    )
    return df[m]


hour_f, day_f = filter_df(hour_df), filter_df(day_df)

st.title("🚲 Dashboard Analisis Bike Sharing 2011-2012")
st.caption("Capital Bikeshare, Washington D.C. | Gunakan filter di sidebar untuk mengeksplorasi data.")

if day_f.empty or hour_f.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini. Silakan ubah filter.")
    st.stop()

# ---------------- KPI ----------------
total = int(day_f["cnt"].sum())
rata_hari = day_f["cnt"].mean()
pct_reg = day_f["registered"].sum() / total * 100
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total penyewaan", f"{total:,}".replace(",", "."))
c2.metric("Rata-rata per hari", f"{rata_hari:,.0f}".replace(",", "."))
c3.metric("Pengguna registered", f"{pct_reg:.1f}%")
c4.metric("Jumlah hari", f"{len(day_f)}")

tab1, tab2, tab4 = st.tabs(["⏰ Pola Jam", "🌦️ Cuaca & Musim", "🔎 Analisis Lanjutan"])

# ---------------- Tab 1 ----------------
with tab1:
    st.subheader("Kapan puncak penyewaan terjadi: hari kerja vs akhir pekan/libur?")
    pola = hour_f.pivot_table(index="hr", columns="day_type", values="cnt", aggfunc="mean")
    warna = {"Hari Kerja": BIRU, "Akhir Pekan/Libur": ORANYE}
    fig, ax = plt.subplots(figsize=(11, 4.8))
    for tipe in pola.columns:
        ax.plot(pola.index, pola[tipe], marker="o", ms=4, lw=2.2, color=warna[tipe], label=tipe)
        jam, nilai = pola[tipe].idxmax(), pola[tipe].max()
        ax.annotate(f"Puncak {jam:02d}:00 ({nilai:.0f}/jam)", xy=(jam, nilai), xytext=(jam + 1.5, nilai + 30),
                    color=warna[tipe], fontsize=9, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.9),
                    arrowprops=dict(arrowstyle="-", color=warna[tipe]))
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("Jam (0-23)")
    ax.set_ylabel("Rata-rata penyewaan per jam")
    ax.set_ylim(0, pola.max().max() * 1.25)
    ax.legend(frameon=False, loc="upper left")
    sns.despine()
    st.pyplot(fig)
    st.info("Hari kerja memiliki dua puncak komuter (sekitar 08:00 dan 17:00), sedangkan akhir pekan/libur "
            "memuncak pada siang hari (sekitar 11:00-16:00). Lakukan redistribusi sebelum jam sibuk dan maintenance pada dini hari.")

# ---------------- Tab 2 ----------------
with tab2:
    st.subheader("Seberapa besar cuaca menurunkan penyewaan harian?")
    col_a, col_b = st.columns([1, 1.4])
    cu = day_f.groupby("weather_label")["cnt"].mean().reindex(URUTAN_CUACA).dropna()
    with col_a:
        fig, ax = plt.subplots(figsize=(5.5, 4.6))
        bars = ax.bar(cu.index, cu.values, color=[BIRU, ABU_MUDA, ABU][: len(cu)])
        acuan = cu.get("Cerah", np.nan)
        for b, (nama, v) in zip(bars, cu.items()):
            teks = f"{v:,.0f}"
            if nama != "Cerah" and not np.isnan(acuan):
                teks += f"\n({(v / acuan - 1) * 100:+.0f}%)"
            ax.text(b.get_x() + b.get_width() / 2, v + cu.max() * 0.02, teks, ha="center", fontsize=9, fontweight="bold")
        ax.set_ylim(0, cu.max() * 1.25)
        ax.set_ylabel("Rata-rata penyewaan per hari")
        ax.tick_params(axis="x", labelsize=8)
        sns.despine()
        st.pyplot(fig)
    with col_b:
        mc = day_f.pivot_table(index="season_label", columns="weather_label", values="cnt", aggfunc="mean")
        mc = mc.reindex(index=[s for s in URUTAN_MUSIM if s in mc.index], columns=[c for c in URUTAN_CUACA if c in mc.columns])
        plot_df = mc.reset_index().melt(id_vars="season_label", var_name="Cuaca", value_name="Rata-rata").dropna()
        fig, ax = plt.subplots(figsize=(7.5, 4.6))
        sns.barplot(data=plot_df, x="season_label", y="Rata-rata", hue="Cuaca", hue_order=list(mc.columns),
                    palette=[BIRU, ABU_MUDA, ABU][: len(mc.columns)], ax=ax)
        ax.set_xlabel("Musim"); ax.set_ylabel("")
        ax.legend(frameon=False, title=None, fontsize=8)
        sns.despine()
        st.pyplot(fig)
    st.info("Cuaca berkabut/mendung menurunkan penyewaan sekitar 17% dan hujan/salju ringan sekitar 63% "
            "(data seluruh periode). Jumlah hari hujan hanya 21 hari, jadi angka per musim perlu dibaca hati-hati.")

# ---------------- Tab 4 ----------------
with tab4:
    st.subheader("Analisis lanjutan: manual grouping dan binning")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        sg = hour_f.groupby(["day_type", "time_segment"])["cnt"].mean().unstack(0).reindex(URUTAN_SEGMEN)
        fig, ax = plt.subplots(figsize=(5, 4.4))
        sg.plot(kind="bar", ax=ax, color=[warna.get(c, BIRU) for c in sg.columns], rot=25, width=0.75)
        ax.set_title("Penyewaan per segmen waktu", loc="left", fontsize=10, fontweight="bold")
        ax.set_xlabel(""); ax.set_ylabel("Rata-rata per jam")
        ax.legend(frameon=False, title=None, fontsize=7)
        sns.despine()
        st.pyplot(fig)
    with col_b:
        sh = day_f.groupby("temp_bin")["cnt"].mean().reindex(URUTAN_SUHU).dropna()
        fig, ax = plt.subplots(figsize=(5, 4.4))
        ax.bar(sh.index, sh.values, color=BIRU)
        for i, v in enumerate(sh.values):
            ax.text(i, v + sh.max() * 0.02, f"{v:,.0f}", ha="center", fontsize=8, fontweight="bold")
        ax.set_ylim(0, sh.max() * 1.15)
        ax.set_title("Penyewaan per kategori suhu", loc="left", fontsize=10, fontweight="bold")
        ax.tick_params(axis="x", rotation=25, labelsize=7)
        ax.set_ylabel("Rata-rata per hari")
        sns.despine()
        st.pyplot(fig)
    with col_c:
        pm = pd.crosstab(day_f["season_label"], day_f["demand_level"], normalize="index").mul(100)
        pm = pm.reindex(index=[s for s in URUTAN_MUSIM if s in pm.index], columns=[d for d in URUTAN_DEMAND if d in pm.columns]).fillna(0)
        fig, ax = plt.subplots(figsize=(5, 4.4))
        pm.plot(kind="bar", stacked=True, ax=ax, rot=0, color=[ABU, ABU_MUDA, "#4d8fc4", "#0f4c81"][: pm.shape[1]], width=0.7)
        ax.set_title("Tingkat permintaan per musim (%)", loc="left", fontsize=10, fontweight="bold")
        ax.set_xlabel(""); ax.set_ylabel("% hari")
        ax.legend(frameon=False, title=None, fontsize=7)
        sns.despine()
        st.pyplot(fig)
    st.caption("Segmen waktu: Dini Hari 00-05, Rush Pagi 06-09, Siang 10-15, Rush Sore 16-19, Malam 20-23. "
               "Permintaan harian: Rendah <3.000, Sedang 3.000-5.000, Tinggi 5.000-7.000, Sangat Tinggi >7.000.")

st.caption("Sumber data: Bike Sharing Dataset (Fanaee-T & Gama, 2013) | Proyek Analisis Data Dicoding")
