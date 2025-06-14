from flask import Flask, render_template, request, jsonify, redirect, url_for, abort, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse
import re
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import subprocess
from flask_migrate import Migrate  # Import Migrate
from PIL import Image # Import Image from Pillow
load_dotenv()

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Create Flask app first
app = Flask(__name__)

# Get the absolute path for the database file in the instance folder
DB_PATH = os.path.join(app.instance_path, 'recipes.db')
DB_URI = f'sqlite:///{DB_PATH}'

# Configure the app
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', DB_URI)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.environ.get('SECRET_KEY', 'devsecret')  # Set a strong secret in production

# Print current working directory and database URI for debugging
print(f"Current working directory: {os.getcwd()}")
print(f"Instance path: {app.instance_path}")
print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
print(f"Database path: {DB_PATH}")

# Ensure the instance directory exists
if not os.path.exists(app.instance_path):
    print(f"Creating instance directory: {app.instance_path}")
    os.makedirs(app.instance_path, exist_ok=True)

db = SQLAlchemy(app)

migrate = Migrate(app, db)  # Initialize Flask-Migrate

class Recipe(db.Model):
    __tablename__ = 'recipe'  # Explicitly set table name
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    source_url = db.Column(db.String(500), nullable=False)
    source_name = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    my_comment = db.Column(db.Text, nullable=True)  # New field for your personal comment

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'ingredients': self.ingredients.split('\n'),
            'instructions': self.instructions.split('\n'),
            'source_url': self.source_url,
            'source_name': self.source_name,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat(),
            'my_comment': self.my_comment,
        }

# Initialize the database after all models are defined
with app.app_context():
    try:
        print(f"Checking database at: {DB_PATH}")
        
        # Check if we can write to the directory
        if os.access(app.instance_path, os.W_OK):
            print(f"Directory {app.instance_path} is writable")
        else:
            print(f"WARNING: Directory {app.instance_path} is NOT writable!")
        
        # Only create tables if they don't exist
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print(f"Existing tables: {existing_tables}")
        
        if 'recipe' not in existing_tables:
            print("Creating missing tables...")
            db.create_all()
            # Verify tables were created
            tables = inspector.get_table_names()
            print(f"Tables after creation: {tables}")
        else:
            print("All required tables exist, no need to create them")
            
    except Exception as e:
        print(f"Error checking/initializing database: {str(e)}")
        raise

ADMIN_PASSWORD = os.environ.get('RECIPE_ADMIN_PASSWORD', 'changeme')  # Set in your environment for security

def get_domain_name(url):
    parsed_uri = urlparse(url)
    return parsed_uri.netloc

