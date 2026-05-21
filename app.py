import streamlit as st
import pandas as pd
import difflib
import re
import cv2
import numpy as np
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
# STYLE CSS
# ---------------------------------------------------------------------------
st.markdown("""
    <style>
    .badge {
        padding: 4px 10px; border-radius: 10px; font-weight: bold;
        margin-right: 5px; display: inline-block; margin-bottom: 5px;
    }
    .nutri-A { background-color: #008b4c; color: white; }
    .nutri-B { background-color: #80c141; color: white; }
    .nutri-C { background-color: #fec917; color: black; }
    .nutri-D { background-color: #ee8100; color: white; }
    .nutri-E { background-color: #e63e11; color: white; }
    .nutri-  { background-color: #aaa;    color: white; }
    .nova    { background-color: #333;    color: white; border-radius: 5px; padding: 2px 8px; }
    .vegan   { background-color: #2ecc71; color: white; }
    .has-pork{ background-color: #e74c3c; color: white; }
    .ai-banner {
        background: linear-gradient(90deg, #4f46e5, #7c3aed);
        color: white; border-radius: 8px; padding: 8px 14px;
        font-size: 14px; margin-bottom: 10px; display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# UTILITAIRES GÉNÉRIQUES
# ---------------------------------------------------------------------------

def clean_barcode(raw: str) -> str:
    """Supprime les apostrophes et espaces parasites d'un code-barres."""
    return str(raw).strip().replace("'", "")


def safe_float(value, default: float = 0.0) -> float:
    """Convertit en float sans lever d'exception."""
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return default


def safe_int(value) -> int | None:
    """Convertit en int ; retourne None si impossible."""
    try:
        v = str(value).strip()
        if v == "" or v.lower() == "nan":
            return None
        return int(float(v))
    except (ValueError, TypeError):
        return None


def safe_str(value, default: str = "") -> str:
    """Retourne une chaîne propre ou la valeur par défaut."""
    if value is None:
        return default
    s = str(value).strip()
    return default if s.lower() == "nan" else s


def get_nova_label(nova_raw) -> str:
    """Retourne le label NOVA à afficher."""
    n = safe_int(nova_raw)
    return str(n) if n is not None else "?"


def get_nutri_class(nutri_raw: str) -> str:
    """Retourne la classe CSS du Nutri-Score (vide si inconnu)."""
    ns = safe_str(nutri_raw).upper()
    return ns if ns in NUTRI_SCORES else ""


# ---------------------------------------------------------------------------
# CHARGEMENT DES DONNÉES
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    """
    Charge et normalise le Google Sheet.
    - Toutes les colonnes attendues sont garanties présentes.
    - Les codes-barres sont systématiquement nettoyés (sans apostrophe).
    - Les colonnes numériques sont converties proprement.
    """
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
    """Décode un code-barres depuis une image PIL. Retourne None si non détecté."""
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
# ANALYSE IA DE L'ÉTIQUETTE (GEMINI)
# ---------------------------------------------------------------------------

# Dictionnaire de normalisation pour les nutri-scores retournés par l'IA
_NUTRI_ALIASES = {
    "a": "A", "b": "B", "c": "C", "d": "D", "e": "E",
    "nutri-score a": "A", "nutri-score b": "B",
    "nutri-score c": "C", "nutri-score d": "D", "nutri-score e": "E",
    "score a": "A", "score b": "B", "score c": "C",
    "score d": "D", "score e": "E",
}


def _get_gemini_model():
    """
    Instancie le modèle Gemini à partir des secrets Streamlit.
    Retourne None si la clé est absente ou invalide, sans faire planter l'app.
    """
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
    """
    Parse la réponse de Gemini au format attendu :
      Nom | Marque | EMB | Ingrédients | Nutriscore

    Règles de robustesse :
    - Insensible à la casse et aux espaces superflus.
    - Accepte les séparateurs '|', ';' et les retours à la ligne numérotés.
    - Normalise le Nutri-Score vers A/B/C/D/E ou "" si non reconnu.
    - Retourne toujours un dict complet (champs vides si absent).
    """
    empty = {"nom": "", "marque": "", "emb": "", "ingredients": "", "nutriscore": ""}

    if not raw_text:
        return empty

    # Tentative 1 : séparateur pipe ou point-virgule sur une seule ligne
    for sep in ("|", ";"):
        parts = [p.strip() for p in raw_text.split(sep)]
        if len(parts) >= 5:
            nutri_raw = parts[4].strip().upper()
            nutri = _NUTRI_ALIASES.get(nutri_raw.lower(), "")
            if not nutri and nutri_raw in NUTRI_SCORES:
                nutri = nutri_raw
            return {
                "nom":          parts[0],
                "marque":       parts[1],
                "emb":          parts[2],
                "ingredients":  parts[3],
                "nutriscore":   nutri,
            }

    # Tentative 2 : réponse multi-lignes avec libellés ("Nom : ...")
    patterns = {
        "nom":         r"nom\s*[:\-]\s*(.+)",
        "marque":      r"marque\s*[:\-]\s*(.+)",
        "emb":         r"(?:emb|usine|code\s+emb)\s*[:\-]\s*(.+)",
        "ingredients": r"ingr[eé]dients?\s*[:\-]\s*(.+)",
        "nutriscore":  r"nutri.?score\s*[:\-]\s*(.+)",
    }
    result = {}
    text_lower = raw_text.lower()
    for field, pattern in patterns.items():
        m = re.search(pattern, text_lower)
        if m:
            val = m.group(1).strip()
            if field == "nutriscore":
                val = _NUTRI_ALIASES.get(val.lower(), val.upper())
                val = val if val in NUTRI_SCORES else ""
            result[field] = val

    # Compléter les champs manquants avec une chaîne vide
    for field in empty:
        result.setdefault(field, "")

    return result


def analyze_label_with_ai(image: Image.Image) -> dict | None:
    """
    Envoie l'image à Gemini et retourne un dict des champs extraits,
    ou None en cas d'échec (clé absente, quota dépassé, réponse illisible…).
    """
    model = _get_gemini_model()
    if model is None:
        st.warning(
            "⚠️ Clé API Gemini non configurée. "
            "Ajoutez `GEMINI_API_KEY` dans `.streamlit/secrets.toml` "
            "pour activer l'analyse automatique."
        )
        return None

    prompt = (
        "Analyse cette étiquette de produit alimentaire et extrais précisément :\n"
        "- Le nom complet du produit\n"
        "- La marque\n"
        "- Le code EMB (ex: FR 12.345.678 CE ou EMB 12345)\n"
        "- La liste complète des ingrédients\n"
        "- Le Nutri-Score (uniquement la lettre : A, B, C, D ou E)\n\n"
        "Réponds UNIQUEMENT sur une ligne, dans ce format exact, sans texte supplémentaire :\n"
        "Nom | Marque | EMB | Ingrédients | Nutriscore\n\n"
        "Si une information est absente sur l'étiquette, mets une chaîne vide à sa place."
    )

    try:
        with st.spinner("🤖 Analyse de l'étiquette en cours…"):
            response = model.generate_content([prompt, image])
        raw = response.text.strip()
    except Exception as e:
        st.error(f"❌ Erreur lors de l'appel à Gemini : {e}")
        return None

    if not raw:
        st.error("❌ Gemini n'a retourné aucune réponse. Réessayez avec une photo plus nette.")
        return None

    parsed = parse_ia_response(raw)

    # Vérification minimale : au moins le nom ou la marque doit être présent
    if not parsed.get("nom") and not parsed.get("marque"):
        st.warning(
            "⚠️ L'IA n'a pas pu extraire d'informations exploitables. "
            "Vérifiez que l'étiquette est bien visible et réessayez."
        )
        return None

    return parsed


# ---------------------------------------------------------------------------
# BADGES HTML
# ---------------------------------------------------------------------------

def get_badges_html(ingredients: str) -> str:
    """Génère les badges Porc / Végétarien selon les ingrédients."""
    ing_low = safe_str(ingredients).lower()
    badges = ""
    if any(kw in ing_low for kw in ("porc", "lard", "cochon", "jambon")):
        badges += '<span class="badge has-pork">🐷 Porc</span>'
    non_veg = (
        "viande", "poisson", "poulet", "boeuf", "veau",
        "agneau", "canard", "dinde", "jambon", "thon", "saumon",
    )
    if not any(kw in ing_low for kw in non_veg):
        badges += '<span class="badge vegan">🍃 Végétarien</span>'
    return badges


# ---------------------------------------------------------------------------
# RECHERCHE D'ALTERNATIVES (CLONES)
# ---------------------------------------------------------------------------

def find_clones(df: pd.DataFrame, product: pd.Series, search_code: str) -> pd.DataFrame:
    """
    Cherche des alternatives fabriquées dans la même usine avec un nom similaire.
    Utilise les 2 premiers mots significatifs (> 3 lettres) pour élargir la recherche.
    """
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
        lambda x: int(
            difflib.SequenceMatcher(None, ref_ing, safe_str(x)).ratio() * 100
        )
    )
    return clones.sort_values("_similarity", ascending=False)


