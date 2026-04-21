import streamlit as st
import pandas as pd
import requests
import difflib
import re
import os

# --- CONFIGURATION & DESIGN ---
st.set_page_config(page_title="CloneDetector Global", page_icon="🌐", layout="wide")

st.markdown("""
    <style>
    .badge { padding: 4px 10px; border-radius: 12px; font-weight: bold; margin-right: 5px; display: inline-block; margin-bottom: 5px; font-size: 0.85em; }
    .vegan { background-color: #2ecc71; color: white; }
    .no-pork { background-color: #f1c40f; color: black; }
    .gluten-free { background-color: #8e44ad; color: white; }
    .diff-red { color: #e74c3c; font-weight: bold; text-decoration: underline; }
    .source-web { background-color: #3498db; color: white; }
    .source-local { background-color: #2c3e50; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS DE CHARGEMENT ---
@st.cache_data(ttl=60)
def load_local_data():
    if os.path.exists("produits.csv"):
        try:
            df = pd.read_csv("produits.csv", dtype=str).fillna("")
            df['code'] = df['code'].str.strip()
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- RECHERCHE PRODUIT UNIQUE (API) ---
def fetch_product_off(barcode):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get('status') == 1:
            p = res['product']
            emb = p.get('emb_codes', '').split(',')[0].strip() or p.get('manufacturing_places', '').split(',')[0].strip()
            return {
                "nom": p.get('product_name_fr', 'Inconnu'),
                "marque": p.get('brands', 'Inconnue'),
                "categorie": p.get('categories_tags', [''])[0].replace('en:', '').replace('fr:', ''),
                "emb": emb,
                "ingredients": p.get('ingredients_text_fr', 'Non renseigné'),
                "sucre": p.get('nutriments', {}).get('sugars_100g', 0),
                "image": p.get('image_front_url', ''),
                "source": "🌐 Open Food Facts"
            }
    except: return None
    return None

# --- RECHERCHE DE CLONES SUR LE WEB (API SEARCH) ---
def fetch_clones_off(emb_code, category_filter):
    # On cherche les produits qui ont ce code EMB
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&tagtype_0=emb_codes&tag_contains_0=contains&tag_0={emb_code}&json=true&page_size=50"
    clones = []
    try:
        res = requests.get(url, timeout=5).json()
        for p in res.get('products', []):
            # Filtrage par catégorie pour rester sur le même type de produit
            p_cats = p.get('categories_tags', [])
            if any(category_filter in c for c in p_cats):
                clones.append({
                    "code": p.get('code'),
                    "nom": p.get('product_name_fr', p.get('product_name', 'Inconnu')),
                    "marque": p.get('brands', 'Inconnue'),
                    "ingredients": p.get('ingredients_text_fr', 'Non renseigné'),
                    "sucre": p.get('nutriments', {}).get('sugars_100g', 0),
                    "source": "🌐 Web"
                })
    except: pass
    return clones

# --- UTILITAIRES ---
def highlight_differences(base_ing, clone_ing):
    base_list = [x.strip().lower() for x in re.split(r'[,;]', str(base_ing))]
    clone_list = [x.strip() for x in re.split(r'[,;]', str(clone_ing))]
    highlighted = []
    for item in clone_list:
        if item.lower() not in base_list:
            highlighted.append(f"<span class='diff-red'>{item}</span>")
        else: highlighted.append(item)
    return ", ".join(highlighted)

def get_badges_html(ingredients):
    badges = ""
    ing_low = str(ingredients).lower()
    if "porc" not in ing_low and "lard" not in ing_low: badges += '<span class="badge no-pork">🚫 🐷 Sans Porc</span>'
    if not any(x in ing_low for x in ["viande", "poisson", "poulet"]): badges += '<span class="badge vegan">🍃 Végétarien</span>'
    if "gluten" not in ing_low and "blé" not in ing_low: badges += '<span class="badge gluten-free">🌾 Sans Gluten</span>'
    return badges

# --- MAIN APP ---
df_local = load_local_data()

st.title("🔬 CloneDetector Global (Mode Web-First)")

with st.form("search"):
    c1, c2 = st.columns([4,1])
    code_input = c1.text_input("Scannez un code-barres :", placeholder="Ex: 3033490593030")
    submit = c2.form_submit_button("Lancer la recherche 🚀")

if submit and code_input:
    # 1. Priorité WEB
    p = fetch_product_off(code_input)
    
    # 2. Secours LOCAL
    if not p and not df_local.empty:
        match_local = df_local[df_local['code'] == code_input]
        if not match_local.empty:
            row = match_local.iloc[0]
            p = {"nom": row['nom'], "marque": row['marque'], "categorie": row['categorie'], 
                 "emb": row['emb'], "ingredients": row['ingredients'], "sucre": row['sucre'], "source": "📁 Base Locale"}

    if p:
        # Affichage Produit
        col_img, col_txt = st.columns([1,3])
        with col_img: 
            if p.get('image'): st.image(p['image'])
        with col_txt:
            st.markdown(f"## {p['nom']} ({p['marque']})")
            st.markdown(f"<span class='badge source-web'>{p['source']}</span>", unsafe_allow_html=True)
            st.markdown(get_badges_html(p['ingredients']), unsafe_allow_html=True)
            st.info(f"🏭 Code Usine détecté : **{p['emb']}** | Type : {p['categorie']}")

        # 3. Recherche de CLONES (Web + Local)
        if p['emb']:
            with st.spinner("Recherche mondiale des clones en cours..."):
                clones_web = fetch_clones_off(p['emb'], p['categorie'])
                
                # Ajout des clones de la base locale
                clones_local = []
                if not df_local.empty:
                    match_clones = df_local[(df_local['emb'] == p['emb']) & (df_local['code'] != code_input)]
                    for _, row in match_clones.iterrows():
                        clones_local.append({"nom": row['nom'], "marque": row['marque'], "ingredients": row['ingredients'], "sucre": row['sucre'], "source": "📁 Local"})
                
                all_clones = clones_web + clones_local
                
                if all_clones:
                    st.success(f"### 💡 {len(all_clones)} Clones trouvés sur le Web et en local !")
                    for c in all_clones[:15]: # Limite à 15 pour la fluidité
                        score = int(difflib.SequenceMatcher(None, str(p['ingredients']), str(c['ingredients'])).ratio() * 100)
                        
                        # Couleur du score
                        color = "green" if score > 85 else "orange" if score > 60 else "red"
                        
                        with st.expander(f"🛒 {c['nom']} ({c['marque']}) - <span style='color:{color}'>{score}% ressemblance</span>", unsafe_allow_html=True):
                            st.write(f"Source : {c['source']}")
                            diff_html = highlight_differences(p['ingredients'], c['ingredients'])
                            st.markdown(f"**Ingrédients :** {diff_html}", unsafe_allow_html=True)
                else:
                    st.warning("Aucun clone trouvé avec ce code usine.")
    else:
        st.error("Produit introuvable sur le Web et dans la base de secours.")