def extract_recipe(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find the title
        title = None
        title_candidates = [
            soup.find('h1'),  # Most common
            soup.find('title'),  # Fallback
            soup.find(class_=re.compile(r'title|recipe-title|recipe-name', re.I)),
            soup.find(id=re.compile(r'title|recipe-title|recipe-name', re.I))
        ]
        for candidate in title_candidates:
            if candidate and candidate.text.strip():
                title = candidate.text.strip()
                break
        
        if not title:
            title = "Untitled Recipe"

        # --- IMPROVED INGREDIENT EXTRACTION ---
        ingredients = []
        seen = set()
        # Find all parents with 'ingredient' in class or id
        ingredient_parents = soup.find_all(
            lambda tag: (
                tag.name in ['ul', 'ol', 'div', 'section'] and (
                    (tag.has_attr('class') and any('ingredient' in c.lower() for c in tag['class'])) or
                    (tag.has_attr('id') and 'ingredient' in tag['id'].lower())
                )
            )
        )
        for parent in ingredient_parents:
            for li in parent.find_all('li', recursive=True):
                text = ' '.join(li.stripped_strings)
                # Remove leading checkbox/bullet characters and whitespace
                text = re.sub(r'^[\s\u25A0-\u25FF\u2022\u25CB\u25CF\u25A1\u25A3\u25A4\u25A5\u25A6\u25A7\u25A8\u25A9\u25AA\u25AB\u25AC\u25AD\u25AE\u25AF\u25B0\u25B1\u25B2\u25B3\u25B4\u25B5\u25B6\u25B7\u25B8\u25B9\u25BA\u25BB\u25BC\u25BD\u25BE\u25BF\u25C0\u25C1\u25C2\u25C3\u25C4\u25C5\u25C6\u25C7\u25C8\u25C9\u25CA\u25CB\u25CC\u25CD\u25CE\u25CF\u25D0\u25D1\u25D2\u25D3\u25D4\u25D5\u25D6\u25D7\u25D8\u25D9\u25DA\u25DB\u25DC\u25DD\u25DE\u25DF\u25E0\u25E1\u25E2\u25E3\u25E4\u25E5\u25E6\u25E7\u25E8\u25E9\u25EA\u25EB\u25EC\u25ED\u25EE\u25EF\u25A0\u25A1\u25A2\u25A3\u25A4\u25A5\u25A6\u25A7\u25A8\u25A9\u25AA\u25AB\u25AC\u25AD\u25AE\u25AF\u25B0\u25B1\u25B2\u25B3\u25B4\u25B5\u25B6\u25B7\u25B8\u25B9\u25BA\u25BB\u25BC\u25BD\u25BE\u25BF\u25C0\u25C1\u25C2\u25C3\u25C4\u25C5\u25C6\u25C7\u25C8\u25C9\u25CA\u25CB\u25CC\u25CD\u25CE\u25CF\u25D0\u25D1\u25D2\u25D3\u25D4\u25D5\u25D6\u25D7\u25D8\u25D9\u25DA\u25DB\u25DC\u25DD\u25DE\u25DF\u25E0\u25E1\u25E2\u25E3\u25E4\u25E5\u25E6\u25E7\u25E8\u25E9\u25EA\u25EB\u25EC\u25ED\u25EE\u25EF\u2022\-]+', '', text)
                text = text.strip()
                # Filter: skip if line contains multiple ▢ or | (summary lines)
                if text.count('▢') > 1 or '|' in text:
                    continue
                if len(text.split()) < 2:
                    continue
                if text in seen:
                    continue
                if re.fullmatch(r'[^a-zA-Z0-9]+', text):
                    continue
                seen.add(text)
                ingredients.append(text)
        # Fallback: if nothing found, try old method
        if not ingredients:
            fallback_uls = soup.find_all('ul')
            for ul in fallback_uls:
                for li in ul.find_all('li', recursive=False):
                    text = ' '.join(li.stripped_strings)
                    if len(text.split()) < 2 or text in seen:
                        continue
                    seen.add(text)
                    ingredients.append(text)
        # --- END IMPROVED INGREDIENT EXTRACTION ---

        # Function to clean instruction text
        def clean_instruction(text):
            text = re.sub(r'^[•▢\d\.\s]+', '', text)
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            return text

        # Try to find instructions
        instructions = []
        seen_instructions = set()
        instruction_candidates = [
            soup.find_all(class_=re.compile(r'instruction|directions|steps|method', re.I)),
            soup.find_all(id=re.compile(r'instruction|directions|steps|method', re.I)),
            soup.find_all(['ol', 'ul'], class_=re.compile(r'steps|instructions', re.I))
        ]
        for candidate_list in instruction_candidates:
            if candidate_list:
                for item in candidate_list:
                    if isinstance(item, str):
                        text = clean_instruction(item)
                    else:
                        text = ' '.join(item.stripped_strings)
                        text = clean_instruction(text)
                    if text and len(text) > 3 and text not in seen_instructions:
                        if not text.lower().startswith(('instructions', 'instruction', 'directions', 'steps', 'crispy sage')):
                            instructions.append(text)
                            seen_instructions.add(text)
                if instructions:
                    break
        if not instructions:
            for list_elem in soup.find_all(['ol', 'ul']):
                items = list_elem.find_all('li')
                if len(items) >= 3:
                    for item in items:
                        text = clean_instruction(item.get_text(strip=True, separator=' '))
                        if text and text not in seen_instructions:
                            instructions.append(text)
                            seen_instructions.add(text)
                    if instructions:
                        break
        if not ingredients or not instructions:
            raise ValueError("Could not extract recipe information from this page")
        return {
            'title': title,
            'ingredients': '\n'.join(ingredients),
            'instructions': '\n'.join(instructions)
        }
    except requests.RequestException as e:
        raise ValueError(f"Could not access the website: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing the recipe: {str(e)}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def crop_to_square(filepath):
    try:
        img = Image.open(filepath)
        width, height = img.size

        # Calculate the size of the square crop
        new_size = min(width, height)

        # Calculate cropping box
        left = (width - new_size) / 2
        top = (height - new_size) / 2
        right = (width + new_size) / 2
        bottom = (height + new_size) / 2

        # Crop the image
        img_cropped = img.crop((left, top, right, bottom))

        # Save the cropped image, overwriting the original
        img_cropped.save(filepath)
        print(f"Image cropped to square: {filepath}")
    except Exception as e:
        print(f"Error cropping image {filepath}: {e}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Incorrect password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/')
def home():
    all_recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
    return render_template('recipes.html', recipes=all_recipes, logged_in=session.get('logged_in', False))

@app.route('/add', methods=['GET'])
def index():
    return render_template('index.html', logged_in=session.get('logged_in', False))

@app.route('/recipes')
def recipes():
    all_recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
    return render_template('recipes.html', recipes=all_recipes, logged_in=session.get('logged_in', False))

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    return render_template('recipe_detail.html', recipe=recipe, logged_in=session.get('logged_in', False))

# Function to attempt to commit and push the database file
def commit_and_push_db():
    try:
        # Get the actual database path from SQLAlchemy
        db_path = db.engine.url.database
        if db_path == ':memory:':
            print("Database is in-memory, cannot commit")
            return
            
        # Convert relative path to absolute if needed
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
            
        print(f"Looking for database at: {db_path}")
        
        if not os.path.exists(db_path):
            print(f"Database file not found at {db_path}")
            return

        # Get the directory containing the database
        project_root = os.path.dirname(db_path)
        print(f"Using project root: {project_root}")

        try:
            # Change to the project root directory before running git commands
            original_dir = os.getcwd()
            print(f"Current directory before change: {original_dir}")
            os.chdir(project_root)
            print(f"Changed to directory: {os.getcwd()}")
            
            try:
                # Check if we're in a git repository
                try:
                    subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                                 capture_output=True, check=True)
                except subprocess.CalledProcessError:
                    print("Not in a git repository. Initializing...")
                    subprocess.run(['git', 'init'], check=True)
                    subprocess.run(['git', 'remote', 'add', 'origin', 
                                  'https://github.com/joshrees77/Recipe-Collector.git'], check=True)
                
                # Get all branches
                branch_result = subprocess.run(['git', 'branch', '-a'], 
                                             capture_output=True, text=True, check=True)
                print("Available branches:")
                print(branch_result.stdout)
                
                # Check if we're in detached HEAD state
                head_result = subprocess.run(['git', 'symbolic-ref', 'HEAD'], 
                                           capture_output=True, text=True)
                if head_result.returncode != 0:
                    print("In detached HEAD state. Checking out main branch...")
                    # Try to checkout main branch, create it if it doesn't exist
                    try:
                        subprocess.run(['git', 'checkout', 'main'], check=True)
                    except subprocess.CalledProcessError:
                        print("Creating main branch...")
                        subprocess.run(['git', 'checkout', '-b', 'main'], check=True)
                
                # Verify we're on main branch
                current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                              capture_output=True, text=True, check=True).stdout.strip()
                print(f"Current branch: {current_branch}")
                
                if not current_branch:
                    print("Still not on a branch. Creating and switching to main...")
                    subprocess.run(['git', 'checkout', '-b', 'main'], check=True)
                    current_branch = 'main'
                
                status_result = subprocess.run(['git', 'status'], 
                                             capture_output=True, text=True, check=True)
                print("Git status:")
                print(status_result.stdout)
                
                # Ensure git is initialized and configured
                print(f"Adding database file: {db_path}")
                subprocess.run(['git', 'add', db_path], check=True)
                
                # Check what's being committed
                diff_result = subprocess.run(['git', 'diff', '--cached'], 
                                           capture_output=True, text=True, check=True)
                print("Changes to be committed:")
                print(diff_result.stdout)
                
                result = subprocess.run(['git', 'commit', '-m', 'Update recipes database'], 
                                      capture_output=True, text=True, check=True)
                print("Commit result:")
                print(result.stdout)

                # Check if there was anything to commit
                if "nothing to commit" in result.stdout.lower():
                    print("No database changes to commit.")
                else:
                    print("Changes detected, pushing to remote...")
                    # Get remote info
                    remote_result = subprocess.run(['git', 'remote', '-v'], 
                                                 capture_output=True, text=True, check=True)
                    print("Remote repositories:")
                    print(remote_result.stdout)
                    
                    # Push with verbose output
                    push_result = subprocess.run(['git', 'push', '-u', 'origin', current_branch], 
                                               capture_output=True, text=True, check=True)
                    print("Push result:")
                    print(push_result.stdout)
                    print("Successfully committed and pushed database.")

            finally:
                # Always change back to the original directory
                os.chdir(original_dir)
                print(f"Changed back to directory: {os.getcwd()}")

        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
            print(f"Command: {e.cmd}")
            print(f"Exit code: {e.returncode}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
        except FileNotFoundError:
            print("Git command not found. Is Git installed on the server?")
        except Exception as e:
            print(f"An error occurred during git operations: {e}")

    except Exception as e:
        print(f"Error in commit_and_push_db: {str(e)}")

@app.route('/add_recipe', methods=['POST'])
def add_recipe():
    if not session.get('logged_in'):
        abort(403)
    
    url = request.form.get('url')
    my_comment = request.form.get('my_comment')
    image_url = None

    # Handle file upload
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # Ensure unique filename
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(filepath):
                filename = f"{base}_{counter}{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                counter += 1
            file.save(filepath)
            crop_to_square(filepath) # Crop the image after saving
            image_url = filename

    try:
        if url:
            # URL scraping mode
            recipe_data = extract_recipe(url)
            recipe = Recipe(
                title=recipe_data['title'],
                ingredients=recipe_data['ingredients'],
                instructions=recipe_data['instructions'],
                source_url=url,
                source_name=get_domain_name(url),
                image_url=image_url if image_url else None,
                my_comment=my_comment
            )
        else:
            # Manual entry mode
            title = request.form.get('title')
            ingredients = request.form.get('ingredients')
            instructions = request.form.get('instructions')
            source_name = request.form.get('source_name')
            source_url = request.form.get('source_url', '')  # Optional

            if not all([title, ingredients, instructions, source_name]):
                return jsonify({'error': 'Missing required fields'}), 400

            recipe = Recipe(
                title=title,
                ingredients=ingredients,
                instructions=instructions,
                source_url=source_url if source_url else '',
                source_name=source_name,
                image_url=image_url if image_url else None,
                my_comment=my_comment
            )

        db.session.add(recipe)
        db.session.commit()
        
        # Attempt to commit and push DB file
        commit_and_push_db()

        return redirect(url_for('recipes'))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if not session.get('logged_in'):
        abort(403)
    recipe = Recipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    flash('Recipe deleted.', 'info')
    return redirect(url_for('recipes'))

@app.route('/api/recipes')
def api_recipes():
    recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
    return jsonify([recipe.to_dict() for recipe in recipes])

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/edit_image/<int:recipe_id>', methods=['GET', 'POST'])
def edit_image(recipe_id):
    if not session.get('logged_in'):
        abort(403)
    recipe = Recipe.query.get_or_404(recipe_id)
    if request.method == 'POST':
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(filepath):
                    filename = f"{base}_{counter}{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    counter += 1
                file.save(filepath)
                crop_to_square(filepath) # Crop the image after saving
                recipe.image_url = filename
                db.session.commit()
                flash('Image updated.', 'success')
                return redirect(url_for('recipe_detail', recipe_id=recipe.id))
        flash('Invalid file or no file selected.', 'danger')
    return render_template('edit_image.html', recipe=recipe)

@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if not session.get('logged_in'):
        abort(403)
    recipe = Recipe.query.get_or_404(recipe_id)
    if request.method == 'POST':
        recipe.title = request.form.get('title', recipe.title)
        recipe.ingredients = request.form.get('ingredients', recipe.ingredients)
        recipe.instructions = request.form.get('instructions', recipe.instructions)
        recipe.my_comment = request.form.get('my_comment', recipe.my_comment)
        db.session.commit()
        flash('Recipe updated.', 'success')
        return redirect(url_for('recipe_detail', recipe_id=recipe.id))
    return render_template('edit_recipe.html', recipe=recipe, logged_in=session.get('logged_in', False))

if __name__ == '__main__':
    app.run(debug=True, port=8080) 