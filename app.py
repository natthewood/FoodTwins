import streamlit as st
import pandas as pd
import requests
import difflib
import re
import os
from PIL import Image

# --- CONFIGURATION & DESIGN ---
st.set_page_config(page_title="TwinFood : Débusquez les clones !", page_icon="👥", layout="wide")

st.markdown("""
    <style>
    .badge { padding: 4px 10px; border-radius: 12px; font-weight: bold; margin-right: 5px; display: inline-block; margin-bottom: 5px; font-size: 0.85em; }
    .vegan { background-color: #2ecc71; color: white; }
    .no-pork { background-color: #f1c40f; color: black; }
    .gluten-free { background-color: #8e44ad; color: white; }
    .diff-red { color: #e74c3c; font-weight: bold; text-decoration: underline; }
    .source-web { background-color: #3498db; color: white; }
    .card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- EN-TÊTE ---
col_logo, col_titre = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
    else:
        st.markdown("## 👥")
with col_titre:
    st.title("TwinFood")
    st.markdown("##### Identifiez les produits de grandes marques et leurs alternatives.")

# --- FONCTIONS ---
@st.cache_data(ttl=10)
def load_local_data():
    if os.path.exists("produits.csv"):
        try:
            return pd.read_csv("produits.csv", dtype=str).fillna("")
        except: return pd.DataFrame()
    return pd.DataFrame()

def save_to_csv(new_row):
    df = load_local_data()
    new_df = pd.DataFrame([new_row])
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_csv("produits.csv", index=False)
    st.cache_data.clear()

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

def fetch_clones_off(emb_code, category_filter):
    # On nettoie la catégorie pour éviter les erreurs d'URL (on ne garde que le dernier segment)
    clean_cat = category_filter.split(',')[-1].strip()
    
    # URL de recherche optimisée
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&tagtype_0=emb_codes&tag_contains_0=contains&tag_0={emb_code}&tagtype_1=categories&tag_contains_1=contains&tag_1={clean_cat}&json=true&page_size=50"
    
    clones = []
    try:
        # On passe le timeout à 10 secondes
        res = requests.get(url, timeout=10).json()
        if "products" in res:
            for p in res.get('products', []):
                clones.append({
                    "code": p.get('code'), # Indispensable pour la comparaison !
                    "nom": p.get('product_name_fr', 'Inconnu'),
                    "marque": p.get('brands', 'Inconnue'),
                    "ingredients": p.get('ingredients_text_fr', 'Non renseigné'),
                    "source": "🌐 Web"
                })
    except Exception as e:
        st.error(f"⚠️ Problème de connexion avec le site : {e}")
    return clones

def highlight_differences(base_ing, clone_ing):
    base_list = [x.strip().lower() for x in re.split(r'[,;]', str(base_ing))]
    clone_list = [x.strip() for x in re.split(r'[,;]', str(clone_ing))]
    return ", ".join([f"<span class='diff-red'>{item}</span>" if item.lower() not in base_list else item for item in clone_list])

def get_badges_html(ingredients):
    badges = ""
    ing_low = str(ingredients).lower()
    if "porc" not in ing_low: badges += '<span class="badge no-pork">🚫 🐷 Sans Porc</span>'
    if not any(x in ing_low for x in ["viande", "poisson"]): badges += '<span class="badge vegan">🍃 Végétarien</span>'
    return badges

# --- INTERFACE ---
tab_search, tab_add = st.tabs(["🔍 Rechercher", "📸 Ajouter"])

with tab_search:
    with st.form("search"):
        code_input = st.text_input("Scannez un code-barres :")
        submit = st.form_submit_button("Chercher 🚀")

    if submit and code_input:
        df_local = load_local_data()
        p = fetch_product_off(code_input)
        
        if not p and not df_local.empty:
            match = df_local[df_local['code'] == code_input]
            if not match.empty:
                row = match.iloc[0]
                p = {"nom": row['nom'], "marque": row['marque'], "categorie": row['categorie'], "emb": row['emb'], "ingredients": row['ingredients'], "sucre": row['sucre'], "source": "📁 Local"}

        if p:
            st.success(f"### {p['nom']} ({p['marque']})")
            st.info(f"🏭 Usine : {p['emb']} | 🏷️ Type : {p['categorie']}")
            
            if p['emb']:
                with st.spinner("Recherche des jumeaux..."):
                    clones = fetch_clones_off(p['emb'], p['categorie'])
                    if clones:
                        st.subheader(f"💡 {len(clones)} Clones trouvés")
                        for c in clones[:15]:
                            if c['nom'] != p['nom']:
                                score = int(difflib.SequenceMatcher(None, str(p['ingredients']), str(c['ingredients'])).ratio() * 100)
                                with st.container():
                                    st.markdown(f"""<div class="card">
                                        <h4 style="margin:0;">{c['nom']}</h4>
                                        <p style="color: gray; margin:0;">Marque : {c['marque']} | Ressemblance : <b>{score}%</b></p>
                                    </div>""", unsafe_allow_html=True)
                                    with st.expander("Comparer la recette"):
                                        diff_html = highlight_differences(p['ingredients'], c['ingredients'])
                                        st.markdown(f"**Ingrédients :** {diff_html}", unsafe_allow_html=True)
                    else:
                        st.warning("Aucun clone trouvé pour cette catégorie précise.")
            else:
                st.error("Pas de code usine détecté.")
        else:
            st.error("Produit inconnu.")

with tab_add:
    st.subheader("📸 Ajouter au CSV local")
    with st.form("add_form", clear_on_submit=True):
        f_code = st.text_input("Code-barres")
        f_nom = st.text_input("Nom")
        f_marque = st.text_input("Marque")
        f_emb = st.text_input("Code Usine (EMB)")
        f_ing = st.text_area("Ingrédients")
        if st.form_submit_button("💾 Sauvegarder"):
            save_to_csv({"code": f_code, "nom": f_nom, "marque": f_marque, "emb": f_emb, "ingredients": f_ing})
            st.success("Produit enregistré !")
