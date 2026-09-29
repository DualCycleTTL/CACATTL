"""
Modul Tampilan, Template HTML & Injeksi Desain
Terminal Teluk Lamong - Pelindo

Menyediakan fungsi untuk memuat template HTML mandiri, menginjeksi stylesheet CSS,
script transisi JavaScript, serta rendering kartu dan komponen grafis.
"""

from pathlib import Path
import base64
import io
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"


def find_asset_file(candidates: list[str]) -> Path | None:
    """Mencari file aset dari daftar kandidat nama file."""
    for name in candidates:
        p = ASSETS_DIR / name
        if p.exists() and p.is_file():
            return p
    return None


@st.cache_resource
def setup_template_and_asset_watchers():
    """
    Mengaktifkan pemantauan otomatis (live reload) untuk folder templates/ dan assets/.
    Ketika pengguna atau developer mengedit file HTML atau CSS, Streamlit akan otomatis
    melakukan rerun pada browser secara real-time tanpa perlu refresh halaman web.
    """
    try:
        from streamlit.watcher.path_watcher import watch_dir
        from streamlit.runtime import Runtime

        def _on_resource_changed(changed_path: str):
            if Runtime.exists():
                try:
                    rt = Runtime.instance()
                    for s_info in rt._session_mgr.list_active_sessions():
                        s_info.session.request_rerun(s_info.session._client_state)
                except Exception:
                    pass

        watch_dir(str(TEMPLATES_DIR.resolve()), _on_resource_changed)
        watch_dir(str(ASSETS_DIR.resolve()), _on_resource_changed)
        return True
    except Exception:
        return False


# Inisialisasi watcher templates dan assets saat modul dimuat
setup_template_and_asset_watchers()



@st.cache_data(show_spinner=False)
def _get_hero_img_src(path_str: str | None, mtime: float = 0.0) -> str:
    """Mengoptimalkan gambar hero agar cepat dimuat di web tanpa lag ukuran file besar."""
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.exists():
        return ""
    try:
        from PIL import Image

        with Image.open(p) as img:
            max_width = 1920
            if img.width > max_width:
                h = int((max_width / img.width) * img.height)
                img = img.resize((max_width, h), Image.Resampling.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return _img_to_base64_src_cached(path_str, mtime)


@st.cache_data(show_spinner=False)
def _img_to_base64_src_cached(path_str: str, mtime: float = 0.0) -> str:
    p = Path(path_str)
    if not p.exists():
        return ""
    ext = p.suffix.lower()
    if ext == ".webp":
        mime = "image/webp"
    elif ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif ext == ".svg":
        mime = "image/svg+xml"
    else:
        mime = "image/png"
    encoded = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def img_to_base64_src(path: Path | None) -> str:
    if not path:
        return ""
    p = path.resolve()
    if not p.exists():
        return ""
    mtime = p.stat().st_mtime
    return _img_to_base64_src_cached(str(p), mtime)


def render_html(content: str):
    """Merender HTML secara murni menggunakan st.html tanpa distorsi parser Markdown."""
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)


