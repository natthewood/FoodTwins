import streamlit as st
import pandas as pd
import requests
import difflib

# 1. Fonction de comparaison
def comparer_listes(texte_ref, texte_comp):
    if not texte_ref or not texte_comp:
        return "Données indisponibles."
    ref_words = str(texte_ref).lower().replace(',', '').split()
    comp_words = str(texte_comp).lower().replace(',', '').split()
    diff_html = ""
    for word in comp_words:
        if word in ref_words:
            diff_html += f"{word} "
        else:
            diff_html += f"<span style='color:red; font-weight:bold;'>{word}</span> "
    return diff_html

# 2. Interface
st.title("🔍 CloneDetector Pro")

with st.form("search"):
    barcode = st.text_input("Code-barres :", value="3021690018514")
    submit = st.form_submit_button("Lancer la recherche")

if submit:
    try:
        # On charge le fichier une seule fois au début
        df = pd.read_csv("produits.csv", dtype={'code': str})
        
        # On cherche le produit scanné
        produit = df[df['code'] == barcode.strip()]
        
        if not produit.empty:
            p = produit.iloc[0]
            st.success(f"### Produit trouvé : {p['nom']}")
            st.info(f"🏭 Usine : {p['emb']}")
            
            # Recherche des clones (même usine, nom différent)
            clones = df[(df['emb'] == p['emb']) & (df['nom'] != p['nom'])]
            
            if not clones.empty:
                st.write("### 💡 Clones potentiels trouvés :")
                for _, c in clones.iterrows():
                    with st.expander(f"✅ {c['nom']}"):
                        st.write("**Comparaison des ingrédients :**")
                        html_diff = comparer_listes(p['ingredients'], c['ingredients'])
                        st.markdown(f"<div style='padding:10px; border:1px solid #ddd;'>{html_diff}</div>", unsafe_allow_html=True)
            else:
                st.warning("Aucun clone trouvé pour cette usine.")
        else:
            st.error("Produit inconnu dans la base locale.")
            
    except Exception as e:
        st.error(f"Erreur technique : {e}")
