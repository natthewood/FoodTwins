import streamlit as st
import pandas as pd
import difflib
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="FoodTwins", page_icon="🔬", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .badge { padding: 4px 10px; border-radius: 10px; font-weight: bold; margin-right: 5px; display: inline-block; margin-bottom: 5px; }
    .nutri-A { background-color: #008b4c; color: white; }
    .nutri-B { background-color: #80c141; color: white; }
    .nutri-C { background-color: #fec917; color: black; }
    .nutri-D { background-color: #ee8100; color: white; }
    .nutri-E { background-color: #e63e11; color: white; }
    .nova { background-color: #333; color: white; border-radius: 5px; padding: 2px 8px; }
    .vegan { background-color: #2ecc71; color: white; }
    .has-pork { background-color: #e74c3c; color: white; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        # On charge ton fichier enrichi
        df = pd.read_csv("produits.csv", dtype=str).fillna("")
        df['code'] = df['code'].str.strip()
        for col in ['sucre', 'sel', 'energie_100g']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return pd.DataFrame()

def get_badges_html(ingredients):
    badges = ""
    ing_low = str(ingredients).lower()
    if "porc" in ing_low or "lard" in ing_low:
        badges += '<span class="badge has-pork">🐷 Porc</span>'
    if not any(x in ing_low for x in ["viande", "poisson", "poulet", "boeuf", "jambon"]):
        badges += '<span class="badge vegan">🍃 Végétarien</span>'
    return badges

# --- CHARGEMENT ---
df = load_data()

st.title("🔬 FoodTwins")
st.markdown("### 🔎 Recherche de jumeaux industriels par Nom")

barcode = st.text_input("Scannez ou saisissez un code-barres (ex: 3998754976027) :").strip()

if barcode:
    res = df[df['code'] == barcode]
    
    if not res.empty:
        p = res.iloc[0]
        
        # --- AFFICHAGE PRODUIT SCANNE ---
        col1, col2 = st.columns([1, 2])
        with col1:
            if p['image_url']: st.image(p['image_url'], use_container_width=True)
            else: st.info("📷 Image non disponible")

        with col2:
            st.write(f"**{p['marque']}**")
            st.header(p['nom'])
            ns = str(p['nutriscore']).upper()
            st.markdown(f"""
                <span class="badge nutri-{ns}">Nutri-Score {ns}</span>
                <span class="nova">NOVA {p['nova']}</span>
                {get_badges_html(p['ingredients'])}
            """, unsafe_allow_html=True)
            st.info(f"🏭 **Usine :** {p['emb']} ({p['usine_lieu']})")

        # --- LOGIQUE DE CLONES PAR NOM ---
        # On prend le premier mot significatif du nom (plus de 3 lettres)
        mots = [m for m in p['nom'].split() if len(m) > 3]
        mot_cle = mots[0] if mots else p['nom']

        # Filtre : Même usine ET le nom contient le mot clé (ex: "Rillettes")
        clones = df[
            (df['emb'] == p['emb']) & 
            (df['nom'].str.contains(mot_cle, case=False, na=False)) & 
            (df['code'] != barcode)
        ]
        
        if not clones.empty:
            st.markdown("---")
            st.subheader(f"💡 {len(clones)} Alternatives détectées pour '{mot_cle}'")
            
            for _, c in clones.head(10).iterrows():
                # Calcul ressemblance sur les ingrédients
                score_text = difflib.SequenceMatcher(None, str(p['ingredients']), str(c['ingredients'])).ratio()
                pct = int(score_text * 100)
                
                with st.expander(f"✅ {c['marque']} - {c['nom']} ({pct}% de ressemblance)"):
                    ca, cb = st.columns([1, 2])
                    with ca:
                        if c['image_url']: st.image(c['image_url'], width=120)
                        st.markdown(f'<span class="badge nutri-{str(c["nutriscore"]).upper()}">Score {str(c["nutriscore"]).upper()}</span>', unsafe_allow_html=True)
                    with cb:
                        st.write(f"**Ingrédients :** {c['ingredients']}")
                        diff_sucre = float(c['sucre']) - float(p['sucre'])
                        st.write(f"**Sucre :** {c['sucre']}g ({'+' if diff_sucre > 0 else ''}{round(diff_sucre,1)}g)")
    else:
        st.error("Produit inconnu dans la base locale.")
