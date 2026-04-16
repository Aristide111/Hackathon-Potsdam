#ENVIRONNNEMENT LINUX : env_PDF_to_JPG
import fitz  # PyMuPDF
import os

def convert_pdf_to_images(pdf_folder, output_folder):
    # Parcourir chaque fichier dans le dossier d'entrée
    for pdf_file in os.listdir(pdf_folder):
        # Vérifier si le fichier est un PDF
        if pdf_file.endswith('.pdf'):
            # Construire le chemin complet du fichier PDF
            pdf_path = os.path.join(pdf_folder, pdf_file)

            # Créer un sous-dossier pour chaque PDF dans le dossier de sortie
            # en utilisant le nom du fichier PDF sans l'extension
            pdf_name = os.path.splitext(pdf_file)[0]
            pdf_output_folder = os.path.join(output_folder, pdf_name)

            # Créer le sous-dossier s'il n'existe pas
            if not os.path.exists(pdf_output_folder):
                os.makedirs(pdf_output_folder)

            # Ouvrir le fichier PDF
            pdf_document = fitz.open(pdf_path)

            # Parcourir chaque page du PDF
            for page_number in range(len(pdf_document)):
                # Charger la page
                page = pdf_document.load_page(page_number)

                # Rendre la page en tant qu'image
                pix = page.get_pixmap()

                # Construire le chemin de sortie pour l'image
                output_path = os.path.join(pdf_output_folder, f"page_{page_number + 1}.png")

                # Sauvegarder l'image
                pix.save(output_path)

            print(f"Conversion terminée pour {pdf_file}. Les images sont sauvegardées dans {pdf_output_folder}")

# Chemins des dossiers d'entrée et de sortie
pdf_folder = "PDF"  # Remplacez par le chemin de votre dossier contenant les PDFs
output_folder = "JPEG"  # Remplacez par le chemin de votre dossier de sortie pour les images

# Appeler la fonction pour convertir les PDFs en images
convert_pdf_to_images(pdf_folder, output_folder)
