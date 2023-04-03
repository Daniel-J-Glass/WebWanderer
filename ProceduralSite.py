import os
import io
import re
import json
import concurrent.futures
import warnings
import time,random

import uuid
import requests

import openai
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

from PIL import Image

from flask import Flask,url_for,current_app
import urllib.parse

from dotenv import load_dotenv
load_dotenv()

from bs4 import BeautifulSoup

from transformers import GPT2Tokenizer
tokenizer = GPT2Tokenizer.from_pretrained('gpt2-xl')

app = Flask(__name__)

# OpenAI API keys
OPENAI_API_KEY = os.environ.get('OPENAI_KEY')
openai.api_key = OPENAI_API_KEY

model_endpoint = "https://api.openai.com/v1/chat/gpt-3.5-turbo"

SD_KEY = os.environ.get('SD_KEY')
stability_api = client.StabilityInference(
    key=SD_KEY, 
    verbose=True,
)

class ProceduralSite:
    '''
    TODO: Check for parent UUID in database, redirect to current if not.
    TODO: 
    '''
    num_retries = 3
    def __init__(self, parent_uuid="", name = "", visuals="", layout="", purpose = "", context_length = 32, image_steps = 15):
        # Database storage procedure
        
        self.name = name
        self.visuals = visuals
        self.layout = layout.format(self.name)
        self.purpose = purpose
        self.context_length = context_length
        self.image_steps = image_steps

        self.html = None
        self.css = None
        self.images = None

        self.html_path = app.template_folder
        self.css_path = os.path.join(app.static_folder,'css')
        self.image_path = os.path.join(app.static_folder,'images')

        #post self to firebase, get uuid return
        #self.uuid = 
        self.uuid = str(uuid.uuid4())[:8] 
        self.html_filename = self.html_path+'/'+f"{self.uuid}.html"


    def generate_site(self):
        response_format = 'Purpose:: <A 15 word description of the generated website>\nHTML:\n<the raw html/css code for the website>\nEND'

        html_prompt = f"Create an HTML code with inline CSS for a website with this description:\n{self.purpose}."

        requirements = [
            "No placeholder text or Latin dummy text. Instead, use generated fake names, descriptions, and titles",
            "No using images from a URL. Instead, you reference local image files",
            "Use images by referencing them similar to this: Example 1: <img src='images/red_roofing_tile_on_a_car.jpg' alt='red roofing tile on top of a car'> Example 2: <img src='images/a_cow_scuba_diving_with_an_octopus.jpg' alt='a cow scuba diving with an octopus'>",
            "Describe images in painstakingly detail in their alt text, describing what they look like for a someone who can't see",
            "Don't use undefined libraries, frameworks, or functions, instead use only HTML and CSS, Javascript if necessary",
            "Images can be clickable, but only if they are relevant to the website's purpose",
            "All clickable elements (button, anchor) have a \"title\" attribute that describes the purpose of the website they link to in painstaking detail. Example 1: <button title='This is a website that fulfills your wildest dreams and will make you explode in 3 seconds'> Example 2: <a href='...' title='This is a website that transports you to the world of cyber walruses'>",
            "Buttons never direct to an external website or HTML files, unless it's explicitly provided by the user. Instead, all buttons describe the website they take you to in their \"title\" attribute",
            "Include at least 3 buttons that link to other websites",
            "If inline CSS makes something seem clickable, it should be clickable in the HTML and have a \"title\" attribute",
            "If there're any input fields, they should be fake and not actually do anything",
            # "No onclick attributes",(making sure their filename is a very detailed description of the image)
            "Output website code that is efficient, expressive, and complete for a website",
            "Output website code that is responsive and fit on any screen size",
            "Do not generate more than 1 HTML page per request",
            "Do not generate any other output, only the HTML and the purpose of the website",
            f"Your output strictly follows this format strictly:\n{response_format}"
        ]
        requirements_str = "\n".join(requirements)
        messages=[
            {"role":"system","content":"Cater to this User Experience:\nYou are a sentient program that generates a seemingly real website. You can sometimes communicate \
             with the website user through html text and images. Your goal is to slowly lead the user through a disorienting \"internet\" of websites \
             by creating the next website based on the button clicked from the previous website. The websites should be eye catching, with images and several buttons.\
             It can be anything, any idea possible. Get extremely creative, but ensure the new website is based on the button clicked and the previous website. \
             It can look like it was made in the early 2000s or the distant future or anywhere in between. Your goal is to make the user want to click as many \
             buttons as possible, so each of the buttons should also redirect you to another interesting part of the websites (while still remaining consistent with the clicked button). \
             The website purpose should be a cohesive synthesis of the website described by the Clicked Button. Your goal is to keep the user clicking buttons forever."},
            # {"role":"assistant","content":"Ok, I will not be restrained in the kinds of websites that I provide."},
            {"role":"system","content":f"Adhere to the website's Technical Requirements:\n{requirements_str}"},
            {"role":"assistant","content":"Ok. I will adhere to both the User Experience and Technical Requirements."},
            {"role":"user", "content": html_prompt}
            ]
        
        token_count = sum([len(tokenizer.encode(message['content'],add_special_tokens=True)) for message in messages])+100 #adding 100 for tokenizer differences
        print(f"Input tokens: {token_count}")

        for i in range(self.num_retries):    
            try:
                print("Generating HTML")
                response =  openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages = messages,
                    max_tokens=4096 - token_count,
                    n=1,
                    temperature=0.7,
                )
                response_text = response.choices[0].message.content.strip()
                # print(response_text)

                self.purpose = re.search(r"(?:Purpose:\s*)([\s\S]+?)(?=\s*HTML\s*)",response_text).group(1)
                html_text = re.search(r"<!DOCTYPE html>(?:.*\n)*<\/html>", response_text, re.DOTALL).group()
                print(f"New Purpose: {self.purpose}")
                print(f"Output tokens: {len(tokenizer.encode(response_text))}")
                break
            except Exception as e:
                print(e)
                time.sleep(5*i+1)
                continue

        html_code = html_text

        # Replace button elements with onclick attribute that redirects to the next page URL
        soup = BeautifulSoup(html_code, 'html.parser')
        for tag in soup.find_all(['a', 'button', 'input','img']):
            #add seperator for parent N's purpose and trim based on context variable
            if tag.has_attr('alt'):
                text = str(tag.get('alt'))
            elif tag.has_attr('title'):
                text = str(tag.get('title'))
            else:
                text = tag.text.strip()
            # Modify text to be the context length surroundings in the html
            # Get the tag's parent and following siblings
            parent = tag.find_parent()
            siblings = parent.find_next_siblings()

            # # Concatenate text from the parent and siblings
            # context = f"Context:\n{str(parent.text.strip())}"
            # # context += "\nContext:"
            # # for sib in siblings:
            # #     if sib.has_attr('alt'):
            # #         context+=f"{sib.get('alt').strip()}, "
            # #     context += f"{str(sib.text.strip())}, "

            # # Trim text to context length
            # encoded_text = tokenizer.encode(context)
            # if len(encoded_text) > self.context_length:
            #     context = tokenizer.decode(encoded_text[:self.context_length])

            context = f"\nClicked button: {text.strip()}"

            next_page = url_for('next_page', parent_purpose=self.purpose.replace("'",""), parent_uuid=self.uuid, button_context=context.replace("'",""))
            # next_page = next_page.replace("'","\\'")
            next_page = next_page.replace('%0A','%0D%0A')
            if tag.name=="button":
                tag['onclick'] = "window.location.href= '"+next_page+"' "
                tag['href'] = next_page
            else:
                if not tag.has_attr('href'):
                    tag['href'] = next_page
                else:
                    if self._check_url(tag.get('href')):
                        pass
                    else:
                        tag['href'] = next_page
        
        html_code = str(soup)

        #TODO: Fix <div class=clickable> based on css to include <a> and href

        # Save generated HTML to file
        with open(self.html_filename, 'w',encoding='utf-8') as f:
            # f.write(response.choices[0].text)
            f.write(html_code)

        self.html = html_code

    def generate_assets(self):
        html_code = self.html
        
        # print(f"HTML:\n{html_code}")

        # Regex for any image file
        image_regex = r"[\"\'\(]+((?:[/\\\w \:\-\.]*)\.(?:jpg|jpeg|png|gif|svg))[\"\'\)]+"
        image_line_regex = r"(.*(?:[^\"\'<=]+\.(?:jpg|jpeg|png|gif|svg))[\"\'\s>]?.*)"
        alt_regex = r"alt\s*=\s*[\'\"]?([^\'\">]+)[\'\"]?"
        title_regex = r"title\s*=\s*[\'\"]?([^\'\">]+)[\'\"]?"
        
        image_lines = re.findall(image_line_regex,html_code)

        # Parallel Execution
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []

            for image_line in image_lines:
                images = re.findall(image_regex,image_line)
                # print(f"Image Line:\n{image_line}")
                for image in images:
                    # print(f"Image:\n{image}")
                    #TODO: make it so src can equal anything, and it gets replaced with the path
                    image_name = os.path.basename(image)
                    print(image_name)
                    try:
                        if "alt" in image_line:
                            content = re.search(alt_regex,image_line).group(1)
                            if "title" in image_line:
                                if re.match(title_regex,image_line):
                                    content+=re.search(title_regex,image_line).group(1)
                        else:
                            content = os.path.splitext(image_name)[0]
                    except:
                        continue

                    image_id = str(uuid.uuid4())[:8]
                    image_filepath = 'static/'+'images/'+f"{image_id}.png"
                    html_code = html_code.replace(image,image_filepath)

                    prompt = content.strip()

                    futures.append(executor.submit(self.generate_image, prompt, image_filepath))

            for future in concurrent.futures.as_completed(futures):
                success = future.result()
                if not success:
                    # Maybe catch failure
                    continue

        with open(self.html_filename, 'w',encoding='utf-8') as f:
            f.write(html_code)
        self.html=html_code

    def generate_image(self, prompt, filepath):
        """takes in prompt and filename and saves generated image to filename

        Args:
            prompt (str): image generation prompt
            filename (str): path to save image to

        Returns:
            bool : returns success or failure
        """
        print(f"Generating image for {prompt}...")
        for i in range(self.num_retries):
            time.sleep(random.randint(0, 2))
            try:
                answers = stability_api.generate(
                    prompt=prompt,
                    steps=self.image_steps, # defaults to 30 if not specified
                    
                )
                # iterating over the generator produces the api response
                for resp in answers:
                    for artifact in resp.artifacts:
                        if artifact.finish_reason == generation.FILTER:
                            print("Your request activated the API's safety filters and could not be processed. Please modify the prompt and try again.")
                            print(prompt)
                        if artifact.type == generation.ARTIFACT_IMAGE:
                            img = Image.open(io.BytesIO(artifact.binary))
                img.save(filepath)

                return True
            except Exception as e:
                print(e)
                time.sleep(5)
                print("Retrying...")
                continue
        
        print("Failed to generate image. Trying OpenAI...")

        for _ in range(self.num_retries):
            # backup image generation
            try:
                #generate an image using dalle2 with prompt
                response = openai.Image.create(
                    prompt=prompt,
                    n=1,
                    size="256x256",
                )

                url = response["data"][0]["url"]

                #download image
                response = requests.get(url)
                img = Image.open(io.BytesIO(response.content))
                img.save(filepath)
                
                return True
            except Exception as e:
                print(e)
                print("Retrying...")
                continue

        print("Failed to generate images. Skipping...")
        return False

    def _check_url(self, url):
        try:
            response = requests.get(url)
            print(response.status_code)
            if response.status_code == 200:
                return True
            else:
                return False
        except requests.exceptions.RequestException as e:
            return False

def test_procedural_site():
    # Create ProceduralSite instance
    site = ProceduralSite("My Website", "modern", "responsive", "A portfolio website to show my skills in aesthetic html, complete with buttons and links to my other projects")

    # Generate site HTML
    site.generate_site()

    # Generate site assets
    site.generate_assets()

    # Check that the generated HTML file exists
    assert os.path.isfile(site.html_filename)


if __name__=="__main__":
    test_procedural_site()