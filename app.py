import streamlit as st
import pandas as pd
import requests
import difflib

# --- CONFIGURATION ---
st.set_page_config(page_title="CloneDetector Debug", page_icon="🔬", layout="wide")

# --- FONCTION DE RECHERCHE WEB AVEC DIAGNOSTIC ---
def fetch_off_data(barcode):
    # On force le format texte et on nettoie
    clean_barcode = str(barcode).strip()
    url = f"https://world.openfoodfacts.org/api/v2/product/{clean_barcode}.json"
    
    # INDISPENSABLE : Le User-Agent pour ne pas être banni
    headers = {
        'User-Agent': 'CloneDetector - DebugMode - Version 1.0 (https://share.streamlit.io/)'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        
        # --- ZONE DIAGNOSTIC ---
        with st.sidebar:
            st.header("🛠 Diagnostic API")
            st.write(f"**URL testée :** {url}")
            st.write(f"**Code réponse :** {res.status_code}")
            if res.status_code == 200:
                st.success("Connexion établie ✅")
            elif res.status_code == 403:
                st.error("Accès refusé (403). L'API bloque la requête.")
            else:
                st.warning(f"Réponse inhabituelle : {res.status_code}")
        # --- FIN DIAGNOSTIC ---

        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 1:
                p = data['product']
                emb = p.get('emb_codes', '').split(',')[0] if p.get('emb_codes') else p.get('manufacturing_places', '')
                return {
                    "nom": p.get('product_name_fr') or p.get('product_name') or "Inconnu",
                    "emb": str(emb).strip(),
                    "ingredients": p.get('ingredients_text_fr') or p.get('ingredients_text') or "Non renseignés",
                    "sucre": p.get('nutriments', {}).get('sugars_100g', 0)
                }
            else:
                st.sidebar.info("Produit non trouvé dans la base OFF.")
    except Exception as e:
        st.sidebar.error(f"Erreur de connexion : {e}")
    return None

def calculer_score(ing1, ing2):
    return int(difflib.SequenceMatcher(None, str(ing1).lower(), str(ing2).lower()).ratio() * 100)

def comparer_visuel(ref, comp):
    ref_words = str(ref).lower().replace(',', '').replace('.', '').split()
    comp_raw = str(comp).split()
    res = ""
    for w in comp_raw:
        clean = w.lower().replace(',', '').replace('.', '')
        if clean in ref_words: res += f"{w} "
        else: res += f"<span style='color:red; font-weight:bold; background-color: #ffecec;'>{w}</span> "
    return res

# --- INTERFACE ---
st.title("🔬 CloneDetector Global")

barcode = st.text_input("Scanner ou entrez un code-barres (ex: 3033490004482) :")

if barcode:
    # 1. Recherche WEB
    data = fetch_off_data(barcode)
    
    # 2. Recherche LOCAL (si web échoue ou pour compléter)
    try:
        df_local = pd.read_csv("produits.csv", dtype={'code': str})
    except:
        st.error("Fichier produits.csv introuvable sur GitHub.")
        df_local = pd.DataFrame()

    if data:
        st.success(f"## {data['nom']}")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Sucre (100g)", f"{data['sucre']}g")
            st.info(f"🏭 Usine (EMB) : {data['emb'] if data['emb'] else 'Non détecté'}")
        with c2:
            with st.expander("📜 Voir la recette complète"):
                st.write(data['ingredients'])

        # 3. Recherche de CLONES dans le CSV
        if data['emb'] and not df_local.empty:
            clean_emb = str(data['emb']).strip()
            clones = df_local[df_local['emb'].str.contains(clean_emb, na=False, case=False) & (df_local['nom'] != data['nom'])]
            
            if not clones.empty:
                st.subheader(f"💡 {len(clones)} Clones trouvés dans votre base")
                for _, c in clones.iterrows():
                    score = calculer_score(data['ingredients'], c['ingredients'])
                    with st.expander(f"✅ {c['nom']} ({score}%)"):
                        st.markdown(f"**Analyse :** {comparer_visuel(data['ingredients'], c['ingredients'])}", unsafe_allow_html=True)
            else:
                st.warning("Aucun clone répertorié pour cette usine.")
    else:
        st.error("Produit inconnu (Web et Local).")
