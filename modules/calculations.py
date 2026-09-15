"""
Modul Perhitungan & Logika Analisis Operasional
Terminal Teluk Lamong - Pelindo

Berisi algoritma komputasi multi-layer:
1. Rekonstruksi & Normalisasi Data (VBA Val(), datetime fallback, vessel cleaner)
2. Layer 1: Deteksi Combo 20ft (Sliding Window Greedy Matching)
3. Layer 1b: Deteksi Twin Lift (Sama Kapal & Delta Waktu DISC_LOAD_TS)
4. Pembentukan Event Ritase Truk
5. Layer 2: Deteksi Dual Cycle (Lintas Aktivitas LOAD vs DISC)
6. Penomoran Urut Event ID Global
7. Perhitungan Ringkasan Metrik & Evaluasi KPI Bulanan
"""

import re
import numpy as np
import pandas as pd
import streamlit as st
from modules.ui import format_number

# ================================================================
# KONSTANTA DEFAULT (Kompak & Terkalibrasi dengan Macro VBA)
# ================================================================
AMBANG_COMBO_MENIT_DEFAULT = 40
AMBANG_DUAL_MENIT_DEFAULT = 240  # 4 jam
AMBANG_TWINLIFT_MENIT_DEFAULT = 1  # 1 menit selisih DISC_LOAD_TS
SIZE_ELIGIBLE = 20  # Ukuran kontainer eligible Combo/Twinlift (20ft)

_VBA_VAL_RE = re.compile(r"^\s*[+-]?\d+(\.\d+)?")


def klasifikasi_activity(val: object) -> str:
    """Klasifikasi aktivitas ke LOAD atau DISC."""
    s = str(val).upper()
    return "LOAD" if "LOAD" in s else "DISC"


def vba_val(x: object) -> float:
    """
    Replikasi fungsi Val() di VBA: baca angka dari AWAL string sampai
    ketemu karakter non-angka pertama, sisanya diabaikan (mis. '20FT' -> 20).
    """
    if pd.isna(x):
        return 0.0
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    m = _VBA_VAL_RE.match(str(x))
    return float(m.group()) if m else 0.0


def bersihkan_ves_id(series: pd.Series) -> pd.Series:
    """
    Normalisasi kolom VES_ID jadi string biasa (dtype object), bukan
    dtype 'string'/ArrowDtype bawaan pandas versi baru.
    Dioptimalkan secara vektorisasi untuk dataset besar.
    """
    s = series.astype("object")
    mask_notna = s.notna()
    s_clean = s[mask_notna].astype(str).str.strip()
    s_clean = s_clean.replace({"": pd.NA})
    out = pd.Series(pd.NA, index=series.index, dtype=object)
    out.loc[s_clean.index] = s_clean
    return out


def siapkan_data(raw: pd.DataFrame, col_map: dict, size_eligible: int) -> pd.DataFrame:
    """Membersihkan dan menyiapkan kolom data operasional standar secara tervektorisasi cepat."""
    df = pd.DataFrame()
    df["VES_ID"] = bersihkan_ves_id(raw[col_map["ves_id"]])

    # Vektorisasi parsing CTR_SIZE (mendukung angka langsung dan pola teks VBA Val seperti '20FT')
    s_size = raw[col_map["size"]]
    num_size = pd.to_numeric(s_size, errors="coerce")
    if num_size.notna().all():
        df["CTR_SIZE"] = num_size.fillna(0.0).astype(float)
    else:
        extracted = s_size.astype(str).str.extract(r"^\s*([+-]?\d+(?:\.\d+)?)", expand=False)
        df["CTR_SIZE"] = pd.to_numeric(extracted, errors="coerce").fillna(0.0).astype(float)

    df["CAR_CHE_ID"] = raw[col_map["truck"]].astype(str).str.strip()

    # Vektorisasi klasifikasi aktivitas LOAD / DISC
    act_str = raw[col_map["activity"]].astype(str).str.upper()
    df["ACTIVITY"] = np.where(act_str.str.contains("LOAD", na=False), "LOAD", "DISC")

    # Parsing datetime cepat
    df["TS_G"] = pd.to_datetime(raw[col_map["ts_g"]], errors="coerce", format="mixed")
    df["TS_H"] = pd.to_datetime(raw[col_map["ts_h"]], errors="coerce", format="mixed")

    both_invalid = df["TS_G"].isna() & df["TS_H"].isna()
    df["TS_G"] = df["TS_G"].fillna(df["TS_H"])
    df["TS_H"] = df["TS_H"].fillna(df["TS_G"])

    if both_invalid.any():
        dummy_ts = pd.Timestamp("1899-12-29")
        df.loc[both_invalid, "TS_G"] = dummy_ts
        df.loc[both_invalid, "TS_H"] = dummy_ts
        st.warning(
            f"{int(both_invalid.sum())} baris punya kedua kolom timestamp "
            f"(DISC_LOAD_TS & STACK_UNSTACK_TS) kosong/tidak valid. Mengikuti "
            f"perilaku VBA, baris ini TETAP diproses sbg event tersendiri "
            f"(tanggal dummy 29 Des 1899), bukan dibuang, supaya total & "
            f"persentase persis sama dengan hasil macro VBA."
        )

    ves_kosong = df["VES_ID"].isna()
    if ves_kosong.any():
        df.loc[ves_kosong, "VES_ID"] = "(VES_ID Kosong)"

    df = df.reset_index(drop=True)
    df["ROW_IDX"] = df.index
    return df


