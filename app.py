import streamlit as st
import pandas as pd
import difflib

# 1. FONCTIONS DE CALCUL (Le "Cerveau" de l'app)
def calculer_score(ing1, ing2):
    """Calcule le % de similitude entre deux listes d'ingrédients"""
    score = difflib.SequenceMatcher(None, str(ing1).lower(), str(ing2).lower()).ratio()
    return int(score * 100)

def comparer_listes_visuel(texte_ref, texte_comp):
    """Surligne les différences et maintient une ponctuation lisible"""
    if not texte_ref or not texte_comp:
        return "Données indisponibles."
    
    # On crée des listes propres pour la comparaison (sans ponctuation)
    ref_words = str(texte_ref).lower().replace(',', '').replace('.', '').split()
    # On garde les mots originaux du clone pour l'affichage (avec virgules si présentes)
    comp_words_raw = str(texte_comp).split()
    
    diff_html = ""
    for word in comp_words_raw:
        # On nettoie le mot juste pour le test de présence
        clean_word = word.lower().replace(',', '').replace('.', '')
        
        if clean_word in ref_words:
            diff_html += f"{word} "
        else:
            # Surlignage du mot différent en gardant sa virgule éventuelle
            diff_html += f"<span style='color:red; font-weight:bold; background-color: #ffecec;'>{word}</span> "
    
    return diff_html
# 2. CONFIGURATION INTERFACE
st.set_page_config(page_title="CloneDetector Pro", page_icon="🔍")
st.title("🔬 CloneDetector Pro")

with st.form("search"):
    barcode = st.text_input("Scannez un code-barres :", value="3021690018514")
    submit = st.form_submit_button("Lancer l'analyse complète 🚀")

if submit:
    try:
        # Chargement des données
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
            
            st.info(f"🏭 **Usine détectée :** {p['emb']}")
            
            # --- RECHERCHE DES CLONES ---
            clones = df[(df['emb'] == p['emb']) & (df['nom'] != p['nom'])]
            
            if not clones.empty:
                st.write("---")
                st.subheader(f"💡 {len(clones)} Clones trouvés pour cette usine")
                
                for _, c in clones.iterrows():
                    score = calculer_score(p['ingredients'], c['ingredients'])
                    
                    # Couleur du score
                    color = "green" if score > 90 else "orange"
                    
                    with st.expander(f"✅ {c['nom']} — Correspondance : {score}%"):
                        st.markdown(f"**Fiabilité de la recette :** <span style='color:{color}; font-weight:bold;'>{score}%</span>", unsafe_allow_html=True)
                        
                        # Comparaison visuelle
                        st.write("**Analyse des différences :**")
                        diff_html = comparer_listes_visuel(p['ingredients'], c['ingredients'])
                        st.markdown(f"<div style='padding:10px; border:1px solid #ddd; border-radius:5px; background-color:white;'>{diff_html}</div>", unsafe_allow_html=True)
                        
                        # Infos secondaires
                        st.write(f"📊 **Sucre :** {c['sucre']}g (Différence : {round(c['sucre'] - p['sucre'], 1)}g)")
            else:
                st.warning("Aucun clone trouvé dans la base pour cette usine.")
                
        else:
            st.error("Désolé, ce code-barres n'est pas encore dans notre base locale.")
            
    except Exception as e:
        st.error(f"Erreur lors de l'analyse : {e}")
