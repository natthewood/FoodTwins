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
    # 1. On tente le Web (OFF)
    data = fetch_off_data(barcode)
    
    # 2. Si le Web échoue, on regarde dans ton CSV local
    if not data:
        try:
            df = pd.read_csv("produits.csv")
            # On cherche le code dans le CSV (on convertit en string pour être sûr)
            row = df[df['code'].astype(str) == str(barcode)]
            if not row.empty:
                data = {
                    "nom": row.iloc[0]['nom'],
                    "emb": row.iloc[0]['emb'],
                    "ingredients": row.iloc[0]['ingredients'],
                    "categorie": row.iloc[0]['categorie']
                }
        except:
            pass

    # 3. Affichage final
    if data:
        st.subheader(f"Produit : {data['nom']}")
        # ... (le reste de ton code pour les clones)
    else:
        st.error("Ce produit est inconnu au bataillon (Web et local).")
