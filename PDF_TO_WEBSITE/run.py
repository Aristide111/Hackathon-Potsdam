from mistralai import Mistral
from dotenv import load_dotenv
import datauri
import os
import shutil
import yaml
from tqdm import tqdm

# --- Config ---
Input = "./PDF"
Output = "./Site"

load_dotenv()
api_key = os.environ["KEY"]
client = Mistral(api_key=api_key)

# --- Architecture MkDocs ---
MKDOCS_ROOT = os.path.join(Output, "lgo")
DOCS_DIR    = os.path.join(MKDOCS_ROOT, "docs")
IMG_DIR     = os.path.join(DOCS_DIR, "img")
CSS_DIR     = os.path.join(DOCS_DIR, "stylesheet")

def create_site_structure():
    os.makedirs(DOCS_DIR,  exist_ok=True)
    os.makedirs(IMG_DIR,   exist_ok=True)
    os.makedirs(CSS_DIR,   exist_ok=True)
    print("Architecture MkDocs créée.")

def write_default_css():
    # Le CSS est fourni séparément ci-dessous, assurez-vous de le copier dans extra.css
    pass

def write_index():
    index_path = os.path.join(DOCS_DIR, "index.md")
    with open(index_path, "wt", encoding="utf-8") as f:
        f.write("# La Gazette Automatique\n\nÉdition générée par IA à partir de vos documents PDF.\n")

def upload_pdf(filepath, filename):
    with open(filepath, "rb") as f:
        uploaded_pdf = client.files.upload(
            file={"file_name": filename, "content": f},
            purpose="ocr"
        )
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
    return signed_url.url

def run_ocr(signed_url):
    return client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": signed_url},
        include_image_base64=True,
    )

# --- MODIFICATION ICI : Unicité des images ---
def save_image(image, prefix):
    parsed = datauri.parse(image.image_base64)
    # On ajoute le préfixe du document pour éviter les collisions
    unique_filename = f"{prefix}_{image.id}"
    image_path = os.path.join(IMG_DIR, unique_filename)
    
    with open(image_path, "wb") as f:
        f.write(parsed.data)
    return f"img/{unique_filename}"

def write_markdown(ocr_response, md_filename, prefix):
    md_path = os.path.join(DOCS_DIR, md_filename)
    with open(md_path, "wt", encoding="utf-8") as f:
        for page in ocr_response.pages:
            content = page.markdown
            for image in page.images:
                # On passe le préfixe ici aussi
                rel_path = save_image(image, prefix)
                # On remplace l'ID original par le nouveau chemin unique
                content = content.replace(image.id, rel_path)
            f.write(content + "\n")
    return md_filename

def write_mkdocs_yml(site_name, nav_entries):
    config = {
        "site_name": site_name,
        "docs_dir": "docs",
        "nav": [{"Accueil": "index.md"}] + nav_entries,
        "theme": {
            "name": "material",
            "language": "fr",
            "palette": { "primary": "black", "accent": "grey" },
            "features": ["navigation.sections", "search.highlight"]
        },
        "extra_css": ["stylesheet/extra.css"]
    }
    yml_path = os.path.join(MKDOCS_ROOT, "mkdocs.yml")
    with open(yml_path, "wt", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

# --- PIPELINE ---
pdf_files = sorted([f for f in os.listdir(Input) if f.lower().endswith(".pdf")])
if not pdf_files:
    exit("Aucun PDF trouvé.")

create_site_structure()
write_index()

nav_entries = []
site_name = "Le Journal de l'IA"

for i, filename in enumerate(tqdm(pdf_files, desc="Traitement")):
    filepath = os.path.join(Input, filename)
    base_name = os.path.splitext(filename)[0]
    # Slug pour les noms de fichiers images (sans espaces)
    file_prefix = base_name.replace(" ", "_") 
    md_filename = f"{base_name}.md"

    try:
        url = upload_pdf(filepath, filename)
        ocr_response = run_ocr(url)
        # On transmet le préfixe pour garantir l'unicité
        write_markdown(ocr_response, md_filename, file_prefix)
        nav_entries.append({base_name: md_filename})
    except Exception as e:
        print(f"Erreur sur {filename}: {e}")

write_mkdocs_yml(site_name, nav_entries)