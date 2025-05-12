import os
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI as A, File as B, UploadFile as C, HTTPException
from fastapi.middleware.cors import CORSMiddleware as D
from fastapi.responses import JSONResponse as E
from openai import OpenAI as F
from PIL import Image as G
import io as H, base64 as I

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = A()
app.add_middleware(D, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Get OpenAI API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI with the API key
if not openai_api_key:
    raise ValueError("OpenAI API key is missing. Set the OPENAI_API_KEY environment variable.")
openai = F(api_key=openai_api_key)

# Function to convert image to base64
def encode_image(image_data: bytes) -> str:
    image = G.open(H.BytesIO(image_data)).convert('RGB')  # Open and convert image to RGB
    buffer = H.BytesIO()  # Create in-memory buffer
    image.save(buffer, format='JPEG')  # Save image to buffer
    encoded = I.b64encode(buffer.getvalue())  # Get base64 encoding
    return encoded.decode()  # Convert bytes to string

@app.post("/analyze")
async def analyze_images(files: List[C] = B(...)):
    try:
        # Prepare image URLs
        image_data = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(await file.read())}"}} for file in files]

        # Add description for OpenAI model
        image_data += [{
            "type": "text",
            "text": (
                "You are given an image of a document. Determine if it is a valid Aadhaar card issued by UIDAI India. "
                "Only respond with 'found aadhaar card' or 'not found'. "
                "To consider it valid, confirm the presence of key Aadhaar features such as:\n"
                "- 'Aadhaar' word in any language\n"
                "- 12-digit Aadhaar number in standard format (xxxx xxxx xxxx)\n"
                "- QR code\n"
                "- UIDAI or Government of India mentions\n"
                "- Name, DOB, and Gender fields\n"
                "If any of these elements are missing or the image is empty, partial, or fake, respond with 'not found' "
                "and ask the user to upload a clear and complete Aadhaar card only."
            )
        }]

        # Call OpenAI API for image analysis
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{
                "role": "system", "content": "You are a document classification expert for Indian identity documents. Be accurate and concise."
            }, {
                "role": "user", "content": image_data
            }]
        )

        # Return the result of the analysis
        return E(content={"result": response.choices[0].message.content})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
