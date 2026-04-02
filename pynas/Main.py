from flask import Flask, request, send_from_directory, render_template, redirect, url_for
import os
import markdown
import shutil

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

VIDEO_EXTENSIONS = {'.mp4', '.webm', '.ogg'}

def get_readme_content(full_path):
    readme_path = os.path.join(full_path, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return markdown.markdown(f.read())
    return None

@app.route('/')
@app.route('/browse/')
@app.route('/browse/<path:subpath>')
def index(subpath=""):
    
    safe_subpath = subpath.strip('/')
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_subpath)
    
    if not os.path.exists(full_path):
        return "Directory not found", 404

    items = os.listdir(full_path)
    folders = []
    files = []
    
    for item in items:
        item_path = os.path.join(full_path, item)
        relative_path = os.path.join(safe_subpath, item).replace('\\', '/')
        
        if os.path.isdir(item_path):
            folders.append({'name': item, 'path': relative_path})
        else:
            ext = os.path.splitext(item)[1].lower()
            files.append({
                'name': item, 
                'path': relative_path,
                'is_video': ext in VIDEO_EXTENSIONS
            })

    readme_html = get_readme_content(full_path)
    return render_template('index.html', 
                           folders=folders, 
                           files=files, 
                           current_path=safe_subpath,
                           readme_html=readme_html)

@app.route('/upload/', defaults={'subpath': ''}, methods=['POST'])
@app.route('/upload/<path:subpath>', methods=['POST'])
def upload_file(subpath):
    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], subpath)
    file = request.files.get('file')
    if file and file.filename:
        file.save(os.path.join(target_dir, file.filename))
    return redirect(url_for('index', subpath=subpath))

@app.route('/mkdir/', defaults={'subpath': ''}, methods=['POST'])
@app.route('/mkdir/<path:subpath>', methods=['POST'])
def make_directory(subpath):
    folder_name = request.form.get('folder_name')
    if folder_name:
        new_dir = os.path.join(app.config['UPLOAD_FOLDER'], subpath, folder_name)
        os.makedirs(new_dir, exist_ok=True)
    return redirect(url_for('index', subpath=subpath))

@app.route('/stream/<path:filepath>')
def stream_video(filepath):
    return render_template('viewer.html', filepath=filepath)

@app.route('/raw/<path:filepath>')
def serve_file(filepath):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filepath)

@app.route('/delete/<path:filepath>')
def delete_item(filepath):
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
    parent_dir = os.path.dirname(filepath)
    if os.path.exists(full_path):
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
    return redirect(url_for('index', subpath=parent_dir))

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run('0.0.0.0', 8080, debug=True)
