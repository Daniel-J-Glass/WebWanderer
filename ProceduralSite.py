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
    
    def __init__(self, parent_uuid="", name = "", visuals="", layout="", purpose = "", context_length = 32, image_steps = 20):
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
        self.html_filename = os.path.join(self.html_path,f"{self.uuid}.html")


    def generate_site(self):
        # Initialize OpenAI Codex API
        
        #   The more weight an attribute has, the more the website will be styled like that attribute. The attributes are loose and should only slightly contribute to the website, so you can still get creative. Don't be so literal about the attributes, just make it loosely like them. It should only effect the purpose a little bit, visuals, and layout:\n\
        #   Attributes: surreal:.01,trippy:.01,unique:.1,shopping:-.2,early_internet_style:.05,deep_internet:.05,esoteric:.05,colorful:.05,parallel_reality:.05,any_other_topic:.5\n\

        response_format = 'Purpose:\n<the new website purpose>\n\nHTML:\n<the html/css code>'

        html_prompt = f"Create HTML code with inline CSS where {self.purpose}\nDesign an imaginative website with a \
flexible layout, applicable visuals, and a consistent style aligned with the site's purpose. \nInclude a website background, images, and multiple buttons to other places, \
that fit the new website. \nImages can also serve as buttons, if appropriate surround them with an anchor tag. \nProvide the destination website generated from the clicked button. \
The new website's purpose should be described great detail in the output, but it should have something extra to it (any idea imaginable).\
\nOutput in this format without any other output:\n\n{response_format}\
\n\nRemember to follow the previous listed requirements."

        requirements = [
            "IMPORTANT!!!!: Don't use placeholder text. Don't use Latin dummy text.",
            "Real fake names, descriptions, and titles",
            "Painstaking detailed alt text for images describing what they look like",
            "Images are always referenced in this format: <image_description.jpg>, unique filenames",
            "Image paths are always in quotes",
            "Image references ALWAYS end in .jpg",
            "No undefined functions",
            "There needs to be at least 3 buttons",
            "Make sure clickable elements are defined in the HTML code",
            "IMPORTANT!!!!!: Butttons do not redirect to a new website, unless the website URL is explicitly provided.",
            "IMPORTANT: Don't redirect to HTML files",
            "No onclick attributes",
            "Efficient, expressive, and complete code for a complex website",
            "The website and all elements should fit on the screen",
            "IMPORTANT!!!!: All clickable elements (button, anchor) have a title attribute that describe the purpose of the website they link to in painstaking detail. Example: title='This is a website that ... and will ...' something like that with a lot of detail",
            "IMPORTANT!!!: Do not generate more than 1 html script.",
            f"IMPORTANT!!!!:The output strictly follows this format verbatim:\n\n{response_format}"
        ]
        requirements_str = "\n".join(requirements)
        messages=[
            {"role":"system","content":"You are a sentient and slightly surreal program that generates a seemingly real website. You can sometimes communicate \
             with the website user. The website should be slightly schizophrenic. Your goal is to slowly lead the user through a labrynth of websites \
             by slightly changing the meaning from the previous website to the new website after clicking a button. These website can be of any random topic imaginable. \
             It can be esoteric, surreal, occult, normal, boring, fantastic, thought provoking, annoying, crazy, anything. Get creative, but only change the website purpose slightly. \
             It should look like it was made in the 2000s. It should be a slightly random website that's informed by \
             the Clicked button. You should do what the Clicked button says. You should make the user want to click more buttons through curiosity. Your goal is to keep the user clicking buttons."},
            # {"role":"assistant","content":"Ok, I will not be restrained in the kinds of websites that I provide."},
            {"role":"system","content":f"Requirements:\n{requirements_str}"},
            {"role":"assistant","content":"Ok, I will all of those requirements."},
            {"role":"user", "content": html_prompt}
            ]
        
        token_count = sum([len(tokenizer.encode(message['content'],add_special_tokens=True)) for message in messages])+100 #adding 100 for tokenizer differences
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
        print(f"New Purpose: {self.purpose}")
        html_text = re.search(r"<!DOCTYPE html>(?:.*\n)*<\/html>", response_text, re.DOTALL).group()

        print(f"Input tokens: {token_count}")
        print(f"Output tokens: {len(tokenizer.encode(response_text))}")

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
                # tag['href'] = next_page
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
        image_regex = r"([\"\'\(](?:[/\\\w \:\-\.]*)\.(?:jpg|jpeg|png|gif|svg)[\"\'\)])"
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
                    if "alt" in image_line:
                        content = re.search(alt_regex,image_line).group(1)
                        if "title" in image_line:
                            content+=re.search(title_regex,image_line).group(1)
                    else:
                        content = os.path.splitext(image_name)[0]

                    image_id = str(uuid.uuid4())[:8]
                    image_filepath = 'static/'+'images/'+f"{image_id}.png"
                    html_code = html_code.replace(image,"'"+image_filepath+"'")

                    prompt = f"{content.strip()} for a website with this purpose {self.purpose}"

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

        for i in range(2):
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
                            warnings.warn(
                                "Your request activated the API's safety filters and could not be processed."
                                "Please modify the prompt and try again.")
                            print(prompt)
                        if artifact.type == generation.ARTIFACT_IMAGE:
                            img = Image.open(io.BytesIO(artifact.binary))
                img.save(filepath)

                return True
            except Exception as e:
                print(e)
                print("Retrying...")
        
        
        return False

    def _check_url(self, url):
        try:
            response = requests.get(url)
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