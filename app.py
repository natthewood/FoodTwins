import streamlit as st
import pandas as pd
import requests
import difflib
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="CloneDetector Ultra", page_icon="🔬", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .badge { padding: 4px 10px; border-radius: 10px; font-weight: bold; margin-right: 5px; display: inline-block; margin-bottom: 5px; }
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
        df['sucre'] = pd.to_numeric(df['sucre'], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def detect_additives(text):
    # Extrait les codes E-numéros (ex: E250, E450)
    return set(re.findall(r'E\d{3,4}', text.upper()))

def get_badges_html(ingredients):
    badges = ""
    ing_low = ingredients.lower()
    
    # Badge Porc
    if "porc" not in ing_low and "lard" not in ing_low:
        badges += '<span class="badge no-pork">🚫 🐷 Sans Porc</span>'
    else:
        badges += '<span class="badge has-pork">🐷 Contient du Porc</span>'
    
    # Badge Végétarien
    if not any(x in ing_low for x in ["viande", "poisson", "poulet", "boeuf", "jambon"]):
        badges += '<span class="badge vegan">🍃 Végétarien</span>'
    
    # Badge Additifs
    additifs = detect_additives(ingredients)
    if additifs:
        badges += f'<span class="badge additive">🧪 {len(additifs)} Additifs</span>'
    
    return badges

# --- CHARGEMENT ---
df = load_data()

st.title("🔬 CloneDetector Ultra")
st.markdown("### Analyse croisée : Usines, Additifs et Catégories")

barcode = st.text_input("Scannez ou saisissez un code-barres :").strip()

if barcode:
    # Recherche du produit principal
    res = df[df['code'] == barcode]
    
    if not res.empty:
        p = res.iloc[0]
        st.markdown(f"## {p['nom']}")
        st.markdown(get_badges_html(p['ingredients']), unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Sucre (100g)", f"{p['sucre']}g")
        c2.info(f"🏭 Usine : {p['emb']}")
        add_p = detect_additives(p['ingredients'])
        c3.warning(f"🧪 Conservateurs : {', '.join(add_p) if add_p else 'Aucun'}")

        # --- LOGIQUE DE CLONES FILTRÉE ---
        # 1. Même usine (EMB)
        # 2. MÊME CATÉGORIE (pour éviter de comparer yaourt et pizza)
        # 3. Code différent
        clones = df[
            (df['emb'] == p['emb']) & 
            (df['categorie'] == p['categorie']) & 
            (df['code'] != barcode)
        ]
        
        if not clones.empty:
            st.markdown("---")
            st.subheader(f"💡 {len(clones)} Alternatives de même type trouvées")
            
            for _, c in clones.head(10).iterrows():
                # Calcul de ressemblance textuelle
                score_text = difflib.SequenceMatcher(None, p['ingredients'], c['ingredients']).ratio()
                
                # Analyse des additifs
                add_c = detect_additives(c['ingredients'])
                common_additives = add_p.intersection(add_c)
                
                # Bonus de score si les additifs sont identiques
                score_final = score_text
                if add_p == add_c: score_final += 0.1
                
                pct = min(int(score_final * 100), 100)
                
                with st.expander(f"✅ {c['nom']} — Ressemblance : {pct}%"):
                    col_a, col_b = st.columns(2)
                    diff_sucre = float(c['sucre']) - float(p['sucre'])
                    col_a.write(f"**Écart Sucre :** {round(diff_sucre,1)}g")
                    col_b.markdown(get_badges_html(c['ingredients']), unsafe_allow_html=True)
                    
                    st.write(f"**Liste des ingrédients :** {c['ingredients']}")
                    if add_c:
                        st.write(f"**Additifs détectés :** {', '.join(add_c)}")
    else:
        st.error("Produit non répertorié dans la base locale.")
