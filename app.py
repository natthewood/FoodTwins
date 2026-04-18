import streamlit as st
import pandas as pd
import difflib

# 1. CERVEAU DE L'APP
def calculer_score(ing1, ing2):
    score = difflib.SequenceMatcher(None, str(ing1).lower(), str(ing2).lower()).ratio()
    return int(score * 100)

def comparer_listes_visuel(texte_ref, texte_comp):
    if not texte_ref or not texte_comp:
        return "Données indisponibles."
    ref_words = str(texte_ref).lower().replace(',', '').replace('.', '').split()
    comp_words_raw = str(texte_comp).split()
    diff_html = ""
    for word in comp_words_raw:
        clean_word = word.lower().replace(',', '').replace('.', '')
        if clean_word in ref_words:
            diff_html += f"{word} "
        else:
            diff_html += f"<span style='color:red; font-weight:bold; background-color: #ffecec;'>{word}</span> "
    return diff_html

# 2. CONFIGURATION ET INTERFACE
st.set_page_config(page_title="CloneDetector Pro", layout="centered")
st.title("🔬 CloneDetector Pro")

with st.form("search"):
    barcode = st.text_input("Scannez un code-barres :", value="3021690018514")
    submit = st.form_submit_button("Lancer l'analyse 🚀")

if submit:
    try:
        df = pd.read_csv("produits.csv", dtype={'code': str})
        produit_scanne = df[df['code'] == barcode.strip()]
        
        if not produit_scanne.empty:
            p = produit_scanne.iloc[0]
            
            # --- AFFICHAGE PRODUIT PRINCIPAL ---
            st.success(f"### {p['nom']}")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Sucre (100g)", f"{p['sucre']}g")
            col2.metric("Régime", p['regime'])
            col3.metric("Porc", "Oui 🐷" if p['porc'] == "Oui" else "Non ❌")
            
            # Affichage de la recette du produit recherché
            with st.expander("📜 Voir la recette complète"):
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px;'>{p['ingredients']}</div>", unsafe_allow_html=True)
            
            st.info(f"🏭 **Usine détectée :** {p['emb']}")
            
            # --- RECHERCHE ET AFFICHAGE ---
            clones = df[(df['emb'] == p['emb']) & (df['nom'] != p['nom'])]
            alternatives = df[(df['categorie'] == p['categorie']) & (df['emb'] != p['emb']) & (df['nom'] != p['nom'])]

            # Section Clones (Même Usine)
            if not clones.empty:
                st.write("---")
                st.subheader(f"🏭 {len(clones)} Clones trouvés (Même usine)")
                for _, c in clones.iterrows():
                    score = calculer_score(p['ingredients'], c['ingredients'])
                    with st.expander(f"✅ {c['nom']} — Correspondance : {score}%"):
                        st.write(f"**Analyse :** Même provenance, similitude de recette à {score}%")
                        diff_html = comparer_listes_visuel(p['ingredients'], c['ingredients'])
                        st.markdown(f"<div style='padding:10px; border:1px solid #ddd; border-radius:5px;'>{diff_html}</div>", unsafe_allow_html=True)

            # Section Alternatives (Même Catégorie)
            if not alternatives.empty:
                st.write("---")
                st.subheader(f"🛒 {len(alternatives)} Alternatives (Catégorie {p['categorie']})")
                for _, a in alternatives.iterrows():
                    score = calculer_score(p['ingredients'], a['ingredients'])
                    with st.expander(f"🔍 {a['nom']} — Similitude : {score}%"):
                        st.write(f"**Note :** Usine différente ({a['emb']})")
                        diff_html = comparer_listes_visuel(p['ingredients'], a['ingredients'])
                        st.markdown(f"<div style='padding:10px; border:1px solid #ddd; border-radius:5px;'>{diff_html}</div>", unsafe_allow_html=True)
        else:
            st.error("Ce produit n'est pas dans notre base locale.")
    except Exception as e:
        st.error(f"Erreur technique : {e}")
