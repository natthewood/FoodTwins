import streamlit as st
import pandas as pd
import requests
import difflib

st.set_page_config(page_title="CloneDetector Debug", layout="wide")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data # Pour éviter de recharger le fichier à chaque clic
def load_csv():
    try:
        # On force tout en texte pour éviter les bugs de nombres
        df = pd.read_csv("produits.csv", dtype=str).fillna("")
        df['code'] = df['code'].str.strip()
        return df
    except Exception as e:
        st.error(f"Erreur de lecture CSV : {e}")
        return pd.DataFrame()

df_local = load_csv()

# --- RECHERCHE API ---
def fetch_off_data(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 1:
                p = data['product']
                emb = p.get('emb_codes', '').split(',')[0] if p.get('emb_codes') else p.get('manufacturing_places', '')
                return {
                    "nom": p.get('product_name_fr', 'Inconnu'),
                    "emb": str(emb).strip(),
                    "ingredients": p.get('ingredients_text_fr', ''),
                    "image": p.get('image_front_url')
                }
    except: pass
    return None

# --- INTERFACE ---
st.title("🔬 Testeur de Base de Données")

# ZONE DE DEBUG (À supprimer plus tard)
with st.expander("🛠 Infos Techniques (Debug)"):
    st.write(f"Nombre de produits chargés : {len(df_local)}")
    if not df_local.empty:
        st.write("Aperçu des 3 premiers codes dans le fichier :")
        st.write(df_local['code'].head(3).tolist())

barcode = st.text_input("Tapez le code 3000000000001 :").strip()

if barcode:
    # 1. On cherche d'abord dans le CSV
    local_match = df_local[df_local['code'] == barcode]
    
    if not local_match.empty:
        prod = local_match.iloc[0]
        st.success(f"✅ Trouvé dans le CSV : {prod['nom']}")
        
        # Recherche des clones par EMB
        if prod['emb']:
            clones = df_local[(df_local['emb'] == prod['emb']) & (df_local['code'] != barcode)]
            st.info(f"Usine détectée : {prod['emb']}. Nombre de clones potentiels : {len(clones)}")
            
            for _, c in clones.head(10).iterrows():
                st.warning(f"Clone trouvé : {c['nom']}")
    else:
        # 2. Si pas dans le CSV, on tente le Web
        st.warning("⚠️ Absent du CSV. Tentative sur le Web...")
        web_data = fetch_off_data(barcode)
        if web_data:
            st.write(f"Produit Web : {web_data['nom']}")
        else:
            st.error("❌ Ce code n'existe nulle part (ni CSV, ni Web).")
