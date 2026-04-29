import streamlit as st
import pandas as pd
import difflib
import re
import cv2
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode

# --- CONFIGURATION ---
st.set_page_config(page_title="FoodTwins", page_icon="🔬", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .badge { padding: 4px 10px; border-radius: 10px; font-weight: bold; margin-right: 5px; display: inline-block; margin-bottom: 5px; }
    .nutri-A { background-color: #008b4c; color: white; }
    .nutri-B { background-color: #80c141; color: white; }
    .nutri-C { background-color: #fec917; color: black; }
    .nutri-D { background-color: #ee8100; color: white; }
    .nutri-E { background-color: #e63e11; color: white; }
    .nova { background-color: #333; color: white; border-radius: 5px; padding: 2px 8px; }
    .vegan { background-color: #2ecc71; color: white; }
    .has-pork { background-color: #e74c3c; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS UTILES ---
@st.cache_data
from st_gsheets_connection import GSheetConnection

def load_data():
    conn = st.connection("gsheets", type=GSheetConnection)
    # Remplacer par l'URL de ton Google Sheet
    url = "https://docs.google.com/spreadsheets/d/TON_ID_ICI/edit#gid=0"
    df = conn.read(spreadsheet=url, ttl="10m") # ttl = cache de 10 minutes
    return df

def scan_barcode(image):
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    detected_barcodes = decode(gray)
    for barcode in detected_barcodes:
        return barcode.data.decode('utf-8')
    return None

def get_badges_html(ingredients):
    badges = ""
    ing_low = str(ingredients).lower()
    if "porc" in ing_low or "lard" in ing_low:
        badges += '<span class="badge has-pork">🐷 Porc</span>'
    if not any(x in ing_low for x in ["viande", "poisson", "poulet", "boeuf", "jambon"]):
        badges += '<span class="badge vegan">🍃 Végétarien</span>'
    return badges

# --- CHARGEMENT ---
df = load_data()

# --- ENTÊTE ---
col_logo, col_titre = st.columns([1, 5])
with col_logo:
    st.image("logo.png", width=80)
with col_titre:
    st.title("FoodTwins")
st.markdown("<p style='color: gray; font-style: italic; font-size: 20px;'>« Ne payez plus le logo, payez le produit. »</p>", unsafe_allow_html=True)

# --- ZONE DE SAISIE ET SCAN ---
barcode = ""
tabs = st.tabs(["⌨️ Saisie Manuelle", "📸 Scanner"])

with tabs[0]:
    barcode_manual = st.text_input("Entrez le code-barres :", key="manual").strip()
    if barcode_manual:
        barcode = barcode_manual

with tabs[1]:
    img_file = st.camera_input("Placez le code-barres face à la caméra")
    if img_file:
        scanned_code = scan_barcode(Image.open(img_file))
        if scanned_code:
            barcode = scanned_code
            st.success(f"Code détecté : {barcode}")
        else:
            st.warning("Code-barres non détecté. Essayez de rapprocher le produit.")

# --- AFFICHAGE DES RÉSULTATS ---
if barcode:
    res = df[df['code'] == barcode]
    
    if not res.empty:
        p = res.iloc[0]
        col1, col2 = st.columns([1, 2])
        with col1:
            if p.get('image_url'): st.image(p['image_url'], use_container_width=True)
            else: st.info("📷 Image non disponible")

        with col2:
            st.write(f"**{p['marque']}**")
            st.header(p['nom'])
            ns = str(p['nutriscore']).upper()
            st.markdown(f"""
                <span class="badge nutri-{ns}">Nutri-Score {ns}</span>
                <span class="nova">{p.get('nova', '?')}</span>
                {get_badges_html(p['ingredients'])}
            """, unsafe_allow_html=True)
            st.info(f"🏭 **Usine :** {p['emb']} ({p.get('usine_lieu', 'Inconnue')})")

        mots = [m for m in p['nom'].split() if len(m) > 3]
        mot_cle = mots[0] if mots else p['nom']

        clones = df[
            (df['emb'] == p['emb']) & 
            (df['nom'].str.contains(mot_cle, case=False, na=False)) & 
            (df['code'] != barcode)
        ]
        
        if not clones.empty:
            st.markdown("---")
            st.subheader(f"💡 {len(clones)} Alternatives détectées pour '{mot_cle}'")
            
            for _, c in clones.head(10).iterrows():
                score_text = difflib.SequenceMatcher(None, str(p['ingredients']), str(c['ingredients'])).ratio()
                pct = int(score_text * 100)
                
                with st.expander(f"✅ {c['marque']} - {c['nom']} ({pct}% de ressemblance)"):
                    ca, cb = st.columns([1, 2])
                    with ca:
                        if c.get('image_url'): st.image(c['image_url'], width=120)
                        st.markdown(f'<span class="badge nutri-{str(c["nutriscore"]).upper()}">Score {str(c["nutriscore"]).upper()}</span>', unsafe_allow_html=True)
                    with cb:
                        st.write(f"**Ingrédients :** {c['ingredients']}")
                        diff_sucre = float(c['sucre']) - float(p['sucre'])
                        st.write(f"**Sucre :** {c['sucre']}g ({'+' if diff_sucre > 0 else ''}{round(diff_sucre,1)}g)")
    
    else:
        st.error(f"Le produit {barcode} n'est pas encore dans notre base.")
        st.info("💡 Aidez-nous à enrichir la base en ajoutant ce produit ci-dessous.")
        
        with st.expander("➕ Ajouter ce produit manuellement"):
            with st.form("ajout_produit"):
                new_nom = st.text_input("Nom du produit")
                new_marque = st.text_input("Marque")
                new_emb = st.text_input("Code Usine EMB")
                new_ing = st.text_area("Liste des ingrédients")
                new_nutri = st.selectbox("Nutriscore", ["A", "B", "C", "D", "E"])
                
                if st.form_submit_button("Enregistrer définitivement"):
                    # Création de la nouvelle ligne
                    new_row = pd.DataFrame([{
                        "code": barcode,
                        "nom": new_nom,
                        "marque": new_marque,
                        "emb": new_emb,
                        "ingredients": new_ing,
                        "nutriscore": new_nutri,
                        "sucre": 0, "sel": 0, "energie_100g": 0 # Valeurs par défaut
                    }])
                    
                    # Sauvegarde réelle dans le fichier CSV
                    new_row.to_csv("produits.csv", mode='a', header=False, index=False)
                    
                    st.success(f"Produit '{new_nom}' ajouté au fichier ! Videz le cache ou relancez pour le voir.")
                    st.cache_data.clear() # Force le rechargement de la base au prochain scan
