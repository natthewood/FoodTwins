import streamlit as st
import pandas as pd
import requests
import difflib

# --- CONFIGURATION ---
st.set_page_config(page_title="CloneDetector Global", page_icon="🔍", layout="wide")

# --- FONCTIONS ---
def fetch_off_data(barcode):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 1:
                p = data['product']
                emb = p.get('emb_codes', '').split(',')[0] if p.get('emb_codes') else p.get('manufacturing_places', '')
                return {
                    "nom": p.get('product_name_fr') or p.get('product_name') or "Inconnu",
                    "emb": str(emb).strip(),
                    "ingredients": p.get('ingredients_text_fr') or p.get('ingredients_text') or "Non renseignés",
                    "categorie": p.get('categories_tags', [None])[0].replace('en:', '').replace('fr:', '') if p.get('categories_tags') else "Divers",
                    "sucre": p.get('nutriments', {}).get('sugars_100g', 0)
                }
    except: return None
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
st.write("Analyse en temps réel : Web (Open Food Facts) + Base de Clones locale")

# Zone de saisie (optimisée pour scanner mobile/douchette)
barcode = st.text_input("Scanner ou entrez un code-barres :", key="barcode_input")

if barcode:
    # 1. Recherche WEB
    with st.spinner("Recherche mondiale..."):
        data = fetch_off_data(barcode)
    
    # 2. Recherche LOCAL (si web échoue)
    if not data:
        try:
            df_local = pd.read_csv("produits.csv", dtype={'code': str})
            local_p = df_local[df_local['code'] == str(barcode).strip()]
            if not local_p.empty:
                lp = local_p.iloc[0]
                data = {"nom": lp['nom'], "emb": lp['emb'], "ingredients": lp['ingredients'], "categorie": lp.get('categorie', 'Divers'), "sucre": lp.get('sucre', 0)}
        except: pass

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
        if data['emb'] and data['emb'] != "":
            try:
                df = pd.read_csv("produits.csv", dtype={'code': str})
                clean_emb = str(data['emb']).strip()
                clones = df[df['emb'].str.contains(clean_emb, na=False, case=False) & (df['nom'] != data['nom'])]
                
                if not clones.empty:
                    st.subheader(f"💡 {len(clones)} Clones trouvés dans votre base")
                    for _, c in clones.iterrows():
                        score = calculer_score(data['ingredients'], c['ingredients'])
                        with st.expander(f"✅ {c['nom']} ({score}%)"):
                            st.markdown(f"**Analyse :** {comparer_visuel(data['ingredients'], c['ingredients'])}", unsafe_allow_html=True)
                else:
                    st.warning("Aucun clone répertorié pour cette usine.")
            except: st.error("Erreur base locale.")
    else:
        st.error("Produit inconnu.")
