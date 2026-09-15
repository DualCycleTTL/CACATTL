"""
Modul Tampilan, Template HTML & Injeksi Desain
Terminal Teluk Lamong - Pelindo

Menyediakan fungsi untuk memuat template HTML mandiri, menginjeksi stylesheet CSS,
script transisi JavaScript, serta rendering kartu dan komponen grafis.
"""

from pathlib import Path
import base64
import io
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
        if hasattr(st, "html"):
            st.html(f"<style>\n{css_content}\n</style>")
        else:
            st.markdown(f"<style>\n{css_content}\n</style>", unsafe_allow_html=True)


def inject_transition_script(js_filename: str = "transition.js"):
    """Membaca file JavaScript dari assets/ dan menginjeksikannya melalui components.html."""
    js_path = ASSETS_DIR / js_filename
    if js_path.exists():
        js_content = js_path.read_text(encoding="utf-8")
        components.html(f"<script>\n{js_content}\n</script>", height=0, width=0)


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


def render_kpi_card(
    label: str,
    value: str | int | float,
    subtext: str = None,
    badge: str = None,
    variant: str = "blue",
):
    """Merender kartu KPI glassmorphism menggunakan template templates/kpi_card.html."""
    formatted_value = format_number(value)
    subtext_html = f'<div class="kpi-subtext">{subtext}</div>' if subtext else ""
    badge_variant = f"badge-{variant}" if variant in ["emerald", "coral", "purple", "amber", "slate", "blue"] else ""
    badge_html = f'<span class="kpi-badge {badge_variant}">{badge}</span>' if badge else ""

    render_template(
        "kpi_card.html",
        label=label,
        value=formatted_value,
        subtext_html=subtext_html,
        badge_html=badge_html,
        variant=variant,
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


