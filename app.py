"""
CACA - Cycle Analyst & Cargo Accelaration Dashboard
Pelindo Terminal Teluk Lamong

Aplikasi analitis berbasis web untuk rekonstruksi siklus truk dermaga,
evaluasi rasio Dual Cycle, utilisasi Twin Lift, serta agregasi produktivitas per kapal.
"""

from pathlib import Path
import time
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

import gc
import modules.charts
import modules.ui

from modules.calculations import (
    AMBANG_COMBO_MENIT_DEFAULT,
    AMBANG_DUAL_MENIT_DEFAULT,
    AMBANG_TWINLIFT_MENIT_DEFAULT,
    SIZE_ELIGIBLE,
    guess,
    proses_analisis_lengkap,
)
from modules.charts import apply_glass_theme
from modules.data_loader import baca_file, build_excel_data_only
from modules.ui import (
    find_asset_file,
    format_number,
    inject_css,
    inject_transition_script,
    render_artistic_hero,
    render_html,
    render_hybrid_loading_indicator,
    render_kpi_card,
    render_template,
)



# ----------------------------------------------------------------
# Konfigurasi Halaman Streamlit
# ----------------------------------------------------------------
st.set_page_config(
    page_title="CACA - Dashboard Analisis Dual Cycle & Twin Lift | Pelindo TTL",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------
# Path Aset Media & Branding
# ----------------------------------------------------------------
LOGO_CACA_ICON_PATH = find_asset_file([
    "caca-logo.png",
    "caca.png",
    "CACA.png",
    "logo-caca.png",
    "logo_caca.png",
    "caca.webp",
    "caca-logo.webp",
])
LOGO_PATH = find_asset_file([
    "pelindo.png",
    "logo-pelindo.png",
    "logo_pelindo.png",
    "logo.png",
])
HERO_BG_PATH = find_asset_file([
    "DJI_20250716133943_0169_D.JPG",
    "DJI_20250716133714_0162_D.JPG",
    "hero-bg.jpg",
    "hero-bg.png",
    "hero.jpg",
    "hero.png",
])

# ----------------------------------------------------------------
# Injeksi Desain CSS & Komponen Hero Banner Artistik
# ----------------------------------------------------------------
inject_css("style.css")
render_artistic_hero(HERO_BG_PATH, LOGO_CACA_ICON_PATH, LOGO_PATH)
inject_transition_script("transition.js")

# Anchor point untuk smooth scroll dari hero banner
render_html(
    '<div id="langkah-analisis" style="scroll-margin-top: 24px; position:relative; top:-12px; height:0; margin:0; padding:0;"></div>'
)

# ================================================================
# LANGKAH 1 (ATAS): Unggah File Data Operasional
# ================================================================
with st.container(border=True):
    render_html('<div id="step1-card-marker" style="display:none;"></div>')
    u_col1, u_col2 = st.columns([2.4, 1.6], vertical_alignment="center", gap="medium")
    with u_col1:
        render_template("step1_header.html")

    with u_col2:
        uploaded = st.file_uploader(
            "Pilih file data aktivitas kontainer",
            type=["xlsx"],
            accept_multiple_files=False,
            label_visibility="collapsed",
            key="file_uploader_widget",
        )
        if uploaded is None:
            render_html('<div class="step1-upload-hint">(Khusus format .xlsx &lt;200 MB)</div>')

# Alur Kerja Bertahap: Jika belum ada file diunggah, Langkah 2 & 3 tidak muncul
if uploaded is None:
    st.session_state.pop("hasil", None)
    st.session_state.pop("_last_file_sig", None)
    st.session_state.pop("_cached_sheets", None)
    st.stop()

# ================================================================
# LANGKAH 2 (TENGAH): Parameter Ambang Batas & Konfigurasi
# ================================================================
file_bytes = uploaded.getvalue()

# Deteksi jika file yang diunggah berubah
file_sig = (uploaded.name, len(file_bytes), hash(file_bytes[:1_000_000]))
if st.session_state.get("_last_file_sig") != file_sig:
    st.session_state.pop("hasil", None)
    st.session_state.pop("_cached_sheets", None)
    st.session_state["_last_file_sig"] = file_sig

# Indikator hybrid loading saat file dibaca pertama kali atau file baru diupload
loading_placeholder = st.empty()

if "_cached_sheets" not in st.session_state:
    def on_read_progress(pct: int, status_text: str, detail_text: str = ""):
        render_hybrid_loading_indicator(
            uploaded.name,
            len(file_bytes),
            pct=pct,
            status_text=status_text,
            detail_text=detail_text,
            placeholder=loading_placeholder,
        )

    try:
        sheets = baca_file(file_bytes, uploaded.name, progress_callback=on_read_progress)
        st.session_state["_cached_sheets"] = sheets
        time.sleep(0.45)
        loading_placeholder.empty()
    except Exception as e:
        loading_placeholder.empty()
        st.error(
            "Gagal membaca file yang diupload. Pastikan file tidak corrupt dan "
            "formatnya benar-benar file Excel (.xlsx)."
        )
        with st.expander("Detail error (untuk dilaporkan)"):
            st.exception(e)
        st.stop()
else:
    sheets = st.session_state["_cached_sheets"]

if not sheets:
    st.error("File tidak berisi sheet/data apa pun.")
    st.stop()

sheet_name = None
raw = None

with st.container(border=True):
    render_template("step2_header.html")

    # Pemilihan Sheet Data Operasional
    sheet_keys = list(sheets.keys())
    sheet_name = st.selectbox("Pilih sheet data operasional:", sheet_keys, index=0)
    raw = sheets[sheet_name]

    # Baris 2: 3 Kolom Parameter Ambang Batas Berjejer Horizontal
    th1, th2, th3 = st.columns([1, 1, 1], gap="medium")
    with th1:
        ambang_combo = st.number_input(
            "Ambang Combo (menit)",
            min_value=1,
            value=AMBANG_COMBO_MENIT_DEFAULT,
            step=5,
            help="Jarak waktu maksimum antar 2 baris size 20ft, truk & aktivitas sama, supaya dianggap 'Combo'.",
        )
        render_html(
            '<div class="step2-param-hint" style="font-size:0.75rem;color:#94a3b8;margin-top:-8px;line-height:1.35;margin-bottom:2px;">'
            'Maks. gap antar 2 baris 20ft (truk &amp; aktivitas sama)</div>'
        )

    with th2:
        ambang_dual = st.number_input(
            "Ambang Dual Cycle (menit)",
            min_value=1,
            value=AMBANG_DUAL_MENIT_DEFAULT,
            step=10,
            help="Jarak waktu maksimum antar 2 event beda aktivitas (LOAD vs DISC) dalam truk yang sama.",
        )
        render_html(
            '<div class="step2-param-hint" style="font-size:0.75rem;color:#94a3b8;margin-top:-8px;line-height:1.35;margin-bottom:2px;">'
            'Maks. gap antar event DISC &amp; LOAD (truk sama)</div>'
        )

    with th3:
        ambang_twinlift = st.number_input(
            "Ambang Twinlift (menit)",
            min_value=1,
            value=AMBANG_TWINLIFT_MENIT_DEFAULT,
            step=1,
            help=(
                "Jarak waktu maksimum DISC_LOAD_TS antar 2 kontainer dalam 1 Combo 20ft, "
                "yang berasal dari kapal (VES_ID) & truk yang sama, supaya dianggap 'Twinlift'."
            ),
        )
        render_html(
            '<div class="step2-param-hint" style="font-size:0.75rem;color:#94a3b8;margin-top:-8px;line-height:1.35;margin-bottom:2px;">'
            'Maks. gap waktu angkat 2 kontainer Combo 20ft</div>'
        )

    # Pemetaan Kolom Otomatis
    cols = list(raw.columns)
    col_map = {
        "ves_id": cols[guess(cols, ["ves", "kapal", "vessel"])],
        "size": cols[guess(cols, ["size", "ctr_size", "ukuran"])],
        "truck": cols[guess(cols, ["car_che", "truck", "che", "trailer", "truk"])],
        "activity": cols[guess(cols, ["activity", "aktivitas", "aktifitas", "act"])],
        "ts_g": cols[guess(cols, ["disc_load", "disc_loading", "waktu", "time", "date"])],
        "ts_h": cols[guess(cols, ["stack_unstack", "unstack_stack", "waktu", "time", "date"])],
    }

    # Peringatan jika hasil analisis sebelumnya sudah usang
    if "hasil" in st.session_state:
        _cached_summary = st.session_state["hasil"].get("summary", {})
        if "total_non_twinlift" not in _cached_summary:
            st.session_state.pop("hasil", None)
            st.warning(
                "Hasil analisis sebelumnya sudah usang. "
                "Silakan klik tombol di bawah untuk menjalankan ulang analisis."
            )

    # Tombol Eksekusi di Bagian Paling Bawah Container Langkah 2 (Ukuran Ringkas & Center)
    render_html('<div style="height:6px;"></div>')
    b_col1, b_col2, b_col3 = st.columns([1.4, 1.2, 1.4])
    with b_col2:
        run = st.button("Jalankan Komputasi Analisis", type="primary", use_container_width=True)

# Jika belum dijalankan dan belum ada hasil: Berhenti di sini
if not run and "hasil" not in st.session_state:
    st.stop()

# Eksekusi Komputasi Analisis
if run:
    loading_calc_placeholder = st.empty()

    def on_calc_progress(pct: int, status_text: str, detail_text: str = ""):
        render_hybrid_loading_indicator(
            uploaded.name,
            len(file_bytes),
            pct=pct,
            status_text=status_text,
            detail_text=detail_text,
            placeholder=loading_calc_placeholder,
        )

    try:
        on_calc_progress(6, "Memulai analisis...", "Inisialisasi pipeline komputasi")
        out_df, events, summary = proses_analisis_lengkap(
            raw,
            col_map,
            SIZE_ELIGIBLE,
            ambang_combo,
            ambang_dual,
            ambang_twinlift,
            progress_callback=on_calc_progress,
        )
        time.sleep(0.45)
        loading_calc_placeholder.empty()
        gc.collect()

        if out_df is None or len(out_df) == 0:
            st.error(
                "Setelah pembersihan, tidak ada baris data yang tersisa. "
                "Kemungkinan kolom waktu DISC_LOAD_TS & STACK_UNSTACK_TS tidak valid."
            )
            st.stop()
    except Exception as e:
        loading_calc_placeholder.empty()
        st.error("Terjadi error saat memproses data.")
        with st.expander("Detail error (untuk dilaporkan)", expanded=True):
            st.exception(e)
        st.stop()

    st.session_state["hasil"] = {
        "out_df": out_df,
        "events": events,
        "summary": summary,
        "ambang_combo": ambang_combo,
        "ambang_dual": ambang_dual,
        "ambang_twinlift": ambang_twinlift,
    }
    st.session_state["_ambang_terakhir"] = (ambang_combo, ambang_dual, ambang_twinlift)

hasil = st.session_state["hasil"]
out_df = hasil["out_df"]
events = hasil["events"]
summary = hasil["summary"]

_ambang_terakhir = st.session_state.get(
    "_ambang_terakhir", (hasil["ambang_combo"], hasil["ambang_dual"], hasil["ambang_twinlift"])
)
if (ambang_combo, ambang_dual, ambang_twinlift) != _ambang_terakhir:
    st.warning(
        "Ambang batas di Pengaturan sudah diubah tapi belum diterapkan. "
        "Hasil di bawah masih menggunakan ambang yang lama — klik "
        "\"Jalankan Komputasi Analisis\" lagi untuk memperbarui."
    )

# ================================================================
# LANGKAH 3: EXECUTIVE KPI & HASIL ANALISIS
# ================================================================
with st.container(border=True):
    render_template("step3_header.html")

    # Smooth scroll otomatis menggeser halaman ke Langkah 3 saat komputasi selesai dijalankan
    if run:
        components.html(
            """
            <script>
            (function() {
                function doScroll() {
                    try {
                        var win = window.parent;
                        if (win && win.triggerScrollToStep3) {
                            win.triggerScrollToStep3();
                        } else {
                            var doc = window.parent.document;
                            var t = doc.getElementById('step3-card-marker');
                            if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    } catch(e) {}
                }
                doScroll();
                setTimeout(doScroll, 100);
                setTimeout(doScroll, 300);
                setTimeout(doScroll, 600);
            })();
            </script>
            """,
            height=0,
            width=0,
        )

    monthly = summary["monthly"].reset_index().rename(columns={"BULAN": "Bulan"})

    # 4 Tab Hasil Analisis
    tab_dual, tab_twinlift, tab_vessel, tab_download = st.tabs(
        ["Dual Cycle", "Twinlift", "Per Vessel", "Download Hasil Analisis"]
    )

    # ----------------------------------------------------------------
    # TAB 1: DUAL CYCLE
    # ----------------------------------------------------------------
    with tab_dual:
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1:
            render_kpi_card("Total Event", format_number(summary["total_event"]), subtext="Ritase Truk", variant="purple")
        with k2:
            render_kpi_card("Dual Cycle", format_number(summary["total_dual"]), variant="blue")
        with k3:
            render_kpi_card("Non Dual", format_number(summary["total_single"]), variant="slate")
        with k4:
            pct_dual_val = summary["pct_dual"] * 100
            render_kpi_card("% Dual Cycle", f"{pct_dual_val:.1f}%", variant="blue")
        with k5:
            render_kpi_card("Container LOAD", format_number(summary["container_load"]), subtext="Total Muat", variant="amber")
        with k6:
            render_kpi_card("Container DISC", format_number(summary["container_disc"]), subtext="Total Bongkar", variant="teal")

        cc1, cc2 = st.columns(2)
        with cc1:
            pie_df = pd.DataFrame(
                {"Status": ["Dual Cycle", "Non Dual"], "Jumlah": [summary["total_dual"], summary["total_single"]]}
            )
            pie_df = pie_df[pie_df["Jumlah"] > 0]
            fig_pie = px.pie(
                pie_df,
                names="Status",
                values="Jumlah",
                hole=0.52,
                title="Dual Cycle vs Non Dual (berbasis Event)",
                color="Status",
                color_discrete_map={"Dual Cycle": "#0284C7", "Non Dual": "#94A3B8"},
            )
            fig_pie.update_traces(
                textinfo="percent+label",
                textposition="inside",
                insidetextorientation="horizontal",
                textfont=dict(family="Plus Jakarta Sans", size=12, color="#ffffff"),
                marker=dict(line=dict(color="#ffffff", width=2)),
            )
            apply_glass_theme(fig_pie)
            fig_pie.update_layout(margin=dict(t=72, b=25, l=25, r=25))
            st.plotly_chart(fig_pie, width="stretch")

        with cc2:
            container_df = pd.DataFrame(
                {
                    "Container": ["Combo", "Combo", "Single", "Single"],
                    "Status": ["Dual Cycle", "Non Dual", "Dual Cycle", "Non Dual"],
                    "Jumlah": [
                        summary["combo_dual"],
                        summary["combo_single"],
                        summary["single_dual"],
                        summary["single_single"],
                    ],
                }
            )
            container_df["Jumlah_Tampil"] = container_df["Jumlah"].apply(format_number)
            fig_bar = px.bar(
                container_df,
                x="Container",
                y="Jumlah",
                color="Status",
                barmode="group",
                title="Rincian Container x Status (Event)",
                color_discrete_map={"Dual Cycle": "#0284C7", "Non Dual": "#94A3B8"},
                text="Jumlah_Tampil",
            )
            fig_bar.update_traces(marker=dict(line=dict(color="#ffffff", width=1)))
            apply_glass_theme(fig_bar)
            st.plotly_chart(fig_bar, width="stretch")

        if len(monthly) > 0:
            monthly_dual_pct = monthly.melt(
                id_vars="Bulan",
                value_vars=["pct_dual", "pct_non_dual"],
                var_name="Kategori",
                value_name="Persentase",
            )
            monthly_dual_pct["Kategori"] = monthly_dual_pct["Kategori"].map(
                {"pct_dual": "Dual Cycle", "pct_non_dual": "Non Dual"}
            )
            monthly_dual_pct["Persentase"] = monthly_dual_pct["Persentase"] * 100

            fig_month_dual = px.bar(
                monthly_dual_pct,
                x="Bulan",
                y="Persentase",
                color="Kategori",
                barmode="stack",
                title="Breakdown Bulanan: Dual Cycle vs Non Dual (%)",
                color_discrete_map={"Dual Cycle": "#0284C7", "Non Dual": "#94A3B8"},
                text_auto=".1f",
            )
            fig_month_dual.update_layout(yaxis=dict(title="% dari Total Event", range=[0, 100]))
            apply_glass_theme(fig_month_dual)
            st.plotly_chart(fig_month_dual, width="stretch")

            monthly_container_pct = monthly.melt(
                id_vars="Bulan",
                value_vars=["pct_combo", "pct_single"],
                var_name="Kategori",
                value_name="Persentase",
            )
            monthly_container_pct["Kategori"] = monthly_container_pct["Kategori"].map(
                {"pct_combo": "Combo", "pct_single": "Single"}
            )
            monthly_container_pct["Persentase"] = monthly_container_pct["Persentase"] * 100

            fig_month_container = px.bar(
                monthly_container_pct,
                x="Bulan",
                y="Persentase",
                color="Kategori",
                barmode="stack",
                title="Breakdown Bulanan: Combo vs Single (%)",
                color_discrete_map={"Combo": "#0EA5E9", "Single": "#64748B"},
                text_auto=".1f",
            )
            fig_month_container.update_layout(yaxis=dict(title="% dari Total Event", range=[0, 100]))
            apply_glass_theme(fig_month_container)
            st.plotly_chart(fig_month_container, width="stretch")

    # ----------------------------------------------------------------
    # TAB 2: TWINLIFT
    # ----------------------------------------------------------------
    with tab_twinlift:
        render_template("tab_twinlift_info.html", ambang_twinlift=hasil["ambang_twinlift"])

        t1, t2, t3, t4 = st.columns(4)
        with t1:
            render_kpi_card("Total Event", format_number(summary["total_event"]), subtext="Basis Perhitungan", variant="purple")
        with t2:
            render_kpi_card("Twinlift", format_number(summary["total_twinlift"]), variant="blue")
        with t3:
            render_kpi_card("Bukan Twinlift", format_number(summary["total_non_twinlift"]), variant="slate")
        with t4:
            pct_twin_val = summary["pct_twinlift_of_total"] * 100
            render_kpi_card("% Twinlift", f"{pct_twin_val:.1f}%", variant="blue")

        tc1, tc2 = st.columns(2)
        with tc1:
            if summary["total_event"] > 0:
                twin_df = pd.DataFrame(
                    {
                        "Status": ["Twinlift", "Bukan Twinlift"],
                        "Jumlah": [summary["total_twinlift"], summary["total_non_twinlift"]],
                    }
                )
                twin_df = twin_df[twin_df["Jumlah"] > 0]
                fig_twin_pie = px.pie(
                    twin_df,
                    names="Status",
                    values="Jumlah",
                    hole=0.52,
                    title="Twinlift vs Bukan Twinlift (dari Total Event)",
                    color="Status",
                    color_discrete_map={"Twinlift": "#0284C7", "Bukan Twinlift": "#94A3B8"},
                )
                fig_twin_pie.update_traces(
                    textinfo="percent+label",
                    textposition="inside",
                    insidetextorientation="horizontal",
                    textfont=dict(family="Plus Jakarta Sans", size=12, color="#ffffff"),
                    marker=dict(line=dict(color="#ffffff", width=2)),
                )
                apply_glass_theme(fig_twin_pie)
                fig_twin_pie.update_layout(margin=dict(t=72, b=25, l=25, r=25))
                st.plotly_chart(fig_twin_pie, width="stretch")
            else:
                st.info("Tidak ada event pada data ini.")

        with tc2:
            if len(monthly) > 0:
                monthly_twin_pct = monthly.melt(
                    id_vars="Bulan",
                    value_vars=["pct_twinlift", "pct_non_twinlift"],
                    var_name="Kategori",
                    value_name="Persentase",
                )
                monthly_twin_pct["Kategori"] = monthly_twin_pct["Kategori"].map(
                    {"pct_twinlift": "Twinlift", "pct_non_twinlift": "Bukan Twinlift"}
                )
                monthly_twin_pct["Persentase"] = monthly_twin_pct["Persentase"] * 100

                fig_month_twin = px.bar(
                    monthly_twin_pct,
                    x="Bulan",
                    y="Persentase",
                    color="Kategori",
                    barmode="stack",
                    title="Breakdown Bulanan: Twinlift vs Bukan Twinlift (% dari Total Event)",
                    color_discrete_map={"Twinlift": "#0284C7", "Bukan Twinlift": "#94A3B8"},
                    text_auto=".1f",
                )
                fig_month_twin.update_layout(yaxis=dict(title="% dari Total Event", range=[0, 100]))
                apply_glass_theme(fig_month_twin)
                st.plotly_chart(fig_month_twin, width="stretch")

    # ----------------------------------------------------------------
    # TAB 3: ANALISIS PER VESSEL
    # ----------------------------------------------------------------
    with tab_vessel:
        render_template("tab_vessel_info.html")

        ves_id_bersih = out_df["VES_ID"].dropna().astype(str).str.strip()
        ves_id_bersih = ves_id_bersih[ves_id_bersih != ""]
        vessel_options = sorted(ves_id_bersih.unique().tolist())

        if len(vessel_options) == 0:
            st.info("Tidak ada data VES_ID pada hasil analisis ini.")
        else:
            selected_vessel = st.selectbox("Cari / pilih VES_ID", vessel_options)
            vessel_df = out_df[out_df["VES_ID"].astype(str).str.strip() == selected_vessel]

            total_rec = len(vessel_df)
            dual_rec = int((vessel_df["STATUS"] == "Dual Cycle").sum())
            non_dual_rec = total_rec - dual_rec
            twinlift_rec = int((vessel_df["TWINLIFT_STATUS"] == "Twinlift").sum())
            non_twinlift_rec = total_rec - twinlift_rec
            combo_rec = int((vessel_df["CONTAINER_STATUS"] == "Combo").sum())
            single_rec = total_rec - combo_rec

            v1, v2, v3, v4, v5 = st.columns(5)
            with v1:
                render_kpi_card("Total Aktivitas", format_number(total_rec), subtext="Baris Data", variant="purple")
            with v2:
                render_kpi_card("Dual Cycle", format_number(dual_rec), variant="blue")
            with v3:
                pct_dual_v = (dual_rec / total_rec * 100) if total_rec else 0
                render_kpi_card("% Dual Cycle", f"{pct_dual_v:.1f}%", variant="blue")
            with v4:
                render_kpi_card("Twinlift", format_number(twinlift_rec), variant="blue")
            with v5:
                pct_twin_v = (twinlift_rec / total_rec * 100) if total_rec else 0
                render_kpi_card("% Twinlift", f"{pct_twin_v:.1f}%", variant="blue")

            vc1, vc2 = st.columns(2)
            with vc1:
                if total_rec > 0:
                    pie_dual_v = pd.DataFrame(
                        {"Status": ["Dual Cycle", "Non Dual"], "Jumlah": [dual_rec, non_dual_rec]}
                    )
                    pie_dual_v = pie_dual_v[pie_dual_v["Jumlah"] > 0]
                    fig_v1 = px.pie(
                        pie_dual_v,
                        names="Status",
                        values="Jumlah",
                        hole=0.52,
                        title=f"Dual Cycle vs Non Dual — {selected_vessel}",
                        color="Status",
                        color_discrete_map={"Dual Cycle": "#0284C7", "Non Dual": "#94A3B8"},
                    )
                    fig_v1.update_traces(
                        textinfo="percent+label",
                        textposition="inside",
                        insidetextorientation="horizontal",
                        textfont=dict(family="Plus Jakarta Sans", size=12, color="#ffffff"),
                        marker=dict(line=dict(color="#ffffff", width=2)),
                    )
                    apply_glass_theme(fig_v1)
                    fig_v1.update_layout(margin=dict(t=72, b=25, l=25, r=25))
                    st.plotly_chart(fig_v1, width="stretch")

            with vc2:
                if total_rec > 0:
                    pie_twin_v = pd.DataFrame(
                        {"Status": ["Twinlift", "Bukan Twinlift"], "Jumlah": [twinlift_rec, non_twinlift_rec]}
                    )
                    pie_twin_v = pie_twin_v[pie_twin_v["Jumlah"] > 0]
                    fig_v2 = px.pie(
                        pie_twin_v,
                        names="Status",
                        values="Jumlah",
                        hole=0.52,
                        title=f"Twinlift vs Bukan Twinlift — {selected_vessel}",
                        color="Status",
                        color_discrete_map={"Twinlift": "#0284C7", "Bukan Twinlift": "#94A3B8"},
                    )
                    fig_v2.update_traces(
                        textinfo="percent+label",
                        textposition="inside",
                        insidetextorientation="horizontal",
                        textfont=dict(family="Plus Jakarta Sans", size=12, color="#ffffff"),
                        marker=dict(line=dict(color="#ffffff", width=2)),
                    )
                    apply_glass_theme(fig_v2)
                    fig_v2.update_layout(margin=dict(t=72, b=25, l=25, r=25))
                    st.plotly_chart(fig_v2, width="stretch")

            vcont_df = pd.DataFrame(
                {"Container": ["Combo", "Single"], "Jumlah": [combo_rec, single_rec]}
            )
            vcont_df["Jumlah_Tampil"] = vcont_df["Jumlah"].apply(format_number)
            fig_v3 = px.bar(
                vcont_df,
                x="Container",
                y="Jumlah",
                title=f"Combo vs Single — {selected_vessel}",
                color="Container",
                color_discrete_map={"Combo": "#0EA5E9", "Single": "#64748B"},
                text="Jumlah_Tampil",
            )
            apply_glass_theme(fig_v3)
            st.plotly_chart(fig_v3, width="stretch")

    # ----------------------------------------------------------------
    # TAB 4: DOWNLOAD HASIL ANALISIS
    # ----------------------------------------------------------------
    with tab_download:
        st.dataframe(out_df.head(1000), use_container_width=True, height=400)
        if len(out_df) > 1000:
            st.caption(
                f"Menampilkan 1.000 baris pertama dari total {format_number(len(out_df))} baris. "
                "Gunakan tombol di bawah untuk mengunduh dataset lengkap."
            )

        hasil_sig = (
            hasil["ambang_combo"],
            hasil["ambang_dual"],
            hasil["ambang_twinlift"],
            len(out_df),
        )
        if st.session_state.get("_download_sig") != hasil_sig:
            st.session_state.pop("_excel_bytes", None)
            st.session_state.pop("_excel_sig", None)
            st.session_state["_download_sig"] = hasil_sig

        excel_ready = "_excel_bytes" in st.session_state and st.session_state.get("_excel_sig") == hasil_sig

        if excel_ready:
            st.download_button(
                "📥 Download File Excel (.xlsx)",
                data=st.session_state["_excel_bytes"],
                file_name="Hasil_Analisis_Dual_Cycle.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            if st.button("Download Hasil Analisis (.xlsx)", use_container_width=True):
                with st.spinner("Menyiapkan file Excel (mohon tunggu)..."):
                    try:
                        st.session_state["_excel_bytes"] = build_excel_data_only(out_df)
                        st.session_state["_excel_sig"] = hasil_sig
                        st.rerun()
                    except Exception as err:
                        st.error(f"Gagal membuat file Excel: {err}.")
