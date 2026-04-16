import base64
import os
from mistralai import Mistral

api_key = os.environ["MISTRAL_API_KEY"]

client = Mistral(api_key=api_key)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

image_path = "AP.pdf"
base64_image = encode_image(image_path)

ocr_response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{base64_image}" })
print(ocr_response)

