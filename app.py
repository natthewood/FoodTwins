import streamlit as st
import requests
import pandas as pd
import difflib

st.set_page_config(page_title="CloneDetector Pro", layout="centered")

# --- FONCTION API ROBUSTE ---
def fetch_off_data(barcode):
    barcode = str(barcode).strip()
    # URL de l'API Open Food Facts
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        # On ajoute un timeout pour éviter que l'app freeze
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 1:
                p = data['product']
                return {
                    "nom": p.get('product_name_fr') or p.get('product_name') or "Inconnu",
                    "emb": p.get('manufacturing_places_re_authoritative') or p.get('emb_codes') or p.get('manufacturing_places'),
                    "ingredients": p.get('ingredients_text_fr') or p.get('ingredients_text') or "",
                    "categorie": p.get('categories_tags', [None])[0]
                }
    except Exception as e:
        st.sidebar.error(f"Erreur API : {e}")
    return None

# --- INTERFACE ---
st.title("🔍 CloneDetector Pro")

with st.form("search_form"):
    barcode_input = st.text_input("Scannez ou entrez un code-barres :", value="3021690018514")
    submit = st.form_submit_button("Lancer la recherche 🚀")

if submit:
    # 1. Tentative Web
    with st.spinner("Recherche sur Open Food Facts..."):
        result = fetch_off_data(barcode_input)
    
    # 2. Si échec Web, tentative Local
    if not result:
        st.warning("Produit non trouvé sur le Web. Vérification du fichier local...")
        try:
            df = pd.read_csv("produits.csv", dtype={'code': str})
            row = df[df['code'] == str(barcode_input).strip()]
            if not row.empty:
                result = {
                    "nom": row.iloc[0]['nom'],
                    "emb": row.iloc[0]['emb'],
                    "ingredients": row.iloc[0]['ingredients'],
                    "categorie": row.iloc[0]['categorie']
                }
        except Exception as e:
            st.error(f"Erreur lecture CSV : {e}")

    # 3. Affichage des résultats
    if result:
        st.success(f"### Produit trouvé : {result['nom']}")
        
        if result['emb']:
            st.info(f"🏭 Code Usine (EMB) : {result['emb']}")
            
            # --- LOGIQUE DE RECHERCHE DES CLONES DANS LE CSV ---
            try:
                df = pd.read_csv("produits.csv", dtype={'code': str})
                # On cherche les produits qui ont le MEME code EMB mais un NOM différent
                clones = df[(df['emb'] == result['emb']) & (df['nom'] != result['nom'])]
                
                if not clones.empty:
                    st.write("### 💡 Clones potentiels trouvés dans l'usine :")
                    for _, clone in clones.iterrows():
                        with st.expander(f"✅ {clone['nom']}"):
                            st.write(f"**Catégorie :** {clone['categorie']}")
                            # Comparaison des ingrédients
                            diff = comparer_listes(result['ingredients'], clone['ingredients'])
                            st.markdown(f"<div style='padding:10px; border:1px solid #ddd; border-radius:5px;'>{diff}</div>", unsafe_allow_html=True)
                else:
                    st.warning("Aucun clone trouvé pour cette usine dans la base locale.")
            except:
                st.error("Impossible de chercher les clones (Erreur fichier).")
        else:
            st.warning("⚠️ Ce produit n'a pas de code usine enregistré.")
    else:
        st.error("❌ Ce produit est inconnu au bataillon.")