# ---------------------------------------------------------------------------
# AFFICHAGE D'UN PRODUIT
# ---------------------------------------------------------------------------

def display_product(p: pd.Series) -> None:
    """Affiche la fiche complète d'un produit."""
    col1, col2 = st.columns([1, 2])

    with col1:
        image_url = safe_str(p["image_url"])
        if image_url:
            st.image(image_url, use_column_width=True)
        else:
            st.info("📷 Image non disponible")

    with col2:
        st.write(f"**{safe_str(p['marque'], 'Marque inconnue')}**")
        st.header(safe_str(p["nom"], "Produit sans nom"))

        ns_class  = get_nutri_class(p["nutriscore"])
        nova_label = get_nova_label(p["nova"])
        badges    = get_badges_html(p["ingredients"])

        st.markdown(
            f'<span class="badge nutri-{ns_class}">Nutri-Score {ns_class or "?"}</span>'
            f'<span class="nova">NOVA {nova_label}</span>'
            f"{badges}",
            unsafe_allow_html=True,
        )

        usine = safe_str(p["emb"], "Inconnue")
        lieu  = safe_str(p["usine_lieu"], "Lieu inconnu")
        st.info(f"🏭 **Usine :** {usine} ({lieu})")


# ---------------------------------------------------------------------------
# AFFICHAGE DES ALTERNATIVES
# ---------------------------------------------------------------------------

