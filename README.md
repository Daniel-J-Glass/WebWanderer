# WebWanderer

This is a Flask application that generates a procedurally-generated website. It uses an AI to generate the content and layout of each page. The website is built using HTML and images that are generated on the fly with ChatGPT and Stable Diffusion.<br>
You can check out the GCP deployed app here (load times are long due to OpenAI API): https://webwanderer.app/

## Installation

To run this application, you will need Python 3 installed on your system. You can install the required Python packages by running:

```
pip install -r requirements.txt
```

Also, you need to fill out the .env with your Dream Booth and OpenAI API keys.

## Usage

To run the application, you can use the following command:

```
python run.py
```

This will start the Flask development server, and you can access the website by navigating to `http://localhost:5000` in your web browser.

The website has two views:

- `/start`: This is the starting screen of the website. It displays a button to start traversing websites.
- `/next_page`: This view generates a new page based on the information from the previous page. It uses ChatGPT and Stable Diffusion to generate the content and layout of the page.

## Demo

https://github.com/Daniel-J-Glass/WebWanderer/assets/38441127/16e4c548-cf65-440a-b429-31a0a95c7250

## Architecture Sketch

![Basic Architecture](https://github.com/Daniel-J-Glass/WebWanderer/blob/main/examples/BasicArchitecture.png)

## License

This project is licensed under the CC BY-NC-ND 4.0 license. See the `LICENSE-CC-BY-NC-ND-4.0.md` file for more information.
