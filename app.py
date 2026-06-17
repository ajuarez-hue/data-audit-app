######### APP HFC ################################################################
# 0. IMPORTACIONES Y CONFIGURACIÓN INICIAL
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import io
import os
import re
import plotly.graph_objects as go

# ── Ruta al logo
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_equilibrium.png")

# ── Paleta de colores Equi ─────────────────────────────────────────────
# Centralizada aquí para que un cambio de branding solo requiera editar este bloque.
BRAND = {
    "navy":   "#020f50",   # color principal de marca
    "blue":   "#1955a6",   # azul secundario
    "yellow": "#f4b21b",   # acento / badge
    "teal":   "#7cccbf",   # éxito / ok
    "salmon": "#f7966b",   # alerta / error
}

st.set_page_config(
    page_title="Equilibrium | Auditoría de Datos",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estado de sesión ──────────────────────────────────────────────────────────
# Agrupado en categorías para evitar colisiones de nombres y facilitar el debug.
# Se inicializa solo si la clave no existe (preserva estado entre reruns).
_SESSION_DEFAULTS = {
    # datos: base de trabajo y registro de cambios
    "df_work":          None,    # DataFrame activo (se modifica durante la sesión)
    "cambios_log":      [],      # historial de acciones para exportar
    "archivo_activo":   None,    # nombre del archivo cargado

    # configuración de la sesión
    "checkpoints":      {},      # snapshots del df_work para restaurar
    "vars_obligatorias": [],     # variables marcadas manualmente como siempre obligatorias
    "col_enc_key":      None,    # columna de encuestador detectada/elegida

    # interfaz
    "dark_mode":        False,   # modo oscuro on/off
    "eliminar_ids":     set(),   # IDs marcados para eliminar en Motor de Corrección
}
for k, v in _SESSION_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────────────────────
# 1. ESTILOS CSS
# Los tokens de color fijos (navy, blue, yellow, etc.) vienen del dict BRAND
# definido al inicio del script — editar allí para cambios de branding.
# ──────────────────────────────────────────────────────────────
def get_css(dark=False):
    if dark:
        BG      = "#0f1117"
        CARD    = "#1a1d27"
        TEXT    = "#e8eaf0"
        SUB     = "#8892b0"
        BORDER  = "#2d3250"
        SIDEBAR = "#0a0d16"
        HDR     = "linear-gradient(135deg,#0a0d16 0%,#020f50 100%)"
        OK_BG, OK_B   = "#0d2e24", "#7cccbf"
        WN_BG, WN_B   = "#2a2510", "#f4b21b"
        ER_BG, ER_B   = "#2a1510", "#f7966b"
        SEC_BG  = "#1a1d27"
        INPUT   = "#1e2235"
        INPUT_T = "#e8eaf0"
        PLOT_BG = "#1a1d27"
    else:
        BG      = "#f4f6fb"
        CARD    = "#ffffff"
        TEXT    = "#020f50"
        SUB     = "#5a6a9a"
        BORDER  = "#c8d0e8"
        SIDEBAR = "#020f50"
        HDR     = "linear-gradient(135deg,#020f50 0%,#1955a6 100%)"
        OK_BG, OK_B   = "#edfaf7", "#7cccbf"
        WN_BG, WN_B   = "#fffbec", "#f4b21b"
        ER_BG, ER_B   = "#fff0ec", "#f7966b"
        SEC_BG  = "#ffffff"
        INPUT   = "#ffffff"
        INPUT_T = "#020f50"
        PLOT_BG = "#f4f6fb"

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Geologica:wght@300;400;500;600;700;900&display=swap');

/* ── Base ── */
html, body, [class*="css"], .stApp {{ font-family:'Geologica',sans-serif !important; }}
.stApp {{ background-color:{BG} !important; }}
.main .block-container {{ padding-top:1.5rem !important; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color:{SIDEBAR} !important;
    border-right:1px solid rgba(255,255,255,0.07) !important;
}}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stCheckbox label {{
    color:#f0f2fa !important;
    font-family:'Geologica',sans-serif !important;
}}
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color:#f0f2fa !important;
    font-size:0.92rem !important;
    font-weight:500 !important;
}}

/* ── Métricas ── */
[data-testid="stMetric"] {{
    background:{CARD} !important;
    border-radius:12px !important;
    padding:18px 20px !important;
    border-left:4px solid #f4b21b !important;
    box-shadow:0 2px 8px rgba(2,15,80,0.08) !important;
}}
[data-testid="stMetricLabel"] {{ color:{SUB} !important; font-weight:600 !important; font-size:0.78rem !important; text-transform:uppercase; letter-spacing:0.05em; }}
[data-testid="stMetricValue"] {{ color:{TEXT} !important; font-weight:700 !important; font-size:1.7rem !important; }}
[data-testid="stMetricDelta"] {{ font-size:0.8rem !important; }}

