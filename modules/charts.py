"""
Modul Visualisasi & Tema Grafik Glassmorphism
Terminal Teluk Lamong - Pelindo

Menyediakan utilitas styling transparansi glassmorphism maritim untuk Plotly Charts.
"""

def apply_glass_theme(fig, title: str = None, *args, **kwargs):
    """
    Menerapkan layout tema transparent glassmorphism maritim pada objek Plotly Figure
    dengan tipografi Plus Jakarta Sans dan warna kontras tinggi.
    """
    default_margin = dict(t=56, b=30, l=40, r=20)
    if fig.layout.margin:
        for k in ['t', 'b', 'l', 'r']:
            val = getattr(fig.layout.margin, k, None)
            if val is not None:
                default_margin[k] = val
    margin = kwargs.get("margin")
    if margin:
        default_margin.update(margin)

    fig.update_layout(
        separators=",.",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, -apple-system, sans-serif", color="#e2e8f0"),
        title=dict(
            text=title or (fig.layout.title.text if fig.layout.title else ""),
            font=dict(size=14, color="#ffffff", family="Plus Jakarta Sans, sans-serif"),
            y=0.98,
            x=0.01,
            xanchor="left",
            yanchor="top",
        ),
        margin=default_margin,
        legend=dict(
            bgcolor="rgba(13, 22, 38, 0.85)",
            bordercolor="rgba(255, 255, 255, 0.12)",
            borderwidth=1,
            font=dict(size=11, family="Plus Jakarta Sans, sans-serif", color="#e2e8f0"),
        ),
        hoverlabel=dict(
            bgcolor="rgba(11, 19, 32, 0.96)",
            font_size=12,
            font_family="Plus Jakarta Sans, sans-serif",
            font_color="#ffffff",
            bordercolor="rgba(56, 189, 248, 0.5)",
        ),
    )
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.08)",
        zerolinecolor="rgba(255, 255, 255, 0.12)",
        linecolor="rgba(255, 255, 255, 0.18)",
        tickfont=dict(color="#94a3b8"),
        title_font=dict(color="#cbd5e1"),
    )
    fig.update_yaxes(
        gridcolor="rgba(255, 255, 255, 0.08)",
        zerolinecolor="rgba(255, 255, 255, 0.12)",
        linecolor="rgba(255, 255, 255, 0.18)",
        tickfont=dict(color="#94a3b8"),
        title_font=dict(color="#cbd5e1"),
    )
    return fig