def display_clones(clones: pd.DataFrame, ref_product: pd.Series) -> None:
    """Affiche les alternatives trouvées pour un produit."""
    nom = safe_str(ref_product["nom"])
    st.markdown("---")
    st.subheader(f"💡 {len(clones)} alternative(s) détectée(s) pour « {nom} »")

    for _, c in clones.head(10).iterrows():
        pct   = int(c.get("_similarity", 0))
        label = f"✅ {safe_str(c['marque'])} — {safe_str(c['nom'])} ({pct}% de ressemblance)"

        with st.expander(label):
            ca, cb = st.columns([1, 2])

            with ca:
                img = safe_str(c["image_url"])
                if img:
                    st.image(img, width=120)
                ns_class = get_nutri_class(c["nutriscore"])
                st.markdown(
                    f'<span class="badge nutri-{ns_class}">Score {ns_class or "?"}</span>',
                    unsafe_allow_html=True,
                )

            with cb:
                st.write(f"**Ingrédients :** {safe_str(c['ingredients'], 'Non renseignés')}")

                ref_sucre = safe_float(ref_product["sucre"])
                alt_sucre = safe_float(c["sucre"])
                diff_sucre = round(alt_sucre - ref_sucre, 1)
                st.write(f"**Sucre :** {alt_sucre}g ({'+' if diff_sucre > 0 else ''}{diff_sucre}g vs produit scanné)")

                ref_sel = safe_float(ref_product["sel"])
                alt_sel = safe_float(c["sel"])
                diff_sel = round(alt_sel - ref_sel, 1)
                st.write(f"**Sel :** {alt_sel}g ({'+' if diff_sel > 0 else ''}{diff_sel}g vs produit scanné)")


# ---------------------------------------------------------------------------
# FORMULAIRE D'AJOUT (avec pré-remplissage IA optionnel)
# ---------------------------------------------------------------------------

