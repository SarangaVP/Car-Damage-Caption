import os
from PIL import Image, ImageTk
import json
import requests
import time
from func_timeout import func_timeout, FunctionTimedOut
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv
import base64

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

root_folder = os.path.join(os.path.dirname(__file__), "CarData")
json_file_path = os.path.join(os.path.dirname(__file__), "car_damage_data.json")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SITE_URL = "<SITE_URL>"
SITE_NAME = "<SITE_NAME>"
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 10

if not os.path.exists(root_folder):
    raise FileNotFoundError(f"The folder {root_folder} does not exist. Please ensure it is present.")

def load_existing_data():
    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, "r") as file:
                content = file.read().strip()
                if content:
                    return json.loads(content)
                else:
                    return []
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

def process_image_with_timeout(image_path, relative_path):
    try:
        return func_timeout(API_TIMEOUT, process_image, args=(image_path, relative_path))
    except FunctionTimedOut:
        print(f"API call timed out for {relative_path} after {API_TIMEOUT} seconds")
        return None

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
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }
                ]
            }

            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME
            }

            start = time.time()
            response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            end = time.time()

            caption = result["choices"][0]["message"]["content"]
            # print(f"API call took {end - start:.2f} seconds for {relative_path}")

            return {
                "image": relative_path,
                "caption": caption
            }
        except requests.exceptions.RequestException as e:
            print(f"Error for {relative_path} (attempt {attempt + 1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1 and "503" in str(e):
                print(f"Retrying after {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"Max retries reached for {relative_path}. Skipping image.")
                return None
        except Exception as e:
            print(f"Unexpected error processing {relative_path}: {str(e)}")
            return None

class ImageReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Car Damage Review")
        self.root.configure(bg="#f0f0f0") 

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Helvetica", 12, "bold"), padding=10, background="#4CAF50", foreground="white")
        style.map("TButton", background=[("active", "#45a049")])
        style.configure("TLabel", font=("Arial", 12), background="#f0f0f0")

        self.existing_data = load_existing_data()
        self.existing_paths = {entry["image"] for entry in self.existing_data}
        self.image_files = self.get_all_images()
        self.current_index = 0

        self.main_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.main_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.main_frame, bg="#f0f0f0")
        self.scrollbar_y = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(self.main_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)

        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content_frame = tk.Frame(self.canvas, bg="#f0f0f0")
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.title_label = ttk.Label(self.content_frame, text="Car Damage Review", font=("Arial", 20, "bold"), foreground="#333333")
        self.title_label.pack(pady=10)

        self.image_frame = tk.Frame(self.content_frame, bg="#ffffff", bd=2, relief="sunken")
        self.image_frame.pack(pady=10)
        self.image_label = ttk.Label(self.image_frame)
        self.image_label.pack()

        self.caption_label = ttk.Label(self.content_frame, text="Condition Description:", font=("Arial", 14, "bold"), foreground="#555555")
        self.caption_label.pack(pady=(10, 5))
        self.caption_text = tk.Text(self.content_frame, height=10, width=80, font=("Arial", 12), bg="#ffffff", fg="#333333", borderwidth=2, relief="groove")
        self.caption_text.pack(pady=5)

        self.save_button = ttk.Button(self.content_frame, text="Save and Next", command=self.save_and_next, style="TButton")
        self.save_button.pack(pady=15)

        self.status_label = ttk.Label(self.content_frame, text="", font=("Arial", 11, "italic"), foreground="#666666")
        self.status_label.pack(pady=10)

        self.content_frame.bind("<Configure>", self.on_frame_configure)

        self.process_next_image()

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def get_all_images(self):
        image_extensions = (".jpg", ".jpeg", ".png")
        image_files = []
        for folder_name, _, files in os.walk(root_folder):
            for file in files:
                if file.lower().endswith(image_extensions):
                    image_path = os.path.join(folder_name, file)
                    relative_path = os.path.relpath(image_path, root_folder).replace("\\", "/")
                    if relative_path not in self.existing_paths:
                        image_files.append((image_path, relative_path))
        return image_files

    def process_next_image(self):
        if self.current_index >= len(self.image_files):
            messagebox.showinfo("Done", "All images have been processed!", parent=self.root)
            self.root.quit()
            return

        image_path, relative_path = self.image_files[self.current_index]
        self.status_label.config(text=f"Processing {relative_path} ({self.current_index + 1}/{len(self.image_files)})")

        img = Image.open(image_path)
        photo = ImageTk.PhotoImage(img)
        self.image_label.config(image=photo)
        self.image_label.image = photo 

        image_data = process_image_with_timeout(image_path, relative_path)
        if image_data:
            self.caption_text.delete("1.0", tk.END)
            self.caption_text.insert(tk.END, image_data["caption"])
            self.current_data = image_data
        else:
            self.caption_text.delete("1.0", tk.END)
            self.caption_text.insert(tk.END, "Error processing image. Edit manually if needed.")
            self.current_data = {"image": relative_path, "caption": ""}

        self.root.update_idletasks() 
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def save_and_next(self):
        edited_caption = self.caption_text.get("1.0", tk.END).strip()
        self.current_data["caption"] = edited_caption
        self.existing_data.append(self.current_data)
        self.existing_paths.add(self.current_data["image"])
        save_json(self.existing_data)

        self.current_index += 1
        self.process_next_image()

def main():
    root = tk.Tk()
    root.state('zoomed')
    app = ImageReviewApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()