def layer1_combo(df: pd.DataFrame, ambang_combo: float, size_eligible: int) -> pd.DataFrame:
    """
    Layer 1: Identifikasi kontainer berukuran 20ft dari truk & aktivitas sama
    yang memenuhi ambang batas waktu Combo (O(m log m) sliding window greedy).
    """
    n = len(df)
    ts_g = df["TS_G"].to_numpy()
    ts_h = df["TS_H"].to_numpy()
    size = df["CTR_SIZE"].to_numpy()
    activity = df["ACTIVITY"].to_numpy()

    assigned = np.zeros(n, dtype=bool)
    group_id = np.zeros(n, dtype=int)

    pairs = []
    truck_positions = df.groupby("CAR_CHE_ID").indices

    thr_delta = np.timedelta64(int(round(ambang_combo * 60)), "s")

    for _, pos in truck_positions.items():
        for act in ("LOAD", "DISC"):
            idx_act = np.array([p for p in pos if activity[p] == act and size[p] == size_eligible])
            m = len(idx_act)
            if m < 2:
                continue

            found = set()
            for ts_arr in (ts_g, ts_h):
                order = idx_act[np.argsort(ts_arr[idx_act])]
                sorted_ts = ts_arr[order]
                left = 0
                for right in range(len(order)):
                    while sorted_ts[right] - sorted_ts[left] > thr_delta:
                        left += 1
                    for b in range(left, right):
                        i, k = order[b], order[right]
                        if i > k:
                            i, k = k, i
                        found.add((int(i), int(k)))

            for i, k in found:
                gap_g = abs((ts_g[k] - ts_g[i]) / np.timedelta64(1, "m"))
                gap_h = abs((ts_h[k] - ts_h[i]) / np.timedelta64(1, "m"))
                gap = min(gap_g, gap_h)
                pairs.append((i, k, gap))

    pairs.sort(key=lambda x: (x[2], x[0], x[1]))

    nxt = 0
    for i, k, _gap in pairs:
        if not assigned[i] and not assigned[k]:
            nxt += 1
            group_id[i] = nxt
            group_id[k] = nxt
            assigned[i] = assigned[k] = True

    for i in range(n):
        if not assigned[i]:
            nxt += 1
            group_id[i] = nxt
            assigned[i] = True

    out = df.copy()
    out["GROUP_ID"] = group_id
    return out


