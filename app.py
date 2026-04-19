import streamlit as st
import pandas as pd
import requests
import difflib
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="CloneDetector Ultra", page_icon="🔬", layout="wide")

# --- STYLE CSS POUR LES BADGES ---
st.markdown("""
    <style>
    .badge { padding: 4px 10px; border-radius: 10px; font-weight: bold; margin-right: 5px; }
    .vegan { background-color: #2ecc71; color: white; }
    .no-pork { background-color: #f1c40f; color: black; }
    .has-pork { background-color: #e74c3c; color: white; }
    .additive { background-color: #9b59b6; color: white; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        df = pd.read_csv("produits.csv", dtype=str).fillna("")
        df['code'] = df['code'].str.strip()
        # Conversion du sucre en nombre pour les calculs
        df['sucre'] = pd.to_numeric(df['sucre'], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def detect_additives(text):
    # Cherche les codes type E250, E202...
    return re.findall(r'E\d{3,4}', text.upper())

def get_badges(ingredients):
    badges = ""
    ing_low = ingredients.lower()
    if "porc" not in ing_low and "lard" not in ing_low:
        badges += '<span class="badge no-pork">🚫 🐷 Sans Porc</span>'
    else:
        badges += '<span class="badge has-pork">🐷 Contient du Porc</span>'
    
    if "viande" not in ing_low and "poisson" not in ing_low and "poulet" not in ing_low:
        badges += '<span class="badge vegan">🍃 Végétarien</span>'
    
    additifs = detect_additives(ingredients)
    if additifs:
        badges += f'<span class="badge additive">🧪 {len(additifs)} Additifs</span>'
    
    return badges

# --- CHARGEMENT ---
df = load_data()

# --- SIDEBAR (FILTRES) ---
st.sidebar.header("🔍 Filtres de recherche")
cat_list = ["Tous"] + sorted(df['categorie'].unique().tolist())
selected_cat = st.sidebar.selectbox("Filtrer par type de produit", cat_list)

# --- INTERFACE ---
st.title("🔬 CloneDetector Ultra")
st.markdown("### L'intelligence artificielle au service de votre panier")

barcode = st.text_input("Scannez ou saisissez un code-barres (ex: 3200849007378) :").strip()

if barcode:
    # Application du filtre catégorie si actif
    if selected_cat != "Tous":
        temp_df = df[df['categorie'] == selected_cat]
    else:
        temp_df = df

    res = temp_df[temp_df['code'] == barcode]
    
    if not res.empty:
        p = res.iloc[0]
        
        # Affichage Produit Principal
        st.markdown(f"## {p['nom']}")
        st.markdown(get_badges(p['ingredients']), unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Sucre (100g)", f"{p['sucre']}g")
        c2.info(f"🏭 Usine : {p['emb']}")
        add_p = detect_additives(p['ingredients'])
        c3.warning(f"🧪 Additifs : {', '.join(add_p) if add_p else 'Aucun'}")

        # RECHERCHE DE CLONES
        clones = df[(df['emb'] == p['emb']) & (df['code'] != barcode)]
        
        if not clones.empty:
            st.markdown("---")
            st.subheader(f"💡 {len(clones)} Alternatives trouvées (Même usine)")
            
            for _, c in clones.head(10).iterrows():
                # Calcul de ressemblance
                score_base = difflib.SequenceMatcher(None, p['ingredients'], c['ingredients']).ratio()
                
                # Bonus/Malus si additifs identiques
                add_c = detect_additives(c['ingredients'])
                if add_p == add_c: score_base += 0.05
                
                final_score = min(int(score_base * 100), 100)
                
                with st.expander(f"✅ {c['nom']} — Ressemblance : {final_score}%"):
                    col_a, col_b = st.columns(2)
                    diff_sucre = float(c['sucre']) - float(p['sucre'])
                    col_a.write(f"**Sucre :** {c['sucre']}g ({'+' if diff_sucre > 0 else ''}{round(diff_sucre,1)}g)")
                    col_b.markdown(get_badges(c['ingredients']), unsafe_allow_html=True)
                    st.write(f"**Ingrédients :** {c['ingredients']}")
    else:
        st.error("Produit introuvable. Vérifiez que le filtre 'Catégorie' correspond au produit.")
