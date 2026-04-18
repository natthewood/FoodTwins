import streamlit as st
import pandas as pd
import requests
import difflib
from streamlit_barcode_scanner import st_barcode_scanner

# 1. FONCTIONS DE RECHERCHE (WEB & LOCAL)
def fetch_off_data(barcode):
    """Cherche le produit sur la base mondiale Open Food Facts"""
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    headers = {'User-Agent': 'CloneDetector - GlobalVersion - 1.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 1:
                p = data['product']
                # Extraction du code EMB (usine)
                emb = p.get('emb_codes', '').split(',')[0] if p.get('emb_codes') else p.get('manufacturing_places', '')
                return {
                    "nom": p.get('product_name_fr') or p.get('product_name') or "Inconnu",
                    "emb": emb.strip(),
                    "ingredients": p.get('ingredients_text_fr') or p.get('ingredients_text') or "Non renseignés",
                    "categorie": p.get('categories_tags', [None])[0].replace('en:', '').replace('fr:', '') if p.get('categories_tags') else "Divers",
                    "sucre": p.get('nutriments', {}).get('sugars_100g', 0)
                }
    except:
        return None
    return None

def calculer_score(ing1, ing2):
    """Calcule le % de similitude entre deux recettes"""
    return int(difflib.SequenceMatcher(None, str(ing1).lower(), str(ing2).lower()).ratio() * 100)

def comparer_visuel(ref, comp):
    """Surligne les ingrédients différents en rouge"""
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

# 2. CONFIGURATION DE L'INTERFACE
st.set_page_config(page_title="CloneDetector Global", page_icon="🔍", layout="wide")

st.title("🔬 CloneDetector Global")
st.markdown("---")

# --- SECTION SCANNER ---
st.subheader("📸 Scannez un produit")
# Le scanner s'affiche ici (uniquement via HTTPS)
barcode = st_barcode_scanner()

# Option de secours : Saisie manuelle
with st.sidebar:
    st.header("Options")
    manual_barcode = st.text_input("Saisie manuelle du code-barres :")
    if manual_barcode:
        barcode = manual_barcode

# 3. LOGIQUE D'ANALYSE
if barcode:
    st.write(f"🔎 Analyse du code : **{barcode}**")
    
    # ÉTAPE A : Recherche Web
    with st.spinner("Recherche mondiale en cours..."):
        data = fetch_off_data(barcode)
    
    # ÉTAPE B : Si non trouvé sur le Web, on cherche dans votre CSV
    if not data:
        try:
            df_local = pd.read_csv("produits.csv", dtype={'code': str})
            local_p = df_local[df_local['code'] == str(barcode).strip()]
            if not local_p.empty:
                lp = local_p.iloc[0]
                data = {
                    "nom": lp['nom'], 
                    "emb": lp['emb'], 
                    "ingredients": lp['ingredients'], 
                    "categorie": lp.get('categorie', 'Divers'), 
                    "sucre": lp.get('sucre', 0)
                }
        except:
            pass

    # ÉTAPE C : Affichage des résultats
    if data:
        st.success(f"## {data['nom']}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.metric("Sucre (100g)", f"{data['sucre']}g")
            st.info(f"🏭 **Code Usine (EMB) :** {data['emb'] if data['emb'] else 'Non détecté'}")
        
        with col2:
            with st.expander("📜 Voir la recette complète"):
                st.write(data['ingredients'])

        # ÉTAPE D : Recherche de Clones (Même usine dans votre CSV)
        if data['emb']:
            try:
                df = pd.read_csv("produits.csv", dtype={'code': str})
                clean_emb = str(data['emb']).strip()
                # On cherche les produits du CSV qui ont le même code usine
                clones = df[df['emb'].str.contains(clean_emb, na=False, case=False) & (df['nom'] != data['nom'])]
                
                if not clones.empty:
                    st.write("---")
                    st.subheader(f"💡 {len(clones)} Clones détectés dans notre base")
                    for _, c in clones.iterrows():
                        score = calculer_score(data['ingredients'], c['ingredients'])
                        with st.expander(f"✅ {c['nom']} — Correspondance : {score}%"):
                            st.markdown(f"**Comparaison des ingrédients :**")
                            diff_html = comparer_visuel(data['ingredients'], c['ingredients'])
                            st.markdown(f"<div style='padding:15px; border:1px solid #ddd; border-radius:10px; background-color:white;'>{diff_html}</div>", unsafe_allow_html=True)
                else:
                    st.warning("Aucun clone répertorié pour cette usine dans notre base locale.")
            except Exception as e:
                st.error(f"Erreur d'accès à la base de clones : {e}")
    else:
        st.error("❌ Produit introuvable (Base mondiale et locale).")

st.markdown("---")
st.caption("Données fournies par Open Food Facts et votre base de données personnelle.")