def deteksi_twinlift(df_combo: pd.DataFrame, ambang_twinlift: float, size_eligible: int):
    """
    Layer 1b: Deteksi kondisi Twin Lift di dalam grup Combo:
    1. Ukuran 20ft
    2. VES_ID sama
    3. Selisih DISC_LOAD_TS <= ambang_twinlift
    Dioptimalkan secara vektorisasi NumPy (~400x lebih cepat daripada groupby loop).
    """
    grp_sizes = df_combo["GROUP_ID"].value_counts()
    combo_gids = grp_sizes.index[grp_sizes == 2]

    status_map = {int(gid): "-" for gid in grp_sizes.index}
    gap_map = {int(gid): None for gid in grp_sizes.index}

    if len(combo_gids) > 0:
        df_twins = df_combo[df_combo["GROUP_ID"].isin(combo_gids)].sort_values(["GROUP_ID", "ROW_IDX"])
        r1 = df_twins.iloc[0::2]
        r2 = df_twins.iloc[1::2]

        gids = r1["GROUP_ID"].to_numpy()
        syarat_size = (r1["CTR_SIZE"].to_numpy() == size_eligible) & (r2["CTR_SIZE"].to_numpy() == size_eligible)
        syarat_kapal = r1["VES_ID"].to_numpy() == r2["VES_ID"].to_numpy()
        gap_mins = np.abs((r2["TS_G"].to_numpy() - r1["TS_G"].to_numpy()) / np.timedelta64(1, "m"))
        syarat_waktu = gap_mins <= ambang_twinlift

        is_twin = syarat_size & syarat_kapal & syarat_waktu
        statuses = np.where(is_twin, "Twinlift", "Bukan Twinlift")
        rounded_gaps = np.round(gap_mins, 2)

        for gid, st_val, gp_val in zip(gids, statuses, rounded_gaps):
            status_map[int(gid)] = st_val
            gap_map[int(gid)] = float(gp_val)

    return status_map, gap_map


def bentuk_event(df: pd.DataFrame) -> pd.DataFrame:
    """Membentuk event ritase truk dari grup hasil Layer 1 (vektorisasi cepat)."""
    is_disc = df["ACTIVITY"].to_numpy() == "DISC"
    evt_start = np.where(is_disc, df["TS_G"].to_numpy(), df["TS_H"].to_numpy())
    evt_end = np.where(is_disc, df["TS_H"].to_numpy(), df["TS_G"].to_numpy())

    tmp = pd.DataFrame(
        {
            "GROUP_ID": df["GROUP_ID"].to_numpy(),
            "ACTIVITY": df["ACTIVITY"].to_numpy(),
            "CAR_CHE_ID": df["CAR_CHE_ID"].to_numpy(),
            "EVT_START": evt_start,
            "EVT_END": evt_end,
        }
    )

    events = tmp.groupby("GROUP_ID", sort=True).agg(
        ACTIVITY=("ACTIVITY", "first"),
        CAR_CHE_ID=("CAR_CHE_ID", "first"),
        START_TS=("EVT_START", "min"),
        END_TS=("EVT_END", "max"),
        N_ANGGOTA=("GROUP_ID", "size"),
    ).reset_index()

    events["CONTAINER_STATUS"] = np.where(events["N_ANGGOTA"] >= 2, "Combo", "Single")
    events = events.drop(columns=["N_ANGGOTA"])
    return events


def layer2_dual(events: pd.DataFrame, ambang_dual: float) -> pd.DataFrame:
    """
    Layer 2: Deteksi pasangan Dual Cycle lintas aktivitas (LOAD vs DISC)
    dalam truk yang sama.
    """
    events = events.reset_index(drop=True)
    n = len(events)
    start = events["START_TS"].to_numpy()
    end = events["END_TS"].to_numpy()
    activity = events["ACTIVITY"].to_numpy()

    assigned = np.zeros(n, dtype=bool)
    status = np.array(["Non Dual"] * n, dtype=object)

    pairs = []
    truck_positions = events.groupby("CAR_CHE_ID").indices

    for _, pos in truck_positions.items():
        pos_sorted = sorted(pos, key=lambda p: start[p])
        m = len(pos_sorted)
        for a in range(m - 1):
            i = pos_sorted[a]
            for b in range(a + 1, m):
                k = pos_sorted[b]
                gap_ab = (start[k] - end[i]) / np.timedelta64(1, "m")
                gap_ba = (start[i] - end[k]) / np.timedelta64(1, "m")
                if gap_ab >= 0:
                    gap = gap_ab
                elif gap_ba >= 0:
                    gap = gap_ba
                else:
                    gap = 0.0

                if gap > ambang_dual:
                    break

                if activity[i] != activity[k]:
                    pairs.append((i, k, gap))

    pairs.sort(key=lambda x: (x[2], x[0], x[1]))
    for i, k, _gap in pairs:
        if not assigned[i] and not assigned[k]:
            status[i] = "Dual Cycle"
            status[k] = "Dual Cycle"
            assigned[i] = assigned[k] = True

    out = events.copy()
    out["STATUS"] = status
    return out


