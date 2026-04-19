import streamlit as st
import pandas as pd
import requests

# --- CHARGEMENT ---
@st.cache_data
def load_csv():
    try:
        # On lit le fichier et on force le nettoyage immédiat
        df = pd.read_csv("produits.csv", sep=',').fillna("")
        # On convertit la colonne code en texte brut, sans virgules ni .0
        df['code'] = df['code'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        return df
    except Exception as e:
        return pd.DataFrame()

df_local = load_csv()

st.title("🔬 CloneDetector : Test de Force")

# Barre de recherche
barcode_input = st.text_input("Entrez le code (ex: 3000000000001) :").strip()

if barcode_input:
    # On affiche ce que l'app "voit" pour aider à comprendre
    st.write(f"🔍 Recherche de : `{barcode_input}`")
    
    # 1. Tentative de correspondance exacte
    match = df_local[df_local['code'] == barcode_input]
    
    # 2. Si échec, tentative de correspondance "souple" (au cas où le CSV a des .0)
    if match.empty:
        match = df_local[df_local['code'].str.contains(barcode_input, na=False)]

    if not match.empty:
        p = match.iloc[0]
        st.success(f"✅ TROUVÉ : {p['nom']}")
        st.info(f"Usine : {p['emb']}")
        
        # Affichage des clones
        clones = df_local[(df_local['emb'] == p['emb']) & (df_local['code'] != p['code'])]
        if not clones.empty:
            st.subheader(f"💡 {len(clones)} Clones trouvés")
            st.table(clones[['nom', 'code']])
    else:
        st.error("❌ Le code n'est toujours pas reconnu dans le fichier CSV.")
        with st.expander("Voir les 5 premiers codes réellement présents dans votre fichier"):
            st.write(df_local['code'].head(5).tolist())
