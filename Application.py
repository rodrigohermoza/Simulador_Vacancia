import streamlit as st
import numpy as np

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Simulador de Vacancia Presidencial – Perú 2026",
    page_icon=None,
    layout="wide",
)

# ─────────────────────────────────────────────
#  DISTRIBUCIÓN DEL CONGRESO
# ─────────────────────────────────────────────
PARTIES = [
    {"name": "Fuerza Popular",     "diputados": 41, "senadores": 22},
    {"name": "Juntos por el Perú", "diputados": 32, "senadores": 14},
    {"name": "Buen Gobierno",      "diputados": 18, "senadores":  7},
    {"name": "Renovación Popular", "diputados": 15, "senadores":  8},
    {"name": "OBRAS",              "diputados": 14, "senadores":  5},
    {"name": "Ahora Nación",       "diputados": 10, "senadores":  4},
]

TOTAL_DIPUTADOS = 130
TOTAL_SENADORES = 60
UMBRAL_DIPUTADOS = 52          # 40 % de 130
UMBRAL_SENADORES = 40          # 2/3 de 60

BASE_AMISTAD = {
    "Keiko Fujimori": {
        "Fuerza Popular":      0.85,
        "Renovación Popular":  0.30,
        "OBRAS":               0.00,
        "Buen Gobierno":      -0.20,
        "Ahora Nación":       -0.30,
        "Juntos por el Perú": -0.70,
    },
    "Roberto Sánchez": {
        "Juntos por el Perú":  0.75,
        "Buen Gobierno":       0.40,
        "Ahora Nación":        0.10,
        "OBRAS":              -0.10,
        "Renovación Popular": -0.40,
        "Fuerza Popular":     -0.75,
    },
}

PARTY_COLORS = {
    "Fuerza Popular":      "#f97316",
"Juntos por el Perú":  "#2e8b57",
"Buen Gobierno":       "#ffcc00",
"Renovación Popular":  "#87ceeb",
"OBRAS":               "#006400",
"Ahora Nación":        "#b22222",
}

# ─────────────────────────────────────────────
#  HELPER: SVG HISTOGRAMA
# ─────────────────────────────────────────────
def make_histogram_svg(hist, bins, umbral, total, cam_label, group=2):
    bars = []
    max_h = max(hist) if max(hist) > 0 else 1
    for count, b in zip(hist, bins):
        if int(b) % group == 0:
            bars.append({"b": int(b), "h": count / max_h * 100, "above": int(b) >= umbral})

    BAR_W = 680 // max(len(bars), 1)
    BAR_W = max(4, min(BAR_W, 22))
    SVG_W = 10 + len(bars) * (BAR_W + 2) + 40
    SVG_H = 260

    rects = []
    labels = []
    umbral_x = None

    for i, bar in enumerate(bars):
        x = 10 + i * (BAR_W + 2)
        bar_h = bar["h"] * 1.7
        y = 205 - bar_h
        fill = "#ef4444" if bar["above"] else "#475569"
        rects.append(
            f'<rect x="{x}" y="{y:.1f}" width="{BAR_W}" '
            f'height="{bar_h:.1f}" fill="{fill}" rx="2" opacity="0.85"/>'
        )
        if bar["b"] % (5 * group) == 0:
            labels.append(
                f'<text x="{x + BAR_W//2}" y="222" text-anchor="middle" '
                f'fill="#94a3b8" font-size="9">{bar["b"]}</text>'
            )
        if umbral_x is None and bar["b"] >= umbral:
            umbral_x = x

    svg_parts = [
        f'<svg viewBox="0 0 {max(SVG_W, 400)} {SVG_H}" '
        f'xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:820px;">',
    ]
    svg_parts.extend(rects)
    svg_parts.extend(labels)

    if umbral_x is not None:
        svg_parts.append(
            f'<line x1="{umbral_x}" y1="10" x2="{umbral_x}" y2="207" '
            f'stroke="#f87171" stroke-width="2" stroke-dasharray="5,3"/>'
        )
        svg_parts.append(
            f'<text x="{umbral_x + 4}" y="20" fill="#f87171" font-size="10" font-weight="700">'
            f'Umbral {umbral}</text>'
        )

    svg_parts.append(
        f'<text x="{max(SVG_W, 400)//2}" y="{SVG_H - 4}" text-anchor="middle" '
        f'fill="#64748b" font-size="9">'
        f'Votos a favor de la vacancia ({cam_label}) — barras agrupadas de {group} en {group}'
        f'</text>'
    )
    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


