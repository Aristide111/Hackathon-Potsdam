import fitz  # PyMuPDF
import os

def convert_images_to_single_pdf(image_folder, output_folder, output_pdf_name):
    # Créer le dossier de sortie s'il n'existe pas
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Créer un nouveau document PDF
    pdf_document = fitz.open()

    # Liste pour stocker les chemins des images
    image_paths = []

    # Parcourir chaque fichier dans le dossier d'entrée
    for image_file in sorted(os.listdir(image_folder)):
        # Vérifier si le fichier est une image (JPEG, PNG, etc.)
        if image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Construire le chemin complet du fichier image
            image_path = os.path.join(image_folder, image_file)
            image_paths.append(image_path)

    # Ajouter chaque image au document PDF
    for image_path in image_paths:
        img = fitz.open(image_path)
        pdf_bytes = img.convert_to_pdf()
        img.close()

        # Créer un nouveau PDF à partir des bytes de l'image
        img_pdf = fitz.open("pdf", pdf_bytes)
        pdf_document.insert_pdf(img_pdf)

    # Construire le chemin de sortie pour le PDF
    output_path = os.path.join(output_folder, output_pdf_name)

    # Sauvegarder le PDF
    pdf_document.save(output_path)
    pdf_document.close()

    print(f"Conversion terminée. Le PDF est sauvegardé dans {output_path}")

# Chemins des dossiers d'entrée et de sortie
image_folder = "JPEG"  # Remplacez par le chemin de votre dossier contenant les images
output_folder = "PDF"  # Remplacez par le chemin de votre dossier de sortie pour les PDFs
output_pdf_name = "compiled_images.pdf"  # Nom du fichier PDF de sortie

# Appeler la fonction pour convertir les images en un seul PDF
convert_images_to_single_pdf(image_folder, output_folder, output_pdf_name)