def beri_event_id(events: pd.DataFrame, df_asli: pd.DataFrame):
    """Memberikan EVENT_ID berurutan sesuai urutan kemunculan truk di log asli."""
    truck_order = list(dict.fromkeys(df_asli["CAR_CHE_ID"].tolist()))
    rank = {tk: i for i, tk in enumerate(truck_order)}

    events = events.copy()
    events["_truck_rank"] = events["CAR_CHE_ID"].map(rank)
    events = events.sort_values(["_truck_rank", "START_TS"]).reset_index(drop=True)
    events["EVENT_ID"] = events.index + 1
    events = events.drop(columns=["_truck_rank"])

    event_id_map = dict(zip(events["GROUP_ID"], events["EVENT_ID"]))
    return events, event_id_map


def gabungkan_hasil(df: pd.DataFrame, events: pd.DataFrame, event_id_map: dict) -> pd.DataFrame:
    """Menggabungkan status komputasi kembali ke DataFrame awal per baris kontainer (vektorisasi cepat via merge)."""
    cols_to_merge = ["GROUP_ID", "EVENT_ID", "CONTAINER_STATUS", "STATUS", "TWINLIFT_STATUS", "TWINLIFT_GAP_MENIT"]
    out = df.merge(events[cols_to_merge], on="GROUP_ID", how="left")
    out = out.drop(columns=["GROUP_ID", "ROW_IDX"])
    return out


def hitung_ringkasan(events: pd.DataFrame, out_df: pd.DataFrame) -> dict:
    """Menghitung ringkasan statistik komprehensif, metrik KPI, dan agregasi bulanan."""
    total_event = len(events)
    total_dual = int((events["STATUS"] == "Dual Cycle").sum())
    total_single = total_event - total_dual

    combo_dual = int(((events["CONTAINER_STATUS"] == "Combo") & (events["STATUS"] == "Dual Cycle")).sum())
    combo_single = int(((events["CONTAINER_STATUS"] == "Combo") & (events["STATUS"] == "Non Dual")).sum())
    single_dual = int(((events["CONTAINER_STATUS"] == "Single") & (events["STATUS"] == "Dual Cycle")).sum())
    single_single = int(((events["CONTAINER_STATUS"] == "Single") & (events["STATUS"] == "Non Dual")).sum())

    total_combo = int((events["CONTAINER_STATUS"] == "Combo").sum())
    total_twinlift = int((events["TWINLIFT_STATUS"] == "Twinlift").sum())
    total_combo_bukan_twinlift = total_combo - total_twinlift
    total_non_twinlift = total_event - total_twinlift
    pct_twinlift_of_total = (total_twinlift / total_event) if total_event else 0
    pct_non_twinlift_of_total = (total_non_twinlift / total_event) if total_event else 0
    pct_twinlift_of_combo = (total_twinlift / total_combo) if total_combo else 0

    dual_load = int(((out_df["STATUS"] == "Dual Cycle") & (out_df["ACTIVITY"] == "LOAD")).sum())
    dual_disc = int(((out_df["STATUS"] == "Dual Cycle") & (out_df["ACTIVITY"] == "DISC")).sum())
    single_load = int(((out_df["STATUS"] == "Non Dual") & (out_df["ACTIVITY"] == "LOAD")).sum())
    single_disc = int(((out_df["STATUS"] == "Non Dual") & (out_df["ACTIVITY"] == "DISC")).sum())

    container_load = dual_load + single_load
    container_disc = dual_disc + single_disc
    container_total = len(out_df)

    ev = events.copy()
    ev["BULAN"] = ev["START_TS"].dt.to_period("M")
    ev["_is_dual"] = (ev["STATUS"] == "Dual Cycle").astype(int)
    ev["_is_combo"] = (ev["CONTAINER_STATUS"] == "Combo").astype(int)
    ev["_is_twinlift"] = (ev["TWINLIFT_STATUS"] == "Twinlift").astype(int)

    monthly = ev.groupby("BULAN").agg(
        total_event=("STATUS", "count"),
        dual=("_is_dual", "sum"),
        combo=("_is_combo", "sum"),
        twinlift=("_is_twinlift", "sum"),
    )
    monthly["non_dual"] = monthly["total_event"] - monthly["dual"]
    monthly["single"] = monthly["total_event"] - monthly["combo"]
    monthly["combo_bukan_twinlift"] = monthly["combo"] - monthly["twinlift"]
    monthly["non_twinlift"] = monthly["total_event"] - monthly["twinlift"]

    monthly["pct_dual"] = np.where(monthly["total_event"] > 0, monthly["dual"] / monthly["total_event"], 0)
    monthly["pct_non_dual"] = np.where(monthly["total_event"] > 0, monthly["non_dual"] / monthly["total_event"], 0)
    monthly["pct_combo"] = np.where(monthly["total_event"] > 0, monthly["combo"] / monthly["total_event"], 0)
    monthly["pct_single"] = np.where(monthly["total_event"] > 0, monthly["single"] / monthly["total_event"], 0)
    monthly["pct_twinlift"] = np.where(monthly["total_event"] > 0, monthly["twinlift"] / monthly["total_event"], 0)
    monthly["pct_non_twinlift"] = np.where(
        monthly["total_event"] > 0, monthly["non_twinlift"] / monthly["total_event"], 0
    )
    monthly["pct_twinlift_of_combo"] = np.where(
        monthly["combo"] > 0, monthly["twinlift"] / monthly["combo"], 0
    )
    monthly["pct_combo_bukan_twinlift_of_combo"] = np.where(
        monthly["combo"] > 0, monthly["combo_bukan_twinlift"] / monthly["combo"], 0
    )

    monthly = monthly.sort_index()
    monthly.index = monthly.index.astype(str)

    return {
        "total_event": total_event,
        "total_dual": total_dual,
        "total_single": total_single,
        "pct_dual": (total_dual / total_event) if total_event else 0,
        "combo_dual": combo_dual,
        "combo_single": combo_single,
        "single_dual": single_dual,
        "single_single": single_single,
        "total_combo": total_combo,
        "total_twinlift": total_twinlift,
        "total_combo_bukan_twinlift": total_combo_bukan_twinlift,
        "total_non_twinlift": total_non_twinlift,
        "pct_twinlift_of_total": pct_twinlift_of_total,
        "pct_non_twinlift_of_total": pct_non_twinlift_of_total,
        "pct_twinlift_of_combo": pct_twinlift_of_combo,
        "dual_load": dual_load,
        "dual_disc": dual_disc,
        "single_load": single_load,
        "single_disc": single_disc,
        "container_load": container_load,
        "container_disc": container_disc,
        "container_total": container_total,
        "monthly": monthly,
    }


