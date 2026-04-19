import streamlit as st
import pandas as pd
import requests
import difflib

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="CloneDetector Global", page_icon="🔍", layout="wide")

# --- FONCTION DE RECHERCHE WEB (MULTI-API) ---
def fetch_off_data(barcode):
    clean_barcode = str(barcode).strip()
    
    # On teste plusieurs routes au cas où l'une d'elles renvoie une 404
    urls = [
        f"https://world.openfoodfacts.org/api/v2/product/{clean_barcode}.json",
        f"https://world.openfoodfacts.org/api/v0/product/{clean_barcode}.json",
        f"https://fr.openfoodfacts.org/api/v0/product/{clean_barcode}.json"
    ]
    
    headers = {'User-Agent': 'CloneDetector - GlobalApp - Version 1.0'}
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            
            # Diagnostic en temps réel dans la barre latérale
            with st.sidebar:
                st.write(f"Test URL: {url.split('/')[4]}") # Affiche v2 ou v0
                st.write(f"Réponse: {res.status_code}")

            if res.status_code == 200:
                data = res.json()
                if data.get('status') == 1 or data.get('status_verbose') == "product found":
                    p = data['product']
                    
                    # Extraction du code usine (EMB)
                    emb = p.get('emb_codes', '').split(',')[0] if p.get('emb_codes') else p.get('manufacturing_places', '')
                    
                    return {
                        "nom": p.get('product_name_fr') or p.get('product_name') or "Inconnu",
                        "emb": str(emb).strip(),
                        "ingredients": p.get('ingredients_text_fr') or p.get('ingredients_text') or "Non renseignés",
                        "sucre": p.get('nutriments', {}).get('sugars_100g', 0),
                        "image": p.get('image_front_url'),
                        "source": "Web (Open Food Facts)"
                    }
        except:
            continue
    return None

# --- FONCTIONS DE COMPARAISON ---
def calculer_score(ing1, ing2):
    return int(difflib.SequenceMatcher(None, str(ing1).lower(), str(ing2).lower()).ratio() * 100)

def comparer_visuel(ref, comp):
    ref_words = str(ref).lower().replace(',', '').replace('.', '').split()
    comp_raw = str(comp).split()
    res = ""
    for w in comp_raw:
        clean = w.lower().replace(',', '').replace('.', '')
        if clean in ref_words:
            res += f"{w} "
        else:
            res += f"<span style='color:red; font-weight:bold; background-color: #ffecec;'>{w}</span> "
    return res

# --- INTERFACE PRINCIPALE ---
st.title("🔬 CloneDetector Global")
st.markdown("Recherche hybride : Base mondiale + Vos clones locaux")

# Sidebar pour le diagnostic
with st.sidebar:
    st.header("🛠 Diagnostic API")
    st.info("Les résultats s'afficher