# ─────────────────────────────────────────────
#  CSS PERSONALIZADO
# ─────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .hero {
    background: linear-gradient(135deg, #dc2626 0%, #7f1d1d 50%, #1e1b4b 100%);
    border-radius: 16px; padding: 2.5rem 2rem;
    margin-bottom: 1.5rem; text-align: center;
    box-shadow: 0 8px 32px rgba(220,38,38,0.25);
  }
  .hero h1 { font-size: 2rem; font-weight: 800; color: #fff; margin: 0; line-height: 1.3; }
  .hero p  { color: #fca5a5; font-size: 0.9rem; margin-top: 0.5rem; }

  .metric-card {
    background: #1e293b; border-radius: 12px;
    padding: 1.2rem 1rem; text-align: center;
    border: 1px solid #334155;
  }
  .metric-card .val { font-size: 2.4rem; font-weight: 800; color: #f1f5f9; }
  .metric-card .lbl { color: #94a3b8; font-size: 0.78rem; margin-top: 0.25rem; }

  .result-box { border-radius: 14px; padding: 1.5rem 2rem; text-align: center; margin-top: 1rem; }
  .result-high   { background: linear-gradient(135deg,#dc2626,#7f1d1d); }
  .result-medium { background: linear-gradient(135deg,#d97706,#78350f); }
  .result-low    { background: linear-gradient(135deg,#059669,#064e3b); }
  .result-box .pct  { font-size: 4rem; font-weight: 900; color: #fff; }
  .result-box .desc { color: #fde68a; font-size: 0.95rem; margin-top: 0.5rem; }

  .party-bar-bg {
    background: #1e293b; border-radius: 8px;
    padding: 0.6rem 0.9rem; margin-bottom: 0.4rem;
  }
  .info-box {
    background: #0f172a; border: 1px solid #334155;
    border-radius: 10px; padding: 0.9rem 1.1rem;
    color: #94a3b8; font-size: 0.82rem; line-height: 1.6;
  }
  .tag { display: inline-block; border-radius: 6px; padding: 0.1rem 0.55rem; font-size: 0.73rem; font-weight: 700; }
  .tag-favor   { background: #dc2626; color: #fff; }
  .tag-contra  { background: #16a34a; color: #fff; }
  .tag-neutral { background: #475569; color: #fff; }

  .stButton>button { border-radius: 10px; font-weight: 600; transition: transform .15s; }
  .stButton>button:hover { transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  HERO HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>Simulador de Vacancia Presidencial</h1>
  <p>Perú 2026 &nbsp;·&nbsp; La firma del acta ya ocurrió &nbsp;·&nbsp; Proceso en dos etapas: Cámara de Diputados → Cámara de Senadores</p>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════
#  SIDEBAR – CONTROLES
# ════════════════════════════════════════════
with st.sidebar:
    st.markdown("## Parámetros de simulación")

    # ── Candidato ──────────────────────────
    st.markdown("### Candidato")
    candidato = st.radio(
        "Candidato:",
        ["Keiko Fujimori", "Roberto Sánchez"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown(
        f'<div class="info-box">Valores de amistad inicializados según afinidad histórica de '
        f'cada partido con <b>{candidato}</b>.</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Modo de votación ───────────────────
    st.markdown("### Modo de votación")
    modo = st.radio(
        "Modo:",
        ["Voto por bloque", "Probabilidad individual"],
        help=(
            "**Bloque**: todo el partido vota igual en cada simulación.\n\n"
            "**Individual**: cada congresista tiene su propia moneda Bernoulli."
        ),
    )
    st.divider()

    # ── Amistad por partido ────────────────
    st.markdown("### Índice de amistad por partido")
    st.caption("−1 = siempre votan POR vacar  |  +1 = nunca votan POR vacar")

    base = BASE_AMISTAD[candidato]
    partido_amistad = {}
    for p in PARTIES:
        nombre = p["name"]
        raw = base[nombre]
        val = st.slider(
            nombre,
            min_value=-1.0, max_value=1.0,
            value=float(np.clip(raw, -1.0, 1.0)),
            step=0.05, format="%.2f",
            key=f"sl_{nombre}_{candidato}",
            help=f"Valor base histórico: {raw:+.2f}",
        )
        partido_amistad[nombre] = float(val)

    st.divider()

    # ── Iteraciones ────────────────────────
    st.markdown("### Número de simulaciones")
    iteraciones = st.number_input(
        "Número de iteraciones",
        min_value=1000, max_value=500_000,
        value=10_000, step=1000,
        help="5 000–10 000 es muy rápido. Hasta 100 000 es tolerable.",
    )
    st.divider()

    run = st.button("Ejecutar simulación", use_container_width=True, type="primary")

# ════════════════════════════════════════════
#  MAIN PANEL
# ════════════════════════════════════════════

# ── Distribución del congreso + umbrales ──
col_info, col_umbral = st.columns([3, 2])

with col_info:
    st.markdown("### Distribución del Congreso")
    hdr = st.columns([3, 1, 1, 2])
    hdr[0].markdown("**Partido**")
    hdr[1].markdown("**Diputados**")
    hdr[2].markdown("**Senadores**")
    hdr[3].markdown("**Amistad final**")

    for p in PARTIES:
        nombre = p["name"]
        ami = partido_amistad[nombre]
        color = PARTY_COLORS[nombre]
        if ami < -0.25:
            tag = '<span class="tag tag-favor">Favorece vacar</span>'
        elif ami > 0.25:
            tag = '<span class="tag tag-contra">Contra la vacancia</span>'
        else:
            tag = '<span class="tag tag-neutral">Indeciso</span>'

        rc = st.columns([3, 1, 1, 2])
        rc[0].markdown(
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{color};'
            f'display:inline-block;"></span><b>{nombre}</b></div>',
            unsafe_allow_html=True,
        )
        rc[1].markdown(f"`{p['diputados']}`")
        rc[2].markdown(f"`{p['senadores']}`")
        rc[3].markdown(f"{tag} `{ami:+.2f}`", unsafe_allow_html=True)

    st.markdown(
        f'<div class="info-box" style="margin-top:0.5rem">'
        f'Total: <b>{TOTAL_DIPUTADOS} diputados</b> · <b>{TOTAL_SENADORES} senadores</b>'
        f'</div>',
        unsafe_allow_html=True,
    )

with col_umbral:
    st.markdown("### Umbrales de vacancia")
    st.markdown("""
    <div class="info-box">
      <b>Etapa 1 – Diputados</b><br>
      Mínimo <b>52 votos</b> a favor (40 % de 130)<br><br>
      <b>Etapa 2 – Senadores</b><br>
      Mínimo <b>40 votos</b> a favor (⅔ de 60)<br><br>
      <i>Si Diputados no alcanza el umbral, el proceso termina (fracaso).</i>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Índice de amistad")
    st.markdown("""
    <div class="info-box">
      <b>−1.0</b> → el partido vota SIEMPRE por vacar<br>
      <b>&nbsp;0.0</b> → 50 % de probabilidad de vacar<br>
      <b>+1.0</b> → el partido NUNCA vota por vacar<br><br>
      P(voto a favor de vacar) = (1 − amistad) / 2
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────
#  SIMULACIÓN
# ─────────────────────────────────────────────
if run:
    N = int(iteraciones)
    modo_bloque = (modo == "Voto por bloque")

    with st.spinner(f"Ejecutando {N:,} simulaciones con NumPy…"):
        d_counts = np.array([p["diputados"]  for p in PARTIES], dtype=np.int32)
        s_counts = np.array([p["senadores"]  for p in PARTIES], dtype=np.int32)
        amistad  = np.array([partido_amistad[p["name"]] for p in PARTIES])

        # p(voto a favor de vacar): amistad=-1 → p=1, amistad=+1 → p=0
        p_favor = (1.0 - amistad) / 2.0

        if modo_bloque:
            # Cada partido lanza UNA moneda por simulación
            rnd_d = np.random.random((N, len(PARTIES)))
            rnd_s = np.random.random((N, len(PARTIES)))
            voto_d = (rnd_d < p_favor[np.newaxis, :]).astype(np.int32)
            voto_s = (rnd_s < p_favor[np.newaxis, :]).astype(np.int32)
            total_d = (voto_d * d_counts[np.newaxis, :]).sum(axis=1)
            total_s = (voto_s * s_counts[np.newaxis, :]).sum(axis=1)
        else:
            # Cada congresista lanza su propia moneda
            p_d = np.repeat(p_favor, d_counts)   # (130,)
            p_s = np.repeat(p_favor, s_counts)   # (60,)
            rnd_d = np.random.random((N, TOTAL_DIPUTADOS))
            rnd_s = np.random.random((N, TOTAL_SENADORES))
            total_d = (rnd_d < p_d[np.newaxis, :]).sum(axis=1)
            total_s = (rnd_s < p_s[np.newaxis, :]).sum(axis=1)

        paso1_ok = total_d >= UMBRAL_DIPUTADOS
        paso2_ok = paso1_ok & (total_s >= UMBRAL_SENADORES)

        n_paso1  = int(paso1_ok.sum())
        n_paso2  = int(paso2_ok.sum())
        pct_paso1 = 100.0 * n_paso1 / N
        pct_paso2 = 100.0 * n_paso2 / N
        avg_d = float(total_d.mean())
        avg_s = float(total_s.mean())

        hist_d, bins_d = np.histogram(total_d, bins=range(0, TOTAL_DIPUTADOS + 2))
        hist_s, bins_s = np.histogram(total_s, bins=range(0, TOTAL_SENADORES + 2))

    # ── Título de resultados ───────────────
    st.markdown(f"## Resultados para **{candidato}**")

    # ── Tarjetas métricas ──────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="val">{N:,}</div>'
            f'<div class="lbl">Simulaciones ejecutadas</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="val" style="color:#f59e0b">{n_paso1:,}</div>'
            f'<div class="lbl">Aprobadas en Diputados<br>({pct_paso1:.1f} %)</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="val" style="color:#ef4444">{n_paso2:,}</div>'
            f'<div class="lbl">Vacancia exitosa<br>(pasaron Senado)</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="val">{avg_d:.1f} / {avg_s:.1f}</div>'
            f'<div class="lbl">Votos promedio<br>Diputados / Senadores</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Caja de resultado principal ────────
    if pct_paso2 >= 60:
        cls, etiqueta = "result-high",   "Alta probabilidad de vacancia"
    elif pct_paso2 >= 30:
        cls, etiqueta = "result-medium", "Probabilidad moderada de vacancia"
    else:
        cls, etiqueta = "result-low",    "Baja probabilidad de vacancia"

    st.markdown(
        f'<div class="result-box {cls}">'
        f'<div class="pct">{pct_paso2:.1f} %</div>'
        f'<div class="desc">{etiqueta}</div>'
        f'<div style="color:#e2e8f0;font-size:0.85rem;margin-top:0.5rem;">'
        f'Probabilidad de que {candidato} sea vacado · {N:,} iteraciones · '
        f'Modo: {modo}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Barras de etapa ────────────────────
    st.markdown("### Detalle por etapa")
    ec1, ec2 = st.columns(2)

    def etapa_html(label, avg, umbral, total, pct_superado):
        pct_barra = min(avg / total * 100, 100)
        color = "#ef4444" if avg >= umbral else "#64748b"
        return (
            f"<b>{label}</b><br>"
            f"Umbral: {umbral} votos · Promedio simulado: {avg:.1f}<br>"
            f'<div style="background:#1e293b;border-radius:8px;height:28px;overflow:hidden;margin:6px 0;">'
            f'<div style="background:{color};width:{pct_barra:.1f}%;height:100%;'
            f'display:flex;align-items:center;padding-left:8px;color:#fff;'
            f'font-size:0.8rem;font-weight:700;">{avg:.1f} votos ({pct_barra:.1f}%)</div></div>'
            f'<span style="color:#94a3b8;font-size:0.78rem;">'
            f'Umbral: {umbral}/{total} ({umbral/total*100:.0f}%) · '
            f'Superado en <b>{pct_superado:.1f}%</b> de las simulaciones</span>'
        )

    with ec1:
        st.markdown(
            etapa_html("Etapa 1 – Cámara de Diputados",
                       avg_d, UMBRAL_DIPUTADOS, TOTAL_DIPUTADOS, pct_paso1),
            unsafe_allow_html=True,
        )
    with ec2:
        st.markdown(
            etapa_html("Etapa 2 – Cámara de Senadores",
                       avg_s, UMBRAL_SENADORES, TOTAL_SENADORES, pct_paso2),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Histogramas ────────────────────────
    st.markdown("### Distribución de votos simulados")
    tab1, tab2 = st.tabs(["Diputados", "Senadores"])

    with tab1:
        st.markdown(f"Umbral: **{UMBRAL_DIPUTADOS} votos** (línea roja punteada)")
        svg_d = make_histogram_svg(
            hist_d, bins_d, UMBRAL_DIPUTADOS, TOTAL_DIPUTADOS, "Diputados", group=3
        )
        st.markdown(
            f'<div style="overflow-x:auto;padding:0.5rem 0;">{svg_d}</div>',
            unsafe_allow_html=True,
        )

    with tab2:
        st.markdown(f"Umbral: **{UMBRAL_SENADORES} votos** (línea roja punteada)")
        svg_s = make_histogram_svg(
            hist_s, bins_s, UMBRAL_SENADORES, TOTAL_SENADORES, "Senadores", group=2
        )
        st.markdown(
            f'<div style="overflow-x:auto;padding:0.5rem 0;">{svg_s}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabla de partidos ──────────────────
    st.markdown("### Probabilidad de voto por partido")
    for p in PARTIES:
        nombre = p["name"]
        ami = partido_amistad[nombre]
        p_vac = (1 - ami) / 2
        color = PARTY_COLORS[nombre]
        pct_bar = int(p_vac * 100)
        st.markdown(
            f'<div class="party-bar-bg">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            f'<span style="color:#f1f5f9;font-weight:600;">'
            f'<span style="color:{color}">●</span> {nombre}</span>'
            f'<span style="color:#94a3b8;font-size:0.8rem;">'
            f'{p["diputados"]} Dip · {p["senadores"]} Sen'
            f'&nbsp;|&nbsp; Amistad: <b>{ami:+.2f}</b>'
            f'&nbsp;|&nbsp; P(vacar): <b>{p_vac*100:.0f}%</b></span></div>'
            f'<div style="background:#334155;border-radius:4px;height:8px;">'
            f'<div style="background:{color};width:{pct_bar}%;height:100%;border-radius:4px;"></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
      <b>Nota metodológica:</b> Este simulador es una herramienta de análisis exploratorio basada
      en supuestos simplificados. Los valores de amistad son estimaciones ilustrativas y los resultados
      <i>no constituyen una predicción</i>. Ajusta los sliders según la información política más reciente.
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="info-box" style="text-align:center;padding:2.5rem;">
      <b>Configure los parámetros en el panel izquierdo y presione "Ejecutar simulación".</b><br><br>
      La simulación usa operaciones vectorizadas con <b>NumPy</b>:
      10 000 iteraciones se completan en milisegundos.
    </div>
    """, unsafe_allow_html=True)