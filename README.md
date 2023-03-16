# WebWanderer

This is a Flask application that generates a procedurally-generated website. It uses an AI to generate the content and layout of each page. The website is built using HTML and images that are generated on the fly with ChatGPT and Stable Diffusion

## Installation

To run this application, you will need Python 3 installed on your system. You can install the required Python packages by running:

```
pip install -r requirements.txt
```

## Usage

To run the application, you can use the following command:

```
python run.py
```

This will start the Flask development server, and you can access the website by navigating to `http://localhost:5000` in your web browser.

The website has two views:

- `/start`: This is the starting screen of the website. It displays a button to start traversing websites.
- `/next_page`: This view generates a new page based on the information from the previous page. It uses an AI to generate the content and layout of the page.

## Screenshots

You can see some examples of the procedurally-generated website below:

![Example 1](https://github.com/Daniel-J-Glass/WebWanderer/blob/main/examples/StartScreen.png)

![Example 2](https://github.com/Daniel-J-Glass/WebWanderer/blob/main/examples/example1.png)

![Example 3](https://github.com/Daniel-J-Glass/WebWanderer/blob/main/examples/example2.png)

## License

This project is licensed under the CC BY-NC-ND 4.0 license. See the `LICENSE-CC-BY-NC-ND-4.0.md` file for more information.
