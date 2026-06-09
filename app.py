import streamlit as st
import pandas as pd
import difflib
import re
import cv2
import numpy as np
import requests
from PIL import Image
from pyzbar.pyzbar import decode
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
st.set_page_config(page_title="FoodTwins", page_icon="🔬", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/13OLqRmOHjWcaJoHsgHXexOXYiU3TGHQaHKR1tCKyChQ/edit?usp=sharing"

REQUIRED_COLUMNS = {
    "code", "nom", "marque", "emb", "ingredients",
    "nutriscore", "nova", "sucre", "sel", "energie_100g",
    "image_url", "usine_lieu",
}

NUTRI_SCORES = ["A", "B", "C", "D", "E"]

# ---------------------------------------------------------------------------
# CSS — Design "Lab Scanner" : fond sombre, accent vert, Space Grotesk
# ---------------------------------------------------------------------------
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">

<style>
/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0D0F14;
    color: #F8FAFC;
}
.stApp { background-color: #0D0F14; }

/* ── Typography ── */
h1, h2, h3, .display {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700;
    letter-spacing: -0.02em;
}

/* ── Hero header ── */
.hero {
    padding: 2.5rem 0 1.5rem;
    text-align: center;
}
.hero-logo {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.8rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    color: #F8FAFC;
}
.hero-logo span { color: #22C55E; }
.hero-tagline {
    color: #6B7280;
    font-size: 1rem;
    font-style: italic;
    margin-top: 4px;
}

/* ── Scan zone hero ── */
.search-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #6B7280;
    margin-bottom: 8px;
    display: block;
}

/* ── Cards ── */
.product-card {
    background: #1A1D24;
    border: 1px solid #2A2D35;
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1.5rem;
}
.product-brand {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #22C55E;
    margin-bottom: 4px;
}
.product-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #F8FAFC;
    margin-bottom: 12px;
}
.factory-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #0D0F14;
    border: 1px solid #2A2D35;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 0.82rem;
    color: #9CA3AF;
    margin-top: 10px;
}

