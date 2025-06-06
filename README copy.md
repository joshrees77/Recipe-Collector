# Recipe Collector

A web application that allows users to collect and organize recipes from various websites. The app scrapes recipe information from provided URLs and presents it in a clean, consistent format while maintaining attribution to the original source.

## Features

- Paste recipe URLs to automatically extract ingredients and instructions
- Clean, consistent formatting for all recipes
- Public website to share your recipe collection
- Proper attribution to original sources
- Persistent storage of all recipes

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

4. Run the development server:
```bash
flask run
```

The application will be available at `http://localhost:5000`

## Usage

1. Visit the homepage
2. Paste a recipe URL into the input field
3. Click "Add Recipe" to scrape and store the recipe
4. View all your collected recipes on the public page

## Technologies Used

- Backend: Flask (Python)
- Database: SQLite with SQLAlchemy
- Frontend: HTML, CSS, JavaScript
- Recipe Scraping: BeautifulSoup4, recipe-scrapers 