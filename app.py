import streamlit as st
import pandas as pd
import requests
import difflib
import re
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="TwinFood", page_icon="👥", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .badge { padding: 4px 10px; border-radius: 12px; font-weight: bold; margin-right: 5px; display: inline-block; margin-bottom: 5px; font-size: 0.85em; }
    .diff-red { color: #e74c3c; font-weight: bold; text-decoration: underline; }
    .card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)
import streamlit as st
import os

# --- INJECTION DU LOGO EN SVG ---
# Nous utilisons du code SVG pour dessiner le logo afin de contourner le bug d'affichage.
st.markdown("""
<style>
.logo-container {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
}
</style>
<div class="logo-container">
    <svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
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
        <path d="M 10 30 L 110 30 L 105 15 L 15 15 Z" fill="url(#grad1)" />
        
        <rect x="30" y="40" width="5" height="50" fill="#ecf0f1" rx="1" />
        <rect x="40" y="40" width="10" height="50" fill="#ecf0f1" rx="1" />
        <rect x="55" y="40" width="3" height="50" fill="#ecf0f1" rx="1" />
        <rect x="63" y="40" width="8" height="50" fill="#ecf0f1" rx="1" />
        <rect x="76" y="40" width="14" height="50" fill="#ecf0f1" rx="1" />
        
        <path d="M 90 40 L 100 50 L 115 25" stroke="url(#grad2)" stroke-width="12" fill="none" stroke-linecap="round" />
        <path d="M 85 45 L 95 55 L 110 30" stroke="url(#grad2)" stroke-width="8" fill="none" stroke-linecap="round" />
        
        <text x="60" y="115" text-anchor="middle" font-size="22" font-weight="bold" fill="#ecf0f1">TF</text>
    </svg>
</div>
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
    st.markdown("##### Parce que la vie devrait être moins chère !")

# --- FONCTIONS ---
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
                "ingredients": p.get('ingredients_text_fr', 'Non renseigné'),
                "source": "🌐 Open Food Facts"
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
                "ingredients": p.get('ingredients_text_fr', 'Non renseigné'),
                "source": "🌐 Web"
            })
    except: pass
    return clones

def highlight_diff(base, target):
    b_list = [x.strip().lower() for x in re.split(r'[,;]', str(base))]
    t_list = [x.strip() for x in re.split(r'[,;]', str(target))]
    return ", ".join([f"<span class='diff-red'>{i}</span>" if i.lower() not in b_list else i for i in t_list])

# --- INTERFACE ---
tab1, tab2 = st.tabs(["🔍 Recherche", "📸 Ajouter"])

with tab1:
    with st.form("search"):
        code_input = st.text_input("Scannez un code-barres :")
        submit = st.form_submit_button("Chercher 🚀")

    if submit and code_input:
        df_local = load_local_data()
        p = fetch_product_off(code_input)
        
        # Sécurité pour le KeyError : on vérifie si les colonnes existent dans le CSV
        if not p and not df_local.empty:
            match = df_local[df_local['code'] == code_input]
            if not match.empty:
                row = match.iloc[0]
                # .get('colonne', 'défaut') évite le KeyError si une colonne manque
                p = {
                    "code": code_input,
                    "nom": row.get('nom', 'Inconnu'),
                    "marque": row.get('marque', 'Inconnue'),
                    "categorie": row.get('categorie', ''),
                    "emb": row.get('emb', ''),
                    "ingredients": row.get('ingredients', 'Non renseigné'),
                    "source": "📁 Local"
                }

        if p:
            st.success(f"### {p['nom']} ({p['marque']})")
            st.info(f"🏭 Usine : {p['emb']} | 🏷️ Type : {p['categorie']}")
            
            if p['emb']:
                with st.spinner("Recherche des jumeaux..."):
                    # 1. Clones du Web
                    all_clones = fetch_clones_off(p['emb'], p['categorie'])
                    
                    # 2. Clones du CSV local
                    if not df_local.empty:
                        loc_matches = df_local[(df_local['emb'] == p['emb']) & (df_local['code'] != code_input)]
                        for _, r in loc_matches.iterrows():
                            all_clones.append({
                                "code": r.get('code'),
                                "nom": r.get('nom', 'Inconnu'),
                                "marque": r.get('marque', 'Inconnue'),
                                "ingredients": r.get('ingredients', ''),
                                "source": "📁 Local"
                            })

                    if all_clones:
                        st.subheader(f"💡 {len(all_clones)} Clones trouvés")
                        for c in all_clones[:15]:
                            # On compare les codes-barres pour ne pas s'afficher soi-même
                            if str(c['code']) != str(code_input):
                                score = int(difflib.SequenceMatcher(None, str(p['ingredients']), str(c['ingredients'])).ratio() * 100)
                                with st.container():
                                    st.markdown(f"""<div class="card">
                                        <h4 style="margin:0;">{c['nom']}</h4>
                                        <p style="color: gray; margin:0;">Marque : {c['marque']} | Ressemblance : <b>{score}%</b></p>
                                    </div>""", unsafe_allow_html=True)
                                    with st.expander("Comparer la recette"):
                                        diff = highlight_diff(p['ingredients'], c['ingredients'])
                                        st.markdown(f"**Ingrédients :** {diff}", unsafe_allow_html=True)
                    else:
                        st.warning("Aucun clone trouvé.")
            else:
                st.warning("Pas de code usine (EMB) pour ce produit.")
        else:
            st.error("Produit introuvable.")