def display_add_form(barcode: str, df: pd.DataFrame) -> None:
    """
    Affiche le formulaire d'ajout d'un produit manquant.
    Propose une analyse IA par photo pour pré-remplir les champs automatiquement.
    """
    st.error(f"Le produit avec le code **{barcode}** n'est pas encore dans notre base.")
    st.info("💡 Aidez-nous à enrichir la base en ajoutant ce produit ci-dessous.")

    with st.expander("➕ Ajouter ce produit", expanded=True):

        # --- SECTION ANALYSE IA ---
        st.markdown(
            '<span class="ai-banner">🤖 Remplissage automatique par IA</span>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Prenez en photo l'étiquette du produit. "
            "L'IA tentera d'extraire les informations automatiquement. "
            "Vous pourrez corriger les champs avant d'enregistrer."
        )

        ai_photo = st.file_uploader(
            "📷 Photo de l'étiquette (optionnel)",
            type=["jpg", "jpeg", "png", "webp"],
            key="ai_label_photo",
        )

        # Valeurs par défaut (vides ou issues de l'IA)
        defaults = {"nom": "", "marque": "", "emb": "", "ingredients": "", "nutriscore": "A"}

        if ai_photo is not None:
            pil_image = Image.open(ai_photo)
            st.image(pil_image, caption="Étiquette importée", width=250)

            if st.button("🔍 Analyser l'étiquette avec l'IA"):
                extracted = analyze_label_with_ai(pil_image)
                if extracted:
                    # Stockage en session_state pour persistance après reruns
                    st.session_state["ai_prefill"] = extracted
                    st.success("✅ Analyse terminée — vérifiez et complétez les champs ci-dessous.")

        # Récupération des valeurs pré-remplies si disponibles
        prefill = st.session_state.get("ai_prefill", {})
        if prefill:
            defaults.update(prefill)
            st.markdown(
                '<span class="ai-banner">✨ Champs pré-remplis par l\'IA — veuillez vérifier</span>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # --- FORMULAIRE MANUEL / PRÉ-REMPLI ---
        new_nom    = st.text_input("Nom du produit *",        value=defaults["nom"])
        new_marque = st.text_input("Marque *",                value=defaults["marque"])
        new_emb    = st.text_input("Code Usine EMB *",        value=defaults["emb"])
        new_ing    = st.text_area("Liste des ingrédients",    value=defaults["ingredients"], height=120)

        # Nutriscore : sélection avec pré-sélection IA si valide
        nutri_index = NUTRI_SCORES.index(defaults["nutriscore"]) \
            if defaults["nutriscore"] in NUTRI_SCORES else 0
        new_nutri = st.selectbox("Nutriscore", NUTRI_SCORES, index=nutri_index)
        new_nova  = st.selectbox("NOVA", [1, 2, 3, 4])

        # --- VALIDATION ET ENREGISTREMENT ---
        if st.button("💾 Enregistrer sur Google Sheets"):
            errors = []
            if not new_nom.strip():
                errors.append("Le nom du produit est obligatoire.")
            if not new_marque.strip():
                errors.append("La marque est obligatoire.")
            if not new_emb.strip():
                errors.append("Le code usine EMB est obligatoire.")

            if errors:
                for err in errors:
                    st.warning(f"⚠️ {err}")
            else:
                new_line = {
                    "code":         clean_barcode(barcode),
                    "nom":          new_nom.strip(),
                    "marque":       new_marque.strip(),
                    "emb":          new_emb.strip(),
                    "ingredients":  new_ing.strip(),
                    "nutriscore":   new_nutri,
                    "nova":         new_nova,
                    "sucre":        0,
                    "sel":          0,
                    "energie_100g": 0,
                    "image_url":    "",
                    "usine_lieu":   "",
                }
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    updated_df = pd.concat(
                        [df, pd.DataFrame([new_line])], ignore_index=True
                    )
                    conn.update(spreadsheet=SHEET_URL, data=updated_df)
                    st.success(f"✅ Produit « {new_nom} » ajouté avec succès !")
                    # Nettoyage du pré-remplissage IA après enregistrement réussi
                    st.session_state.pop("ai_prefill", None)
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'écriture : {e}")


# ---------------------------------------------------------------------------
# APPLICATION PRINCIPALE
# ---------------------------------------------------------------------------

def main() -> None:
    df = load_data()
    if df.empty:
        st.stop()

    # Entête
    col_logo, col_titre = st.columns([1, 5])
    with col_logo:
        try:
            st.image("logo.png", width=80)
        except Exception:
            st.write("🔬")
    with col_titre:
        st.title("FoodTwins")
    st.markdown(
        "<p style='color: gray; font-style: italic; font-size: 20px;'>"
        "« Ne payez plus le logo, payez le produit. »</p>",
        unsafe_allow_html=True,
    )

    # Zone de saisie / scan
    barcode = ""
    tabs = st.tabs(["⌨️ Saisie Manuelle", "📸 Scanner"])

    with tabs[0]:
        raw_input = st.text_input("Entrez le code-barres :", key="manual").strip()
        if raw_input:
            barcode = clean_barcode(raw_input)

    with tabs[1]:
        img_file = st.camera_input("Placez le code-barres face à la caméra")
        if img_file:
            scanned = scan_barcode(Image.open(img_file))
            if scanned:
                barcode = clean_barcode(scanned)
                st.success(f"✅ Code détecté : **{barcode}**")
            else:
                st.warning("⚠️ Code-barres non détecté. Rapprochez le produit de la caméra.")

    if not barcode:
        return

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
        st.info("ℹ️ Aucune alternative détectée dans notre base pour ce produit.")


if __name__ == "__main__":
    main()
