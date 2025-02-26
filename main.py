#! /base/bin/python3

import os
import glob
import base64
from dotenv import load_dotenv # type: ignore
from groq import Groq # type: ignore
import json 
import shutil 
from PIL import Image
from io import BytesIO
from datetime import datetime

load_dotenv()

class CleanScreenShots:
    DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
    ALLOWED_CATEGORIES = ["Meme","Study","Documents","Random","Images"]
    def get_screenshots(self):
        # Patterns like ~/Desktop/Screenshot*.[jpg/png/jpeg]
        patterns = [os.path.join(self.DESKTOP_PATH, f"*Screenshot*.{ext}") for ext in ["png", "jpg", "jpeg"]]
        screenshots = []
        for pattern in patterns:
            screenshots.extend(glob.glob(pattern))
        return screenshots

    # Helper function from ChatGPT
    def compress_resize_image(self, image_path, max_size=2.5 * 1024 * 1024):
        img = Image.open(image_path)
        img.thumbnail((1920, 1080))
        buf = BytesIO()
        ext = os.path.splitext(image_path)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            img.save(buf, format="JPEG", quality=85)
        else:
            img.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    
    def encode_image(self, image_path):
        max_size = 2.5 * 1024 * 1024
        if os.path.getsize(image_path) > max_size:
            return self.compress_resize_image(image_path, max_size)
        else:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")

    def get_mime_type(self, image_path):
        # Creating prefix for base64 data based on file extension type
        ext = os.path.splitext(image_path)[1].lower()
        if ext == ".png":
            return "image/png"
        elif ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        else:
            return "application/octet-stream"

    def categorize_image(self, image_path):
        base64_image = self.encode_image(image_path)
        mime_type = self.get_mime_type(image_path)
        image_data_url = f"data:{mime_type};base64,{base64_image}"

        prompt = f"""Categorize the following image into one of these categories:
          Meme : Generally images with some satirical text or just images that are funny
          Study : Math equations, formulas, experiment results
          Documents: Documents that look like pdf or present some useful information with proper context and are strictly text based.
          Random: Code snippets without any context, or documents without any context. Generally small in length. Also include outdated tickets or invitations
          Images: Images of people that do no count as meme.

          Always return only a JSON object. It should be in the schema:
          
          {{"category": "value"}}

          Make sure the following things about the return:
          Category can only be of values, {self.ALLOWED_CATEGORIES}
          
          The current date is {datetime.today().strftime('%Y-%m-%d')}
        """

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                ],
            }
        ]
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.2-90b-vision-preview",
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
        )
        return chat_completion.choices[0].message.content

    def process_all_screenshots(self):
        screenshots = self.get_screenshots()
        assert screenshots, "No screenshots matched, check screenshot names"
        k = 0
        while k < len(screenshots):
            batch = screenshots[k:k+5]
            for image_path in batch:
                print(f"Processing {image_path}...")
                result = json.loads(self.categorize_image(image_path))
                category = result["category"]
                self.save_to_folders(category, image_path)
            if k + 5 < len(screenshots):
                proceed = input("Do you wish to continue? (y/n): ").strip().lower()
                while proceed not in ["y", "n", "yes", "no"]:
                    print("Invalid input. Please enter 'y' or 'n'.")
                    proceed = input("Do you wish to continue? (y/n): ").strip().lower()
                if proceed in ["n", "no"]:
                    break
            k += 5

    def save_to_folders(self, category, image_path):
        allowed = self.ALLOWED_CATEGORIES + [s.lower() for s in self.ALLOWED_CATEGORIES]
        print(category)
        if category not in allowed:
            raise Exception("Cannot save docs for unknown categories")
        
        output_path = os.path.join(self.DESKTOP_PATH, category)
        os.makedirs(output_path, exist_ok=True)
        output_path = os.path.join(output_path, os.path.basename(image_path))
        shutil.move(image_path, output_path)

if __name__ == "__main__":
    cs = CleanScreenShots()
    cs.process_all_screenshots()
