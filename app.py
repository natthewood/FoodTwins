import streamlit as st
import pandas as pd
import requests
import difflib
import re
import os
from PIL import Image

# --- CONFIGURATION & DESIGN ---
# Mise à jour du titre et de l'icône de l'onglet du navigateur
st.set_page_config(page_title="TwinFood : Débusquez les clones !", page_icon="👥", layout="wide")

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

# --- EN-TÊTE AVEC LOGO ET NOM ---
# Assure-toi d'avoir un fichier logo.png dans le même dossier
col_logo, col_titre = st.columns([1, 5])

with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
    else:
        # Affiche une icône de substitution sympa au lieu d'un message d'erreur
        st.markdown("## 👥")
with col_titre:
    st.title("TwinFood : Débusquez les clones !")
    st.markdown("##### Identifiez les produits de grandes marques et leurs alternatives de distributeurs.")


# --- FONCTIONS DE GESTION DU CSV ---
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

# --- RECHERCHE API OPEN FOOD FACTS ---
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
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&tagtype_0=emb_codes&tag_contains_0=contains&tag_0={emb_code}&json=true&page_size=50"
    clones = []
    try:
        res = requests.get(url, timeout=5).json()
        for p in res.get('products', []):
            p_cats = p.get('categories_tags', [])
            # On force le même type de produit pour le clone
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
def fetch_clones_off(emb_code, category_filter):
    # On ajoute un filtre de catégorie directement dans l'URL de recherche Open Food Facts
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&tagtype_0=emb_codes&tag_contains_0=contains&tag_0={emb_code}&tagtype_1=categories&tag_contains_1=contains&tag_1={category_filter}&json=true&page_size=50"
    # ... reste du code
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
    if not any(x in ing_low for x in ["viande", "poisson", "poulet", "boeuf"]): badges += '<span class="badge vegan">🍃 Végétarien</span>'
    if "gluten" not in ing_low and "blé" not in ing_low and "orge" not in ing_low: badges += '<span class="badge gluten-free">🌾 Sans Gluten</span>'
    return badges

# --- INTERFACE PRINCIPALE ---
st.markdown("---") # Ligne de séparation sous l'en-tête
tab_search, tab_add = st.tabs(["🔍 Rechercher & Comparer", "📸 Ajouter au CSV Local"])

