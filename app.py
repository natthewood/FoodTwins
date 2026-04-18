import streamlit as st
import requests
import difflib

# 1. FONCTIONS TECHNIQUES
def comparer_listes(texte_ref, texte_comp):
    if not texte_ref or not texte_comp:
        return "Données indisponibles."
    ref_words = str(texte_ref).lower().replace(',', '').replace('.', '').split()
    comp_words = str(texte_comp).lower().replace(',', '').replace('.', '').split()
    diff_html = ""
    for word in comp_words:
        if word in ref_words:
            diff_html += f"{word} "
        else:
            diff_html += f"<span style='color:red; font-weight:bold; background-color: #ffecec;'>{word}</span> "
    return diff_html

def fetch_off_data(barcode):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get('status') == 1:
            p = res['product']
            return {
                "nom": p.get('product_name', 'Inconnu'),
                "emb": p.get('manufacturing_places_re_authoritative', p.get('emb_codes', '')),
                "ingredients": p.get('ingredients_text_fr', p.get('ingredients_text', '')),
                "categorie": p.get('categories_tags', [None])[0]
            }
    except: return None
    return None

def find_clones_api(emb_code, category_tag):
    if not emb_code: return []
    clean_emb = str(emb_code).split(',')[0].strip()
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&manufacturing_places_tags={clean_emb}&categories_tags={category_tag}&json=true"
    try:
        res = requests.get(url, timeout=5).json()
        return res.get('products', [])
    except: return []

# 2. INTERFACE ET FORMULAIRE
st.title("🔬 CloneDetector Pro")

with st.form("search_form"):
    barcode = st.text_input("Scannez ou entrez un code-barres :", placeholder="Ex: 3021690018514")
    submit_button = st.form_submit_button("Lancer la recherche 🔍")

if submit_button and barcode:
    data = fetch_off_data(barcode)
    if data:
        st.subheader(f"Produit : {data['nom']}")
        
        if data['emb']:
            st.info(f"🏭 Usine : {data['emb']}")
            clones = find_clones_api(data['emb'], data['categorie'])
            
            autres_produits = [c for c in clones if c.get('product_name', '').lower() != data['nom'].lower()]
            
            if autres_produits:
                st.write("### 💡 Équivalents trouvés :")
                for c in autres_produits:
                    nom_clone = c.get('product_name', 'Marque Distributeur')
                    st.write(f"✅ **{nom_clone}**")
                    with st.expander(f"🔬 Comparer la recette avec {nom_clone}"):
                        ing_clone = c.get('ingredients_text_fr', c.get('ingredients_text', ''))
                        diff_result = comparer_listes(data['ingredients'], ing_clone)
                        st.markdown(f"<div style='padding:10px; border:1px solid #ddd; border-radius:5px;'>{diff_result}</div>", unsafe_allow_html=True)
            else:
                st.warning("Aucun clone répertorié pour cette usine.")
        else:
            st.error("Code usine (EMB) absent sur Open Food Facts pour ce produit.")
    else:
        st.error("Produit non trouvé. Vérifiez le code-barres.")
