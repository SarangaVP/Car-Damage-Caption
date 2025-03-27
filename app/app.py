import os
import json
import base64
import requests
from flask import Flask, render_template, request, jsonify, send_from_directory
from func_timeout import func_timeout, FunctionTimedOut
from urllib.parse import unquote  

app = Flask(__name__)
root_folder = "CarData"
json_file_path = "car_damage_data.json"
OPENROUTER_API_KEY = ""
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SITE_URL = "<YOUR_SITE_URL>"
SITE_NAME = "<YOUR_SITE_NAME>"
API_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 10

if not os.path.exists(root_folder):
    raise FileNotFoundError(f"The folder {root_folder} does not exist.")

def load_existing_data():
    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, "r") as file:
                content = file.read().strip()
                return json.loads(content) if content else []
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {json_file_path}. Starting with an empty list.")
            return []
    return []

def save_json(data):
    with open(json_file_path, "w") as json_file:
        json.dump(data, json_file, indent=4)
    print(f"JSON updated at {json_file_path}")

def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def process_image(image_path, relative_path):
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
            return {"image": relative_path, "caption": result["choices"][0]["message"]["content"]}
        except Exception as e:
            print(f"Error for {relative_path} (attempt {attempt + 1}): {str(e)}")
            # if attempt < MAX_RETRIES - 1:
            #     time.sleep(RETRY_DELAY)
            # else:
            #     return None

def get_all_images():
    image_extensions = (".jpg", ".jpeg", ".png")
    existing_data = load_existing_data()
    existing_paths = {entry["image"] for entry in existing_data}
    image_files = []
    for folder_name, _, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(image_extensions):
                image_path = os.path.join(folder_name, file)
                relative_path = os.path.relpath(image_path, root_folder).replace("\\", "/")
                if relative_path not in existing_paths:
                    image_files.append((image_path, relative_path))
    return image_files

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/review', methods=['GET', 'POST'])
def review():
    image_files = get_all_images()
    if not image_files:
        return render_template('review.html', message="All images have been processed!")

    if request.method == 'POST':
        data = request.get_json()
        caption = data.get('caption')
        image_path = unquote(data.get('image_path'))

        existing_data = load_existing_data()
        existing_data.append({"image": image_path, "caption": caption})
        save_json(existing_data)

        image_files = get_all_images()
        if not image_files:
            return jsonify({"message": "All images processed!", "done": True})

        next_image_path, next_relative_path = image_files[0]
        image_data = process_image(next_image_path, next_relative_path)
        if image_data:
            return jsonify({"image_path": next_relative_path, "caption": image_data["caption"], "total": len(image_files)})
        return jsonify({"error": "Failed to process image"})

    image_path, relative_path = image_files[0]
    image_data = process_image(image_path, relative_path)
    if image_data:
        return render_template('review.html', image_path=relative_path, caption=image_data["caption"], total=len(image_files))
    return render_template('review.html', message="Error processing first image.")

@app.route('/images/<path:filename>')
def serve_image(filename):
    filename = unquote(filename)
    return send_from_directory(root_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)