/* ── Badges ── */
.badge {
    padding: 4px 11px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 6px;
    display: inline-block;
    margin-bottom: 6px;
}
.nutri-A { background: #166534; color: #BBF7D0; border: 1px solid #15803D; }
.nutri-B { background: #14532D; color: #86EFAC; border: 1px solid #16A34A; }
.nutri-C { background: #713F12; color: #FDE68A; border: 1px solid #CA8A04; }
.nutri-D { background: #7C2D12; color: #FDBA74; border: 1px solid #EA580C; }
.nutri-E { background: #7F1D1D; color: #FCA5A5; border: 1px solid #DC2626; }
.nutri-  { background: #1F2937; color: #9CA3AF; border: 1px solid #374151; }
.nova-badge {
    background: #1F2937;
    color: #D1D5DB;
    border: 1px solid #374151;
    border-radius: 20px;
    padding: 4px 11px;
    font-size: 0.75rem;
    font-weight: 600;
    display: inline-block;
    margin-right: 6px;
    margin-bottom: 6px;
}
.badge-vegan   { background: #064E3B; color: #6EE7B7; border: 1px solid #059669; }
.badge-pork    { background: #7F1D1D; color: #FCA5A5; border: 1px solid #DC2626; }

/* ── Stat boxes ── */
.stats-row {
    display: flex;
    gap: 10px;
    margin-top: 14px;
    flex-wrap: wrap;
}
.stat-box {
    flex: 1;
    min-width: 80px;
    background: #0D0F14;
    border: 1px solid #2A2D35;
    border-radius: 10px;
    padding: 10px 14px;
    text-align: center;
}
.stat-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #F8FAFC;
}
.stat-label {
    font-size: 0.68rem;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 2px;
}

/* ── Clone card ── */
.clone-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #F8FAFC;
    margin-bottom: 1rem;
}
.similarity-bar {
    height: 4px;
    background: #1F2937;
    border-radius: 2px;
    margin-top: 4px;
}
.similarity-fill {
    height: 4px;
    background: #22C55E;
    border-radius: 2px;
}

/* ── AI banner ── */
.ai-banner {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border: 1px solid #4338CA;
    color: #A5B4FC;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 12px;
}

/* ── OFF banner (Open Food Facts) ── */
.off-banner {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #064e3b, #065f46);
    border: 1px solid #059669;
    color: #6EE7B7;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 12px;
}

/* ── Divider ── */
.section-divider {
    border: none;
    border-top: 1px solid #1F2937;
    margin: 1.5rem 0;
}

/* ── Inputs & buttons theming ── */
.stTextInput > div > div > input {
    background: #1A1D24 !important;
    border: 1px solid #374151 !important;
    border-radius: 10px !important;
    color: #F8FAFC !important;
    padding: 10px 14px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #22C55E !important;
    box-shadow: 0 0 0 2px rgba(34,197,94,0.15) !important;
}
.stButton > button {
    background: #22C55E !important;
    color: #0D0F14 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 22px !important;
    letter-spacing: -0.01em !important;
    transition: opacity 0.15s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

/* Secondary button style via class trick */
[data-testid="stExpander"] {
    background: #1A1D24 !important;
    border: 1px solid #2A2D35 !important;
    border-radius: 12px !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: #1A1D24;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 7px;
    color: #9CA3AF;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
}
.stTabs [aria-selected="true"] {
    background: #22C55E !important;
    color: #0D0F14 !important;
}

/* Selectbox, text_area */
.stSelectbox > div > div, .stTextArea > div > div > textarea {
    background: #1A1D24 !important;
    border: 1px solid #374151 !important;
    border-radius: 10px !important;
    color: #F8FAFC !important;
}

/* Info / warning / error boxes */
.stAlert {
    border-radius: 10px !important;
}

/* Hide default streamlit branding */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# UTILITAIRES
# ---------------------------------------------------------------------------

def clean_barcode(raw: str) -> str:
    return str(raw).strip().replace("'", "")

def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return default

def safe_int(value) -> int | None:
    try:
        v = str(value).strip()
        if v == "" or v.lower() == "nan":
            return None
        return int(float(v))
    except (ValueError, TypeError):
        return None

def safe_str(value, default: str = "") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return default if s.lower() == "nan" else s

def get_nova_label(nova_raw) -> str:
    n = safe_int(nova_raw)
    return str(n) if n is not None else "?"

def get_nutri_class(nutri_raw: str) -> str:
    ns = safe_str(nutri_raw).upper()
    return ns if ns in NUTRI_SCORES else ""


# ---------------------------------------------------------------------------
# CHARGEMENT DES DONNÉES
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=SHEET_URL)
    except Exception as e:
        st.error(f"❌ Impossible de se connecter à Google Sheets : {e}")
        return pd.DataFrame(columns=list(REQUIRED_COLUMNS))

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df.fillna("")
    df["code"] = df["code"].apply(clean_barcode)
    for col in ("sucre", "sel", "energie_100g"):
        df[col] = df[col].apply(safe_float)
    return df


# ---------------------------------------------------------------------------
# SCAN CODE-BARRES
# ---------------------------------------------------------------------------

def scan_barcode(image: Image.Image) -> str | None:
    try:
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        detected = decode(gray)
        if detected:
            return detected[0].data.decode("utf-8")
    except Exception as e:
        st.warning(f"Erreur lors du scan : {e}")
    return None


# ---------------------------------------------------------------------------
# OPEN FOOD FACTS — enrichissement automatique
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def fetch_from_off(barcode: str) -> dict | None:
    """
    Interroge l'API Open Food Facts pour un code-barres donné.
    Retourne un dict normalisé ou None si le produit est inconnu.
    """
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    headers = {"User-Agent": "FoodTwins/1.0 (contact@foodtwins.fr)"}
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != 1:
            return None
        p = data.get("product", {})
        nutriments = p.get("nutriments", {})

        nutriscore_raw = p.get("nutriscore_grade", "").upper()
        nutriscore = nutriscore_raw if nutriscore_raw in NUTRI_SCORES else ""

        nova_raw = p.get("nova_group")
        nova = safe_int(nova_raw)

        ingredients_text = p.get("ingredients_text_fr") or p.get("ingredients_text", "")
        image_url = (
            p.get("image_front_url")
            or p.get("image_url")
            or ""
        )

        emb_codes = p.get("emb_codes", "")

        return {
            "nom":          p.get("product_name_fr") or p.get("product_name", ""),
            "marque":       p.get("brands", ""),
            "emb":          emb_codes,
            "ingredients":  ingredients_text,
            "nutriscore":   nutriscore,
            "nova":         nova if nova else 1,
            "sucre":        safe_float(nutriments.get("sugars_100g", 0)),
            "sel":          safe_float(nutriments.get("salt_100g", 0)),
            "energie_100g": safe_float(nutriments.get("energy-kcal_100g", 0)),
            "image_url":    image_url,
            "usine_lieu":   p.get("manufacturing_places", ""),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ANALYSE IA GEMINI (étiquette photo)
# ---------------------------------------------------------------------------

_NUTRI_ALIASES = {
    "a": "A", "b": "B", "c": "C", "d": "D", "e": "E",
    "nutri-score a": "A", "nutri-score b": "B",
    "nutri-score c": "C", "nutri-score d": "D", "nutri-score e": "E",
}

def _get_gemini_model():
    try:
        import google.generativeai as genai
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception:
        return None

def parse_ia_response(raw_text: str) -> dict:
    empty = {"nom": "", "marque": "", "emb": "", "ingredients": "", "nutriscore": ""}
    if not raw_text:
        return empty
    for sep in ("|", ";"):
        parts = [p.strip() for p in raw_text.split(sep)]
        if len(parts) >= 5:
            nutri_raw = parts[4].strip().upper()
            nutri = _NUTRI_ALIASES.get(nutri_raw.lower(), "")
            if not nutri and nutri_raw in NUTRI_SCORES:
                nutri = nutri_raw
            return {"nom": parts[0], "marque": parts[1], "emb": parts[2],
                    "ingredients": parts[3], "nutriscore": nutri}
    patterns = {
        "nom":         r"nom\s*[:\-]\s*(.+)",
        "marque":      r"marque\s*[:\-]\s*(.+)",
        "emb":         r"(?:emb|usine|code\s+emb)\s*[:\-]\s*(.+)",
        "ingredients": r"ingr[eé]dients?\s*[:\-]\s*(.+)",
        "nutriscore":  r"nutri.?score\s*[:\-]\s*(.+)",
    }
    result = {}
    for field, pattern in patterns.items():
        m = re.search(pattern, raw_text.lower())
        if m:
            val = m.group(1).strip()
            if field == "nutriscore":
                val = _NUTRI_ALIASES.get(val.lower(), val.upper())
                val = val if val in NUTRI_SCORES else ""
            result[field] = val
    for field in empty:
        result.setdefault(field, "")
    return result

def analyze_label_with_ai(image: Image.Image) -> dict | None:
    model = _get_gemini_model()
    if model is None:
        return None
    prompt = (
        "Analyse cette étiquette de produit alimentaire et extrais précisément :\n"
        "- Le nom complet du produit\n"
        "- La marque\n"
        "- Le code EMB (ex: FR 12.345.678 CE ou EMB 12345)\n"
        "- La liste complète des ingrédients\n"
        "- Le Nutri-Score (uniquement la lettre : A, B, C, D ou E)\n\n"
        "Réponds UNIQUEMENT sur une ligne dans ce format exact :\n"
        "Nom | Marque | EMB | Ingrédients | Nutriscore\n\n"
        "Si une information est absente, mets une chaîne vide."
    )
    try:
        with st.spinner("🤖 Analyse de l'étiquette…"):
            response = model.generate_content([prompt, image])
        raw = response.text.strip()
    except Exception as e:
        st.error(f"❌ Erreur Gemini : {e}")
        return None
    if not raw:
        return None
    parsed = parse_ia_response(raw)
    if not parsed.get("nom") and not parsed.get("marque"):
        return None
    return parsed


# ---------------------------------------------------------------------------
# BADGES
# ---------------------------------------------------------------------------

def get_badges_html(ingredients: str) -> str:
    ing_low = safe_str(ingredients).lower()
    badges = ""
    if any(kw in ing_low for kw in ("porc", "lard", "cochon", "jambon")):
        badges += '<span class="badge badge-pork">🐷 Porc</span>'
    non_veg = ("viande", "poisson", "poulet", "boeuf", "veau",
               "agneau", "canard", "dinde", "jambon", "thon", "saumon")
    if not any(kw in ing_low for kw in non_veg):
        badges += '<span class="badge badge-vegan">🍃 Végétarien</span>'
    return badges


# ---------------------------------------------------------------------------
# CLONES
# ---------------------------------------------------------------------------

def find_clones(df: pd.DataFrame, product: pd.Series, search_code: str) -> pd.DataFrame:
    nom = safe_str(product["nom"])
    emb = safe_str(product["emb"])
    mots = [m for m in nom.split() if len(m) > 3]
    if not mots:
        return pd.DataFrame()
    pattern = "|".join(re.escape(m) for m in mots[:2])
    clones = df[
        (df["emb"] == emb)
        & (df["nom"].str.contains(pattern, case=False, na=False, regex=True))
        & (df["code"] != search_code)
    ].copy()
    ref_ing = safe_str(product["ingredients"])
    clones["_similarity"] = clones["ingredients"].apply(
        lambda x: int(difflib.SequenceMatcher(None, ref_ing, safe_str(x)).ratio() * 100)
    )
    return clones.sort_values("_similarity", ascending=False)


# ---------------------------------------------------------------------------
# AFFICHAGE PRODUIT
# ---------------------------------------------------------------------------

def display_product(p: pd.Series) -> None:
    ns_class   = get_nutri_class(p["nutriscore"])
    nova_label = get_nova_label(p["nova"])
    badges     = get_badges_html(p["ingredients"])
    sucre      = safe_float(p["sucre"])
    sel        = safe_float(p["sel"])
    energie    = safe_float(p["energie_100g"])
    usine      = safe_str(p["emb"], "Inconnue")
    lieu       = safe_str(p["usine_lieu"], "Lieu inconnu")
    image_url  = safe_str(p["image_url"])
    brand      = safe_str(p["marque"], "Marque inconnue")
    name       = safe_str(p["nom"], "Produit sans nom")

    st.markdown('<div class="product-card">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2.5])

    with col1:
        if image_url:
            st.image(image_url, use_column_width=True)
        else:
            st.markdown(
                '<div style="background:#0D0F14;border:1px dashed #374151;'
                'border-radius:12px;height:160px;display:flex;align-items:center;'
                'justify-content:center;color:#4B5563;font-size:2rem;">📦</div>',
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown(f'<div class="product-brand">{brand}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="product-name">{name}</div>', unsafe_allow_html=True)

        st.markdown(
            f'<span class="badge nutri-{ns_class}">Nutri-Score {ns_class or "?"}</span>'
            f'<span class="nova-badge">NOVA {nova_label}</span>'
            f"{badges}",
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="stats-row">'
            f'<div class="stat-box"><div class="stat-value">{sucre}g</div>'
            '<div class="stat-label">Sucres</div></div>'
            f'<div class="stat-box"><div class="stat-value">{sel}g</div>'
            '<div class="stat-label">Sel</div></div>'
            f'<div class="stat-box"><div class="stat-value">{int(energie)}</div>'
            '<div class="stat-label">kcal/100g</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="factory-chip">🏭 {usine} &nbsp;·&nbsp; {lieu}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# AFFICHAGE CLONES
# ---------------------------------------------------------------------------

def display_clones(clones: pd.DataFrame, ref_product: pd.Series) -> None:
    nom = safe_str(ref_product["nom"])
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="clone-header">💡 {len(clones)} alternative(s) pour «&nbsp;{nom}&nbsp;»</div>',
        unsafe_allow_html=True,
    )

    for _, c in clones.head(10).iterrows():
        pct   = int(c.get("_similarity", 0))
        ns    = get_nutri_class(c["nutriscore"])
        label = f"{safe_str(c['marque'])} — {safe_str(c['nom'])}"

        with st.expander(f"✅ {label}  •  {pct}% de ressemblance"):
            ca, cb = st.columns([1, 2.5])

            with ca:
                img = safe_str(c["image_url"])
                if img:
                    st.image(img, width=110)
                st.markdown(
                    f'<span class="badge nutri-{ns}">Nutri-Score {ns or "?"}</span>'
                    f'<div class="similarity-bar"><div class="similarity-fill" style="width:{pct}%"></div></div>'
                    f'<div style="font-size:0.72rem;color:#6B7280;margin-top:3px">{pct}% similaire</div>',
                    unsafe_allow_html=True,
                )

            with cb:
                ing = safe_str(c["ingredients"], "Non renseignés")
                st.markdown(
                    f'<p style="font-size:0.82rem;color:#9CA3AF;line-height:1.5">{ing[:280]}{"…" if len(ing)>280 else ""}</p>',
                    unsafe_allow_html=True,
                )

                ref_sucre, alt_sucre = safe_float(ref_product["sucre"]), safe_float(c["sucre"])
                ref_sel,   alt_sel   = safe_float(ref_product["sel"]),   safe_float(c["sel"])
                diff_s = round(alt_sucre - ref_sucre, 1)
                diff_e = round(alt_sel   - ref_sel,   1)

                def delta_color(v):
                    return "#4ADE80" if v < 0 else ("#F87171" if v > 0 else "#9CA3AF")

                st.markdown(
                    f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px">'
                    f'<div style="font-size:0.82rem">🍬 Sucre&nbsp;<strong>{alt_sucre}g</strong>'
                    f'&nbsp;<span style="color:{delta_color(diff_s)};font-size:0.75rem">'
                    f'({("+" if diff_s>0 else "")}{diff_s}g)</span></div>'
                    f'<div style="font-size:0.82rem">🧂 Sel&nbsp;<strong>{alt_sel}g</strong>'
                    f'&nbsp;<span style="color:{delta_color(diff_e)};font-size:0.75rem">'
                    f'({("+" if diff_e>0 else "")}{diff_e}g)</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# FORMULAIRE D'AJOUT
# ---------------------------------------------------------------------------

def display_add_form(barcode: str, df: pd.DataFrame) -> None:
    st.markdown(
        '<div style="background:#1A1D24;border:1px solid #2A2D35;border-radius:16px;'
        'padding:1.5rem;margin-top:1.5rem">',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-family:Space Grotesk,sans-serif;font-size:1.3rem;font-weight:700;'
        f'margin-bottom:4px">Produit introuvable</div>'
        f'<div style="color:#6B7280;font-size:0.85rem;margin-bottom:1rem">'
        f'Code <code style="color:#22C55E">{barcode}</code> absent de la base — '
        f'aidez-nous à l\'enrichir.</div>',
        unsafe_allow_html=True,
    )

    # ── Enrichissement automatique : OFF d'abord, puis IA ──────────────────

    # 1. Open Food Facts
    off_data = None
    if "off_prefill" not in st.session_state or st.session_state.get("off_barcode") != barcode:
        with st.spinner("🌍 Recherche sur Open Food Facts…"):
            off_data = fetch_from_off(barcode)
        if off_data:
            st.session_state["off_prefill"] = off_data
            st.session_state["off_barcode"] = barcode
        else:
            st.session_state.pop("off_prefill", None)
    else:
        off_data = st.session_state.get("off_prefill")

    defaults = {
        "nom": "", "marque": "", "emb": "", "ingredients": "",
        "nutriscore": "A", "nova": 1, "sucre": 0.0, "sel": 0.0,
        "energie_100g": 0.0, "image_url": "", "usine_lieu": "",
    }

    if off_data:
        st.markdown(
            '<span class="off-banner">🌍 Données récupérées via Open Food Facts — vérifiez avant d\'enregistrer</span>',
            unsafe_allow_html=True,
        )
        defaults.update({k: v for k, v in off_data.items() if v not in (None, "", 0, 0.0)})

    # 2. Analyse IA par photo (optionnel, complète OFF si champs manquants)
    with st.expander("📷 Compléter via photo d'étiquette (IA)", expanded=not bool(off_data)):
        st.caption(
            "Prenez en photo l'étiquette. L'IA (Gemini) tentera d'extraire les informations manquantes."
        )
        ai_photo = st.file_uploader(
            "Photo de l'étiquette", type=["jpg", "jpeg", "png", "webp"], key="ai_label_photo"
        )
        if ai_photo:
            pil_image = Image.open(ai_photo)
            st.image(pil_image, caption="Étiquette importée", width=220)
            if st.button("🔍 Analyser avec Gemini"):
                extracted = analyze_label_with_ai(pil_image)
                if extracted:
                    st.session_state["ai_prefill"] = extracted
                    st.success("✅ Analyse terminée — vérifiez les champs ci-dessous.")
                else:
                    st.warning("⚠️ Aucune information extraite. Photo plus nette recommandée.")

    ai_fill = st.session_state.get("ai_prefill", {})
    if ai_fill:
        st.markdown(
            '<span class="ai-banner">✨ Champs complétés par l\'IA — vérifiez</span>',
            unsafe_allow_html=True,
        )
        # IA ne remplace que les champs vides
        for k, v in ai_fill.items():
            if k in defaults and not defaults[k]:
                defaults[k] = v

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── Formulaire ──────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        new_nom    = st.text_input("Nom du produit *",  value=defaults["nom"])
        new_marque = st.text_input("Marque *",          value=defaults["marque"])
        new_emb    = st.text_input("Code usine EMB *",  value=defaults["emb"])
        new_lieu   = st.text_input("Lieu de fabrication", value=defaults.get("usine_lieu",""))
        new_img    = st.text_input("URL image",         value=defaults.get("image_url",""))
    with c2:
        nutri_index = NUTRI_SCORES.index(defaults["nutriscore"]) if defaults["nutriscore"] in NUTRI_SCORES else 0
        new_nutri  = st.selectbox("Nutri-Score", NUTRI_SCORES, index=nutri_index)
        nova_opts  = [1, 2, 3, 4]
        nova_val   = int(defaults["nova"]) if safe_int(defaults["nova"]) in nova_opts else 1
        new_nova   = st.selectbox("NOVA", nova_opts, index=nova_opts.index(nova_val))
        new_sucre  = st.number_input("Sucres (g/100g)",   value=float(defaults["sucre"]),  min_value=0.0, step=0.1)
        new_sel    = st.number_input("Sel (g/100g)",      value=float(defaults["sel"]),    min_value=0.0, step=0.01)
        new_kcal   = st.number_input("Énergie (kcal/100g)", value=float(defaults["energie_100g"]), min_value=0.0, step=1.0)

    new_ing = st.text_area("Ingrédients", value=defaults["ingredients"], height=110)

    # ── Bouton d'enregistrement ────────────────────────────────────────────
    if st.button("💾 Enregistrer dans la base"):
        errors = []
        if not new_nom.strip():    errors.append("Le nom du produit est obligatoire.")
        if not new_marque.strip(): errors.append("La marque est obligatoire.")
        if not new_emb.strip():    errors.append("Le code usine EMB est obligatoire.")

        if errors:
            for e in errors:
                st.warning(f"⚠️ {e}")
        else:
            new_line = {
                "code": clean_barcode(barcode),
                "nom": new_nom.strip(), "marque": new_marque.strip(),
                "emb": new_emb.strip(), "ingredients": new_ing.strip(),
                "nutriscore": new_nutri, "nova": new_nova,
                "sucre": new_sucre, "sel": new_sel,
                "energie_100g": new_kcal,
                "image_url": new_img.strip(),
                "usine_lieu": new_lieu.strip(),
            }
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                updated_df = pd.concat([df, pd.DataFrame([new_line])], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success(f"✅ Produit « {new_nom} » ajouté avec succès !")
                for key in ("ai_prefill", "off_prefill", "off_barcode"):
                    st.session_state.pop(key, None)
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ Erreur lors de l'écriture : {e}")

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# APPLICATION PRINCIPALE
# ---------------------------------------------------------------------------

def main() -> None:
    df = load_data()
    if df.empty:
        st.stop()

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="hero">'
        '<div class="hero-logo">Food<span>Twins</span></div>'
        '<div class="hero-tagline">« Ne payez plus le logo, payez le produit. »</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Zone de saisie / scan ──────────────────────────────────────────────
    st.markdown('<span class="search-label">Scanner ou saisir un code-barres</span>', unsafe_allow_html=True)

    barcode = ""
    tabs = st.tabs(["⌨️  Saisie manuelle", "📸  Scanner"])

    with tabs[0]:
        raw_input = st.text_input(
            "Code-barres", label_visibility="collapsed",
            placeholder="Ex : 3017620422003", key="manual"
        ).strip()
        if raw_input:
            barcode = clean_barcode(raw_input)

    with tabs[1]:
        img_file = st.camera_input("Placez le code-barres face à la caméra", label_visibility="collapsed")
        if img_file:
            scanned = scan_barcode(Image.open(img_file))
            if scanned:
                barcode = clean_barcode(scanned)
                st.success(f"✅ Code détecté : **{barcode}**")
            else:
                st.warning("⚠️ Code non détecté — rapprochez le produit de la caméra.")

    if not barcode:
        st.markdown(
            '<div style="text-align:center;color:#374151;padding:3rem 0;font-size:0.9rem">'
            '🔍 Entrez ou scannez un code-barres pour commencer'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Recherche dans la base ─────────────────────────────────────────────
    res = df[df["code"] == barcode]

    if res.empty:
        display_add_form(barcode, df)
        return

    product = res.iloc[0]
    display_product(product)

    clones = find_clones(df, product, barcode)
    if not clones.empty:
        display_clones(clones, product)
    else:
        st.markdown(
            '<div style="margin-top:1.5rem;padding:1rem 1.2rem;background:#1A1D24;'
            'border:1px solid #2A2D35;border-radius:12px;color:#6B7280;font-size:0.85rem">'
            'ℹ️ Aucune alternative détectée dans notre base pour ce produit.'
            '</div>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
