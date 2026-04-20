import streamlit as st
import pandas as pd
import requests
import difflib
import re
import os

# --- CONFIGURATION & DESIGN ---
st.set_page_config(page_title="CloneDetector Ultimate", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
    .badge { padding: 4px 10px; border-radius: 12px; font-weight: bold; margin-right: 5px; display: inline-block; margin-bottom: 5px; font-size: 0.85em; }
    .vegan { background-color: #2ecc71; color: white; }
    .no-pork { background-color: #f1c40f; color: black; }
    .gluten-free { background-color: #8e44ad; color: white; }
    .warning { background-color: #e74c3c; color: white; }
    .diff-red { color: #e74c3c; font-weight: bold; text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS DE BASE ---
@st.cache_data(ttl=60) # Recharge les données toutes les minutes si modifiées
def load_data():
    if os.path.exists("produits.csv"):
        df = pd.read_csv("produits.csv", dtype=str).fillna("")
        df['code'] = df['code'].str.strip()
        df['sucre'] = pd.to_numeric(df['sucre'], errors='coerce').fillna(0)
        return df
    return pd.DataFrame()

def save_new_product(new_data):
    df = load_data()
    new_df = pd.DataFrame([new_data])
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_csv("produits.csv", index=False)
    st.cache_data.clear() # Force le rafraîchissement

def get_badges_html(ingredients):
    badges = ""
    ing_low = ingredients.lower()
    
    if "porc" not in ing_low and "lard" not in ing_low and "gélatine" not in ing_low:
        badges += '<span class="badge no-pork">🚫 🐷 Sans Porc</span>'
    if not any(x in ing_low for x in ["viande", "poisson", "poulet", "boeuf", "jambon"]):
        badges += '<span class="badge vegan">🍃 Végétarien</span>'
    if not any(x in ing_low for x in ["blé", "farine de blé", "gluten", "orge"]):
        badges += '<span class="badge gluten-free">🌾 Sans Gluten</span>'
    
    return badges

def highlight_differences(base_ing, clone_ing):
    # Coupe les ingrédients par virgule
    base_list = [x.strip().lower() for x in re.split(r'[,;]', base_ing)]
    clone_list = [x.strip() for x in re.split(r'[,;]', clone_ing)]
    
    highlighted = []
    for item in clone_list:
        # Si l'ingrédient du clone n'est pas dans le produit de base, on le met en rouge
        if item.lower() not in base_list:
            highlighted.append(f"<span class='diff-red'>{item}</span>")
        else:
            highlighted.append(item)
    return ", ".join(highlighted)

def get_score_color(score):
    if score >= 90: return "🟢"
    elif score >= 70: return "🟠"
    else: return "🔴"

# --- CHARGEMENT ---
df = load_data()

# --- INTERFACE UTILISATEUR : ONGLETS ---
st.title("🔬 CloneDetector Ultimate")
tab_search, tab_add = st.tabs(["🔍 Rechercher & Comparer", "📸 Scanner & Ajouter à la base"])

# ==========================================
# ONGLET 1 : RECHERCHE ET COMPARAISON
# ==========================================
with tab_search:
    st.markdown("### Scannez un produit pour trouver ses clones")
    
    # Utilisation d'un Formulaire pour avoir le bouton "Entrée"
    with st.form("search_form"):
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            barcode = st.text_input("Saisissez le code-barres (ou utilisez un scanner USB/Bluetooth) :", placeholder="Ex: 3200849007378")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True) # Alignement vertical
            submitted = st.form_submit_button("Chercher 🚀")

    if submitted and barcode:
        barcode = barcode.strip()
        res = df[df['code'] == barcode]
        
        if not res.empty:
            p = res.iloc[0]
            st.success(f"## {p['nom']} ({p['marque']})")
            st.markdown(get_badges_html(p['ingredients']), unsafe_allow_html=True)
            
            # Infos détaillées du produit
            c1, c2, c3 = st.columns(3)
            c1.metric("Catégorie", p['categorie'])
            c2.info(f"🏭 Usine : {p['emb']}")
            if 'usine_lieu' in p:
                c3.info(f"📍 Lieu : {p['usine_lieu']}")

            st.write(f"**Ingrédients d'origine :** {p['ingredients']}")

            # --- RECHERCHE DES CLONES ---
            # Condition stricte : Même usine ET Même catégorie
            clones = df[(df['emb'] == p['emb']) & (df['categorie'] == p['categorie']) & (df['code'] != barcode)]
            
            if not clones.empty:
                st.markdown("---")
                st.subheader(f"💡 {len(clones)} Alternatives strictement identiques (Même type, même usine)")
                
                for _, c in clones.head(10).iterrows():
                    # Calcul de ressemblance
                    score = int(difflib.SequenceMatcher(None, p['ingredients'], c['ingredients']).ratio() * 100)
                    color_icon = get_score_color(score)
                    
                    with st.expander(f"{color_icon} {c['nom']} — Correspondance : {score}%"):
                        st.markdown(get_badges_html(c['ingredients']), unsafe_allow_html=True)
                        
                        # Ingrédients avec différences en rouge
                        ing_diff_html = highlight_differences(p['ingredients'], c['ingredients'])
                        st.markdown(f"**Ingrédients :** {ing_diff_html}", unsafe_allow_html=True)
                        st.caption("*(Les ingrédients en rouge vif et soulignés sont absents de votre produit scanné)*")
            else:
                st.warning("Aucun clone du même type trouvé dans cette usine.")
        else:
            st.error("❌ Produit introuvable dans la base de données locale. Allez dans l'onglet 'Scanner & Ajouter' pour l'insérer !")


# ==========================================
# ONGLET 2 : SCANNER ET AJOUTER (CROWDSOURCING)
# ==========================================
with tab_add:
    st.markdown("### 📸 Ajouter un produit manquant à la base `.csv`")
    st.write("Prenez en photo le code-barres et l'étiquette des ingrédients pour l'ajouter à notre base.")
    
    col_photo1, col_photo2 = st.columns(2)
    with col_photo1:
        photo_code = st.camera_input("1. Photo du Code-barres")
    with col_photo2:
        photo_ing = st.camera_input("2. Photo des Ingrédients")
        
    with st.form("add_product_form"):
        st.subheader("📝 Remplir les informations extraites")
        new_code = st.text_input("Code-barres lu :")
        new_nom = st.text_input("Nom du produit (ex: Yaourt Nature) :")
        new_marque = st.text_input("Marque :")
        
        # Sélection de la catégorie parmi celles existantes
        cats_existantes = df['categorie'].unique().tolist() if not df.empty else ["Produits laitiers", "Charcuterie", "Biscuits"]
        new_cat = st.selectbox("Catégorie stricte :", cats_existantes + ["+ Ajouter une nouvelle catégorie"])
        
        new_emb = st.text_input("Code Usine (EMB) lu sur l'emballage :", placeholder="Ex: FR 53.054.005 CE")
        new_ing = st.text_area("Liste des ingrédients :")
        new_sucre = st.number_input("Taux de sucre (g/100g) :", min_value=0.0, step=0.1)
        
        submit_add = st.form_submit_button("💾 Enregistrer dans le CSV")
        
        if submit_add:
            if new_code and new_nom and new_emb:
                new_data = {
                    "code": new_code, "nom": new_nom, "marque": new_marque, 
                    "categorie": new_cat, "emb": new_emb, "ingredients": new_ing,
                    "sucre": new_sucre, "usine_lieu": "Ajout Utilisateur"
                }
                save_new_product(new_data)
                st.success(f"✅ Le produit {new_nom} a été ajouté avec succès à la base de données !")
                st.balloons()
            else:
                st.error("⚠️ Veuillez au moins remplir le Code-barres, le Nom et le Code EMB.")
