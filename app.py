import streamlit as st
import pandas as pd
import requests
import difflib

# 1. CERVEAU : Recherche Web (Open Food Facts)
def fetch_off_data(barcode):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    headers = {'User-Agent': 'CloneDetector - WebVersion - 1.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 1:
                p = data['product']
                # On essaie de trouver le code EMB dans différents champs de l'API
                emb = p.get('emb_codes', '').split(',')[0] if p.get('emb_codes') else p.get('manufacturing_places', '')
                return {
                    "nom": p.get('product_name_fr') or p.get('product_name') or "Inconnu",
                    "emb": emb,
                    "ingredients": p.get('ingredients_text_fr') or p.get('ingredients_text') or "Non renseignés",
                    "categorie": p.get('categories_tags', [None])[0].replace('en:', '').replace('fr:', '') if p.get('categories_tags') else "Divers",
                    "sucre": p.get('nutriments', {}).get('sugars_100g', 0)
                }
    except:
        return None
    return None

# 2. CERVEAU : Comparaison
def calculer_score(ing1, ing2):
    return int(difflib.SequenceMatcher(None, str(ing1).lower(), str(ing2).lower()).ratio() * 100)

def comparer_visuel(ref, comp):
    ref_words = str(ref).lower().replace(',', '').split()
    comp_raw = str(comp).split()
    res = ""
    for w in comp_raw:
        clean = w.lower().replace(',', '')
        if clean in ref_words: res += f"{w} "
        else: res += f"<span style='color:red; font-weight:bold;'>{w}</span> "
    return res

# --- INTERFACE ---
st.set_page_config(page_title="CloneDetector Global", layout="wide")
st.title("🌐 CloneDetector Global")

barcode = st.text_input("Scannez n'importe quel produit du monde :", placeholder="Ex: 3017620422003")

if barcode:
    # ÉTAPE 1 : On cherche sur le Web
    with st.spinner("Interrogation de la base mondiale..."):
        data = fetch_off_data(barcode)
    
    # ÉTAPE 2 : Si pas sur le Web, on cherche dans ton CSV
    if not data:
        df_local = pd.read_csv("produits.csv", dtype={'code': str})
        local_p = df_local[df_local['code'] == barcode.strip()]
        if not local_p.empty:
            lp = local_p.iloc[0]
            data = {"nom": lp['nom'], "emb": lp['emb'], "ingredients": lp['ingredients'], "categorie": lp['categorie'], "sucre": lp['sucre']}

    if data:
        st.header(f"📦 {data['nom']}")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Sucre (100g)", f"{data['sucre']}g")
            st.info(f"🏭 Code Usine : {data['emb'] if data['emb'] else 'Non détecté'}")
        
        with col2:
            with st.expander("📜 Recette complète"):
                st.write(data['ingredients'])

        # ÉTAPE 3 : Recherche de Clones dans ton CSV (Basée sur l'EMB du Web)
        if data['emb']:
            df = pd.read_csv("produits.csv", dtype={'code': str})
            # On nettoie le code EMB pour la recherche
            clean_emb = data['emb'].strip()
            clones = df[df['emb'].str.contains(clean_emb, na=False, case=False) & (df['nom'] != data['nom'])]
            
            if not clones.empty:
                st.subheader(f"💡 Clones détectés dans notre base ({len(clones)})")
                for _, c in clones.iterrows():
                    score = calculer_score(data['ingredients'], c['ingredients'])
                    with st.expander(f"✅ {c['nom']} ({score}%)"):
                        st.markdown(f"**Analyse comparative :**<br>{comparer_visuel(data['ingredients'], c['ingredients'])}", unsafe_allow_html=True)
            else:
                st.warning("Aucun clone répertorié pour cette usine dans notre base locale.")
    else:
        st.error("Produit introuvable (Web et Local).")
