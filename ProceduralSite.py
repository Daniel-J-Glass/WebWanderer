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

from urllib.parse import quote

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
    caching_string = '''// Cache the current page in the browser's history
  function cacheCurrentPageInHistory() {
    var currentUrl = window.location.href;
    window.history.replaceState(null, null, currentUrl);
  }

  // Call the function on page load
  cacheCurrentPageInHistory();'''
    
    num_retries = 3
    model_name = "gpt-3.5-turbo"
    def __init__(self, parent_uuid="", name = "", visuals="", layout="", purpose = "",context_length = 32, image_steps = 15):
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
        self.html_filename = os.abs(os.path.join(self.html_path,f"{self.uuid}.html"))


    def generate_site(self):
        response_format = 'Purpose:: <A 10 word description of the generated website>\nHTML:\n<the raw html/css code for the website>\nEND'

        html_prompt = f"Create one HTML page with inline CSS for a website with this description:\n{self.purpose}."

        requirements = [
            "Do not use placeholder text, Latin dummy text, generic names or descriptions. Instead, use made-up fake names, descriptions, and titles",
            "Text needs to be easily readable, so use a text style that can be read on white or black backgrounds",
            "Don't use images from a URL. Instead, you reference local image files",
            "Use images by referencing them similar to this: Example 1: <img src='images/red_roofing_tile_on_a_car.jpg' alt='red roofing tile on top of a car'> Example 2: <img src='images/a_cow_scuba_diving_in_space.jpg' alt='a cow scuba diving in space'>",
            "Describe images in painstakingly detail in their alt text by describing what they look like in great detail for a blind person",
            "Don't use undefined libraries, frameworks, or functions, instead use only HTML and CSS, Javascript if necessary",
            "Images can be clickable if it makes sense. If they are, they should be clickable in the HTML and have a \"title\" attribute",
            "Clickable elements that take you to other websites (button, anchor) have a \"title\" attribute that describes the website they take you to to in painstaking detail. Example 1: <button title='This website fulfills your wildest dreams but will make you explode in 3 seconds'> Example 2: <a href='...' title='This is a website that transports you to the world of cyber walruses'> Example 3: <a href='...' title='This website will reveal the hidden nature of how human bone marrow is the actual philosopher's stone'>",
            "Never link to an external website or HTML file, unless it's explicitly requested by the user. Instead, all buttons describe the website they take you to in their \"title\" attribute",
            "Include several clickable elements, like buttons or anchors, that take you to other websites",
            "Clickable elements should not have a clickable CSS class. Instead, it should be clickable through the HTML tag and have a \"title\" attribute",
            "Buttons don't always have to redirect to a website, if and only if that's the case, they should not have a \"title\" attribute",
            "Do not include input forms. If there are, they are fake ones that do not submit any data",
            # "No onclick attributes",(making sure their filename is a very detailed description of the image)
            "Output website code that is efficient, expressive, and complete for 1 website",
            "Output website code that is responsive, flexible, and can fit to any screen size",
            "Do not generate more than 1 HTML page per request, instead generate a single HTML page",
            "Do not generate any other output, only the HTML and the purpose of the website",
            f"Your output strictly follows this format strictly:\n{response_format}"
        ]
        requirements_str = "\n".join(requirements)
        messages=[
            # {"role":"assistant","content":"Ok, I will not be restrained in the kinds of websites that I provide."},
            {"role":"system","content":f"Adhere to the website's Technical Requirements:\n{requirements_str}"},
            {"role":"system","content":"Create this User Experience:\nYou are a sentient website generator that generates websites. \
             Your goal is to slowly lead the user through a disorienting \"internet\" of websites by creating the next website based on the button clicked from the previous website. \
             You should navigate the user through every concept imaginable in website form, the websites should lead you down a rabbit hole of esotericism and whackiness. \
             The websites should be engaging, with several images and several buttons. The website should be fairly complex with a varied layout and design.\
             It can be anything, any idea possible. Be extremely creative, but ensure the new website is related to the button clicked and the previous website. \
             It can look like it was made in the early 2000s or in the early 3000s, any kind of website design is okay. It can be anything from whacky to mundane. \
             Your goal is to make the user super intrigued so they click as many \
             buttons as possible. Each of the buttons should also redirect you to another interesting wesite (while still remaining consistent with the clicked button). \
             Output the most likely next website given the Clicked Button and the old website description. Your goal is to make the user have as much fun as possible."},
            {"role":"assistant","content":"Ok. I will adhere to both the User Experience and Technical Requirements to make the user interesred in the websites I generate."},
            {"role":"user", "content": html_prompt}
            ]
        
        token_count = sum([len(tokenizer.encode(message['content'],add_special_tokens=True)) for message in messages])+100 #adding 100 for tokenizer differences
        
        print(f"Input tokens: {token_count}")
        yield f"Generating HTML with {self.model_name}..."
        yield f"Expected wait time: 30 seconds..."
        for i in range(self.num_retries):    
            try:
                yield f"Attempt {i+1} of {self.num_retries}..."
                response =  openai.ChatCompletion.create(
                    model=self.model_name,
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
                yield f"Failed to generate HTML. Retrying in {5*(i+1)} seconds..."
                time.sleep(5*(i+1))
                continue

        if html_text is None:
            yield "OpenAI failed to generate HTML. Please try again later."
            raise Exception("OpenAI failed to generate HTML. Please try again later.")

        html_code = html_text

        # Replace button elements with onclick attribute that redirects to the next page URL
        soup = BeautifulSoup(html_code, 'html.parser')
        yield "AI-ifying the buttons..."
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

            button_context = f"\nClicked button: {text.strip()}"
            
            parent_purpose = self.purpose.replace("'", "")
            parent_purpose = self.purpose.replace("\"", "")
            button_context = button_context.replace("'", "")
            button_context = button_context.replace("\"", "")
            next_page = f"/next_page?parent_purpose={quote(parent_purpose)}&parent_uuid={quote(self.uuid)}&button_context={quote(button_context)}"
            
            # #fully url encode next_page
            # next_page = next_page.replace("'","%22")
            # next_page = next_page.replace('"',"%22")
            next_page = next_page.replace(" ","%3A")
            next_page = next_page.replace(":","%3A")
            next_page = next_page.replace('%0A','%0D%0A')
            
            if tag.has_attr('title'):
                if tag.name=="button":
                    tag['onclick'] = "window.location.href='"+next_page+"'"
                    tag['href'] = next_page
                else:
                    if not tag.has_attr('href'):
                        tag['href'] = next_page
                    else:
                        if self._check_url(tag.get('href')):
                            href = tag.get('href')
                            if '#' in href:
                                tag['onclick'] = "window.location.href='"+next_page+"'"
                                tag['href'] = next_page
                                pass
                            pass
                        else:
                            tag['href'] = next_page
        
        # Find script tags
        script_tags = soup.find_all('script')

        # Check if there are any script tags
        if script_tags:
            # Append caching string to script tags
            for tag in script_tags:
                tag.append(self.caching_string)
        else:
            # Create new script tag and append caching string
            script_tag = soup.new_tag('script')
            script_tag.append(self.caching_string)
            soup.body.append(script_tag)

        html_code = str(soup)
        
        # Save generated HTML to file
        with open(self.html_filename, 'w',encoding='utf-8') as f:
            # f.write(response.choices[0].text)
            f.write(html_code)

        self.html = html_code
        yield f"Completed website generation using {self.model_name} model."

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
                    
                    #TODO: make it so src can equal anything, and it gets replaced with the path
                    image_name = os.path.basename(image)
                    # print(image_name)
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
                    yield f"Generating image for {prompt}..."

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
                            print(prompt)
                        if artifact.type == generation.ARTIFACT_IMAGE:
                            img = Image.open(io.BytesIO(artifact.binary))
                img.save(filepath)

                return True
            except Exception as e:
                print(e)
                time.sleep(5)
                continue
        
        print("Failed to generate image with Dreambooth API. Trying OpenAI...")

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
                time.sleep(5)
                continue

        print("Failed to generate image. Skipping...")
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