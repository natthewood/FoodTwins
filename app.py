import streamlit as st
import pandas as pd
import requests
import difflib

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="CloneDetector Global", page_icon="🔍", layout="wide")

# --- FONCTION DE RECHERCHE WEB (MULTI-API) ---
def fetch_off_data(barcode):
    clean_barcode = str(barcode).strip()
    urls = [
        f"https://world.openfoodfacts.org/api/v2/product/{clean_barcode}.json",
        f"https://world.openfoodfacts.org/api/v0/product/{clean_barcode}.json",
        f"https://fr.openfoodfacts.org/api/v0/product/{clean_barcode}.json"
    ]
    headers = {'User-Agent': 'CloneDetector - GlobalApp - Version 1.0'}
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get('status') == 1 or data.get('status_verbose') == "product found":
                    p = data['product']
                    emb = p.get('emb_codes', '').split(',')[0] if p.get('emb_codes') else p.get('manufacturing_places', '')
                    return {
                        "nom": p.get('product_name_fr') or p.get('product_name') or "Inconnu",
                        "emb": str(emb).strip(),
                        "ingredients": p.get('ingredients_text_fr') or p.get('ingredients_text') or "Non renseignés",
                        "sucre": p.get('nutriments', {}).get('sugars_100g', 0),
                        "image": p.get('image_front_url'),
                        "source": "Web (Open Food Facts)"
                    }
        except:
            continue
    return None

def calculer_score(ing1, ing2):
    return int(difflib.SequenceMatcher(None, str(ing1).lower(), str(ing2).lower()).ratio() * 100)

def comparer_visuel(ref, comp):
    ref_words = str(ref).lower().replace(',', '').replace('.', '').split()
    comp_raw = str(comp).split()
    res = ""
    for w in comp_raw:
        clean = w.lower().replace(',', '').replace('.', '')
        if clean in ref_words:
            res += f"{w} "
        else:
            res += f"<span style='color:red; font-weight:bold; background-color: #ffecec;'>{w}</span> "
    return res

# --- INTERFACE PRINCIPALE ---
st.title("🔬 CloneDetector Global")
st.markdown("Recherche hybride : Base mondiale + Vos clones locaux")

# Sidebar pour le diagnostic
with st.sidebar:
    st.header("🛠 Diagnostic API")
    # CORRECTION ICI : La phrase est bien fermée sur une seule ligne
    st.info("Les résultats s'afficheront ici lors du scan.")

barcode = st.text_input("Scanner ou entrez un code-barres (ex: 3229820129488) :")

if barcode:
    data = fetch_off_data(barcode)
    
# --- CHARGEMENT DU CSV SÉCURISÉ ---
try:
    # On force TOUTES les colonnes à être lues comme du texte brut (str)
    df_local = pd.read_csv("produits.csv", dtype=str)
    # On nettoie les espaces invisibles au cas où
    df_local['code'] = df_local['code'].str.strip()
except Exception as e:
    st.sidebar.error(f"Erreur fichier : {e}")
    df_local = pd.DataFrame()

    if not data and not df_local.empty:
        local_match = df_local[df_local['code'] == str(barcode).strip()]
        if not local_match.empty:
            lp = local_match.iloc[0]
            data = {
                "nom": lp['nom'], 
                "emb": lp['emb'], 
                "ingredients": lp['ingredients'], 
                "sucre": lp.get('sucre', 0),
                "source": "Base locale (CSV)"
            }

    if data:
        st.markdown("---")
        col_img, col_txt = st.columns([1, 3])
        with col_img:
            if data.get('image'):
                st.image(data['image'], use_container_width=True)
            else:
                st.info("📷 Pas d'image")
        with col_txt:
            st.success(f"## {data['nom']}")
            st.caption(f"Source : {data['source']}")
            c1, c2 = st.columns(2)
            c1.metric("Sucre (100g)", f"{data['sucre']}g")
            c2.info(f"🏭 Code Usine : {data['emb'] if data['emb'] else 'Non détecté'}")
            with st.expander("📜 Voir la recette"):
                st.write(data['ingredients'])

        if data['emb'] and not df_local.empty:
            clean_emb = str(data['emb']).strip()
            clones = df_local[df_local['emb'].str.contains(clean_emb, na=False, case=False) & (df_local['nom'] != data['nom'])]
            if not clones.empty:
                st.subheader(f"💡 {len(clones)} Clones détectés")
                for _, c in clones.iterrows():
                    score = calculer_score(data['ingredients'], c['ingredients'])
                    with st.expander(f"✅ {c['nom']} ({score}%)"):
                        diff_html = comparer_visuel(data['ingredients'], c['ingredients'])
                        st.markdown(f"<div style='padding:10px; border:1px solid #ddd;'>{diff_html}</div>", unsafe_allow_html=True)
    else:
        st.error("❌ Produit introuvable.")