def load_template(_template_name: str, **context) -> str:
    """Memuat file template HTML dari folder templates/ dan melakukan interpolasi variabel."""
    file_path = TEMPLATES_DIR / _template_name
    if not file_path.exists():
        raise FileNotFoundError(f"Template HTML tidak ditemukan: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    for key, val in context.items():
        placeholder = f"{{{{ {key} }}}}"
        placeholder_no_spaces = f"{{{{{key}}}}}"
        val_str = "" if val is None else str(val)
        content = content.replace(placeholder, val_str)
        content = content.replace(placeholder_no_spaces, val_str)
    return content


def render_template(_template_name: str, **context):
    """Memuat template HTML dan langsung merendernya ke Streamlit."""
    html = load_template(_template_name, **context)
    render_html(html)


def inject_css(css_filename: str = "style.css"):
    """Membaca file CSS dari folder assets/ dan menginjeksikannya ke dalam aplikasi."""
    css_path = ASSETS_DIR / css_filename
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
        mtime = int(css_path.stat().st_mtime)
        style_tag = f"<style id=\"caca-custom-style\" data-v=\"{mtime}\">\n{css_content}\n</style>"
        if hasattr(st, "html"):
            st.html(style_tag)
        else:
            st.markdown(style_tag, unsafe_allow_html=True)


def inject_transition_script(js_filename: str = "transition.js"):
    """Membaca file JavaScript dari assets/ dan menginjeksikannya melalui components.html."""
    js_path = ASSETS_DIR / js_filename
    if js_path.exists():
        js_content = js_path.read_text(encoding="utf-8")
        components.html(f"<script>\n{js_content}\n</script>", height=1, width=1)


def render_artistic_hero(hero_path: Path | None, icon_path: Path | None, brand_path: Path | None):
    """Merender komponen hero banner menggunakan template templates/hero.html."""
    hero_mtime = hero_path.stat().st_mtime if hero_path and hero_path.exists() else 0.0
    img_src = _get_hero_img_src(str(hero_path.resolve()), hero_mtime) if hero_path else ""
    icon_src = img_to_base64_src(icon_path)
    brand_src = img_to_base64_src(brand_path)

    caca_logo_html = (
        f'<img src="{icon_src}" style="height:74px;width:auto;display:block;object-fit:contain;background:transparent;filter:drop-shadow(0 4px 14px rgba(0, 0, 0, 0.85)) drop-shadow(0 0 18px rgba(255, 255, 255, 0.25));" alt="CACA Logo" />'
        if icon_src
        else '<span style="font-size:1.85rem;font-weight:900;color:#ffffff;letter-spacing:-0.5px;text-shadow:0 3px 12px rgba(0,0,0,0.85);">CACA</span>'
    )
    pelindo_logo_html = (
        f'<img src="{brand_src}" style="height:52px;width:auto;display:block;object-fit:contain;background:transparent;filter:drop-shadow(0 3px 8px rgba(0, 0, 0, 0.75)) drop-shadow(0 8px 24px rgba(0, 0, 0, 0.55));" alt="Pelindo Logo" />'
        if brand_src
        else '<span style="font-size:1.35rem;font-weight:800;color:#ffffff;text-shadow:0 3px 12px rgba(0,0,0,0.85);">PELINDO</span>'
    )

    bg_style = (
        f"background-image: linear-gradient(180deg, rgba(7, 12, 24, 0.16) 0%, rgba(7, 12, 24, 0.02) 35%, rgba(7, 12, 24, 0.30) 75%, #070c18 100%), url('{img_src}');"
        if img_src
        else "background: #070c18;"
    )

    render_template(
        "hero.html",
        bg_style=bg_style,
        caca_logo_html=caca_logo_html,
        pelindo_logo_html=pelindo_logo_html,
    )


def format_number(val: int | float | str | None) -> str:
    """
    Memformat angka bulat dengan pemisah ribuan titik (format Indonesia/ID),
    contoh: 326070 -> '326.070'.
    """
    if val is None:
        return "0"
    if isinstance(val, (int, float)):
        val_int = int(round(val))
        return f"{val_int:,}".replace(",", ".")
    s = str(val).strip()
    import re
    if re.match(r"^-?\d{1,3}(,\d{3})+$", s):
        return s.replace(",", ".")
    if s.lstrip("-").isdigit():
        return f"{int(s):,}".replace(",", ".")
    return s


def get_tooltip_html(label: str, tooltip: str | None = None, align_right: bool = True) -> str:
    """Menghasilkan markup HTML untuk icon tanda tanya (?) persis seperti icon help bawaan Streamlit."""
    if not tooltip:
        return ""
    align_class = "align-right" if align_right else ""
    return (
        f'<div class="kpi-tooltip-container">'
        f'<span class="kpi-tooltip-trigger" aria-label="Penjelasan {label}" onclick="event.stopPropagation();">'
        f'<span class="kpi-help-icon">?</span>'
        f'</span>'
        f'<div class="kpi-tooltip-bubble {align_class}" role="tooltip">'
        f'<div class="kpi-tooltip-header"><span class="kpi-tooltip-title">{label}</span></div>'
        f'<div class="kpi-tooltip-text">{tooltip}</div>'
        f'</div>'
        f'</div>'
    )


def render_kpi_card(
    label: str,
    value: str | int | float,
    subtext: str = None,
    badge: str = None,
    variant: str = "blue",
    tooltip: str = None,
    align_tooltip_right: bool = False,
    extra_class: str = "",
):
    """Merender kartu KPI glassmorphism menggunakan template templates/kpi_card.html."""
    formatted_value = format_number(value)
    subtext_html = f'<div class="kpi-subtext">{subtext}</div>' if subtext else ""
    badge_variant = f"badge-{variant}" if variant in ["emerald", "coral", "purple", "amber", "slate", "blue"] else ""
    badge_html = f'<span class="kpi-badge {badge_variant}">{badge}</span>' if badge else ""
    tooltip_html = get_tooltip_html(label, tooltip, align_tooltip_right)

    render_template(
        "kpi_card.html",
        label=label,
        value=formatted_value,
        subtext_html=subtext_html,
        badge_html=badge_html,
        variant=variant,
        tooltip_html=tooltip_html,
        extra_class=extra_class,
    )


def render_dual_cycle_kpi_section(summary: dict):
    """
    Merender seluruh komponen KPI untuk Tab Dual Cycle:
    - Default 5 kartu: Total Petikemas, Total Ritase, Dual Cycle, Non Dual, % Dual Cycle.
    - Toggle interaktif murni CSS: Container LOAD & Container DISC muncul saat Total Petikemas diklik.
    - Icon tanda tanya (?) dengan tooltip penjelasan pada setiap kartu.
    """
    pct_dual_val = summary.get("pct_dual", 0) * 100
    render_template(
        "dual_cycle_kpis.html",
        container_total=format_number(summary.get("container_total", 0)),
        total_event=format_number(summary.get("total_event", 0)),
        container_load=format_number(summary.get("container_load", 0)),
        container_disc=format_number(summary.get("container_disc", 0)),
        total_dual=format_number(summary.get("total_dual", 0)),
        total_single=format_number(summary.get("total_single", 0)),
        pct_dual_formatted=f"{pct_dual_val:.1f}%",
    )


def format_file_size(size_bytes: int) -> str:
    """Memformat ukuran byte file ke representasi yang ramah pengguna (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_hybrid_loading_indicator_html(
    filename: str,
    file_size_bytes: int,
    pct: int = 0,
    status_text: str = "Mempersiapkan data...",
    detail_text: str = "",
) -> str:
    """Menghasilkan string HTML untuk komponen hybrid loading indicator."""
    file_size = format_file_size(file_size_bytes)
    pct_clamped = max(0, min(100, int(pct)))
    # SVG 88x88, r=36 -> C = 2 * pi * 36 = 226.19
    stroke_dashoffset = round(226.19 * (1 - pct_clamped / 100.0), 2)

    is_done = pct_clamped >= 100
    done_class = "is-done" if is_done else ""
    stroke_color = "#10b981" if is_done else "#38bdf8"
    track_color = "rgba(16, 185, 129, 0.2)" if is_done else "rgba(56, 189, 248, 0.16)"

    if not detail_text:
        formatted_detail = file_size
    else:
        formatted_detail = f"{file_size} • {detail_text}"

    return load_template(
        "hybrid_loading_indicator.html",
        filename=filename,
        file_size=file_size,
        pct=pct_clamped,
        stroke_dashoffset=stroke_dashoffset,
        status_text=status_text,
        detail_text=formatted_detail,
        done_class=done_class,
        stroke_color=stroke_color,
        track_color=track_color,
    )


def render_hybrid_loading_indicator(
    filename: str,
    file_size_bytes: int,
    pct: int = 0,
    status_text: str = "Mempersiapkan data...",
    detail_text: str = "",
    placeholder=None,
):
    """Merender komponen hybrid loading indicator berbasis progres riil Python."""
    html = get_hybrid_loading_indicator_html(
        filename=filename,
        file_size_bytes=file_size_bytes,
        pct=pct,
        status_text=status_text,
        detail_text=detail_text,
    )
    target = placeholder if placeholder is not None else st
    target.markdown(html, unsafe_allow_html=True)


def prepare_dual_cycle_table(events: pd.DataFrame, out_df: pd.DataFrame) -> pd.DataFrame:
    """
    Menyusun tabel rincian pasangan Dual Cycle (vektorisasi cepat via merge).
    Menghubungkan event DISC dan LOAD pada truk yang sama dengan format:
    Truk | DISC (Kapal, Crane) -> Gap -> LOAD (Kapal, Crane) | Jenis Dual
    """
    if events is None or len(events) == 0:
        return pd.DataFrame()
    ev_dual = events[(events["STATUS"] == "Dual Cycle") & (events["DUAL_PAIR_ID"] > 0)].copy()
    if len(ev_dual) == 0:
        return pd.DataFrame()

    ev_dual["START_TS"] = pd.to_datetime(ev_dual["START_TS"])
    ev_dual["END_TS"] = pd.to_datetime(ev_dual["END_TS"])

    ves_map = {}
    size_map = {}
    if out_df is not None and len(out_df) > 0 and "VES_ID" in out_df.columns:
        ves_map = out_df.groupby("EVENT_ID")["VES_ID"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique())
        ).to_dict()
    if out_df is not None and len(out_df) > 0 and "CTR_SIZE" in out_df.columns:
        size_map = out_df.groupby("EVENT_ID")["CTR_SIZE"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique()) + "ft"
        ).to_dict()

    ev_dual["VES_ID"] = ev_dual["EVENT_ID"].map(ves_map).fillna("-")
    ev_dual["UKURAN_CTR"] = ev_dual["EVENT_ID"].map(size_map).fillna("-")
    ev_dual["CRANE_ID"] = ev_dual["CRANE_ID"].fillna("-").astype(str)

    disc = ev_dual[ev_dual["ACTIVITY"] == "DISC"].drop_duplicates(subset=["DUAL_PAIR_ID"])
    load = ev_dual[ev_dual["ACTIVITY"] == "LOAD"].drop_duplicates(subset=["DUAL_PAIR_ID"])

    merged = pd.merge(disc, load, on="DUAL_PAIR_ID", suffixes=("_DISC", "_LOAD"))
    if len(merged) == 0:
        return pd.DataFrame()

    merged["TRUK_ID"] = merged["CAR_CHE_ID_DISC"].fillna(merged["CAR_CHE_ID_LOAD"]).astype(str)
    merged["TRUK_ID"] = merged["TRUK_ID"].str.replace(r"\.0$", "", regex=True)

    disc_first = merged["START_TS_DISC"] <= merged["START_TS_LOAD"]
    gap_forward = (merged["START_TS_LOAD"] - merged["END_TS_DISC"]).dt.total_seconds() / 60.0
    gap_backward = (merged["START_TS_DISC"] - merged["END_TS_LOAD"]).dt.total_seconds() / 60.0

    merged["URUTAN"] = np.where(disc_first, "DISC ➔ LOAD", "LOAD ➔ DISC")
    merged["GAP_MENIT"] = np.where(disc_first, gap_forward, gap_backward)
    merged["GAP_MENIT"] = np.maximum(0.0, merged["GAP_MENIT"]).round(1)

    merged["KATEGORI"] = np.where(merged["VES_ID_DISC"] == merged["VES_ID_LOAD"], "Murni", "Campuran")

    merged["WAKTU_DISC"] = (
        merged["START_TS_DISC"].dt.strftime("%d/%m/%y %H:%M") + " - " + merged["END_TS_DISC"].dt.strftime("%H:%M")
    )
    merged["WAKTU_LOAD"] = (
        merged["START_TS_LOAD"].dt.strftime("%d/%m/%y %H:%M") + " - " + merged["END_TS_LOAD"].dt.strftime("%H:%M")
    )

    merged["RINGKASAN_PASANGAN"] = (
        merged["TRUK_ID"]
        + " | DISC ("
        + merged["VES_ID_DISC"]
        + ", "
        + merged["CRANE_ID_DISC"]
        + ") | ➔ "
        + merged["GAP_MENIT"].astype(str)
        + "mnt ➔ | LOAD ("
        + merged["VES_ID_LOAD"]
        + ", "
        + merged["CRANE_ID_LOAD"]
        + ") | "
        + merged["KATEGORI"]
    )

    merged = merged.sort_values(by=["START_TS_DISC", "TRUK_ID"]).reset_index(drop=True)

    res = pd.DataFrame(
        {
            "Truk": merged["TRUK_ID"],
            "Format Rincian": merged["RINGKASAN_PASANGAN"],
            "Urutan": merged["URUTAN"],
            "Event DISC": merged["EVENT_ID_DISC"],
            "Kapal DISC": merged["VES_ID_DISC"],
            "Crane DISC": merged["CRANE_ID_DISC"],
            "Waktu DISC": merged["WAKTU_DISC"],
            "Tipe DISC": merged["CONTAINER_STATUS_DISC"],
            "Event LOAD": merged["EVENT_ID_LOAD"],
            "Kapal LOAD": merged["VES_ID_LOAD"],
            "Crane LOAD": merged["CRANE_ID_LOAD"],
            "Waktu LOAD": merged["WAKTU_LOAD"],
            "Tipe LOAD": merged["CONTAINER_STATUS_LOAD"],
            "Gap (Menit)": merged["GAP_MENIT"],
            "Jenis": merged["KATEGORI"],
        }
    )
    return res


def prepare_non_dual_table(events: pd.DataFrame, out_df: pd.DataFrame) -> pd.DataFrame:
    """
    Menyusun tabel rincian aktivitas Non Dual (single cycle ritase truk).
    Format: Truk | Aktivitas (Kapal, Crane) | Durasi | Tipe Kontainer
    """
    if events is None or len(events) == 0:
        return pd.DataFrame()
    ev_non = events[events["STATUS"] == "Non Dual"].copy()
    if len(ev_non) == 0:
        return pd.DataFrame()

    ev_non["START_TS"] = pd.to_datetime(ev_non["START_TS"])
    ev_non["END_TS"] = pd.to_datetime(ev_non["END_TS"])

    ves_map = {}
    size_map = {}
    if out_df is not None and len(out_df) > 0 and "VES_ID" in out_df.columns:
        ves_map = out_df.groupby("EVENT_ID")["VES_ID"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique())
        ).to_dict()
    if out_df is not None and len(out_df) > 0 and "CTR_SIZE" in out_df.columns:
        size_map = out_df.groupby("EVENT_ID")["CTR_SIZE"].apply(
            lambda s: ", ".join(s.dropna().astype(str).unique()) + "ft"
        ).to_dict()

    ev_non["VES_ID"] = ev_non["EVENT_ID"].map(ves_map).fillna("-")
    ev_non["UKURAN_CTR"] = ev_non["EVENT_ID"].map(size_map).fillna("-")
    ev_non["CRANE_ID"] = ev_non["CRANE_ID"].fillna("-").astype(str)

    ev_non["TRUK_ID"] = ev_non["CAR_CHE_ID"].astype(str).str.replace(r"\.0$", "", regex=True)
    ev_non["DURASI_MENIT"] = ((ev_non["END_TS"] - ev_non["START_TS"]).dt.total_seconds() / 60.0).round(1)
    ev_non["DURASI_MENIT"] = np.maximum(0.0, ev_non["DURASI_MENIT"])

    ev_non["WAKTU_MULAI"] = ev_non["START_TS"].dt.strftime("%d/%m/%y %H:%M:%S")
    ev_non["WAKTU_SELESAI"] = ev_non["END_TS"].dt.strftime("%d/%m/%y %H:%M:%S")

    ev_non["RINGKASAN_EVENT"] = (
        ev_non["TRUK_ID"]
        + " | "
        + ev_non["ACTIVITY"]
        + " ("
        + ev_non["VES_ID"]
        + ", "
        + ev_non["CRANE_ID"]
        + ") | Durasi: "
        + ev_non["DURASI_MENIT"].astype(str)
        + "mnt | "
        + ev_non["CONTAINER_STATUS"]
    )

    ev_non = ev_non.sort_values(by=["START_TS", "TRUK_ID"]).reset_index(drop=True)

    res = pd.DataFrame(
        {
            "Truk": ev_non["TRUK_ID"],
            "Format Rincian": ev_non["RINGKASAN_EVENT"],
            "Event ID": ev_non["EVENT_ID"],
            "Aktivitas": ev_non["ACTIVITY"],
            "Kapal": ev_non["VES_ID"],
            "Crane": ev_non["CRANE_ID"],
            "Waktu Mulai": ev_non["WAKTU_MULAI"],
            "Waktu Selesai": ev_non["WAKTU_SELESAI"],
            "Durasi (Menit)": ev_non["DURASI_MENIT"],
            "Tipe Kontainer": ev_non["CONTAINER_STATUS"],
            "Status": "Non Dual (Single Cycle)",
        }
    )
    return res


@st.dialog("Rincian Aktivitas Dual-Cycle", width="large")
def _show_dual_cycle_dialog(events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    df_data = prepare_dual_cycle_table(events, out_df)
    if len(df_data) == 0:
        st.info("Tidak ada data pasangan Dual Cycle yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_dual", type="secondary"):
            st.rerun()
        return

    # Mini KPI Summary Row
    total_pairs = len(df_data)
    total_events = total_pairs * 2
    total_trucks = df_data["Truk"].nunique()
    avg_gap = df_data["Gap (Menit)"].mean()
    count_murni = int((df_data["Jenis"] == "Murni").sum())
    count_campuran = int((df_data["Jenis"] == "Campuran").sum())

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        st.metric("Total Pasangan", f"{format_number(total_pairs)} psg")
    with mk2:
        st.metric("Truk Terlibat", f"{format_number(total_trucks)} Truk")
    with mk3:
        st.metric("Rata-rata Gap", f"{avg_gap:.1f} menit")
    with mk4:
        st.metric("Dual Murni", f"{format_number(count_murni)} psg")

    # Filter Pencarian & Kategori
    fc1, fc2, fc3, fc4 = st.columns([1.8, 1.1, 1.1, 1.1])
    with fc1:
        search_txt = st.text_input(
            "🔍 Cari Truk / Kapal / Crane:",
            placeholder="Ketik ID Truk / Kapal / Crane",
            key="filter_dual_search",
        ).strip().lower()
    with fc2:
        kategori_filter = st.selectbox(
            "Jenis Pasangan:",
            ["Semua Kategori", "Hanya Murni", "Hanya Campuran"],
            key="filter_dual_kategori_sel",
        )
    with fc3:
        urutan_filter = st.selectbox(
            "Urutan Siklus:",
            ["Semua Urutan", "DISC ➔ LOAD", "LOAD ➔ DISC"],
            key="filter_dual_urutan_sel",
        )
    with fc4:
        mode_kolom = st.selectbox(
            "Tampilan Kolom:",
            ["Semua Kolom", "Rincian Operasional", "Format Ringkas"],
            key="filter_dual_mode_kolom",
        )

    # Terapkan Filtering
    filtered_df = df_data.copy()
    if search_txt:
        mask = (
            filtered_df["Truk"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Kapal DISC"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Kapal LOAD"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Crane DISC"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Crane LOAD"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Format Rincian"].str.lower().str.contains(search_txt, na=False)
        )
        filtered_df = filtered_df[mask]

    if kategori_filter == "Hanya Murni":
        filtered_df = filtered_df[filtered_df["Jenis"] == "Murni"]
    elif kategori_filter == "Hanya Campuran":
        filtered_df = filtered_df[filtered_df["Jenis"] == "Campuran"]

    if urutan_filter != "Semua Urutan":
        filtered_df = filtered_df[filtered_df["Urutan"] == urutan_filter]

    if mode_kolom == "Rincian Operasional":
        filtered_df = filtered_df.drop(columns=["Format Rincian"])
    elif mode_kolom == "Format Ringkas":
        filtered_df = filtered_df[["Truk", "Format Rincian", "Urutan", "Gap (Menit)", "Jenis"]]

    # Dataframe Interaktif dengan Column Config Lengkap
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "Truk": st.column_config.TextColumn("No Truk", width="small"),
            "Format Rincian": st.column_config.TextColumn("Ringkasan Siklus", width="medium"),
            "Urutan": st.column_config.TextColumn("Urutan", width="small"),
            "Event DISC": st.column_config.NumberColumn("Evt DISC", format="%d", width="small"),
            "Kapal DISC": st.column_config.TextColumn("Kapal DISC", width="small"),
            "Crane DISC": st.column_config.TextColumn("Crane DISC", width="small"),
            "Waktu DISC": st.column_config.TextColumn("Waktu DISC", width="small"),
            "Tipe DISC": st.column_config.TextColumn("Tipe DISC", width="small"),
            "Event LOAD": st.column_config.NumberColumn("Evt LOAD", format="%d", width="small"),
            "Kapal LOAD": st.column_config.TextColumn("Kapal LOAD", width="small"),
            "Crane LOAD": st.column_config.TextColumn("Crane LOAD", width="small"),
            "Waktu LOAD": st.column_config.TextColumn("Waktu LOAD", width="small"),
            "Tipe LOAD": st.column_config.TextColumn("Tipe LOAD", width="small"),
            "Gap (Menit)": st.column_config.NumberColumn("Gap (Mnt)", format="%.1f mnt", width="small"),
            "Jenis": st.column_config.TextColumn("Jenis", width="small"),
        },
    )

    st.caption(f"Menampilkan **{len(filtered_df):,}** dari total **{len(df_data):,}** pasangan Dual Cycle.")

@st.dialog("Rincian Aktivitas Non-Dual", width="large")
def _show_non_dual_dialog(events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    df_data = prepare_non_dual_table(events, out_df)
    if len(df_data) == 0:
        st.info("Tidak ada data Non Dual yang ditemukan pada dataset ini.")
        if st.button("Tutup", key="btn_close_empty_non", type="secondary"):
            st.rerun()
        return

    # Mini KPI Summary Row
    total_events = len(df_data)
    total_trucks = df_data["Truk"].nunique()
    disc_count = int((df_data["Aktivitas"] == "DISC").sum())
    load_count = int((df_data["Aktivitas"] == "LOAD").sum())
    avg_dur = df_data["Durasi (Menit)"].mean()

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        st.metric("Total Event Non Dual", f"{format_number(total_events)} evt")
    with mk2:
        st.metric("Truk Terlibat", f"{format_number(total_trucks)} Truk")
    with mk3:
        st.metric("Bongkar (DISC)", f"{format_number(disc_count)} evt", f"{load_count} LOAD")
    with mk4:
        st.metric("Rata-rata Durasi", f"{avg_dur:.1f} mnt")

    # Filter Pencarian & Aktivitas
    fc1, fc2, fc3 = st.columns([1.8, 1.1, 1.1])
    with fc1:
        search_txt = st.text_input(
            "🔍 Cari Truk / Kapal / Crane:",
            placeholder="Ketik nomor truk (cth: 117) atau nama kapal...",
            key="filter_non_search",
        ).strip().lower()
    with fc2:
        act_filter = st.selectbox(
            "Filter Aktivitas:",
            ["Semua Aktivitas", "Hanya DISC (Bongkar)", "Hanya LOAD (Muat)"],
            key="filter_non_act_sel",
        )
    with fc3:
        mode_kolom_non = st.selectbox(
            "Tampilan Kolom:",
            ["Semua Kolom", "Rincian Operasional", "Format Ringkas"],
            key="filter_non_mode_kolom",
        )

    # Terapkan Filtering
    filtered_df = df_data.copy()
    if search_txt:
        mask = (
            filtered_df["Truk"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Kapal"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Crane"].str.lower().str.contains(search_txt, na=False)
            | filtered_df["Format Rincian"].str.lower().str.contains(search_txt, na=False)
        )
        filtered_df = filtered_df[mask]

    if act_filter == "Hanya DISC (Bongkar)":
        filtered_df = filtered_df[filtered_df["Aktivitas"] == "DISC"]
    elif act_filter == "Hanya LOAD (Muat)":
        filtered_df = filtered_df[filtered_df["Aktivitas"] == "LOAD"]

    if mode_kolom_non == "Rincian Operasional":
        filtered_df = filtered_df.drop(columns=["Format Rincian"])
    elif mode_kolom_non == "Format Ringkas":
        filtered_df = filtered_df[["Truk", "Format Rincian", "Aktivitas", "Durasi (Menit)", "Status"]]

    # Dataframe Interaktif
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config={
            "Truk": st.column_config.TextColumn("No Truk", width="small"),
            "Format Rincian": st.column_config.TextColumn("Ringkasan Aktivitas", width="medium"),
            "Event ID": st.column_config.NumberColumn("Event ID", format="%d", width="small"),
            "Aktivitas": st.column_config.TextColumn("Aktivitas", width="small"),
            "Kapal": st.column_config.TextColumn("Kapal", width="small"),
            "Crane": st.column_config.TextColumn("Crane", width="small"),
            "Waktu Mulai": st.column_config.TextColumn("Waktu Mulai", width="small"),
            "Waktu Selesai": st.column_config.TextColumn("Waktu Selesai", width="small"),
            "Durasi (Menit)": st.column_config.NumberColumn("Durasi (Mnt)", format="%.1f mnt", width="small"),
            "Tipe Kontainer": st.column_config.TextColumn("Tipe Kontainer", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )

    st.caption(f"Menampilkan **{len(filtered_df):,}** dari total **{len(df_data):,}** event Non Dual.")


def show_activity_detail_dialog(status: str, events: pd.DataFrame, out_df: pd.DataFrame, summary: dict = None):
    """
    Menampilkan modal pop-up interaktif rincian aktivitas operasional
    saat irisan Donut Chart ('Dual Cycle' atau 'Non Dual') diklik.
    Menyediakan tabel interaktif, format ringkasan truk, filter pencarian,
    serta tombol unduh CSV.
    """
    if status == "Dual Cycle":
        _show_dual_cycle_dialog(events, out_df, summary)
    else:
        _show_non_dual_dialog(events, out_df, summary)



