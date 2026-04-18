import streamlit as st
import pandas as pd
import difflib

# Configuration pour mobile (barre latérale fermée par défaut)
st.set_page_config(page_title="CloneDetector", page_icon="📱", initial_sidebar_state="collapsed")

# --- CSS PERSONNALISÉ POUR MOBILE ---
st.markdown("""
    <style>
    /* Rendre les boutons plus grands pour le pouce */
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 20px !important;
        border-radius: 15px;
    }
    /* Style des cartes produits */
    .product-card {
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 15px;
        background-color: #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

def load_local_data():
    try: return pd.read_csv("produits.csv")
    except: return None

def get_status_ui(score):
    if score >= 90: return "#28a745", "🟢", "CLONE CONFIRMÉ"
    elif score >= 60: return "#ffc107", "🟡", "MÊME USINE"
    else: return "#dc3545", "🔴", "DIFFÉRENT"

def calculer_similitude(p_cible, p_comp):
    if p_cible['code'] == p_comp['code']: return -1
    score = 0
    if str(p_cible['emb']).strip().lower() == str(p_comp['emb']).strip().lower(): score += 60
    ratio = difflib.SequenceMatcher(None, str(p_cible['ingredients']).lower(), str(p_comp['ingredients']).lower()).ratio()
    score += (ratio * 30)
    if abs(p_cible['sucre'] - p_comp['sucre']) < 1.5: score += 10
    return round(score, 1)

# --- CORPS DE L'APPLICATION ---
st.title("📱 CloneDetector")

df = load_local_data()

if df is not None:
    # MODE SCANNER (Utilise la caméra du téléphone)
    with st.expander("📷 SCANNER UN CODE-BARRES", expanded=False):
        img_file = st.camera_input("Placez le code-barres devant l'objectif")
        if img_file:
            st.warning("Analyse de l'image... (Nécessite la base API complète)")

    # MODE RECHERCHE MANUELLE
    produit_nom = st.selectbox("Sélectionnez ou cherchez un produit :", ["---"] + df['nom'].tolist())
    
    if produit_nom != "---":
        p = df[df['nom'] == produit_nom].iloc[0]
        
        # Fiche produit simplifiée
        st.markdown(f"""
            <div class='product-card'>
                <h2 style='margin:0;'>{p['nom']}</h2>
                <p>🏭 Usine : <b>{p['emb']}</b></p>
                <p>🍭 Sucre : {p['sucre']}g | {'🌱 Vegan' if p['regime']=='Vegan' else '🥩 Omnivore'}</p>
            </div>
        """, unsafe_allow_html=True)

        st.subheader("🔍 Équivalents trouvés :")
        
        df_cat = df[df['categorie'] == p['categorie']]
        clones = []
        for _, row in df_cat.iterrows():
            s = calculer_similitude(p, row)
            if s > 0: clones.append({**row, "score": s})
        
        if clones:
            for c in sorted(clones, key=lambda x: x['score'], reverse=True):
                color, icon, label = get_status_ui(c['score'])
                st.markdown(f"""
                    <div style="border-left: 8px solid {color}; padding: 10px; background: white; border-radius: 10px; box-shadow: 2px 2px 5px #ddd; margin-bottom:10px;">
                        <b style="color:{color};">{icon} {c['nom']} ({c['score']}%)</b><br>
                        <small>Fabricant identique détecté</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucun clone connu pour ce produit.")

else:
    st.error("Fichier de données manquant.")