/* ── Encabezado ── */
.eq-header {{
    background:{HDR};
    padding:26px 32px 20px 32px;
    border-radius:14px;
    margin-bottom:24px;
    box-shadow:0 4px 20px rgba(2,15,80,0.15);
}}
.eq-title {{ color:#ffffff !important; font-size:1.75rem !important; font-weight:700 !important; margin:0 !important; line-height:1.2 !important; }}
.eq-header p  {{ color:#c8d8f8 !important; font-size:0.88rem !important; margin:5px 0 0 0 !important; }}
.eq-badge {{
    background:#f4b21b; color:#020f50 !important;
    font-size:0.68rem; font-weight:800; padding:2px 10px;
    border-radius:20px; letter-spacing:0.08em;
    display:inline-block; margin-bottom:6px;
}}

/* ── Secciones ── */
.section-title {{
    color:{TEXT} !important;
    font-size:1rem; font-weight:700;
    padding:9px 16px;
    border-left:4px solid #f4b21b;
    background:{SEC_BG};
    border-radius:0 8px 8px 0;
    margin:20px 0 14px 0;
    box-shadow:0 1px 4px rgba(2,15,80,0.06);
}}

/* ── Alertas ── */
.eq-ok   {{ background:{OK_BG}; border-left:4px solid {OK_B};  border-radius:0 8px 8px 0; padding:11px 16px; color:{TEXT}; font-size:0.88rem; margin:8px 0; }}
.eq-warn {{ background:{WN_BG}; border-left:4px solid {WN_B};  border-radius:0 8px 8px 0; padding:11px 16px; color:{TEXT}; font-size:0.88rem; margin:8px 0; }}
.eq-err  {{ background:{ER_BG}; border-left:4px solid {ER_B};  border-radius:0 8px 8px 0; padding:11px 16px; color:{TEXT}; font-size:0.88rem; margin:8px 0; }}
.eq-info {{ background:{CARD};  border-left:4px solid {BORDER}; border-radius:0 8px 8px 0; padding:11px 16px; color:{SUB};  font-size:0.88rem; margin:8px 0; }}

/* ── Sidebar labels ── */
.sidebar-label {{
    font-size:0.65rem; font-weight:800;
    letter-spacing:0.14em; color:#7a8ab8 !important;
    text-transform:uppercase; margin:16px 0 5px 0;
}}

/* ── Inputs (dark mode fix) ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"],
textarea {{
    background-color:{INPUT} !important;
    color:{INPUT_T} !important;
    border-color:{BORDER} !important;
    border-radius:8px !important;
}}

/* ── File uploader ── */
[data-testid="stFileUploader"] {{
    background:{CARD} !important;
    border-radius:12px !important;
    padding:4px !important;
}}
[data-testid="stFileUploaderDropzone"] {{
    border:2px dashed {BORDER} !important;
    border-radius:10px !important;
    background:{BG} !important;
    text-align:center !important;
}}
[data-testid="stFileUploaderDropzone"] p {{
    color:{SUB} !important;
}}

/* ── Expander ── */
[data-testid="stExpander"] {{
    background:{CARD} !important;
    border:1px solid {BORDER} !important;
    border-radius:10px !important;
}}
[data-testid="stExpander"] summary p {{
    color:{TEXT} !important;
    font-weight:600 !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    background:transparent !important;
    border-bottom:2px solid {BORDER} !important;
}}
.stTabs [data-baseweb="tab"] {{
    color:{SUB} !important;
    font-weight:600 !important;
    font-size:0.87rem !important;
    background:transparent !important;
}}
.stTabs [aria-selected="true"] {{
    color:{TEXT} !important;
    border-bottom:3px solid #f4b21b !important;
    background:transparent !important;
}}

/* ── Dataframe ── */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"] {{
    border-radius:10px !important;
    overflow:hidden !important;
    border:1px solid {BORDER} !important;
}}

/* ── Texto general ── */
p, li, span:not(.eq-badge) {{ color:{TEXT} !important; }}
h1, h2, h3, h4, h5 {{ color:{TEXT} !important; }}
hr {{ border-color:{BORDER} !important; opacity:0.5 !important; }}

/* ── Botones ── */
[data-testid="baseButton-primary"] {{
    background:#1955a6 !important;
    color:#ffffff !important;
    border-radius:8px !important;
    font-weight:600 !important;
    border:none !important;
}}
[data-testid="baseButton-primary"]:hover {{
    background:#020f50 !important;
}}
[data-testid="baseButton-secondary"] {{
    background:{CARD} !important;
    color:{TEXT} !important;
    border:1.5px solid {BORDER} !important;
    border-radius:8px !important;
    font-weight:600 !important;
}}
</style>"""

dark = st.session_state.dark_mode
st.markdown(get_css(dark), unsafe_allow_html=True)
############# TERMINA LA CONFIGURACIÓN DE LA PÁGINA ####################################################################

# ──────────────────────────────────────────────────────────────
# 2. HELPERS — UTILIDADES GENERALES
# ──────────────────────────────────────────────────────────────

def plot_colors():
    """Devuelve (bg_outer, bg_paper, text_color, grid_color) según modo."""
    if st.session_state.dark_mode:
        return "#1a1d27", "#1a1d27", "#e8eaf0", "rgba(255,255,255,0.06)"
    return "#f4f6fb", "#ffffff", "#020f50", "rgba(2,15,80,0.06)"

def leer_archivo(f):
    """
    Lee una base de datos en .xlsx, .dta o .csv.

    Para CSV usa sep=None + engine='python' para que Pandas detecte
    automáticamente el separador (coma, punto y coma, tabulador, etc.).
    Esto evita fallos cuando la base viene de Excel con configuración
    regional que exporta con ';' en lugar de ','.

    Retorna None si f es None (protege contra activaciones prematuras
    del componente file_uploader antes de que el usuario elija archivo).
    """
    if f is None:
        return None
    if f.name.endswith(".xlsx"):
        return pd.read_excel(f)
    if f.name.endswith(".dta"):
        return pd.read_stata(f)
    # CSV: detección automática de separador para cubrir exportaciones regionales
    try:
        return pd.read_csv(f, sep=None, engine="python")
    except Exception:
        f.seek(0)                      # reinicia el puntero tras el intento fallido
        return pd.read_csv(f)          # fallback con coma estándar

def detectar_plataforma(df_s):
    lbl_cols = [c for c in df_s.columns if "label" in c.lower()]
    if any("kobo" in c.lower() for c in df_s.columns):
        return "KoBoToolbox"
    if any("::" in c for c in lbl_cols):
        return "SurveyCTO / ODK"
    return "KoBoToolbox / ODK"

def normalizar_label(df_s):
    prioridad = [
        "label::spanish","label::español","label::espanol",
        "label::spanish (es)","label::español (es)",
        "label::english","label::english (en)",
        "label",
    ]
    for p in prioridad:
        m = next((c for c in df_s.columns if c.lower().strip() == p), None)
        if m:
            return m
    return next((c for c in df_s.columns if "label" in c.lower()), None)

# @st.cache_data memoriza el resultado por (archivo, args).
# Si el usuario solo cambia de pestaña o ajusta la UI sin cambiar el archivo,
# Streamlit devuelve el resultado anterior sin volver a procesar.
@st.cache_data(show_spinner=False)
def leer_instrumento(f):
    if f is None:
        return None, None
    if f.name.endswith(".xlsx"):
        xls  = pd.ExcelFile(f)
        hoja = "survey" if "survey" in xls.sheet_names else xls.sheet_names[0]
        df_i = pd.read_excel(f, sheet_name=hoja, dtype=str).fillna("")
        df_c = (pd.read_excel(f, sheet_name="choices", dtype=str).fillna("")
                if "choices" in xls.sheet_names else None)
        return df_i, df_c
    df_i = pd.read_csv(f, dtype=str).fillna("")
    return df_i, None

def df_a_excel(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Base_Corregida")
    return buf.getvalue()

def df_a_stata(df):
    """Exporta a formato .dta (Stata). Maneja tipos incompatibles automáticamente."""
    buf = io.BytesIO()
    df_copy = df.copy()
    # Stata limita nombres de columna a 32 caracteres
    rename_map = {}
    seen = {}
    for col in df_copy.columns:
        short = col[:32]
        if short in seen:
            seen[short] += 1
            short = (col[:29] + f"_{seen[short]}")[:32]
        else:
            seen[short] = 0
        rename_map[col] = short
    df_copy = df_copy.rename(columns=rename_map)
    # Convertir columnas object complejas a string
    for col in df_copy.select_dtypes(include="object").columns:
        df_copy[col] = df_copy[col].astype(str).replace("nan", "")
    # Convertir bool a int (Stata no soporta bool)
    for col in df_copy.select_dtypes(include="bool").columns:
        df_copy[col] = df_copy[col].astype(int)
    try:
        df_copy.to_stata(buf, write_index=False, version=118)
    except Exception:
        # Fallback: convertir todo a string si falla
        df_copy = df_copy.astype(str)
        df_copy.to_stata(buf, write_index=False, version=118)
    return buf.getvalue()

def colores_semaforo(vals, media, std):
    # Semáforo de 3 niveles basado en desviaciones estándar:
    #   Verde  (teal)   → v < media + 1σ    (Normal)
    #   Amarillo        → media + 1σ ≤ v < media + 2σ  (Alerta)
    #   Rojo  (salmon)  → v ≥ media + 2σ    (Crítico)
    uw, uc = media + std, media + 2 * std
    return ["#f7966b" if v >= uc else "#f4b21b" if v >= uw else "#4bb8a9" for v in vals]

def colorear_flags(df_flags):
    PALETA = {
        "flag_missings":      (244, 178,  27),
        "flag_duplicados":    ( 25,  85, 166),
        "flag_duracion":      (247, 150, 107),
        "flag_edad":          (124, 204, 191),
        "flag_gasto":         (246, 222, 174),
    }
    DEFAULT = (100, 149, 237)

    def color_celda(val, rgb):
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ""
        if pd.isna(val) or v == 0:
            return ""
        intensidad = min(0.85, 0.30 + v * 0.15)
        return (f"background-color:rgba({rgb[0]},{rgb[1]},{rgb[2]},{intensidad});"
                f"color:#020f50;font-weight:700;border-radius:4px;")

    styled = df_flags.style
    for col in df_flags.columns:
        cl = col.lower()
        if cl.startswith("flag") or cl.endswith("_flag"):
            rgb = next((v for k, v in PALETA.items() if k in cl), DEFAULT)
            try:
                styled = styled.map(lambda v, c=rgb: color_celda(v, c), subset=[col])
            except Exception:
                pass
    return styled

FUNCIONES_COMPLEJAS = [
    "pulldata(", "regex(", "count-selected(",
    "string-length(", "string(", "number(",
    "date(", "decimal-date-value(", "if(",
    "coalesce(", "jr:choice-name(",
]

def expr_es_compleja(expr):
    """Detecta si una expresión relevant contiene funciones no parseables."""
    if not expr or str(expr).strip().lower() in ("", "nan", "none"):
        return False
    expr_low = str(expr).lower()
    return any(fn in expr_low for fn in FUNCIONES_COMPLEJAS)

def evaluar_relevant(expr, row):
    """
    Evalúa una expresión relevant de ODK/SurveyCTO contra una fila.
    Retorna:
        True  → variable es relevante (debe tener dato)
        False → variable es skip válido (puede estar vacía)
    Si la expresión no se puede parsear → True (conservador: cuenta como requerida).
    Soporta: selected(), not(), =, !=, >, >=, <, <=, and, or.
    """
    if not expr or str(expr).strip().lower() in ("", "nan", "none"):
        return True  # sin condición = siempre requerida

    try:
        work = str(expr).strip()

        # 1. selected(${var}, 'code') → True/False
        def sub_selected(m):
            var, code = m.group(1), m.group(2)
            val = str(row.get(var, "") or "")
            return "True" if code in val.split() else "False"
        work = re.sub(
            r"selected\(\s*\$\{([^}]+)\}\s*,\s*['\"]([^'\"]+)['\"]\s*\)",
            sub_selected, work)

        # 2. ${var} op 'string'
        def sub_str_op(m):
            var, op, val = m.group(1), m.group(2), m.group(3)
            rv = str(row.get(var, "") or "")
            if op == "=":  return "True" if rv == val else "False"
            if op == "!=": return "True" if rv != val else "False"
            return "False"
        work = re.sub(
            r'\$\{([^}]+)\}\s*(!=|=)\s*[\'"]([^\'"]*)[\'"]',
            sub_str_op, work)

        # 3. ${var} op número
        def sub_num_op(m):
            var, op, thr = m.group(1), m.group(2), float(m.group(3))
            try:
                rv = float(row.get(var, float("nan")))
                res = {">=": rv>=thr, ">": rv>thr, "<=": rv<=thr,
                       "<": rv<thr, "=": rv==thr, "!=": rv!=thr}.get(op, False)
                return "True" if res else "False"
            except Exception:
                return "False"
        work = re.sub(
            r"\$\{([^}]+)\}\s*(>=|<=|!=|>|<|=)\s*(-?\d+(?:\.\d+)?)",
            sub_num_op, work)

        # 4. ${var} suelto (sin operador) → True si tiene dato, False si vacío
        def sub_var(m):
            v = row.get(m.group(1), "")
            return "False" if (pd.isna(v) or str(v).strip() == "") else "True"
        work = re.sub(r"\$\{([^}]+)\}", sub_var, work)

        # 5. Operadores lógicos ODK → Python
        work = re.sub(r"\band\b", " and ", work, flags=re.IGNORECASE)
        work = re.sub(r"\bor\b",  " or ",  work, flags=re.IGNORECASE)
        work = re.sub(r"\bnot\b", " not ", work, flags=re.IGNORECASE)

        # Validación de seguridad: después de las sustituciones, work solo debe
        # contener tokens seguros (True, False, operadores lógicos y paréntesis).
        # Si detectamos algo fuera de esa lista, lanzamos excepción en lugar de
        # ejecutar código arbitrario proveniente del archivo de instrumento.
        _SAFE_TOKENS = re.compile(r"^[\s\(\)TrueFalseandrnotz]+$")
        # "z" cubre "not" completo; la regex revisa token a token también:
        _safe_check = re.sub(r"\b(True|False|and|or|not)\b", "", work)
        _safe_check = re.sub(r"[\s\(\)]", "", _safe_check)
        if _safe_check:                # quedan caracteres no seguros → abortar
            return True
        return bool(eval(work))       # en este punto solo hay True/False/and/or/not/()

    except Exception:
        return True   # si no parsea → conservador: tratar como requerida


@st.cache_data(show_spinner=False)
def calcular_missings_inteligentes(df, df_inst, col_id=None):
    """
    Calcula missings respetando las condiciones relevant del instrumento.

    Retorna (df_por_encuesta, df_por_variable):
      df_por_encuesta:
        ID | Miss. reales | Skips inválidos | Variables con missing | Variables con skip inv.
      df_por_variable:
        Variable | Miss. reales | Skips inválidos | % Miss. reales | Tipo de missing
    Limitantes documentadas:
      - Expresiones XPath no parseables → tratadas como siempre requeridas.
      - Funciones SurveyCTO avanzadas (regex, pulldata, etc.) → ignoradas.
      - Variables del instrumento que no existen en la base → omitidas.
    """
    col_name = next((c for c in df_inst.columns if c.lower() == "name"), None)
    col_type = next((c for c in df_inst.columns if c.lower() == "type"), None)
    col_rel  = next((c for c in df_inst.columns if c.lower() == "relevant"), None)

    if not col_name or not col_type:
        return None, None

    SKIP_TYPES = {
        "begin group","end group","begin repeat","end repeat",
        "start","end","today","deviceid","username","duration",
        "calculate","hidden","note","acknowledge","xml-external",
    }

    col_lbl_inst = normalizar_label(df_inst)
    vars_audit, vars_complejas = [], []
    for _, irow in df_inst.iterrows():
        tipo   = str(irow.get(col_type, "")).strip().lower()
        nombre = str(irow.get(col_name, "")).strip()
        rel    = str(irow.get(col_rel,  "")).strip() if col_rel else ""
        base   = tipo.split()[0] if " " in tipo else tipo
        if not nombre or base in SKIP_TYPES or nombre not in df.columns:
            continue
        rel_clean = None if rel.lower() in ("nan","none","") else rel
        vars_audit.append({"var": nombre, "relevant": rel_clean})
        if rel_clean and expr_es_compleja(rel_clean):
            etiqueta = str(irow.get(col_lbl_inst, "")).strip() if col_lbl_inst else ""
            vars_complejas.append({
                "Variable":  nombre,
                "Etiqueta":  etiqueta or nombre,
                "Condición": rel_clean,
            })

    if not vars_audit:
        return None, None, []

    # ── Evaluar fila por fila ────────────────────────────────
    rows_enc, vars_miss_count, vars_skip_count = [], {}, {}
    for v in vars_audit:
        vars_miss_count[v["var"]] = 0
        vars_skip_count[v["var"]] = 0

    for idx, df_row in df.iterrows():
        id_val = str(df_row[col_id]) if (col_id and col_id in df.columns) else str(idx)
        miss_reales, skips_inv = [], []

        for vi in vars_audit:
            var = vi["var"]
            val = df_row.get(var)
            vacio = pd.isna(val) or str(val).strip() == ""

            if vi["relevant"]:
                relevante = evaluar_relevant(vi["relevant"], df_row)
                if relevante and vacio:
                    miss_reales.append(var)
                    vars_miss_count[var] += 1
                elif not relevante and not vacio:
                    skips_inv.append(var)
                    vars_skip_count[var] += 1
            else:
                if vacio:
                    miss_reales.append(var)
                    vars_miss_count[var] += 1

        rows_enc.append({
            "ID":                  id_val,
            "Miss. reales":        len(miss_reales),
            "Skips inválidos":     len(skips_inv),
            "Variables con missing": ", ".join(miss_reales[:6])
                                      + ("…" if len(miss_reales) > 6 else ""),
            "Variables con skip inv.": ", ".join(skips_inv[:6])
                                        + ("…" if len(skips_inv) > 6 else ""),
        })

    df_enc = pd.DataFrame(rows_enc)

    # ── Resumen por variable ────────────────────────────────
    n = len(df)
    rows_var = []
    for vi in vars_audit:
        nm  = vi["var"]
        nm_ = vars_miss_count[nm]
        ns_ = vars_skip_count[nm]
        tipo_miss = (
            "Siempre requerida" if vi["relevant"] is None
            else "Condicional (relevant)"
        )
        rows_var.append({
            "Variable":        nm,
            "Miss. reales":    nm_,
            "% Miss. reales":  round(nm_ / n * 100, 1) if n > 0 else 0,
            "Skips inválidos": ns_,
            "Tipo":            tipo_miss,
            "Condición relevant": vi["relevant"] or "—",
        })

    df_var = (pd.DataFrame(rows_var)
              .sort_values("Miss. reales", ascending=False)
              .reset_index(drop=True))

    return df_enc, df_var, vars_complejas


# vars_oblig es una lista — la convertimos a tuple antes de cachear porque
# st.cache_data requiere argumentos hasheables (las listas no lo son).
@st.cache_data(show_spinner=False)
def calcular_missings_obligatorios(df, vars_oblig: tuple, col_id=None, col_enc=None):
    """
    Calcula missings para variables marcadas manualmente como siempre obligatorias.
    No usa lógica relevant — si la celda está vacía, es un missing, punto.

    Retorna (df_enc, df_var, df_por_enc):
      df_enc:     ID | Encuestador | Miss. oblig. | Variables con missing
      df_var:     Variable | Etiqueta | Miss. oblig. | % Miss.
      df_por_enc: Encuestador | N encuestas | Miss. oblig. | Enc. afectadas | % afectadas
                  (None si no hay columna de encuestador)
    """
    vars_validas = [v for v in vars_oblig if v in df.columns]
    if not vars_validas:
        return None, None, None

    rows_enc = []
    vars_miss_count = {v: 0 for v in vars_validas}

    for idx, df_row in df.iterrows():
        id_val  = str(df_row[col_id])  if (col_id  and col_id  in df.columns) else str(idx)
        enc_val = str(df_row[col_enc]) if (col_enc and col_enc in df.columns) else "—"
        miss_vars = []
        for v in vars_validas:
            val = df_row.get(v)
            if pd.isna(val) or str(val).strip() == "":
                miss_vars.append(v)
                vars_miss_count[v] += 1
        rows_enc.append({
            "ID":          id_val,
            "Encuestador": enc_val,
            "Miss. oblig.": len(miss_vars),
            "Variables":    ", ".join(miss_vars[:8]) + ("…" if len(miss_vars) > 8 else ""),
        })

    df_enc = pd.DataFrame(rows_enc)

    n = len(df)
    df_var = pd.DataFrame([
        {"Variable": v, "Miss. oblig.": vars_miss_count[v],
         "% Miss.": round(vars_miss_count[v] / n * 100, 1)}
        for v in vars_validas
    ]).sort_values("Miss. oblig.", ascending=False).reset_index(drop=True)

    # Resumen por encuestador
    if col_enc and col_enc in df.columns:
        df_por_enc = (
            df_enc.groupby("Encuestador")
            .agg(
                **{"N encuestas":       ("ID",           "count"),
                   "Miss. oblig.":      ("Miss. oblig.", "sum"),
                   "Enc. afectadas":    ("Miss. oblig.", lambda x: (x > 0).sum())}
            )
            .reset_index()
        )
        df_por_enc["% afectadas"] = (
            df_por_enc["Enc. afectadas"] / df_por_enc["N encuestas"] * 100
        ).round(1)
        df_por_enc = df_por_enc.sort_values("Miss. oblig.", ascending=False).reset_index(drop=True)
    else:
        df_por_enc = None

    return df_enc, df_var, df_por_enc


# ──────────────────────────────────────────────────────────────
# 3. FLAGS AUTOMÁTICOS
# Genera una columna de flag por dimensión (missings, duplicados, duración).
# encuesta_válida = 1 solo si los tres flags son 0 (AND lógico).
# ──────────────────────────────────────────────────────────────
def calcular_flags(df, col_id, col_dur, mn, mx):
    n_miss   = df.isnull().sum(axis=1)
    dup_mask = df.duplicated(keep=False)
    flags    = pd.DataFrame()
    flags["ID"] = (df[col_id].astype(str)
                   if (col_id and col_id in df.columns)
                   else df.index.astype(str))
    flags["Missings"]        = n_miss.values
    flags["flag_missings"]   = (n_miss > 0).astype(int)
    flags["flag_duplicados"] = dup_mask.astype(int)
    if col_dur and col_dur in df.columns:
        dur_m = pd.to_numeric(df[col_dur], errors="coerce") / 60
        flags["Duración (min)"] = dur_m.round(1).values
        flags["flag_duracion"]  = ((dur_m < mn) | (dur_m > mx)).astype(int)
    else:
        flags["Duración (min)"] = None
        flags["flag_duracion"]  = 0
    flags["encuesta_válida"] = (
        (flags["flag_missings"] == 0) &
        (flags["flag_duplicados"] == 0) &
        (flags["flag_duracion"] == 0)
    ).astype(int)
    return flags.reset_index(drop=True)

@st.cache_data(show_spinner=False)
def auditar_instrumento(df_s, df_c, col_lbl):
    """
    Auditoría inteligente en 3 niveles:
      Error       → problema que rompe la encuesta
      Advertencia → mala práctica pero no crítica
      Info        → observación estructural
    """
    alertas = []

    # Tipos que NO necesitan label (estructurales / metadatos)
    SKIP_LABEL = {
        "begin group","end group","begin repeat","end repeat",
        "start","end","today","deviceid","username","duration",
        "calculate","hidden","xml-external","caseid",
    }
    # Tipos que SÍ deberían tener label (visibles al encuestador)
    NEED_LABEL = {
        "integer","decimal","text","date","time","datetime",
        "select_one","select_multiple","note","geopoint",
        "image","audio","video","barcode","range","acknowledge",
        "rank",
    }
    # Tipos que no necesitan constraint (no son numéricos libres)
    NO_CONSTRAINT = {
        "begin group","end group","begin repeat","end repeat",
        "start","end","today","deviceid","username","duration",
        "calculate","hidden","text","select_one","select_multiple",
        "note","geopoint","image","audio","video","date","time",
        "datetime","acknowledge","xml-external","barcode","range",
        "rank","caseid",
    }

    col_type = next((c for c in df_s.columns if c.lower() == "type"), None)
    col_name = next((c for c in df_s.columns if c.lower() == "name"), None)
    col_con  = next((c for c in df_s.columns
                     if "constraint" in c.lower() and "message" not in c.lower()), None)

    if not col_type or not col_name:
        return pd.DataFrame()

    for _, row in df_s.iterrows():
        tipo_raw = str(row.get(col_type, "")).strip()
        tipo_lo  = tipo_raw.lower()
        base     = tipo_lo.split()[0] if " " in tipo_lo else tipo_lo
        nombre   = str(row.get(col_name, "")).strip()

        if not nombre or not tipo_lo or base in SKIP_LABEL:
            continue

        # ── 1. Label vacío en pregunta visible ──────────────────
        if base in NEED_LABEL and col_lbl:
            lbl = str(row.get(col_lbl, "")).strip()
            if not lbl or lbl.lower() in ("nan", "none", ""):
                nivel = "Error" if base in ("select_one","select_multiple","integer","decimal") else "Advertencia"
                alertas.append({
                    "Variable":    nombre,
                    "Tipo":        tipo_raw,
                    "Nivel":       nivel,
                    "Descripción": "Label vacío — la pregunta no tiene texto visible para el encuestador.",
                })

        # ── 2. Campo numérico sin constraint ────────────────────
        if base in ("integer","decimal") and col_con:
            con = str(row.get(col_con, "")).strip()
            if not con or con.lower() in ("nan","none",""):
                alertas.append({
                    "Variable":    nombre,
                    "Tipo":        tipo_raw,
                    "Nivel":       "Advertencia",
                    "Descripción": "Campo numérico sin constraint — se recomienda definir rango válido de valores.",
                })

        # ── 3. Lista de choices inexistente ─────────────────────
        if base in ("select_one","select_multiple") and df_c is not None:
            partes = tipo_lo.split()
            lista  = partes[1] if len(partes) > 1 else ""
            col_list = next((c for c in df_c.columns if "list" in c.lower()), None)
            if lista and col_list:
                listas = set(df_c[col_list].astype(str).str.strip().str.lower().unique())
                if lista not in listas:
                    alertas.append({
                        "Variable":    nombre,
                        "Tipo":        tipo_raw,
                        "Nivel":       "Error",
                        "Descripción": f"Lista '{lista}' no encontrada en choices — la pregunta no tendrá opciones.",
                    })

    if not alertas:
        return pd.DataFrame()
    df_a = pd.DataFrame(alertas)
    orden = {"Error": 0, "Advertencia": 1, "Info": 2}
    df_a["_ord"] = df_a["Nivel"].map(orden)
    return df_a.sort_values("_ord").drop(columns="_ord").reset_index(drop=True)

# ──────────────────────────────────────────────────────────────
# 4. EXPORTACIÓN
# generar_reporte: Excel multi-hoja (resumen, flags, missings, outliers, log)
# df_a_excel / df_a_stata: exportaciones simples de la base corregida
# ──────────────────────────────────────────────────────────────
def generar_reporte(df_orig, df_final, df_flags, resumen_iqr,
                    df_out_det, cambios_log, nombre, eliminar_ids=None):
    buf = io.BytesIO()
    miss_var = df_orig.isnull().sum()
    miss_var = miss_var[miss_var > 0].reset_index()
    miss_var.columns = ["Variable", "N Missings"]
    miss_var["Pct Total"] = (miss_var["N Missings"] / len(df_orig) * 100).round(2)
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame({
            "Indicador": [
                "Archivo auditado", "Total encuestas (original)",
                "Total encuestas (final)", "Encuestas válidas",
                "Encuestas con flag", "Celdas con missings",
                "Total outliers", "Duplicados",
                "Completitud (%)", "Acciones aplicadas",
            ],
            "Valor": [
                nombre, len(df_orig), len(df_final),
                int(df_flags["encuesta_válida"].sum()),
                int((df_flags["encuesta_válida"] == 0).sum()),
                int(df_orig.isnull().sum().sum()),
                int(resumen_iqr["N Outliers"].sum()) if not resumen_iqr.empty else 0,
                int(df_orig.duplicated().sum()),
                round((1 - df_orig.isnull().sum().sum() / max(df_orig.size, 1)) * 100, 1),
                len(cambios_log),
            ],
        }).to_excel(w, sheet_name="Resumen Ejecutivo", index=False)
        df_flags.to_excel(w, sheet_name="Flags por Encuesta", index=False)
        if not miss_var.empty:
            miss_var.to_excel(w, sheet_name="Missings por Variable", index=False)
        if not resumen_iqr.empty:
            resumen_iqr.to_excel(w, sheet_name="Outliers por Variable", index=False)
        if not df_out_det.empty:
            df_out_det.to_excel(w, sheet_name="Detalle Outliers", index=False)
        if cambios_log:
            pd.DataFrame({"Acción": cambios_log}).to_excel(
                w, sheet_name="Historial de Cambios", index=False)
        if eliminar_ids:
            pd.DataFrame({"ID Eliminado": sorted(eliminar_ids)}).to_excel(
                w, sheet_name="IDs Eliminados", index=False)
    return buf.getvalue()

# ──────────────────────────────────────────────────────────────
# 5. MOTOR DE CORRECCIÓN — funciones de aplicación de fixes
# Cada función recibe el df de trabajo y la tabla de decisiones del usuario.
# Retorna (df_corregido, log_de_acciones).
# ──────────────────────────────────────────────────────────────
def aplicar_fix_missings(df_w, tbl_n, tbl_c):
    log, res, drop = [], df_w.copy(), set()
    for tbl in [tbl_n, tbl_c]:
        if tbl is None:
            continue
        for _, row in tbl.iterrows():
            col, r = row["Variable"], row["Corrección"]
            n = int(res[col].isnull().sum())
            if n == 0:
                continue
            if r == "Mediana":
                v = res[col].median(); res[col] = res[col].fillna(v)
                log.append(f"✔ `{col}`: {n} missings → mediana ({round(v,2)})")
            elif r == "Media":
                v = res[col].mean(); res[col] = res[col].fillna(v)
                log.append(f"✔ `{col}`: {n} missings → media ({round(v,2)})")
            elif r == "Moda":
                v = res[col].mode()
                if len(v):
                    res[col] = res[col].fillna(v[0])
                    log.append(f"✔ `{col}`: {n} missings → moda")
            elif r == "Sin respuesta":
                res[col] = res[col].fillna("Sin respuesta")
                log.append(f"✔ `{col}`: {n} missings → 'Sin respuesta'")
            elif r == "Eliminar fila":
                drop.update(res[res[col].isnull()].index)
                log.append(f"🗑 `{col}`: {n} filas marcadas para eliminar")
    if drop:
        res = res.drop(index=list(drop)).reset_index(drop=True)
        log.append(f"Total filas eliminadas por missings: {len(drop)}")
    return res, log

def aplicar_fix_outliers(df_w, tbl):
    log, res, drop = [], df_w.copy(), set()
    for _, row in tbl.iterrows():
        col, r = row["Variable"], row["Corrección"]
        li, ls = row["Lím. Inf."], row["Lím. Sup."]
        mask = (res[col] < li) | (res[col] > ls)
        n = int(mask.sum())
        if n == 0:
            continue
        if r == "Winsorizar":
            res[col] = res[col].clip(lower=li, upper=ls)
            log.append(f"✔ `{col}`: {n} outliers recortados a [{round(li,2)}, {round(ls,2)}]")
        elif r == "Reemplazar con mediana":
            v = res[col].median(); res.loc[mask, col] = v
            log.append(f"✔ `{col}`: {n} outliers → mediana ({round(v,2)})")
        elif r == "Marcar con flag":
            res[f"{col}_flag"] = mask.astype(int)
            log.append(f"🚩 `{col}`: {n} outliers marcados en columna `{col}_flag`")
        elif r == "Eliminar fila":
            drop.update(res[mask].index)
            log.append(f"🗑 `{col}`: {n} filas marcadas para eliminar")
    if drop:
        res = res.drop(index=list(drop)).reset_index(drop=True)
        log.append(f"Total filas eliminadas por outliers: {len(drop)}")
    return res, log

def aplicar_fix_dup(df_w, r):
    res = df_w.copy(); n = int(res.duplicated().sum())
    if n == 0:
        return res, ["Sin duplicados encontrados."]
    if r == "Primera ocurrencia":
        return res.drop_duplicates(keep="first").reset_index(drop=True), [f"✔ {n} duplicados → conservada primera ocurrencia"]
    elif r == "Última ocurrencia":
        return res.drop_duplicates(keep="last").reset_index(drop=True),  [f"✔ {n} duplicados → conservada última ocurrencia"]
    elif r == "Eliminar todas":
        return res.drop_duplicates(keep=False).reset_index(drop=True),   [f"🗑 {n} filas duplicadas eliminadas completamente"]
    else:
        res["duplicado_flag"] = res.duplicated(keep=False).astype(int)
        return res, [f"🚩 {n} filas marcadas en columna `duplicado_flag`"]

# ──────────────────────────────────────────────────────────────
# 6. SIDEBAR — navegación y configuración de apariencia
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=210)
    else:
        st.markdown("""
        <div style='text-align:center;padding:12px 0 18px 0;'>
            <div style='font-size:1.4rem;font-weight:800;letter-spacing:0.04em;color:#f0f2fa;'>equilibrium</div>
            <div style='font-size:0.58rem;letter-spacing:0.18em;color:#7a8ab8;'>BUSINESS · DATA · COMMUNITIES</div>
            <div style='font-size:0.58rem;color:#4a5a80;margin-top:4px;font-style:italic;'>
                Coloca logo_equilibrium.png<br>en la carpeta del proyecto
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>Módulos</div>", unsafe_allow_html=True)
    modulo = st.radio(
        "Selecciona módulo",
        ["📋  Revisión de Encuesta", "🗄️  Auditoría de Base de Datos"],
        label_visibility="collapsed",
    )

    st.markdown("<div class='sidebar-label'>Apariencia</div>", unsafe_allow_html=True)
    nuevo_dark = st.checkbox("🌗  Modo oscuro", value=st.session_state.dark_mode)
    if nuevo_dark != st.session_state.dark_mode:
        st.session_state.dark_mode = nuevo_dark
        st.rerun()

    st.markdown("<div class='sidebar-label'>Versión</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.72rem;color:#7a8ab8;line-height:1.8;'>"
        "<b style='color:#a0aec8;'>v3.3.0</b><br>"
        "SurveyCTO · KoBoToolbox · ODK<br>"
        "Equilibrium Data Team"
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# 7. MÓDULO 1 — REVISIÓN DE ENCUESTA (INSTRUMENTO)
# Auditoría de programación XLSForm: estructura, diccionario, choices,
# labels vacíos, campos numéricos sin constraint, listas huérfanas.
# ══════════════════════════════════════════════════════════════
if modulo == "📋  Revisión de Encuesta":
    st.markdown("""
    <div class='eq-header'>
        <div class='eq-badge'>MÓDULO 1</div>
        <div class='eq-title'>Revisión de Encuesta</div>
        <p>Auditoría de programación del instrumento &nbsp;·&nbsp; SurveyCTO &nbsp;·&nbsp; KoBoToolbox &nbsp;·&nbsp; ODK</p>
    </div>""", unsafe_allow_html=True)

    col_up, col_info = st.columns([3, 2])
    with col_up:
        archivo_enc = st.file_uploader(
            "Sube el instrumento (.xlsx con hojas survey/choices, o .csv)",
            type=["xlsx", "csv"],
            label_visibility="visible",
        )
    with col_info:
        st.markdown("""
        <div class='eq-info' style='margin-top:28px;'>
            <b>Formatos aceptados</b><br>
            XLSForm estándar con hojas <code>survey</code> y <code>choices</code><br>
            Compatible con SurveyCTO, KoBo y ODK Collect
        </div>""", unsafe_allow_html=True)

    if archivo_enc is None:
        st.markdown("""
        <div style='text-align:center;padding:70px 20px;opacity:0.5;'>
            <div style='font-size:3rem;'>📋</div>
            <h3>Sube el instrumento para comenzar</h3>
        </div>""", unsafe_allow_html=True)
        st.stop()

    df_inst, df_ch = leer_instrumento(archivo_enc)
    col_name = next((c for c in df_inst.columns if c.lower() == "name"), None)
    col_type = next((c for c in df_inst.columns if c.lower() == "type"), None)
    col_rel  = next((c for c in df_inst.columns if c.lower() == "relevant"), None)
    col_con  = next((c for c in df_inst.columns
                     if "constraint" in c.lower() and "message" not in c.lower()), None)
    col_req  = next((c for c in df_inst.columns if c.lower() == "required"), None)
    col_lbl  = normalizar_label(df_inst)
    plat     = detectar_plataforma(df_inst)

    badge_color = "#7cccbf" if "Kobo" in plat else "#f4b21b"
    st.markdown(
        f"<div class='eq-ok'>"
        f"<b>{archivo_enc.name}</b> &nbsp;·&nbsp; {len(df_inst)} filas &nbsp;·&nbsp; "
        f"{len(df_inst.columns)} columnas &nbsp;|&nbsp; "
        f"<span style='background:{badge_color};color:#020f50;padding:2px 10px;"
        f"border-radius:12px;font-weight:700;font-size:0.78rem;'>{plat}</span>"
        + (f" &nbsp;·&nbsp; Label detectado: <code>{col_lbl}</code>" if col_lbl else
           " &nbsp;·&nbsp; <span style='color:#f7966b;'>⚠ columna label no detectada</span>")
        + "</div>",
        unsafe_allow_html=True,
    )

    tab_est, tab_dic, tab_aud, tab_ch_tab = st.tabs([
        "📐 Estructura", "📚 Diccionario ODK",
        "🔍 Auditoría de Programación", "🗂 Choices",
    ])

    # ── TAB 1: Estructura ─────────────────────────────────────
    with tab_est:
        st.markdown("<div class='section-title'>Métricas del instrumento</div>", unsafe_allow_html=True)

        SKIP_M = {
            "begin group","end group","begin repeat","end repeat",
            "start","end","today","deviceid","username","duration",
            "note","calculate","acknowledge",
        }
        total_vars = 0
        if col_type:
            total_vars = int((~df_inst[col_type].str.strip().str.lower().isin(SKIP_M)).sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Preguntas", total_vars)
        if col_type:
            m2.metric("Tipos distintos", int(df_inst[col_type].nunique()))
            m3.metric("select_one",
                      int(df_inst[col_type].str.contains("select_one", na=False).sum()))
            m4.metric("Grupos",
                      int(df_inst[col_type].str.strip().str.lower().eq("begin group").sum()))

        st.markdown("<div class='section-title'>Vista del instrumento</div>", unsafe_allow_html=True)
        st.dataframe(df_inst, use_container_width=True)

        if col_type:
            st.markdown("<div class='section-title'>Distribución de tipos</div>", unsafe_allow_html=True)
            tipos_df = df_inst[col_type].value_counts().reset_index()
            tipos_df.columns = ["Tipo", "Cantidad"]
            ca, cb = st.columns([1, 2])
            with ca:
                st.dataframe(tipos_df, use_container_width=True, hide_index=True)
            with cb:
                pb, pp, pt, pg = plot_colors()
                fig = go.Figure(go.Bar(
                    y=tipos_df["Tipo"], x=tipos_df["Cantidad"], orientation="h",
                    marker_color="#1955a6", marker_line_width=0,
                    text=tipos_df["Cantidad"], textposition="outside",
                    textfont=dict(color=pt, size=12),
                ))
                fig.update_layout(
                    margin=dict(l=0, r=50, t=10, b=0),
                    height=max(220, len(tipos_df) * 34),
                    plot_bgcolor=pb, paper_bgcolor=pp,
                    xaxis=dict(showgrid=True, gridcolor=pg, color=pt),
                    yaxis=dict(showgrid=False, autorange="reversed", color=pt),
                )
                st.plotly_chart(fig, use_container_width=True)

        if col_name:
            st.markdown("<div class='section-title'>Buscador de variables</div>", unsafe_allow_html=True)
            busq = st.text_input("Buscar por nombre o parte del nombre:", key="busq_est")
            if busq:
                res_b = df_inst[df_inst[col_name].str.contains(busq, case=False, na=False)]
                if not res_b.empty:
                    st.success(f"**{len(res_b)}** coincidencia(s)")
                    st.dataframe(res_b, use_container_width=True, hide_index=True)
                else:
                    st.warning("Sin coincidencias.")

    # ── TAB 2: Diccionario ODK ────────────────────────────────
    with tab_dic:
        st.markdown("<div class='section-title'>Diccionario de variables</div>", unsafe_allow_html=True)
        st.caption("Resumen estructurado: variable · etiqueta · tipo · saltos lógicos · validaciones.")

        if not col_name or not col_type:
            st.markdown("<div class='eq-warn'>El instrumento no tiene columnas 'name' o 'type' reconocibles.</div>",
                        unsafe_allow_html=True)
        else:
            SKIP_D = {
                "begin group","end group","begin repeat","end repeat",
                "start","end","today","deviceid","username","calculate","hidden",
            }
            TIPO_L = {
                "integer":"Número entero","decimal":"Decimal","text":"Texto libre",
                "date":"Fecha","time":"Hora","datetime":"Fecha y hora",
                "geopoint":"GPS","image":"Foto","audio":"Audio","video":"Video",
                "acknowledge":"Confirmación","note":"Nota",
            }

            def tipo_legible(t):
                t = str(t).strip().lower()
                if t.startswith("select_one"):      return "Selección única"
                if t.startswith("select_multiple"): return "Selección múltiple"
                return TIPO_L.get(t, t.capitalize())

            def opciones_choices(tipo_raw):
                if df_ch is None:
                    return ""
                t = str(tipo_raw).strip().lower()
                if not (t.startswith("select_one") or t.startswith("select_multiple")):
                    return ""
                partes = t.split(); lista = partes[1] if len(partes) > 1 else ""
                if not lista:
                    return ""
                col_list = next((c for c in df_ch.columns if "list" in c.lower()), None)
                col_val  = next((c for c in df_ch.columns if c.lower() == "name"), None)
                lbl2     = normalizar_label(df_ch)
                if not col_list or not col_val:
                    return ""
                sub = df_ch[df_ch[col_list].str.strip().str.lower() == lista]
                if sub.empty:
                    return f"(lista '{lista}' no encontrada)"
                if lbl2 and lbl2 in sub.columns:
                    return " · ".join(sub[lbl2].fillna("").astype(str).tolist())
                return " · ".join(sub[col_val].astype(str).tolist())

            rows_dic, grupo = [], ""
            for _, row in df_inst.iterrows():
                tipo_raw = str(row.get(col_type, "")).strip()
                nombre   = str(row.get(col_name, "")).strip()
                tipo_lo  = tipo_raw.lower()
                base     = tipo_lo.split()[0] if " " in tipo_lo else tipo_lo
                if base == "begin group":
                    grupo = str(row.get(col_lbl, "")).strip() if col_lbl else nombre
                    continue
                if base in ("end group","end repeat"):
                    grupo = ""; continue
                if base in SKIP_D or not nombre:
                    continue
                rows_dic.append({
                    "Variable":         nombre,
                    "Sección":          grupo,
                    "Tipo":             tipo_legible(tipo_raw),
                    "Etiqueta":         str(row.get(col_lbl, "")).strip() if col_lbl else "",
                    "Obligatoria":      "Sí" if str(row.get(col_req, "")).strip().lower()
                                              in ("yes","true","1") else "No",
                    "Salto (relevant)": str(row.get(col_rel, "")).strip() if col_rel else "",
                    "Constraint":       str(row.get(col_con, "")).strip() if col_con else "",
                    "Opciones":         opciones_choices(tipo_raw),
                })

            df_dic = pd.DataFrame(rows_dic).replace({"nan":"","None":""})

            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Total variables", len(df_dic))
            d2.metric("Obligatorias",    int((df_dic["Obligatoria"] == "Sí").sum()))
            d3.metric("Con salto lógico",int((df_dic["Salto (relevant)"] != "").sum()))
            d4.metric("Con constraint",  int((df_dic["Constraint"] != "").sum()))

            fa, fb = st.columns(2)
            with fa:
                tipo_f = st.selectbox("Filtrar por tipo:",
                    ["(todos)"] + sorted(df_dic["Tipo"].unique()), key="tipo_f")
            with fb:
                busq_d = st.text_input("Buscar variable o etiqueta:",
                    placeholder="ej: ingreso", key="busq_dic")

            df_show = df_dic.copy()
            if tipo_f != "(todos)":
                df_show = df_show[df_show["Tipo"] == tipo_f]
            if busq_d:
                mask = (df_show["Variable"].str.contains(busq_d, case=False, na=False) |
                        df_show["Etiqueta"].str.contains(busq_d, case=False, na=False))
                df_show = df_show[mask]

            st.dataframe(df_show, use_container_width=True, hide_index=True,
                column_config={
                    "Opciones":         st.column_config.TextColumn("Opciones", width="large"),
                    "Salto (relevant)": st.column_config.TextColumn("Salto lógico", width="medium"),
                })

            buf_dic = io.BytesIO()
            with pd.ExcelWriter(buf_dic, engine="openpyxl") as w:
                df_dic.to_excel(w, sheet_name="Diccionario ODK", index=False)
            st.download_button(
                "⬇ Exportar diccionario (Excel)",
                data=buf_dic.getvalue(),
                file_name=f"diccionario_{archivo_enc.name.split('.')[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # ── TAB 3: Auditoría de Programación ─────────────────────
    with tab_aud:
        st.markdown("<div class='section-title'>Auditoría automática de programación</div>",
                    unsafe_allow_html=True)

        if not col_lbl:
            st.markdown("""
            <div class='eq-warn'>
                ⚠ No se detectó columna de labels en este instrumento.<br>
                Columnas encontradas: <code>{}</code><br>
                Se omite la revisión de labels — se revisan solo choices y constraints.
            </div>""".format(", ".join(df_inst.columns[:12].tolist())), unsafe_allow_html=True)

        df_alertas = auditar_instrumento(df_inst, df_ch, col_lbl)

        if df_alertas.empty:
            st.markdown("<div class='eq-ok'>✅ No se encontraron problemas en la programación.</div>",
                        unsafe_allow_html=True)
        else:
            errores    = df_alertas[df_alertas["Nivel"] == "Error"]
            advertenc  = df_alertas[df_alertas["Nivel"] == "Advertencia"]
            infos      = df_alertas[df_alertas["Nivel"] == "Info"]

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Total hallazgos", len(df_alertas))
            a2.metric("🔴 Errores críticos", len(errores))
            a3.metric("🟡 Advertencias",     len(advertenc))
            a4.metric("🔵 Informativo",      len(infos))

            if not errores.empty:
                st.markdown("<div class='eq-err'>Errores críticos detectados — corregir antes de publicar.</div>",
                            unsafe_allow_html=True)
            elif not advertenc.empty:
                st.markdown("<div class='eq-warn'>Advertencias — revisar si aplican al diseño del instrumento.</div>",
                            unsafe_allow_html=True)

            # Colores por nivel
            def color_nivel(val):
                if val == "Error":       return "background-color:#fff0ec;color:#c0392b;font-weight:700;"
                if val == "Advertencia": return "background-color:#fffbec;color:#b7770d;font-weight:700;"
                return "background-color:#e8f0ff;color:#1955a6;font-weight:600;"

            st.dataframe(
                df_alertas.style.map(color_nivel, subset=["Nivel"]),
                use_container_width=True, hide_index=True,
            )

            st.caption(
                "**Criterios de auditoría:** "
                "🔴 Error = rompe la encuesta (label vacío en campo visible, lista choices inexistente). "
                "🟡 Advertencia = mala práctica (campo numérico sin constraint). "
                "Solo se auditan campos visibles al encuestador — se ignoran metadatos del sistema, "
                "campos calculate, y variables estructurales."
            )

    # ── TAB 4: Choices ────────────────────────────────────────
    with tab_ch_tab:
        if df_ch is not None:
            st.markdown("<div class='section-title'>Listas de opciones (choices)</div>",
                        unsafe_allow_html=True)
            col_list = next((c for c in df_ch.columns if "list" in c.lower()), None)
            if col_list:
                listas = sorted(df_ch[col_list].dropna().unique())
                sel = st.selectbox("Filtrar por lista:", ["(mostrar todas)"] + list(listas))
                sub = df_ch if sel == "(mostrar todas)" else df_ch[df_ch[col_list] == sel]
                st.metric("Opciones mostradas", len(sub))
                st.dataframe(sub, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_ch, use_container_width=True, hide_index=True)
        else:
            st.markdown("<div class='eq-warn'>No se encontró hoja 'choices' en este archivo.</div>",
                        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 8. MÓDULO 2 — AUDITORÍA DE BASE DE DATOS
# Flujo: carga → configuración → flags → diagnóstico (missings + outliers)
#        → Motor de Corrección (editor, eliminación, imputación) → descarga.
# Guard principal: todo el contenido está dentro de
#   if st.session_state["df_work"] is not None:
# para evitar errores de renderizado con la base vacía al abrir la app.
# ══════════════════════════════════════════════════════════════
else:
    st.markdown("""
    <div class='eq-header'>
        <div class='eq-badge'>MÓDULO 2</div>
        <div class='eq-title'>Auditoría de Base de Datos</div>
        <p>Diagnóstico &nbsp;·&nbsp; Flags &nbsp;·&nbsp; Missings &nbsp;·&nbsp; Outliers &nbsp;·&nbsp; Corrección</p>
    </div>""", unsafe_allow_html=True)

    # ── Upload ────────────────────────────────────────────────
    cu1, cu2 = st.columns(2)
    with cu1:
        st.markdown("##### 🗄️ Base de datos")
        archivo_db = st.file_uploader(
            "Export de SurveyCTO, KoBo u otra plataforma",
            type=["csv", "xlsx"], key="db",
            label_visibility="visible",
        )
    with cu2:
        st.markdown("##### 📋 Instrumento *(opcional)*")
        archivo_inst = st.file_uploader(
            "Activa mapeo cruzado, etiquetas y validación de valores",
            type=["csv", "xlsx"], key="inst",
            label_visibility="visible",
        )

    if archivo_db is None:
        st.markdown("""
        <div style='text-align:center;padding:70px 20px;opacity:0.5;'>
            <div style='font-size:3rem;'>🗄️</div>
            <h3>Sube tu base de datos para comenzar</h3>
        </div>""", unsafe_allow_html=True)
        st.stop()

    df = leer_archivo(archivo_db)
    if st.session_state.archivo_activo != archivo_db.name:
        st.session_state.df_work      = df.copy()
        st.session_state.cambios_log  = []
        st.session_state.checkpoints  = {}
        st.session_state.eliminar_ids = set()
        st.session_state.archivo_activo = archivo_db.name

    # ── Instrumento opcional ──────────────────────────────────
    mapa_labels, mapa_tipos, df_ch_m2, inst_ok = {}, {}, None, False
    if archivo_inst:
        try:
            df_i2, df_ch_m2 = leer_instrumento(archivo_inst)
            cn = next((c for c in df_i2.columns if c.lower() == "name"), None)
            cl = normalizar_label(df_i2)
            ct = next((c for c in df_i2.columns if c.lower() == "type"), None)
            if cn:
                if cl: mapa_labels = dict(zip(df_i2[cn].astype(str), df_i2[cl].fillna("").astype(str)))
                if ct: mapa_tipos  = dict(zip(df_i2[cn].astype(str), df_i2[ct].fillna("").astype(str)))
                inst_ok = True
        except Exception:
            pass

    flags_previos = [c for c in df.columns
                     if c.lower().startswith("flag") or c.lower().endswith("_flag")]

    # ── Configuración ─────────────────────────────────────────
    with st.expander("⚙️ Configuración — columnas clave y umbrales", expanded=False):
        g1, g2, g3, g4, g5 = st.columns(5)
        with g1:
            opts_id = ["(usar índice)"] + list(df.columns)
            def_id  = next((i+1 for i,c in enumerate(df.columns)
                            if c.lower() in ["key","id","_id","uuid","id_encuesta"]), 0)
            sel_id  = st.selectbox("Columna ID:", opts_id, index=def_id)
            col_id  = None if sel_id == "(usar índice)" else sel_id
        with g2:
            opts_dur = ["(no disponible)"] + list(df.columns)
            def_dur  = next((i+1 for i,c in enumerate(df.columns)
                             if "durat" in c.lower()), 0)
            sel_dur  = st.selectbox("Columna duración (seg):", opts_dur, index=def_dur)
            col_dur  = None if sel_dur == "(no disponible)" else sel_dur
        with g3:
            min_min = st.number_input("Duración mínima (min):", 0, value=5, step=1)
        with g4:
            max_min = st.number_input("Duración máxima (min):", 1, value=120, step=5)
        with g5:
            # Auto-detectar columna de encuestador por nombre
            _ENC_KEYS = ["encuestador","surveyor","username","interviewer",
                         "enumerador","fieldworker","operador","recolector"]
            _def_enc_idx = next(
                (i+1 for i,c in enumerate(df.columns)
                 if any(k in c.lower() for k in _ENC_KEYS)), 0)
            opts_enc = ["(no disponible)"] + list(df.columns)
            sel_enc  = st.selectbox(
                "Columna encuestador:", opts_enc, index=_def_enc_idx,
                help="Se usa para desglosar missings y flags por encuestador. "
                     "Si tu base usa otro nombre, selecciónalo aquí.")
            _col_enc_new = None if sel_enc == "(no disponible)" else sel_enc
            # Persistir en session_state para que la sección missings lo lea
            st.session_state["col_enc_key"] = _col_enc_new

    # ── Calcular flags y outliers ─────────────────────────────
    df_flags = calcular_flags(df, col_id, col_dur, min_min, max_min)

    # ── Pre-cálculo de missings inteligentes (una sola vez) ──────────────────
    # Se calcula aquí, antes de los tabs, para reutilizarlo en:
    #   1. Corregir flag_missings (abajo, en este mismo bloque)
    #   2. Mostrar métricas y detalle en TAB 1 — Diagnóstico
    # Así evitamos llamar calcular_missings_inteligentes() tres veces.
    if inst_ok:
        _df_miss_enc_top, _df_miss_var_top, _vars_complejas_top = \
            calcular_missings_inteligentes(df, df_i2, col_id=col_id)
    else:
        _df_miss_enc_top, _df_miss_var_top, _vars_complejas_top = None, None, []

    # Si hay instrumento, corregir flag_missings con el conteo inteligente.
    # calcular_flags() usa nulls crudos (toda celda vacía = flag), lo que
    # penaliza saltos válidos. Aquí lo reemplazamos: flag=1 solo si la
    # encuesta tiene al menos 1 missing REAL según el relevant del instrumento.
    if inst_ok and _df_miss_enc_top is not None:
        # Agrupar por ID (por si hay duplicados) y mapear a flag binario
        miss_por_id = _df_miss_enc_top.groupby("ID")["Miss. reales"].sum()
        id_series   = (df[col_id].astype(str)
                       if (col_id and col_id in df.columns)
                       else pd.Series(df.index.astype(str)))
        df_flags["flag_missings"] = (
            id_series.map(miss_por_id).fillna(0).gt(0).astype(int).values
        )
        # Recalcular encuesta_válida con el flag_missings corregido
        df_flags["encuesta_válida"] = (
            (df_flags["flag_missings"]   == 0) &
            (df_flags["flag_duplicados"] == 0) &
            (df_flags["flag_duracion"]   == 0)
        ).astype(int)

    n_validas = int((df_flags["encuesta_válida"] == 1).sum())
    n_flags   = int((df_flags["encuesta_válida"] == 0).sum())

    cols_num = [c for c in df.select_dtypes(include="number").columns
                if not (col_dur and c == col_dur) and c not in flags_previos]
    resultados_iqr, outliers_det = [], []
    for col in cols_num:
        serie = df[col].dropna()
        if serie.empty:
            continue
        q1, q3 = serie.quantile(.25), serie.quantile(.75)
        iqr = q3 - q1; li, ls = q1 - 1.5*iqr, q3 + 1.5*iqr
        n_out = int(((serie < li) | (serie > ls)).sum())
        resultados_iqr.append({
            "Variable": col,
            "Etiqueta": mapa_labels.get(col, "—"),
            "Min":  round(serie.min(), 2), "Max": round(serie.max(), 2),
            "Q1":   round(q1, 2),          "Q3":  round(q3, 2),
            "Lím. Inf.": round(li, 2),     "Lím. Sup.": round(ls, 2),
            "N Outliers": n_out,
            "% Outliers": round(n_out / len(serie) * 100, 1),
        })
        for idx in df[(df[col] < li) | (df[col] > ls)].index:
            id_val = str(df.loc[idx, col_id]) if (col_id and col_id in df.columns) else str(idx)
            outliers_det.append({
                "ID":          id_val,
                "Variable":    col,
                "Etiqueta":    mapa_labels.get(col, "—"),
                "Valor":       round(df.loc[idx, col], 4),
                "Lím. Inf.":   round(li, 4),
                "Lím. Sup.":   round(ls, 4),
                "Dirección":   "↑ Sobre límite" if df.loc[idx, col] > ls else "↓ Bajo límite",
            })

    resumen_iqr = pd.DataFrame(resultados_iqr)
    df_out_det  = pd.DataFrame(outliers_det)
    total_out   = int(resumen_iqr["N Outliers"].sum()) if not resumen_iqr.empty else 0

    st.markdown(
        f"<div class='eq-ok'>"
        f"<b>{archivo_db.name}</b> &nbsp;·&nbsp; {len(df):,} registros &nbsp;·&nbsp; "
        f"{len(df.columns)} variables"
        + (f" &nbsp;|&nbsp; Instrumento: <b>{archivo_inst.name}</b>" if inst_ok else "")
        + (f" &nbsp;|&nbsp; <b>{len(flags_previos)}</b> flag(s) pre-existentes" if flags_previos else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["📊 Diagnóstico", "🔀 Mapeo de Instrumento",
                    "🔧 Motor de Corrección", "⬇ Descarga"])

    # ════════════════════════════════════════════════════════
    # TAB 1 — DIAGNÓSTICO
    # ════════════════════════════════════════════════════════
    with tabs[0]:
        st.markdown("<div class='section-title'>Resumen ejecutivo</div>", unsafe_allow_html=True)

        # Los missings no se muestran en el resumen ejecutivo.
        # El detalle completo (con contexto y gráficas) está en la sección
        # Missings más abajo. Los resultados ya calculados antes de los tabs
        # (_df_miss_enc_top, _df_miss_var_top, _vars_complejas_top) se
        # reutilizan directamente en esa sección.

        # Resumen ejecutivo: 4 métricas fijas, sin missings en el top.
        # Los missings se muestran con contexto completo en la sección de abajo.
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Total encuestas",  f"{len(df):,}")
        s2.metric("Filas duplicadas", f"{int(df.duplicated().sum()):,}")
        s3.metric("Total outliers",   f"{total_out:,}")
        s4.metric("Encuestas válidas", f"{n_validas:,}",
                  delta=f"-{n_flags} con flags", delta_color="inverse")

        # Flags pre-existentes
        if flags_previos:
            st.markdown("<div class='section-title'>Flags pre-existentes</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='eq-warn'>La base ya contiene <b>{len(flags_previos)}</b> "
                f"columna(s) de flags: "
                f"{'  '.join([f'<code>{f}</code>' for f in flags_previos])}</div>",
                unsafe_allow_html=True)
            ids_ = (df[col_id].astype(str) if (col_id and col_id in df.columns)
                    else pd.Series(df.index.astype(str)))
            df_fp = pd.DataFrame({"ID": ids_.values})
            for fp in flags_previos:
                df_fp[fp] = df[fp].values
            st.dataframe(colorear_flags(df_fp), use_container_width=True, hide_index=True)

        # Flags calculados
        st.markdown("<div class='section-title'>Flags calculados por la app</div>", unsafe_allow_html=True)
        df_fl = df_flags.copy()
        df_fl["encuesta_válida"] = df_fl["encuesta_válida"].map({1: "✅ Válida", 0: "⚠️ Con problema"})
        cols_fl = ["ID", "Missings", "flag_missings", "flag_duplicados",
                   "Duración (min)", "flag_duracion", "encuesta_válida"]
        if df_flags["flag_duracion"].sum() == 0 and not col_dur:
            cols_fl = [c for c in cols_fl if c not in ("Duración (min)", "flag_duracion")]
        st.dataframe(colorear_flags(df_fl[cols_fl]), use_container_width=True, hide_index=True)

        st.divider()

        # ── Missings ─────────────────────────────────────────
        st.markdown("<div class='section-title'>Missings</div>", unsafe_allow_html=True)

        # ── Detectar columna de encuestador ─────────────────
        # Se auto-detecta en el expander de configuración; aquí solo leemos
        # el valor ya guardado en session_state.
        col_enc = st.session_state.get("col_enc_key")

        # Reusar los ya calculados arriba para el resumen ejecutivo
        if inst_ok:
            df_miss_enc  = _df_miss_enc_top
            df_miss_var  = _df_miss_var_top
            vars_complejas = _vars_complejas_top
        else:
            df_miss_enc, df_miss_var, vars_complejas = None, None, []

        # Los missings se dividen en dos categorías:
        #   1. Obligatorios: variables que el usuario selecciona manualmente
        #   2. Condicionados: variables cuya obligatoriedad depende del relevant del instrumento

        miss_tab_oblig, miss_tab_cond = st.tabs(["📋 Obligatorios", "🔀 Condicionados"])

        # ══════════════════════════════════════════════════════
        # CATEGORÍA 1 — MISSINGS OBLIGATORIOS
        # El usuario selecciona manualmente las variables que
        # siempre deben tener respuesta (10-15 variables core).
        # No se usa lógica relevant — celda vacía = missing real.
        # ══════════════════════════════════════════════════════
        with miss_tab_oblig:
            st.markdown(
                "Selecciona las variables que **siempre deben tener respuesta** en tu encuesta "
                "(p. ej. identificador, nombre, consentimiento, módulos centrales). "
                "La plataforma contará como missing cualquier celda vacía en estas variables, "
                "sin importar condiciones de salto.",
                unsafe_allow_html=False)

            # Opciones de variables: excluir metadatos y col_id
            _SYS = {"start","end","today","deviceid","username","duration",
                    "_id","_uuid","uuid","key","_index","_parent_index",
                    "_submission_time","_submitted_by","_version","_tags",
                    "_notes","meta","instanceid","instancename"}
            _opts_oblig = [
                c for c in df.columns
                if c != col_id
                and c.lower().strip() not in _SYS
                and not c.lower().startswith(("_", "meta/"))
            ]

            vars_oblig = st.multiselect(
                "Variables obligatorias:",
                options=_opts_oblig,
                default=st.session_state.get("vars_obligatorias", []),
                format_func=lambda c: f"{c}  —  {mapa_labels[c]}" if c in mapa_labels else c,
                help="Escoge entre 5 y 20 variables core. "
                     "El análisis es inmediato cada vez que cambias la selección.",
                key="vars_obligatorias",
            )

            if not vars_oblig:
                st.info("Selecciona al menos una variable para activar el análisis de missings obligatorios.")
            else:
                _df_enc_ob, _df_var_ob, _df_por_enc_ob = calcular_missings_obligatorios(
                    df, tuple(vars_oblig), col_id=col_id, col_enc=col_enc)  # tuple para cache

                if _df_enc_ob is not None:
                    _total_ob   = int(_df_enc_ob["Miss. oblig."].sum())
                    _enc_afect  = int((_df_enc_ob["Miss. oblig."] > 0).sum())
                    _pct_afect  = round(_enc_afect / len(df) * 100, 1)

                    oo1, oo2, oo3, oo4 = st.columns(4)
                    oo1.metric("Variables auditadas", len(vars_oblig))
                    oo2.metric("Missings obligatorios", f"{_total_ob:,}")
                    oo3.metric("Encuestas afectadas",   f"{_enc_afect:,}")
                    oo4.metric("% encuestas afectadas", f"{_pct_afect}%")

                    # Sub-tabs: Por variable | Por encuesta | Por encuestador
                    ob_t1, ob_t2, ob_t3 = st.tabs(
                        ["Por variable", "Por encuesta", "👤 Por encuestador"])

                    with ob_t1:
                        if _df_var_ob is None or _df_var_ob.empty or _df_var_ob["Miss. oblig."].sum() == 0:
                            st.markdown("<div class='eq-ok'>✅ Sin missings en estas variables.</div>",
                                        unsafe_allow_html=True)
                        else:
                            _dvf = _df_var_ob[_df_var_ob["Miss. oblig."] > 0].copy()
                            st.dataframe(_dvf, use_container_width=True, hide_index=True)
                            pb, pp, pt, pg = plot_colors()
                            _med = _dvf["Miss. oblig."].mean()
                            _std = _dvf["Miss. oblig."].std() if len(_dvf) > 1 else 0
                            _etq = [mapa_labels.get(c, c) for c in _dvf["Variable"]]
                            fig_ob = go.Figure(go.Bar(
                                y=_etq, x=_dvf["Miss. oblig."].values, orientation="h",
                                marker_color=colores_semaforo(_dvf["Miss. oblig."].values, _med, _std),
                                marker_line_width=0,
                                text=[f"{v} ({p}%)" for v, p in zip(
                                    _dvf["Miss. oblig."], _dvf["% Miss."])],
                                textposition="outside", textfont=dict(color=pt, size=11),
                            ))
                            fig_ob.update_layout(
                                margin=dict(l=0, r=90, t=20, b=0),
                                height=max(260, len(_dvf) * 38),
                                plot_bgcolor=pb, paper_bgcolor=pp,
                                xaxis=dict(showgrid=True, gridcolor=pg, color=pt),
                                yaxis=dict(showgrid=False, autorange="reversed", color=pt),
                            )
                            st.plotly_chart(fig_ob, use_container_width=True)

                    with ob_t2:
                        _def = _df_enc_ob[_df_enc_ob["Miss. oblig."] > 0].sort_values(
                            "Miss. oblig.", ascending=False).reset_index(drop=True)
                        if _def.empty:
                            st.markdown("<div class='eq-ok'>✅ Ninguna encuesta tiene missings en estas variables.</div>",
                                        unsafe_allow_html=True)
                        else:
                            st.dataframe(_def, use_container_width=True, hide_index=True)

                    with ob_t3:
                        if col_enc is None:
                            st.info(
                                "No se detectó columna de encuestador. "
                                "Configúrala en **⚙️ Configuración** (arriba) para ver este desglose.")
                        elif _df_por_enc_ob is None or _df_por_enc_ob.empty:
                            st.markdown("<div class='eq-ok'>✅ Sin missings por encuestador.</div>",
                                        unsafe_allow_html=True)
                        else:
                            st.caption("Resumen de missings obligatorios por encuestador:")
                            st.dataframe(_df_por_enc_ob, use_container_width=True, hide_index=True)

                            # Detalle expandible por encuestador
                            for enc_name in _df_por_enc_ob["Encuestador"].tolist():
                                _df_enc_rows = _df_enc_ob[
                                    (_df_enc_ob["Encuestador"] == enc_name) &
                                    (_df_enc_ob["Miss. oblig."] > 0)
                                ].sort_values("Miss. oblig.", ascending=False)
                                if _df_enc_rows.empty:
                                    continue
                                n_miss_enc = int(_df_enc_rows["Miss. oblig."].sum())
                                with st.expander(
                                    f"👤 {enc_name} — {n_miss_enc} missing(s) en "
                                    f"{len(_df_enc_rows)} encuesta(s)", expanded=False):
                                    st.dataframe(_df_enc_rows.reset_index(drop=True),
                                                 use_container_width=True, hide_index=True)

        # ══════════════════════════════════════════════════════
        # CATEGORÍA 2 — MISSINGS CONDICIONADOS
        # Usa la lógica relevant del instrumento para determinar
        # cuándo cada variable es obligatoria. Solo disponible
        # cuando se cargó el instrumento.
        # ══════════════════════════════════════════════════════
        with miss_tab_cond:
            # ── Con instrumento ──────────────────────────────
            if df_miss_enc is not None:
                # ── Análisis inteligente ─────────────────────
                total_miss_real  = int(df_miss_enc["Miss. reales"].sum())
                total_skip_inv   = int(df_miss_enc["Skips inválidos"].sum())
                enc_con_miss     = int((df_miss_enc["Miss. reales"] > 0).sum())
                enc_con_skip     = int((df_miss_enc["Skips inválidos"] > 0).sum())

                # Total crudo para comparación
                total_crudo = int(df.isnull().sum().sum())

            mi1, mi2, mi3, mi4 = st.columns(4)
            mi1.metric("Missings reales",    f"{total_miss_real:,}",
                       help="Celdas vacías que SÍ debían tener dato (condición relevant cumplida o sin condición)")
            mi2.metric("Skips inválidos",    f"{total_skip_inv:,}",
                       help="Celdas con dato cuando la pregunta NO debía mostrarse (posible error de programación)")
            mi3.metric("Encuestas afectadas",f"{enc_con_miss:,}",
                       help="Encuestas con al menos 1 missing real")
            mi4.metric("Celdas vacías crudas",f"{total_crudo:,}",
                       help="Total de celdas NULL en la base sin considerar relevancia (número inflado)")

            if total_miss_real < total_crudo:
                diff = total_crudo - total_miss_real
                st.markdown(
                    f"<div class='eq-ok'>"
                    f"✅ Al aplicar las reglas de relevancia del instrumento, "
                    f"el número real de missings baja de <b>{total_crudo:,}</b> a "
                    f"<b>{total_miss_real:,}</b> "
                    f"(<b>{diff:,}</b> celdas vacías son saltos válidos, no missings)."
                    f"</div>", unsafe_allow_html=True)
            elif total_miss_real == 0:
                st.markdown("<div class='eq-ok'>✅ No hay missings reales en la base.</div>",
                            unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='eq-warn'>"
                    f"<b>{total_miss_real:,}</b> missing(s) real(es) en "
                    f"<b>{enc_con_miss}</b> encuesta(s)."
                    f"</div>", unsafe_allow_html=True)

            if total_skip_inv > 0:
                st.markdown(
                    f"<div class='eq-err'>"
                    f"⚠️ <b>{total_skip_inv:,}</b> skip inválido(s): preguntas con dato "
                    f"cuando la condición relevant era falsa — posible error de programación "
                    f"o de digitación."
                    f"</div>", unsafe_allow_html=True)

            tab_m1, tab_m2, tab_m3, tab_m4 = st.tabs(
                ["Por variable", "Por encuesta", "👤 Por encuestador", "Skips inválidos"])

            with tab_m1:
                df_var_f = df_miss_var[df_miss_var["Miss. reales"] > 0].copy()
                if df_var_f.empty:
                    st.markdown("<div class='eq-ok'>Sin missings reales por variable.</div>",
                                unsafe_allow_html=True)
                else:
                    media_m = df_var_f["Miss. reales"].mean()
                    std_m   = df_var_f["Miss. reales"].std() if len(df_var_f) > 1 else 0
                    umb_2sd = media_m + 2 * std_m
                    df_var_f["Nivel"] = df_var_f["Miss. reales"].apply(
                        lambda v: "🔴 Crítico" if v >= umb_2sd
                        else "🟡 Alerta" if v >= media_m + std_m
                        else "🟢 Normal")
                    st.dataframe(
                        df_var_f[["Variable","Miss. reales","% Miss. reales","Nivel","Tipo",
                                  "Condición relevant"]],
                        use_container_width=True, hide_index=True)

                    pb, pp, pt, pg = plot_colors()
                    etq = [mapa_labels.get(c, c) for c in df_var_f["Variable"]]
                    fig_m = go.Figure(go.Bar(
                        y=etq, x=df_var_f["Miss. reales"].values,
                        orientation="h",
                        marker_color=colores_semaforo(
                            df_var_f["Miss. reales"].values, media_m, std_m),
                        marker_line_width=0,
                        text=[f"{v} ({p}%)" for v, p in zip(
                            df_var_f["Miss. reales"], df_var_f["% Miss. reales"])],
                        textposition="outside",
                        textfont=dict(color=pt, size=11),
                    ))
                    if umb_2sd > 0:
                        fig_m.add_vline(x=umb_2sd, line_dash="dash",
                            line_color="#f7966b", line_width=2,
                            annotation_text=f"Umbral crítico ({umb_2sd:.1f})",
                            annotation_font_color=pt,
                            annotation_position="top right")
                    fig_m.update_layout(
                        margin=dict(l=0, r=90, t=20, b=0),
                        height=max(280, len(df_var_f) * 38),
                        plot_bgcolor=pb, paper_bgcolor=pp,
                        xaxis=dict(showgrid=True, gridcolor=pg, color=pt),
                        yaxis=dict(showgrid=False, autorange="reversed", color=pt),
                    )
                    st.plotly_chart(fig_m, use_container_width=True)

            with tab_m2:
                df_enc_f = df_miss_enc[df_miss_enc["Miss. reales"] > 0].copy()
                if df_enc_f.empty:
                    st.markdown("<div class='eq-ok'>Sin encuestas con missings reales.</div>",
                                unsafe_allow_html=True)
                else:
                    # Agregar columna de encuestador si está disponible
                    if col_enc and col_enc in df.columns:
                        _id_to_enc = {}
                        for _, _r in df.iterrows():
                            _idk = str(_r[col_id]) if (col_id and col_id in df.columns) else str(_r.name)
                            _id_to_enc[_idk] = str(_r[col_enc])
                        df_enc_f = df_enc_f.copy()
                        df_enc_f.insert(1, "Encuestador",
                                        df_enc_f["ID"].map(_id_to_enc).fillna("—"))
                    st.dataframe(df_enc_f.sort_values("Miss. reales", ascending=False),
                                 use_container_width=True, hide_index=True)

            with tab_m3:
                # Resumen por encuestador usando missings condicionados
                if col_enc is None:
                    st.info("Configura la columna de encuestador en **⚙️ Configuración** para ver este desglose.")
                else:
                    # Unir col_enc a df_miss_enc usando col_id
                    _id_enc_map = {}
                    for _, _r in df.iterrows():
                        _idk = str(_r[col_id]) if (col_id and col_id in df.columns) else str(_r.name)
                        _id_enc_map[_idk] = str(_r[col_enc])
                    _df_cond_enc = df_miss_enc.copy()
                    _df_cond_enc["Encuestador"] = _df_cond_enc["ID"].map(_id_enc_map).fillna("—")
                    _df_cond_grp = (
                        _df_cond_enc.groupby("Encuestador")
                        .agg(**{
                            "N encuestas":    ("ID",             "count"),
                            "Miss. reales":   ("Miss. reales",   "sum"),
                            "Enc. afectadas": ("Miss. reales",   lambda x: (x > 0).sum()),
                        })
                        .reset_index()
                    )
                    _df_cond_grp["% afectadas"] = (
                        _df_cond_grp["Enc. afectadas"] / _df_cond_grp["N encuestas"] * 100
                    ).round(1)
                    _df_cond_grp = _df_cond_grp.sort_values("Miss. reales", ascending=False).reset_index(drop=True)
                    st.caption("Missings condicionados (relevant) por encuestador:")
                    st.dataframe(_df_cond_grp, use_container_width=True, hide_index=True)

                    # Detalle expandible por encuestador
                    for _enc_n in _df_cond_grp["Encuestador"].tolist():
                        _rows_enc = _df_cond_enc[
                            (_df_cond_enc["Encuestador"] == _enc_n) &
                            (_df_cond_enc["Miss. reales"] > 0)
                        ].sort_values("Miss. reales", ascending=False)
                        if _rows_enc.empty:
                            continue
                        with st.expander(
                            f"👤 {_enc_n} — {int(_rows_enc['Miss. reales'].sum())} missing(s) en "
                            f"{len(_rows_enc)} encuesta(s)", expanded=False):
                            st.dataframe(_rows_enc.drop(columns=["Encuestador"]).reset_index(drop=True),
                                         use_container_width=True, hide_index=True)

            with tab_m4:
                df_skip_f = df_miss_enc[df_miss_enc["Skips inválidos"] > 0].copy()
                if df_skip_f.empty:
                    st.markdown(
                        "<div class='eq-ok'>✅ Sin skips inválidos detectados.</div>",
                        unsafe_allow_html=True)
                else:
                    st.caption(
                        "Estas encuestas tienen dato en campos que debían estar vacíos "
                        "según la lógica de salto del instrumento.")
                    st.dataframe(
                        df_skip_f[["ID","Skips inválidos","Variables con skip inv."]]
                        .sort_values("Skips inválidos", ascending=False),
                        use_container_width=True, hide_index=True)

            st.caption(
                "**Limitantes del análisis:** "
                "Expresiones XPath no parseables (funciones avanzadas como "
                "`pulldata()`, `regex()`, `count-selected()`) se tratan como "
                "siempre requeridas — pueden inflar ligeramente el conteo. "
                "Variables del instrumento ausentes en la base son omitidas.")

            # ── Ajuste manual para variables con expresiones complejas ──────
            if vars_complejas:
                n_comp = len(vars_complejas)
                with st.expander(
                    f"⚙️ {n_comp} variable(s) que no pudimos evaluar automáticamente "
                    f"— revisión manual opcional", expanded=False):
                    st.markdown(
                        "Algunas preguntas tienen condiciones de salto con funciones "
                        "avanzadas (p. ej. `pulldata()`, `regex()`) que la plataforma "
                        "no puede interpretar automáticamente. Por eso las tratamos "
                        "como **siempre obligatorias** (criterio conservador). "
                        "Si sabes que alguna de estas variables en realidad **no era obligatoria** "
                        "para todos los registros, desmarca la casilla — así el conteo de "
                        "missings será más preciso.")
                    st.markdown("---")

                    # Inicializar defaults en session_state la primera vez que aparece cada variable
                    for row in vars_complejas:
                        sk = f"ovr_{row['Variable']}"
                        if sk not in st.session_state:
                            st.session_state[sk] = True   # por defecto: obligatoria

                    # Mostrar una fila por variable
                    for row in vars_complejas:
                        vname = row["Variable"]
                        etq   = row["Etiqueta"]
                        cond  = row["Condición"]
                        sk    = f"ovr_{vname}"
                        col_chk, col_lbl = st.columns([1, 11])
                        with col_chk:
                            # key vincula el widget directamente a st.session_state[sk]
                            st.checkbox(
                                label=vname,
                                key=sk,
                                label_visibility="collapsed")
                        with col_lbl:
                            es_oblig  = st.session_state[sk]
                            estado_txt = "✅ obligatoria" if es_oblig else "⏭️ ignorar (skip válido)"
                            st.markdown(
                                f"**{etq}**  \n"
                                f"<span style='font-size:0.82em;color:gray'>"
                                f"Variable: `{vname}` &nbsp;|&nbsp; "
                                f"Condición: `{cond}`</span>  \n"
                                f"<span style='font-size:0.82em'>{estado_txt}</span>",
                                unsafe_allow_html=True)

                    # Calcular impacto del ajuste — leer directo de session_state
                    vars_ignoradas = [
                        row["Variable"] for row in vars_complejas
                        if not st.session_state.get(f"ovr_{row['Variable']}", True)
                    ]
                    if vars_ignoradas:
                        # Recalcular con las variables ignoradas excluidas de los missings
                        miss_ajustado = int(df_miss_var[
                            ~df_miss_var["Variable"].isin(vars_ignoradas)
                        ]["Miss. reales"].sum()) if df_miss_var is not None else total_miss_real

                        reduccion = total_miss_real - miss_ajustado
                        if reduccion > 0:
                            st.markdown(
                                f"<div class='eq-info'>"
                                f"📊 <b>Ajuste aplicado:</b> al ignorar "
                                f"<b>{len(vars_ignoradas)}</b> variable(s), "
                                f"el conteo de missings reales baja de "
                                f"<b>{total_miss_real:,}</b> → <b>{miss_ajustado:,}</b> "
                                f"(−{reduccion:,} celdas)."
                                f"</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(
                                "<div class='eq-info'>"
                                "📊 Las variables desmarcadas no tenían missings, "
                                "el conteo total no cambia."
                                "</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(
                            "<div class='eq-info'>"
                            "💡 Todas las variables ambiguas se están contando como obligatorias. "
                            "Desmarca las que en tu encuesta sean saltos válidos para afinar el conteo."
                            "</div>", unsafe_allow_html=True)

            else:
                # ── Modo básico (sin instrumento) ────────────────
                # Excluir automáticamente columnas de sistema/metadatos
                SYS_COLS = {
                    "start","end","today","deviceid","username","duration",
                    "_id","_uuid","uuid","key","_index","_parent_index",
                    "_submission_time","_submitted_by","_version","_tags",
                    "_notes","meta","instanceid","instancename",
                }
                cols_datos = [
                    c for c in df.columns
                    if c != col_id and c.lower().strip() not in SYS_COLS
                    and not c.lower().startswith(("_", "meta/"))
                ]
    
                st.markdown(
                    f"<div class='eq-warn'>"
                    f"⚠️ <b>Sin instrumento</b> — se muestran celdas vacías en las "
                    f"<b>{len(cols_datos)}</b> variable(s) de contenido "
                    f"(metadatos del sistema excluidos automáticamente). "
                    f"El conteo puede estar inflado si la encuesta tiene saltos lógicos. "
                    f"Carga el instrumento para un análisis que respete esas condiciones."
                    f"</div>", unsafe_allow_html=True)
    
                df_rev  = df[cols_datos]
                miss_v  = df_rev.isnull().sum()
                cols_mv = miss_v[miss_v > 0].sort_values(ascending=False)
                media_m = cols_mv.mean() if len(cols_mv) > 1 else 0
                std_m   = cols_mv.std()  if len(cols_mv) > 1 else 0
                umb_2sd = media_m + 2 * std_m
    
                n_miss_total = int(df_rev.isnull().sum().sum())
                n_enc_miss   = int((df_rev.isnull().sum(axis=1) > 0).sum())
                mb1, mb2, mb3 = st.columns(3)
                mb1.metric("Variables analizadas",  len(cols_datos))
                mb2.metric("Celdas vacías",         f"{n_miss_total:,}")
                mb3.metric("Encuestas afectadas",   f"{n_enc_miss:,}")
    
                if cols_mv.empty:
                    st.markdown("<div class='eq-ok'>✅ No hay celdas vacías en las variables de contenido.</div>",
                                unsafe_allow_html=True)
                else:
                    t1, t2 = st.columns(2)
                    with t1:
                        st.caption("**Por encuesta**")
                        n_mf = df_rev.isnull().sum(axis=1)
                        ids_ = (df[col_id].astype(str) if (col_id and col_id in df.columns)
                                else pd.Series(df.index.astype(str)))
                        tbl_id = pd.DataFrame({
                            "ID": ids_.values,
                            "Celdas vacías": n_mf.values,
                            "Variables": [
                                ", ".join([c for c in cols_datos if pd.isnull(df.loc[i, c])])
                                for i in df.index],
                        })
                        tbl_id = (tbl_id[tbl_id["Celdas vacías"] > 0]
                                  .sort_values("Celdas vacías", ascending=False)
                                  .reset_index(drop=True))
                        st.dataframe(tbl_id, use_container_width=True, hide_index=True)
                    with t2:
                        st.caption("**Por variable**")
                        tbl_var = pd.DataFrame({
                            "Variable": cols_mv.index,
                            "Celdas vacías": cols_mv.values,
                            "% del total": (cols_mv.values / len(df) * 100).round(1),
                            "Nivel": ["🔴 Crítico" if v >= umb_2sd
                                      else "🟡 Alerta" if v >= media_m + std_m
                                      else "🟢 Normal" for v in cols_mv.values],
                        }).reset_index(drop=True)
                        st.dataframe(tbl_var, use_container_width=True, hide_index=True)
    
                    pb, pp, pt, pg = plot_colors()
                    fig_m = go.Figure(go.Bar(
                        y=list(cols_mv.index), x=cols_mv.values, orientation="h",
                        marker_color=colores_semaforo(cols_mv.values, media_m, std_m),
                        marker_line_width=0,
                        text=[f"{v} ({v/len(df)*100:.1f}%)" for v in cols_mv.values],
                        textposition="outside", textfont=dict(color=pt, size=11),
                    ))
                    if umb_2sd > 0:
                        fig_m.add_vline(x=umb_2sd, line_dash="dash",
                            line_color="#f7966b", line_width=2,
                            annotation_text=f"Umbral ({umb_2sd:.1f})",
                            annotation_font_color=pt, annotation_position="top right")
                    fig_m.update_layout(
                        margin=dict(l=0, r=80, t=20, b=0),
                        height=max(280, len(cols_mv) * 38),
                        plot_bgcolor=pb, paper_bgcolor=pp,
                        xaxis=dict(showgrid=True, gridcolor=pg, color=pt),
                        yaxis=dict(showgrid=False, autorange="reversed", color=pt),
                    )
                    st.plotly_chart(fig_m, use_container_width=True)

        st.divider()

        # Outliers
        st.markdown("<div class='section-title'>Outliers por variable (método IQR)</div>",
                    unsafe_allow_html=True)
        if resumen_iqr.empty:
            st.markdown("<div class='eq-warn'>Sin columnas numéricas para analizar.</div>",
                        unsafe_allow_html=True)
        else:
            con_out = resumen_iqr[resumen_iqr["N Outliers"] > 0]
            o1, o2, o3 = st.columns(3)
            o1.metric("Variables numéricas", len(resumen_iqr))
            o2.metric("Con outliers",        len(con_out))
            o3.metric("Total outliers",      f"{total_out:,}")

            if not con_out.empty:
                pb, pp, pt, pg = plot_colors()
                n_o    = con_out["N Outliers"].values
                med_o  = n_o.mean(); std_o = n_o.std() if len(n_o) > 1 else 0
                etq_o  = [mapa_labels.get(c, c) if inst_ok else c for c in con_out["Variable"]]
                fig_o  = go.Figure(go.Bar(
                    y=etq_o, x=n_o, orientation="h",
                    marker_color=colores_semaforo(n_o, med_o, std_o),
                    marker_line_width=0,
                    text=[f"{v} ({p}%)" for v, p in zip(con_out["N Outliers"], con_out["% Outliers"])],
                    textposition="outside", textfont=dict(color=pt, size=11),
                ))
                fig_o.update_layout(
                    margin=dict(l=0, r=90, t=10, b=0),
                    height=max(260, len(con_out) * 40),
                    plot_bgcolor=pb, paper_bgcolor=pp,
                    xaxis=dict(showgrid=True, gridcolor=pg, color=pt),
                    yaxis=dict(showgrid=False, autorange="reversed", color=pt),
                )
                st.plotly_chart(fig_o, use_container_width=True)

            tbl_iqr = resumen_iqr.copy()
            if not inst_ok:
                tbl_iqr = tbl_iqr.drop(columns=["Etiqueta"])
            st.dataframe(
                tbl_iqr.sort_values("N Outliers", ascending=False),
                use_container_width=True, hide_index=True,
            )

    # ════════════════════════════════════════════════════════
    # TAB 2 — MAPEO
    # ════════════════════════════════════════════════════════
    with tabs[1]:
        if not inst_ok:
            st.markdown("""
            <div style='text-align:center;padding:60px 20px;opacity:0.5;'>
                <div style='font-size:3rem;'>📋</div>
                <h3>Carga el instrumento para activar este módulo</h3>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div class='section-title'>Diagnóstico cruzado instrumento ↔ base</div>",
                        unsafe_allow_html=True)
            vars_inst = set(mapa_labels.keys())
            vars_db   = set(df.columns)
            en_ambos  = vars_inst & vars_db
            solo_inst = vars_inst - vars_db
            solo_db   = vars_db   - vars_inst

            m1, m2, m3 = st.columns(3)
            m1.metric("Variables mapeadas",      len(en_ambos))
            m2.metric("Solo en instrumento",     len(solo_inst))
            m3.metric("Columnas huérfanas (DB)", len(solo_db))
            st.divider()

            cx, cy = st.columns(2)
            with cx:
                st.caption("**Variables mapeadas correctamente**")
                if en_ambos:
                    st.dataframe(pd.DataFrame({
                        "Variable":         sorted(en_ambos),
                        "Etiqueta":         [mapa_labels.get(c, "") for c in sorted(en_ambos)],
                        "Tipo instrumento": [mapa_tipos.get(c, "")  for c in sorted(en_ambos)],
                        "Tipo en base":     [str(df[c].dtype)        for c in sorted(en_ambos)],
                    }), use_container_width=True, hide_index=True)
            with cy:
                if solo_inst:
                    st.caption("**En instrumento pero NO en la base**")
                    st.markdown(
                        "<div class='eq-warn'>Pueden ser variables condicionales o no exportadas.</div>",
                        unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame({
                        "Variable": sorted(solo_inst),
                        "Etiqueta": [mapa_labels.get(c, "") for c in sorted(solo_inst)],
                    }), use_container_width=True, hide_index=True)
                if solo_db:
                    st.caption("**Columnas huérfanas (en base, sin definición en instrumento)**")
                    st.markdown(
                        "<div class='eq-err'>Típicamente metadatos del sistema (_id, _uuid) "
                        "o variables no documentadas.</div>", unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame({
                        "Variable":    sorted(solo_db),
                        "Tipo en base":[str(df[c].dtype) for c in sorted(solo_db)],
                    }), use_container_width=True, hide_index=True)

            # Validación select_one
            if df_ch_m2 is not None:
                st.divider()
                st.markdown("<div class='section-title'>Validación de valores (select_one)</div>",
                            unsafe_allow_html=True)
                col_list = next((c for c in df_ch_m2.columns if "list" in c.lower()), None)
                col_val  = next((c for c in df_ch_m2.columns if c.lower() == "name"), None)
                invalidos = []
                for var, tipo in mapa_tipos.items():
                    if "select_one" in str(tipo) and var in df.columns and col_list and col_val:
                        lista = str(tipo).replace("select_one", "").strip()
                        valid = set(df_ch_m2[df_ch_m2[col_list] == lista][col_val].astype(str))
                        if valid:
                            inv = df[var].dropna().astype(str)
                            n_inv_v = int((~inv.isin(valid)).sum())
                            if n_inv_v > 0:
                                invalidos.append({
                                    "Variable":         var,
                                    "Valores inválidos":n_inv_v,
                                    "Lista":            lista,
                                    "Ejemplos":         ", ".join(inv[~inv.isin(valid)].unique()[:5]),
                                })
                if invalidos:
                    st.markdown(
                        f"<div class='eq-err'>Valores fuera de lista en "
                        f"<b>{len(invalidos)}</b> variable(s).</div>", unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(invalidos), use_container_width=True, hide_index=True)
                else:
                    st.markdown(
                        "<div class='eq-ok'>✅ Todos los valores select_one son válidos.</div>",
                        unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # TAB 3 — MOTOR DE CORRECCIÓN
    # ════════════════════════════════════════════════════════
    with tabs[2]:
        df_w = st.session_state.df_work

        # ════════════════════════════════════════════════════════
        # EDITOR DE DATOS — edición celda a celda estilo Stata
        # ════════════════════════════════════════════════════════
        st.markdown("<div class='section-title'>✏️ Editor de datos</div>",
                    unsafe_allow_html=True)
        st.caption(
            "Edita cualquier celda directamente — útil para corregir valores tras "
            "verificar con el encuestador. Cada cambio queda registrado en el log. "
            "Columnas de sistema están bloqueadas.")

        # Columnas de sistema que no se deben editar
        _SYS_LOCK = {"_id","_uuid","_submission_time","deviceid","_version",
                     "_submitted_by","KEY","key","instanceid","instancename",
                     "_index","_parent_index","_tags","_notes"}
        _locked = [c for c in df_w.columns if c.lower() in _SYS_LOCK
                   or c.lower().startswith("_")]
        _editable = [c for c in df_w.columns if c not in _locked]

        # Construir column_config: bloqueadas en gris, editables libres
        _edit_cfg = {}
        for c in df_w.columns:
            if c in _locked:
                _edit_cfg[c] = st.column_config.TextColumn(c, disabled=True)
            else:
                # Detectar tipo para usar el widget correcto
                if pd.api.types.is_integer_dtype(df_w[c]):
                    _edit_cfg[c] = st.column_config.NumberColumn(c, disabled=False)
                elif pd.api.types.is_float_dtype(df_w[c]):
                    _edit_cfg[c] = st.column_config.NumberColumn(c, disabled=False,
                                                                  format="%.4f")
                else:
                    _edit_cfg[c] = st.column_config.TextColumn(c, disabled=False)

        edited_df = st.data_editor(
            df_w.copy(),
            column_config=_edit_cfg,
            hide_index=False,
            use_container_width=True,
            key="editor_datos",
            height=min(600, max(250, len(df_w) * 38 + 50)),
            num_rows="fixed",   # no permitir agregar/borrar filas desde aquí
        )

        # Detectar cambios comparando con df_w celda a celda
        _cambios_nuevos = []
        for _c in _editable:
            if _c not in edited_df.columns:
                continue
            for _i in df_w.index:
                _v_antes = df_w.at[_i, _c]
                _v_desp  = edited_df.at[_i, _c]
                # Comparar ignorando NaN==NaN
                _ambos_nan = pd.isna(_v_antes) and pd.isna(_v_desp)
                if not _ambos_nan and _v_antes != _v_desp:
                    _id_val = (str(df_w.at[_i, col_id])
                               if (col_id and col_id in df_w.columns)
                               else str(_i))
                    _cambios_nuevos.append({
                        "ID":       _id_val,
                        "Variable": _c,
                        "Antes":    _v_antes,
                        "Después":  _v_desp,
                    })

        if _cambios_nuevos:
            st.markdown(
                f"<div class='eq-warn'>"
                f"✏️ <b>{len(_cambios_nuevos)}</b> cambio(s) pendiente(s) — "
                f"presiona <b>Aplicar cambios</b> para guardarlos."
                f"</div>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(_cambios_nuevos),
                         use_container_width=True, hide_index=True)

            if st.button("💾 Aplicar cambios al dataset", type="primary",
                         key="btn_aplicar_edicion"):
                # Guardar en df_work
                st.session_state.df_work = edited_df.copy()
                # Registrar en log de cambios
                for _ch in _cambios_nuevos:
                    st.session_state.cambios_log.append(
                        f"[Editor manual] ID {_ch['ID']} · "
                        f"{_ch['Variable']}: «{_ch['Antes']}» → «{_ch['Después']}»"
                    )
                st.success(f"✅ {len(_cambios_nuevos)} cambio(s) guardados en el dataset.")
                st.rerun()
        else:
            st.markdown(
                "<div class='eq-ok'>Sin cambios pendientes — "
                "edita cualquier celda arriba para corregir valores.</div>",
                unsafe_allow_html=True)

        st.divider()

        # ── PASO 1: Decisión por encuesta ─────────────────────
        st.markdown("<div class='section-title'>Paso 1 — Selección de encuestas a eliminar</div>",
                    unsafe_allow_html=True)
        st.caption(
            "Marca la casilla **Eliminar** en cada encuesta que quieras quitar de la base. "
            "Puedes marcar/desmarcar cualquier fila libremente. "
            "Las encuestas con flags vienen pre-marcadas, pero puedes cambiarlas."
        )

        # Construir tabla de decisiones
        ids_col = (df_w[col_id].astype(str) if (col_id and col_id in df_w.columns)
                   else pd.Series(df_w.index.astype(str)))

        # Solo las filas que existen en df_w
        ids_en_trabajo = set(ids_col.values)
        flags_en_trabajo = df_flags[df_flags["ID"].astype(str).isin(ids_en_trabajo)].copy()

        eliminar_guardados = st.session_state.eliminar_ids

        # ── Construir tabla completa: flags + todos los datos de la base ──
        # Columnas fijas al inicio: ID, flags, Estado, Eliminar
        # Luego todas las columnas de df_w para poder ver la encuesta completa
        _col_enc_motor = st.session_state.get("col_enc_key")

        _dec_ids = flags_en_trabajo["ID"].astype(str).values

        # Columna Eliminar (checkbox)
        _eliminar_col = [
            (str(row["ID"]) in eliminar_guardados)
            if eliminar_guardados
            else (row["encuesta_válida"] == 0)
            for _, row in flags_en_trabajo.iterrows()
        ]

        # Armar df con flags primero
        df_dec = pd.DataFrame({
            "🗑 Eliminar":    _eliminar_col,
            "Estado":         flags_en_trabajo["encuesta_válida"].map(
                                  {1: "✅ Válida", 0: "⚠️ Con problema"}).values,
            "Miss.":          flags_en_trabajo["flag_missings"].values,
            "Dup.":           flags_en_trabajo["flag_duplicados"].values,
            "Dur.":           flags_en_trabajo["flag_duracion"].values,
        })

        # Agregar todas las columnas originales de df_w alineadas por posición,
        # no por índice — df_w puede tener índices no consecutivos tras eliminaciones
        _df_w_reset = df_w.reset_index(drop=True)
        _flags_reset = flags_en_trabajo.reset_index(drop=True)
        for _c in df_w.columns:
            df_dec[_c] = _df_w_reset[_c].values

        # column_config: solo Eliminar es editable, todo lo demás disabled
        _col_cfg = {
            "🗑 Eliminar": st.column_config.CheckboxColumn(
                "🗑 Eliminar", help="Marca para eliminar esta encuesta"),
            "Estado":  st.column_config.TextColumn("Estado",  disabled=True, width="medium"),
            "Miss.":   st.column_config.NumberColumn("Miss.", disabled=True, width="small"),
            "Dup.":    st.column_config.NumberColumn("Dup.",  disabled=True, width="small"),
            "Dur.":    st.column_config.NumberColumn("Dur.",  disabled=True, width="small"),
        }
        for _c in df_w.columns:
            _col_cfg[_c] = st.column_config.TextColumn(_c, disabled=True)

        # Botones de selección masiva
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("Marcar todos con flags"):
            st.session_state.eliminar_ids = set(
                flags_en_trabajo[flags_en_trabajo["encuesta_válida"] == 0]["ID"].astype(str))
            st.rerun()
        if b2.button("Desmarcar todos"):
            st.session_state.eliminar_ids = set()
            st.rerun()
        if b3.button("Marcar TODOS"):
            st.session_state.eliminar_ids = set(flags_en_trabajo["ID"].astype(str))
            st.rerun()
        n_marcados = int(df_dec["🗑 Eliminar"].sum())
        b4.markdown(
            f"<div style='padding:8px 0;font-weight:700;color:#f7966b;'>"
            f"🗑 {n_marcados} marcadas para eliminar</div>",
            unsafe_allow_html=True)

        edited_dec = st.data_editor(
            df_dec,
            column_config=_col_cfg,
            column_order=["🗑 Eliminar", "Estado", "Miss.", "Dup.", "Dur."] + list(df_w.columns),
            hide_index=True,
            use_container_width=True,
            key="editor_elim",
            height=min(600, max(200, len(df_dec) * 38 + 50)),
        )

        # Guardar cambios del editor — leer IDs desde la columna de la base original
        _id_col_name = col_id if (col_id and col_id in df_w.columns) else None
        if _id_col_name:
            nuevos_ids = set(
                edited_dec[edited_dec["🗑 Eliminar"] == True][_id_col_name].astype(str))
        else:
            # Sin columna ID usamos el índice de la tabla
            nuevos_ids = set(
                edited_dec[edited_dec["🗑 Eliminar"] == True].index.astype(str))

        ca, cb = st.columns([2, 3])
        with ca:
            if st.button("💾 Guardar selección", type="secondary"):
                st.session_state.eliminar_ids = nuevos_ids
                st.success(f"Guardado: {len(nuevos_ids)} encuestas marcadas para eliminar.")

        with cb:
            n_a_eliminar = len(nuevos_ids)
            n_quedaran   = len(df_w) - n_a_eliminar
            if n_a_eliminar > 0:
                st.markdown(
                    f"<div class='eq-warn'>"
                    f"Se eliminarán <b>{n_a_eliminar}</b> encuestas · "
                    f"Quedarán <b>{n_quedaran}</b> en la base"
                    f"</div>", unsafe_allow_html=True)

        if st.button("🗑 Aplicar eliminación ahora", type="primary"):
            ids_a_elim = st.session_state.eliminar_ids if st.session_state.eliminar_ids else nuevos_ids
            if not ids_a_elim:
                st.warning("No hay encuestas marcadas para eliminar.")
            else:
                id_col_w = (df_w[col_id].astype(str) if (col_id and col_id in df_w.columns)
                            else pd.Series(df_w.index.astype(str)))
                antes = len(df_w)
                nuevo_df = df_w[~id_col_w.isin(ids_a_elim)].reset_index(drop=True)
                st.session_state.df_work = nuevo_df
                st.session_state.cambios_log.append(
                    f"Eliminadas {antes - len(nuevo_df)} encuestas manualmente "
                    f"(IDs: {', '.join(sorted(ids_a_elim)[:10])}"
                    f"{'...' if len(ids_a_elim) > 10 else ''})"
                )
                st.session_state.eliminar_ids = set()
                st.success(f"✅ Aplicado. Quedan {len(nuevo_df):,} encuestas.")
                st.rerun()

        st.divider()

        # ── PASO 2: Correcciones por variable ─────────────────
        st.markdown("<div class='section-title'>Paso 2 — Correcciones por variable</div>",
                    unsafe_allow_html=True)

        t_miss, t_out, t_dup = st.tabs(["Missings", "Outliers", "Duplicados"])

        with t_miss:
            miss_w  = df_w.isnull().sum()
            cols_mw = miss_w[miss_w > 0].index.tolist()
            if not cols_mw:
                st.markdown("<div class='eq-ok'>✅ Sin missings en la base de trabajo.</div>",
                            unsafe_allow_html=True)
            else:
                num_m = [c for c in cols_mw if pd.api.types.is_numeric_dtype(df_w[c])]
                cat_m = [c for c in cols_mw if not pd.api.types.is_numeric_dtype(df_w[c])]
                OPC_N = ["Mediana", "Media", "Moda", "Sin respuesta", "Eliminar fila", "Dejar como está"]
                OPC_C = ["Moda", "Sin respuesta", "Eliminar fila", "Dejar como está"]

                en, ec = None, None
                if num_m:
                    st.caption(f"**{len(num_m)} variable(s) numéricas** con missings:")
                    rg = st.selectbox("Regla por defecto (numéricas):", OPC_N, key="rg_n")
                    tbl_n = pd.DataFrame({
                        "Variable":  num_m,
                        "Missings":  [int(df_w[c].isnull().sum()) for c in num_m],
                        "% Missing": [round(df_w[c].isnull().sum()/len(df_w)*100,1) for c in num_m],
                        "Corrección":[rg] * len(num_m),
                    })
                    en = st.data_editor(tbl_n, column_config={
                        "Corrección": st.column_config.SelectboxColumn(
                            "Corrección", options=OPC_N, required=True)},
                        disabled=["Variable","Missings","% Missing"],
                        hide_index=True, use_container_width=True, key="en")
                    with st.expander("👁 Preview — filas afectadas"):
                        for _, row in en.iterrows():
                            if row["Corrección"] == "Dejar como está": continue
                            af = df_w[df_w[row["Variable"]].isnull()][[row["Variable"]]].head(6)
                            if not af.empty:
                                st.markdown(f"**{row['Variable']}** ({int(df_w[row['Variable']].isnull().sum())} filas) → _{row['Corrección']}_")
                                st.dataframe(af, use_container_width=True)

                if cat_m:
                    st.caption(f"**{len(cat_m)} variable(s) categóricas** con missings:")
                    rg2 = st.selectbox("Regla por defecto (categóricas):", OPC_C, key="rg_c")
                    tbl_c = pd.DataFrame({
                        "Variable":  cat_m,
                        "Missings":  [int(df_w[c].isnull().sum()) for c in cat_m],
                        "% Missing": [round(df_w[c].isnull().sum()/len(df_w)*100,1) for c in cat_m],
                        "Corrección":[rg2] * len(cat_m),
                    })
                    ec = st.data_editor(tbl_c, column_config={
                        "Corrección": st.column_config.SelectboxColumn(
                            "Corrección", options=OPC_C, required=True)},
                        disabled=["Variable","Missings","% Missing"],
                        hide_index=True, use_container_width=True, key="ec")

                if st.button("✔ Aplicar correcciones de missings", type="primary", key="btn_miss"):
                    nd, log = aplicar_fix_missings(df_w, en, ec)
                    st.session_state.df_work = nd
                    st.session_state.cambios_log.extend(log)
                    st.success(f"Aplicado. Base: {len(nd):,} filas.")
                    for l in log: st.markdown(f"- {l}")
                    st.rerun()

        with t_out:
            res_o = []
            for col in df_w.select_dtypes(include="number").columns:
                if col_dur and col == col_dur: continue
                s = df_w[col].dropna()
                if s.empty: continue
                q1, q3 = s.quantile(.25), s.quantile(.75)
                iqr = q3 - q1; li, ls = q1-1.5*iqr, q3+1.5*iqr
                n_o = int(((s < li) | (s > ls)).sum())
                if n_o > 0:
                    res_o.append({
                        "Variable": col,
                        "N Outliers": n_o,
                        "Lím. Inf.": round(li, 3),
                        "Lím. Sup.": round(ls, 3),
                        "Corrección": "Dejar como está",
                    })
            if not res_o:
                st.markdown("<div class='eq-ok'>✅ Sin outliers en la base de trabajo.</div>",
                            unsafe_allow_html=True)
            else:
                OPC_O = ["Winsorizar", "Reemplazar con mediana",
                         "Marcar con flag", "Eliminar fila", "Dejar como está"]
                rgo = st.selectbox("Regla por defecto:", OPC_O, key="rg_o")
                tbl_o = pd.DataFrame(res_o)
                tbl_o["Corrección"] = rgo
                eo = st.data_editor(tbl_o, column_config={
                    "Corrección": st.column_config.SelectboxColumn(
                        "Corrección", options=OPC_O, required=True)},
                    disabled=["Variable","N Outliers","Lím. Inf.","Lím. Sup."],
                    hide_index=True, use_container_width=True, key="eo")
                with st.expander("👁 Preview — valores a corregir"):
                    for _, row in eo.iterrows():
                        if row["Corrección"] == "Dejar como está": continue
                        li_, ls_ = row["Lím. Inf."], row["Lím. Sup."]
                        prev = df_w[(df_w[row["Variable"]] < li_) |
                                    (df_w[row["Variable"]] > ls_)][[row["Variable"]]].head(6)
                        if not prev.empty:
                            st.markdown(f"**{row['Variable']}** → _{row['Corrección']}_ (rango válido: {li_} – {ls_})")
                            st.dataframe(prev, use_container_width=True)
                if st.button("✔ Aplicar correcciones de outliers", type="primary", key="btn_out"):
                    nd, log = aplicar_fix_outliers(df_w, eo)
                    st.session_state.df_work = nd
                    st.session_state.cambios_log.extend(log)
                    st.success("Aplicado.")
                    for l in log: st.markdown(f"- {l}")
                    st.rerun()

        with t_dup:
            nd_w = int(df_w.duplicated().sum())
            if nd_w == 0:
                st.markdown("<div class='eq-ok'>✅ Sin duplicados en la base de trabajo.</div>",
                            unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='eq-warn'><b>{nd_w}</b> fila(s) duplicada(s).</div>",
                            unsafe_allow_html=True)
                with st.expander("👁 Ver filas duplicadas"):
                    st.dataframe(df_w[df_w.duplicated(keep=False)].head(20),
                                 use_container_width=True)
                rd = st.selectbox("¿Qué hacer con los duplicados?", [
                    "Primera ocurrencia", "Última ocurrencia",
                    "Eliminar todas", "Marcar con flag",
                ], key="rd")
                if st.button("✔ Aplicar corrección de duplicados", type="primary", key="btn_dup"):
                    nd, log = aplicar_fix_dup(df_w, rd)
                    st.session_state.df_work = nd
                    st.session_state.cambios_log.extend(log)
                    st.success("Aplicado.")
                    for l in log: st.markdown(f"- {l}")
                    st.rerun()

        # ── Checkpoints ───────────────────────────────────────
        st.divider()
        st.markdown("<div class='section-title'>Checkpoints</div>", unsafe_allow_html=True)
        cp1, cp2 = st.columns(2)
        with cp1:
            cp_n = st.text_input("Nombre del checkpoint:", placeholder="ej: tras_limpiar_missings")
            if st.button("💾 Guardar estado actual") and cp_n:
                st.session_state.checkpoints[cp_n] = st.session_state.df_work.copy()
                st.success(f"Guardado: '{cp_n}' ({len(st.session_state.df_work):,} filas)")
        with cp2:
            if st.session_state.checkpoints:
                cp_r = st.selectbox("Restaurar desde:", list(st.session_state.checkpoints.keys()))
                if st.button("↩ Restaurar"):
                    st.session_state.df_work = st.session_state.checkpoints[cp_r].copy()
                    st.session_state.cambios_log.append(f"Restaurado desde '{cp_r}'")
                    st.success(f"Restaurado desde '{cp_r}'.")
                    st.rerun()

        if st.session_state.cambios_log:
            with st.expander(f"📋 Historial de cambios ({len(st.session_state.cambios_log)} acciones)"):
                for e in st.session_state.cambios_log:
                    st.markdown(f"- {e}")
            if st.button("🔄 Reiniciar todo (volver a la base original)"):
                st.session_state.df_work        = df.copy()
                st.session_state.cambios_log    = []
                st.session_state.checkpoints    = {}
                st.session_state.eliminar_ids   = set()
                st.rerun()

    # ════════════════════════════════════════════════════════
    # TAB 4 — DESCARGA
    # ════════════════════════════════════════════════════════
    with tabs[3]:
        df_fin = st.session_state.df_work
        st.markdown("<div class='section-title'>Resumen de la sesión</div>", unsafe_allow_html=True)
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Registros originales",      f"{len(df):,}")
        d2.metric("Registros tras corrección", f"{len(df_fin):,}")
        d3.metric("Acciones realizadas",       len(st.session_state.cambios_log))
        d4.metric("Checkpoints guardados",     len(st.session_state.checkpoints))
        st.divider()

        st.markdown("##### Base de datos corregida")
        fmt = st.radio("Formato:", ["CSV", "Excel (.xlsx)", "Stata (.dta)"],
                       horizontal=True, label_visibility="visible")
        nb  = archivo_db.name.rsplit(".", 1)[0]
        if fmt == "CSV":
            st.download_button(
                "⬇ Descargar base corregida (CSV)",
                data=df_fin.to_csv(index=False).encode("utf-8"),
                file_name=f"{nb}_corregida.csv", mime="text/csv", type="primary",
            )
        elif fmt == "Excel (.xlsx)":
            st.download_button(
                "⬇ Descargar base corregida (Excel)",
                data=df_a_excel(df_fin),
                file_name=f"{nb}_corregida.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )
        else:  # Stata .dta
            st.markdown(
                "<div class='eq-info'>"
                "📌 <b>Stata (.dta)</b> — Los nombres de columna se truncan a 32 caracteres "
                "si son más largos. Variables tipo texto se convierten a string."
                "</div>", unsafe_allow_html=True)
            try:
                dta_bytes = df_a_stata(df_fin)
                st.download_button(
                    "⬇ Descargar base corregida (Stata .dta)",
                    data=dta_bytes,
                    file_name=f"{nb}_corregida.dta",
                    mime="application/octet-stream",
                    type="primary",
                )
            except Exception as e:
                st.error(f"Error generando .dta: {e}")

        st.divider()
        st.markdown("##### Tabla de flags")
        st.download_button(
            "⬇ Descargar tabla de flags (CSV)",
            data=df_flags.to_csv(index=False).encode("utf-8"),
            file_name=f"{nb}_flags.csv", mime="text/csv",
        )

        st.divider()
        st.markdown("##### Reporte ejecutivo completo (Excel)")
        st.caption("Incluye: Resumen · Flags · Missings · Outliers · IDs eliminados · Historial")
        reporte = generar_reporte(
            df, df_fin, df_flags, resumen_iqr, df_out_det,
            st.session_state.cambios_log, archivo_db.name,
            eliminar_ids=st.session_state.eliminar_ids,
        )
        st.download_button(
            "⬇ Descargar reporte de auditoría (Excel)",
            data=reporte,
            file_name=f"{nb}_reporte_auditoria.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# cd C:\Users\acond\OneDrive\Desktop\HFC
# python -m streamlit run app.py