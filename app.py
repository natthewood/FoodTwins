import difflib

def comparer_listes(texte_ref, texte_comp):
    """Compare deux listes d'ingrédients et surligne les différences"""
    if not texte_ref or not texte_comp:
        return "Données indisponibles pour la comparaison."
    
    ref_words = texte_ref.lower().replace(',', '').split()
    comp_words = texte_comp.lower().replace(',', '').split()
    
    diff_html = ""
    for word in comp_words:
        # Si le mot est dans le produit de marque, on l'affiche normalement
        if word in ref_words:
            diff_html += f"{word} "
        # Si c'est un ingrédient différent, on le met en rouge
        else:
            diff_html += f"<span style='color:red; font-weight:bold;'>{word}</span> "
    
    return diff_html

# --- DANS TA BOUCLE DE CLONES DANS STREAMLIT ---
# (Remplace la partie "Voir détails" par ceci)
with st.expander("🔬 Comparaison de la recette"):
    st.write("**Ingrédients du clone :**")
    diff_result = comparer_listes(data['ingredients'], c.get('ingredients_text_fr', ''))
    st.markdown(f"<div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>{diff_result}</div>", unsafe_allow_html=True)
    
    st.caption("Les mots en rouge sont présents dans le clone mais pas dans l'original.")
