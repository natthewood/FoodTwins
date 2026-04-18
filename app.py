import streamlit as st
import requests
import difflib

# 1. DEFINITION DES FONCTIONS (Toujours en haut du fichier)

def comparer_listes(texte_ref, texte_comp):
    """Compare deux listes d'ingrédients et surligne les différences"""
    if not texte_ref or not texte_comp:
        return "Données indisponibles pour la comparaison."
    
    # Nettoyage simple pour la comparaison
    ref_words = str(texte_ref).lower().replace(',', '').replace('.', '').split()
    comp_words = str(texte_comp).lower().replace(',', '').replace('.', '').split()
    
    diff_html = ""
    for word in comp_words:
        if word in ref_words:
            diff_html += f"{word} "
        else:
            # Surlignage des ingrédients différents
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

# 2. INTERFACE UTILISATEUR

st.title("🔬 CloneDetector Pro")

# On crée un formulaire pour regrouper la saisie et le bouton
with st.form("search_form"):
    barcode = st.text_input("Scannez ou entrez un code-barres :", placeholder="Ex: 3021690018514")
    submit_button = st.form_submit_button("Lancer la recherche 🔍")

# La recherche ne se lance que si on clique sur le bouton OU si on fait "Entrée"
if submit_button and barcode:
    data = fetch_off_data(barcode)
    if data:
        # ... (le reste de ton code actuel pour afficher les résultats)