# --- ONGLET 1 : RECHERCHE ---
with tab_search:
    with st.form("search"):
        c1, c2 = st.columns([4,1])
        code_input = c1.text_input("Scannez un code-barres :", placeholder="Ex: 3033490593030")
        submit = c2.form_submit_button("Chercher 🚀")

    if submit and code_input:
        df_local = load_local_data()
        p = fetch_product_off(code_input) # Priorité Web
        
        if not p and not df_local.empty: # Secours Local
            match = df_local[df_local['code'] == code_input]
            if not match.empty:
                row = match.iloc[0]
                p = {"nom": row['nom'], "marque": row['marque'], "categorie": row['categorie'], 
                     "emb": row['emb'], "ingredients": row['ingredients'], "sucre": row['sucre'], "source": "📁 Base Locale"}

        if p:
            col_img, col_txt = st.columns([1,3])
            with col_img: 
                if p.get('image'): st.image(p['image'], use_column_width=True)
                else: st.write("📷 Pas d'image")
            with col_txt:
                st.markdown(f"## {p['nom']} ({p['marque']})")
                st.markdown(f"<span class='badge source-web'>{p['source']}</span> {get_badges_html(p['ingredients'])}", unsafe_allow_html=True)
                
                c_sucre, c_emb = st.columns(2)
                c_sucre.metric("Sucre (100g)", f"{p.get('sucre', 'N/A')}g")
                
                emb_code = str(p.get('emb', '')).strip()
                if emb_code:
                    c_emb.success(f"🏭 Code Usine détecté : **{emb_code}**")
                else:
                    c_emb.error("❌ Pas de code EMB détecté.")
                
                st.write(f"**Type de produit :** {p.get('categorie', 'Non classé')}")
                st.write(f"**Ingrédients :** {p.get('ingredients', 'Non renseigné')}")

            if emb_code:
                with st.spinner("Recherche des clones sur le Web et en local..."):
                    clones_web = fetch_clones_off(emb_code, p['categorie'])
                    clones_local = []
                    if not df_local.empty:
                        ml = df_local[(df_local['emb'] == emb_code) & (df_local['code'] != code_input)]
                        for _, r in ml.iterrows():
                            clones_local.append({"nom": r['nom'], "marque": r['marque'], "ingredients": r['ingredients'], "sucre": r['sucre'], "source": "📁 Local"})
                    
                    all_clones = clones_web + clones_local
                    if all_clones:
                        st.subheader(f"💡 {len(all_clones)} Clones trouvés")
                        # Remplacer la boucle d'affichage des clones par ceci :
                        for c in all_clones[:10]:
    with st.container():
        # Création d'une "carte" visuelle
        st.markdown(f"""
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
            <h4 style="margin:0;">{c['nom']}</h4>
            <p style="color: gray; margin:0;">Marque : {c['marque']} | Source : {c['source']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Comparaison des ingrédients à l'intérieur de la carte
        score = int(difflib.SequenceMatcher(None, str(p['ingredients']), str(c['ingredients'])).ratio() * 100)
        with st.expander(f"Comparer la recette ({score}% identique)"):
            diff_html = highlight_differences(p['ingredients'], c['ingredients'])
            st.markdown(f"**Différences :** {diff_html}", unsafe_allow_html=True)
                        for c in all_clones[:15]:
                            score = int(difflib.SequenceMatcher(None, str(p['ingredients']), str(c['ingredients'])).ratio() * 100)
                            color_icon = "🟢" if score > 85 else "🟠" if score > 65 else "🔴"
                            
                            with st.expander(f"{color_icon} {c['nom']} ({c['marque']}) — Ressemblance : {score}%"):
                                st.write(f"Source : {c['source']}")
                                diff_html = highlight_differences(p['ingredients'], c['ingredients'])
                                st.markdown(f"**Ingrédients :** {diff_html}", unsafe_allow_html=True)
                                st.caption("*(Les ingrédients en rouge vif sont absents de votre produit de référence)*")
                    else: st.warning("Pas de clone trouvé pour cette usine dans cette catégorie.")
            else: st.warning("Recherche de clones impossible sans code EMB.")
        else: st.error("❌ Produit inconnu sur le Web et en local.")

# --- ONGLET 2 : AJOUTER ---
with tab_add:
    st.subheader("📸 Ajouter un produit manquant à votre CSV local")
    col1, col2 = st.columns(2)
    with col1: cam_code = st.camera_input("Photo du Code")
    with col2: cam_ing = st.camera_input("Photo Ingrédients")

    with st.form("add_form", clear_on_submit=True):
        f_code = st.text_input("Code-barres")
        f_nom = st.text_input("Nom")
        f_marque = st.text_input("Marque")
        f_cat = st.text_input("Catégorie (ex: rillettes, yaourt)")
        f_emb = st.text_input("Code Usine (EMB)")
        f_ing = st.text_area("Ingrédients")
        f_sucre = st.text_input("Sucre (g/100g)")
        
        if st.form_submit_button("💾 Sauvegarder dans le CSV local"):
            if f_code and f_emb:
                save_to_csv({"code": f_code, "nom": f_nom, "marque": f_marque, "categorie": f_cat, "emb": f_emb, "ingredients": f_ing, "sucre": f_sucre})
                st.success(f"✅ Produit {f_nom} enregistré avec succès !")
                st.balloons()
            else: st.error("⚠️ Code-barres et Code Usine sont obligatoires !")