def guess(options, keywords, default_idx=0):
    """Menebak indeks kolom terbaik berdasarkan daftar kata kunci."""
    for kw in keywords:
        for i, c in enumerate(options):
            if kw.lower() in str(c).lower():
                return i
    return default_idx


def proses_analisis_lengkap(
    raw,
    col_map,
    size_eligible,
    ambang_combo,
    ambang_dual,
    ambang_twinlift,
    progress_callback=None,
):
    """
    Fungsi orkestrasi pipeline kalkulasi lengkap dari raw DataFrame sampai summary.
    Mengembalikan (out_df, events, summary).
    """
    if progress_callback:
        progress_callback(12, "Menyiapkan & memvalidasi data...", "Standardisasi kolom data")

    df = siapkan_data(raw, col_map, size_eligible)
    if len(df) == 0:
        return None, None, None

    if progress_callback:
        progress_callback(32, "Menganalisis siklus truk (Combo)...", f"{format_number(len(df))} baris kontainer")

    df_combo = layer1_combo(df, ambang_combo, size_eligible)

    if progress_callback:
        progress_callback(52, "Mendeteksi Twin Lift kontainer...", "Evaluasi pasangan lifting")

    twinlift_status_map, twinlift_gap_map = deteksi_twinlift(df_combo, ambang_twinlift, size_eligible)

    if progress_callback:
        progress_callback(68, "Merekronstruksi event aktivitas...", "Pemetaan pergerakan kontainer")

    events = bentuk_event(df_combo)
    events["TWINLIFT_STATUS"] = events["GROUP_ID"].map(twinlift_status_map)
    events["TWINLIFT_GAP_MENIT"] = events["GROUP_ID"].map(twinlift_gap_map)

    if progress_callback:
        progress_callback(80, "Menghitung rasio Dual Cycle...", f"{format_number(len(events))} event terdeteksi")

    events = layer2_dual(events, ambang_dual)
    events, event_id_map = beri_event_id(events, df_combo)

    if progress_callback:
        progress_callback(92, "Menyusun ringkasan metrik KPI...", "Agregasi produktivitas kapal")

    out_df = gabungkan_hasil(df_combo, events, event_id_map)
    summary = hitung_ringkasan(events, out_df)

    if progress_callback:
        progress_callback(100, "Analisis komputasi selesai!", "Menyiapkan dashboard visualisasi...")

    return out_df, events, summary
