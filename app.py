import streamlit as st
import pandas as pd
import requests
import difflib
import re
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="TwinFood", page_icon="👥", layout="wide")

# --- LOGO SVG & SLOGAN ---
st.markdown("""
<div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px;">
    <svg width="80" height="80" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#34495e;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#2c3e50;stop-opacity:1" />
            </linearGradient>
            <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#2ecc71;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#27ae60;stop-opacity:1" />
            </linearGradient>
        </defs>
        <path d="M 20 20 L 100 20 L 100 100 C 100 110, 20 110, 20 100 Z" fill="url(#grad1)" />
        <rect x="30" y="40" width="5" height="50" fill="#ecf0f1" rx="1" />
        <rect x="40" y="40" width="10" height="50" fill="#ecf0f1" rx="1" />
        <rect x="55" y="40" width="3" height="50" fill="#ecf0f1" rx="1" />
        <rect x="63" y="40" width="8" height="50" fill="#ecf0f1" rx="1" />
        <path d="M 90 40 L 100 50 L 115 25" stroke="url(#grad2)" stroke-width="12" fill="none" stroke-linecap="round" />
        <text x="60" y="115" text-anchor="middle" font-size="22" font-weight="bold" fill="#ecf0f1">TF</text>
    </svg>
    <div>
        <h1 style="margin:0;">TwinFood</h1>
        <h5 style="margin:0; color: #7f8c8d;">Parce que la vie devrait être moins chère</h5>
    </div>
</div>
""", unsafe_allow_html=True)

# --- STYLE CSS ---
st.markdown("""
    <style>
    .card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: white; color: black; }
    .diff-red { color: #e74c3c; font-weight: bold; text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS ---
def highlight_diff(base, target):
    """Compare les ingrédients et surligne les différences."""
    b_list = [x.strip().lower() for x in re.split(r'[,;]', str(base))]
    t_list = [x.strip() for x in re.split(r'[,;]', str(target))]
    return ", ".join([f"<span class='diff-red'>{i}</span>" if i.lower() not in b_list else i for i in t_list])

@st.cache_data(ttl=5)
def load_local_data():
    if os.path.exists("produits.csv"):
        try:
            return pd.read_csv("produits.csv", dtype=str).fillna("")
        except: return pd.DataFrame()
    return pd.DataFrame()

def fetch_product_off(barcode):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get('status') == 1:
            p = res['product']
            emb = p.get('emb_codes', '').split(',')[0].strip() or p.get('manufacturing_places', '').split(',')[0].strip()
            cat = p.get('categories_tags', [''])[0].replace('en:', '').replace('fr:', '')
            return {
                "code": barcode,
                "nom": p.get('product_name_fr', 'Inconnu'),
                "marque": p.get('brands', 'Inconnue'),
                "categorie": cat,
                "emb": emb,
                "ingredients": p.get('ingredients_text_fr', 'Non renseigné')
            }
    except: return None
    return None

def fetch_clones_off(emb_code, category_filter):
    clean_cat = category_filter.split(',')[-1].strip()
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&tagtype_0=emb_codes&tag_contains_0=contains&tag_0={emb_code}&tagtype_1=categories&tag_contains_1=contains&tag_1={clean_cat}&json=true&page_size=50"
    clones = []
    try:
        res = requests.get(url, timeout=10).json()
        for p in res.get('products', []):
            clones.append({
                "code": p.get('code'),
                "nom": p.get('product_name_fr', 'Inconnu'),
                "marque": p.get('brands', 'Inconnue'),
                "ingredients": p.get('ingredients_text_fr', 'Non renseigné')
            })
    except: pass
    return clones

# --- INTERFACE ---
code_input = st.text_input("Scannez ou saisissez un code-barres :")

if code_input:
    df_local = load_local_data()
    p = fetch_product_off(code_input)
    
    # Secours Local (KeyError Protection avec .get)
    if not p and not df_local.empty:
        match = df_local[df_local['code'] == code_input]
        if not match.empty:
            row = match.iloc[0]
            p = {
                "code": code_input,
                "nom": row.get('nom', 'Inconnu'),
                "marque": row.get('marque', 'Inconnue'),
                "categorie": row.get('categorie', 'Inconnue'),
                "emb": row.get('emb', ''),
                "ingredients": row.get('ingredients', 'Non renseigné')
            }

    if p:
        st.success(f"### {p['nom']} ({p['marque']})")
        st.info(f"🏭 Usine : {p['emb']} | 🏷️ Type : {p['categorie']}")
        
        if p['emb']:
            with st.spinner("Recherche des jumeaux..."):
                all_clones = fetch_clones_off(p['emb'], p['categorie'])
                
                # Ajout des clones du CSV local
                if not df_local.empty:
                    loc_matches = df_local[(df_local['emb'] == p['emb']) & (df_local['code'] != code_input)]
                    for _, r in loc_matches.iterrows():
                        all_clones.append({
                            "code": r.get('code'),
                            "nom": r.get('nom', 'Inconnu'),
                            "marque": r.get('marque', 'Inconnue'),
                            "ingredients": r.get('ingredients', '')
                        })

                if all_clones:
                    st.subheader(f"💡 {len(all_clones)} Clones trouvés")
                    for c in all_clones[:15]:
                        if str(c.get('code')) != str(code_input):
                            score = int(difflib.SequenceMatcher(None, str(p['ingredients']), str(c['ingredients'])).ratio() * 100)
                            with st.container():
                                st.markdown(f"""<div class="card">
                                    <h4 style="margin:0;">{c.get('nom')}</h4>
                                    <p style="color: gray; margin:0;">Marque : {c.get('marque')} | Ressemblance : <b>{score}%</b></p>
                                </div>""", unsafe_allow_html=True)
                                with st.expander("Comparer la recette"):
                                    diff_html = highlight_diff(p['ingredients'], c['ingredients'])
                                    st.markdown(f"**Ingrédients :** {diff_html}", unsafe_allow_html=True)
                else:
                    st.warning("Aucun clone trouvé.")
        else:
            st.warning("Ce produit n'a pas de code usine répertorié.")
    else:
        st.error("Produit introuvable.")
