import streamlit as st
import pandas as pd
import requests
import difflib
import re
import os

# --- CONFIGURATION & DESIGN ---
st.set_page_config(page_title="TwinFood", page_icon="👥", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .badge { padding: 4px 10px; border-radius: 12px; font-weight: bold; margin-right: 5px; display: inline-block; margin-bottom: 5px; font-size: 0.85em; }
    .vegan { background-color: #2ecc71; color: white; }
    .no-pork { background-color: #f1c40f; color: black; }
    .diff-red { color: #e74c3c; font-weight: bold; text-decoration: underline; background-color: #fdf2f2; padding: 2px; border-radius: 3px; }
    .card { border: 1px solid #ddd; padding: 20px; border-radius: 12px; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); color: black; }
    .source-tag { font-size: 0.7em; background: #3498db; color: white; padding: 2px 6px; border-radius: 4px; float: right; }
    </style>
    """, unsafe_allow_html=True)

# --- EN-TÊTE ---
col_head1, col_head2 = st.columns([1, 4])
with col_head1:
    st.markdown("""<svg width="100" height="100" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#34495e;stop-opacity:1" /><stop offset="100%" style="stop-color:#2c3e50;stop-opacity:1" /></linearGradient><linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:#2ecc71;stop-opacity:1" /><stop offset="100%" style="stop-color:#27ae60;stop-opacity:1" /></linearGradient></defs><path d="M 20 20 L 100 20 L 100 100 C 100 110, 20 110, 20 100 Z" fill="url(#grad1)" /><rect x="35" y="40" width="5" height="40" fill="#ecf0f1" /><rect x="45" y="40" width="10" height="40" fill="#ecf0f1" /><rect x="60" y="40" width="3" height="40" fill="#ecf0f1" /><path d="M 90 40 L 100 50 L 115 25" stroke="url(#grad2)" stroke-width="10" fill="none" stroke-linecap="round" /></svg>""", unsafe_allow_html=True)
with col_head2:
    st.title("TwinFood")
    st.markdown("#### Parce que la vie devrait être moins chère")

# --- FONCTIONS ---
def highlight_diff(base, target):
    b_list = [x.strip().lower() for x in re.split(r'[,;.]', str(base)) if x.strip()]
    t_list = [x.strip() for x in re.split(r'[,;.]', str(target)) if x.strip()]
    highlighted = []
    for item in t_list:
        if item.lower() not in b_list:
            highlighted.append(f"<span class='diff-red'>{item}</span>")
        else:
            highlighted.append(item)
    return ", ".join(highlighted)

def get_badges(ingredients):
    badges = ""
    ing_low = str(ingredients).lower()
    
    # Correction de la syntaxe pour plusieurs mots
    pork_terms = ["porc", "jambon", "lardons", "salami"]
    if not any(word in ing_low for word in pork_terms):
        badges += '<span class="badge no-pork">🚫🐷 Sans Porc</span>'
    
    veggie_terms = ["viande", "boeuf", "poulet", "poisson", "thon", "saumon"]
    if not any(word in ing_low for word in veggie_terms):
        badges += '<span class="badge vegan">🍃 Veggie</span>'
        
    return badges

@st.cache_data(ttl=5)
def load_data():
    if os.path.exists("produits.csv"):
        return pd.read_csv("produits.csv", dtype=str).fillna("")
    return pd.DataFrame(columns=["code", "nom", "marque", "categorie", "emb", "ingredients"])

def fetch_off(barcode):
    try:
        res = requests.get(f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json", timeout=8).json()
        if res.get('status') == 1:
            p_data = res['product']
            emb = p_data.get('emb_codes', '').split(',')[0].strip() or p_data.get('manufacturing_places', '').split(',')[0].strip()
            return {
                "code": barcode, "nom": p_data.get('product_name_fr', 'Inconnu'),
                "marque": p_data.get('brands', 'Inconnue'), "emb": emb,
                "categorie": p_data.get('categories_tags', [''])[0].replace('en:', '').replace('fr:', ''),
                "ing": p_data.get('ingredients_text_fr', 'Non renseigné'), "img": p_data.get('image_front_url', '')
            }
    except: return None

def fetch_clones(emb, cat_filter):
    clones_list = []
    try:
        clean_cat = cat_filter.split(',')[-1].strip()
        url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&tagtype_0=emb_codes&tag_contains_0=contains&tag_0={emb}&tagtype_1=categories&tag_contains_1=contains&tag_1={clean_cat}&json=true"
        res = requests.get(url, timeout=8).json()
        for p_item in res.get('products', []):
            clones_list.append({"code": p_item.get('code'), "nom": p_item.get('product_name_fr', 'Inconnu'), "marque": p_item.get('brands', 'Inconnue'), "ing": p_item.get('ingredients_text_fr', 'Non renseigné')})
    except: pass
    return clones_list

# --- INTERFACE PAR ONGLETS ---
tab_search, tab_add = st.tabs(["🔍 Rechercher un jumeau", "📸 Enrichir la base"])

with tab_search:
    with st.form("search_form"):
        code_input = st.text_input("Scannez ou saisissez un code-barres (ex: 3560070513904) :")
        submit_button = st.form_submit_button("Lancer la recherche 🚀")
    
    if (submit_button or code_input) and code_input:
        df_local = load_data()
        p = fetch_off(code_input)
        
        if not p and not df_local.empty:
            match = df_local[df_local['code'] == str(code_input)]
            if not match.empty:
                r = match.iloc[0]
                p = {"code": code_input, "nom": r.get('nom'), "marque": r.get('marque'), "emb": r.get('emb'), "categorie": r.get('categorie'), "ing": r.get('ingredients'), "img": ""}

        if p:
            col_img, col_info = st.columns([1, 3])
            with col_img:
                if p.get('img'): st.image(p['img'], width=150)
                else: st.markdown("### 🍕")
            with col_info:
                st.subheader(f"{p['nom']} - {p['marque']}")
                st.markdown(get_badges(p['ing']), unsafe_allow_html=True)
                st.info(f"🏭 Usine : **{p['emb']}** | 🏷️ Catégorie : {p['categorie']}")
            
            with st.expander("📄 Voir les ingrédients du produit scanné"):
                st.write(p['ing'])

            if p['emb']:
                with st.spinner("Analyse des usines en cours..."):
                    clones = fetch_clones(p['emb'], p['categorie'])
                    if not df_local.empty:
                        loc = df_local[(df_local['emb'] == p['emb']) & (df_local['code'] != code_input)]
                        for _, r in loc.iterrows():
                            clones.append({"code": r.get('code'), "nom": r.get('nom'), "marque": r.get('marque'), "ing": r.get('ingredients'), "src": "LOCAL"})

                    if clones:
                        st.divider()
                        st.markdown(f"### 💡 {len(clones)} Alternatives trouvées")
                        for c in clones[:15]:
                            if str(c['code']) != str(p['code']):
                                score = int(difflib.SequenceMatcher(None, p['ing'], c['ing']).ratio() * 100)
                                with st.container():
                                    st.markdown(f"""<div class="card"><span class="source-tag">{"Fichier Local" if c.get('src') else "Open Food Facts"}</span><h4 style="margin:0;">{c['nom']} ({c['marque']})</h4><p style="margin:5px 0;">Ressemblance recette : <b>{score}%</b></p>{get_badges(c['ing'])}</div>""", unsafe_allow_html=True)
                                    with st.expander("🔍 Comparer les compositions en détail"):
                                        c1, c2 = st.columns(2)
                                        with c1:
                                            st.caption("Recette Originale")
                                            st.write(p['ing'])
                                        with c2:
                                            st.caption("Recette du Clone (Différences en rouge)")
                                            diff_html = highlight_diff(p['ing'], c['ing'])
                                            st.markdown(f"<div style='font-size:0.9em;'>{diff_html}</div>", unsafe_allow_html=True)
            else:
                st.warning("Impossible de trouver des clones sans code usine (EMB).")
        else:
            st.error("Produit introuvable.")

with tab_add:
    st.subheader("Ajouter un produit manquant")
    with st.form("add_form", clear_on_submit=True):
        f1, f2 = st.columns(2)
        with f1:
            new_code = st.text_input("Code-barres*")
            new_nom = st.text_input("Nom du produit*")
        with f2:
            new_marque = st.text_input("Marque*")
            new_emb = st.text_input("Code Usine (EMB)*")
        new_cat = st.text_input("Catégorie (ex: Sandwichs)")
        new_ing = st.text_area("Ingrédients")
        
        if st.form_submit_button("Enregistrer le produit"):
            if new_code and new_nom:
                new_data = pd.DataFrame([{"code": str(new_code), "nom": new_nom, "marque": new_marque, "categorie": new_cat, "emb": new_emb, "ingredients": new_ing}])
                df_old = load_data()
                pd.concat([df_old, new_data]).to_csv("produits.csv", index=False)
                st.success("Produit ajouté avec succès !")
            else:
                st.error("Veuillez remplir les champs obligatoires.")
