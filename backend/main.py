import os
import json
import base64
import requests
import shutil
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from urllib.parse import unquote
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

root_folder = "CarData"
generated_json_file = "generated_car_damage_data.json"  
manual_json_file = "manual_car_damage_data.json"  
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SITE_URL = "<YOUR_SITE_URL>"
SITE_NAME = "<YOUR_SITE_NAME>"
MAX_RETRIES = 3

app.mount("/images", StaticFiles(directory=root_folder), name="images")

if not os.path.exists(root_folder):
    raise FileNotFoundError(f"The folder {root_folder} does not exist.")

def load_json(file_path: str):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as file:
                content = file.read().strip()
                return json.loads(content) if content else []
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {file_path}. Starting with an empty list.")
            return []
    return []

def save_json(data: list, file_path: str):
    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=4)
    print(f"JSON updated at {file_path}")

def encode_image(image_path: str):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def process_image_with_gemma(image_path: str, relative_path: str) -> Optional[str]:
    for attempt in range(MAX_RETRIES):
        try:
            image_base64 = encode_image(image_path)
            prompt = (
                "Describe a car’s condition in one paragraph for a car damage dataset, based on the provided image. "
                "If visible damage exists, detail the type, the specific parts affected, the severity, and notable aspects like "
                "the damage location. If no damage is visible, state that clearly and include the car’s "
                "overall condition and any relevant observations. Ensure the description is clear, precise, and avoids assumptions "
                "beyond the image content. Do not include introductory phrases like 'Here is a description,' 'Based on the image,' "
                "'This image shows,' or any reference to the image itself and statements like 'further inspection is needed'; focus solely on the car’s state in a direct, standalone manner."
            )

            payload = {
                "model": "google/gemma-3-12b-it:free",
                "messages": [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]}
                ]
            }

            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME
            }

            response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error for {relative_path} with Gemma (attempt {attempt + 1}): {str(e)}")
            return None

def evaluate_with_pixtral(image_path: str, caption: str) -> dict:
    for attempt in range(MAX_RETRIES):
        try:
            image_base64 = encode_image(image_path)
            evaluation_prompt = (
                f"Evaluate the following description of a car’s condition based on the provided image. "
                f"Score it out of 5 (1 being very inaccurate, 5 being very accurate) based on how well it describes the car’s visible condition. "
                f"Provide a brief explanation for your score. Return your response in this format: 'Score: X/5 - Explanation: [your explanation]'. "
                f"The description to evaluate is: '{caption}'"
            )

            payload = {
                "model": "mistralai/pixtral-12b",
                "messages": [
                    {"role": "user", "content": [
                        {"type": "text", "text": evaluation_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]}
                ]
            }

            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME
            }

            response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            response_text = result["choices"][0]["message"]["content"]
            
            try:
                score_line = response_text.split(' - ')[0]
                score = int(score_line.split(':')[1].split('/')[0].strip())
                explanation = response_text.split(' - Explanation: ')[1].strip()
                return {"score": score, "explanation": explanation}
            except Exception as e:
                print(f"Error parsing Pixtral response: {e}")
                return {"score": None, "explanation": response_text}
        except Exception as e:
            print(f"Error evaluating with Pixtral (attempt {attempt + 1}): {str(e)}")
            return {"score": None, "explanation": "Evaluation failed"}

def get_all_images():
    image_extensions = (".jpg", ".jpeg", ".png")
    generated_data = load_json(generated_json_file)  
    existing_paths = {entry["image"] for entry in generated_data}
    image_files = []
    for folder_name, _, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(image_extensions):
                image_path = os.path.join(folder_name, file)
                relative_path = os.path.relpath(image_path, root_folder).replace("\\", "/")
                if relative_path not in existing_paths:
                    image_files.append((image_path, relative_path))
    return image_files

class ReviewData(BaseModel):
    action: str
    image_path: str
    gemma_caption: str
    manual_caption: Optional[str] = ''
    gemma_score: Optional[int] = None
    manual_score: Optional[int] = None

@app.get("/review")
async def get_review():
    image_files = get_all_images()
    if not image_files:
        return {"message": "All images have been processed!", "done": True}

    image_path, relative_path = image_files[0]
    gemma_caption = process_image_with_gemma(image_path, relative_path)
    if gemma_caption:
        return {
            "image_path": relative_path,
            "gemma_caption": gemma_caption,
            "total": len(image_files)
        }
    raise HTTPException(status_code=500, detail="Failed to process image with Gemma")

@app.post("/review")
async def post_review(data: ReviewData):
    image_files = get_all_images()
    full_image_path = os.path.join(root_folder, unquote(data.image_path))

    if data.action == "check":
        gemma_eval = evaluate_with_pixtral(full_image_path, data.gemma_caption) if data.gemma_caption else {"score": None, "explanation": "No Gemma caption provided"}
        manual_eval = evaluate_with_pixtral(full_image_path, data.manual_caption) if data.manual_caption else {"score": None, "explanation": "No manual caption provided"}
        return {
            "gemma_score": gemma_eval["score"],
            "gemma_explanation": gemma_eval["explanation"],
            "manual_score": manual_eval["score"],
            "manual_explanation": manual_eval["explanation"]
        }

    elif data.action == "save":
        generated_data = load_json(generated_json_file)
        manual_data = load_json(manual_json_file)

        # Removed pixtral_score from the entries
        generated_entry = {"image": data.image_path, "caption": data.gemma_caption}
        manual_entry = {"image": data.image_path, "caption": data.manual_caption}

        generated_data.append(generated_entry)
        if data.manual_caption:
            manual_data.append(manual_entry)

        save_json(generated_data, generated_json_file) 
        save_json(manual_data, manual_json_file)

        image_files = get_all_images()
        if not image_files:
            return {"message": "All images processed!", "done": True}

        next_image_path, next_relative_path = image_files[0]
        gemma_caption = process_image_with_gemma(next_image_path, next_relative_path)
        if gemma_caption:
            return {
                "image_path": next_relative_path,
                "gemma_caption": gemma_caption,
                "total": len(image_files)
            }
        raise HTTPException(status_code=500, detail="Failed to process image with Gemma")

    raise HTTPException(status_code=400, detail="Invalid action")

@app.post("/upload_folder")
async def upload_folder(files: list[UploadFile] = File(...)):
    try:
        for file in files:
            relative_path = file.filename
            if not relative_path:
                relative_path = file.filename

            if not file.content_type or not file.content_type.startswith("image/"):
                print(f"Skipping non-image file: {relative_path}")
                continue

            target_path = os.path.join(root_folder, relative_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            print(f"Saved file: {target_path}")

        return {"message": "Folder uploaded successfully"}
    except Exception as e:
        print(f"Error in upload_folder: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading folder: {str(e)}")
    finally:
        for file in files:
            file.file.close()