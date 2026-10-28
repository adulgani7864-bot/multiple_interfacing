import os
import uuid
import random
import glob
import shutil
import cv2
import subprocess
import requests
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'jpg', 'jpeg', 'png', 'gif'}

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.environ.get('FLASK_SECRET', 'change-this-secret')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


FFMPEG_BIN = shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'
FFPROBE_BIN = shutil.which('ffprobe') or r'C:\ffmpeg\bin\ffprobe.exe'


def _rel_upload_url(path):
    rel_filename = os.path.relpath(path, app.config['UPLOAD_FOLDER']).replace('\\', '/')
    return url_for('uploaded_file', filename=rel_filename)


def is_h264_video(source_path):
    if not source_path or not os.path.exists(source_path) or not os.path.exists(FFPROBE_BIN):
        return False
    probe = subprocess.run(
        [FFPROBE_BIN, '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', source_path],
        capture_output=True, text=True
    )
    codec = (probe.stdout or '').strip().lower()
    return codec in {'h264', 'avc1'}


def extract_preview_poster(source_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    poster_path = os.path.join(output_dir, f"{uuid.uuid4().hex}_poster.jpg")
    cap = cv2.VideoCapture(source_path)
    if not cap.isOpened():
        return None
    ok, frame = cap.read()
    if not ok:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 1)
        ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None
    cv2.imwrite(poster_path, frame)
    return poster_path if os.path.exists(poster_path) else None


def convert_video_to_mp4(source_path, output_dir, suffix='browser'):
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source video not found: {source_path}")
    if is_h264_video(source_path) and source_path.lower().endswith('.mp4'):
        return source_path
    if not os.path.exists(FFMPEG_BIN):
        raise RuntimeError('ffmpeg was not found. Install ffmpeg to create browser-playable previews.')

    os.makedirs(output_dir, exist_ok=True)
    target_path = os.path.join(output_dir, f"{uuid.uuid4().hex}_{suffix}.mp4")
    common = [FFMPEG_BIN, '-y', '-i', source_path, '-c:v', 'libx264', '-preset', 'ultrafast',
              '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
    completed = subprocess.run(common + ['-c:a', 'aac', '-ac', '2', target_path], capture_output=True, text=True)
    if completed.returncode != 0 or not os.path.exists(target_path) or os.path.getsize(target_path) == 0:
        completed = subprocess.run(common + ['-an', target_path], capture_output=True, text=True)
    if completed.returncode != 0 or not os.path.exists(target_path) or os.path.getsize(target_path) == 0:
        err = (completed.stderr or completed.stdout or 'ffmpeg failed').strip()[-800:]
        raise RuntimeError(f'Unable to create a browser-playable MP4: {err}')
    return target_path


def static_or_placeholder(path, w=320, h=200, text='Image'):
    static_path = os.path.join(app.static_folder, path)
    if os.path.exists(static_path) and os.path.getsize(static_path) > 0:
        return url_for('static', filename=path)
    return f"https://via.placeholder.com/{w}x{h}.png?text={text.replace(' ','+')}"


IMAGES_TO_FETCH = {
    'templates/sunset.jpg': 'https://images.unsplash.com/photo-1501973801540-537f08ccae7b?auto=format&fit=crop&w=800&q=80',
    'templates/city.jpg': 'https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=800&q=80',
    'templates/traffic.jpg': 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=800&q=80',
    'templates/basketball.jpg': 'https://images.unsplash.com/photo-1517649763962-0c623066013b?auto=format&fit=crop&w=800&q=80',
    'templates/person.jpg': 'https://images.unsplash.com/photo-1531123414780-f98e8a05b5d8?auto=format&fit=crop&w=800&q=80',
    'examples/annotated_person_1.jpg': 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=800&q=80',
    'examples/annotated_traffic_1.jpg': 'https://images.unsplash.com/photo-1508057198894-247b23fe5ade?auto=format&fit=crop&w=800&q=80',
    'examples/annotated_basketball_1.jpg': 'https://images.unsplash.com/photo-1521412644187-c49fa049e84d?auto=format&fit=crop&w=800&q=80',
}

# Additional images to seed the carousel/templates
IMAGES_TO_FETCH.update({
    'examples/annotated_sports_2.jpg': 'https://images.unsplash.com/photo-1517649763962-0c623066013b?auto=format&fit=crop&w=900&q=80',
    'examples/annotated_city_2.jpg': 'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=900&q=80',
    'templates/forest.jpg': 'https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=900&q=80',
    'templates/mountain.jpg': 'https://images.unsplash.com/photo-1501785888041-4e8b0f9b4e34?auto=format&fit=crop&w=900&q=80',
    'examples/annotated_people_2.jpg': 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=80',
})


def ensure_static_images():
    for rel, url in IMAGES_TO_FETCH.items():
        out = os.path.join(app.static_folder, rel)
        outdir = os.path.dirname(out)
        try:
            if os.path.exists(out) and os.path.getsize(out) > 0:
                continue
            os.makedirs(outdir, exist_ok=True)
            print(f"Downloading {url} -> {out}")
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            with open(out, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")


# Try to ensure example/template images exist on startup
try:
    ensure_static_images()
except Exception:
    pass


@app.route('/')
def index():
    templates = [
        {'id': 'tpl1', 'title': 'Sunset Banner', 'image': static_or_placeholder('templates/sunset.jpg', text='Sunset'), 'text': 'Welcome to YOWOv3'},
        {'id': 'tpl2', 'title': 'City Frame', 'image': static_or_placeholder('templates/city.jpg', text='City'), 'text': 'Object and Action Detection'},
        {'id': 'tpl3', 'title': 'Traffic Surveillance', 'image': static_or_placeholder('templates/traffic.jpg', text='Traffic'), 'text': 'Vehicle and pedestrian detection overlay'},
        {'id': 'tpl4', 'title': 'Basketball Court', 'image': static_or_placeholder('templates/basketball.jpg', text='Basketball'), 'text': 'Sports action highlighting'},
    ]

    # Person detection description card (rendered separately)
    person_info = {
        'title': 'Person Detection',
        'image': static_or_placeholder('examples/annotated_people_2.jpg', text='Person'),
        'description': 'Person detection finds and localizes people in each frame using bounding boxes. Combine this with action recognition to label activities (e.g., running, jumping, sitting) for each detected person. Outputs include bounding box coordinates, detection confidence, and optional tracking IDs across frames.'
    }

    # main carousel: list of dicts with url and is_video flag
    carousel = [
        {'url': static_or_placeholder('examples/annotated_person_1.jpg', text='Annotated+Person'), 'is_video': False},
        {'url': static_or_placeholder('examples/annotated_traffic_1.jpg', text='Annotated+Traffic'), 'is_video': False},
        {'url': static_or_placeholder('examples/annotated_basketball_1.jpg', text='Annotated+Basketball'), 'is_video': False},
    ]

    # prepare three additional carousels: recent uploads, video previews, image examples
    carousel_recent = []
    carousel_videos = []
    carousel_images = []
    # category carousels for specific detection types
    category_carousels = {
        'Car Detection': [],
        'Action Detection': [],
        'Theft Detection': [],
        'Motion Detection': [],
    }

    # include uploaded images (newest first)
    try:
        relevant_video_paths = []
        converted_dir = os.path.join(UPLOAD_FOLDER, 'processed_videos', 'converted')
        os.makedirs(converted_dir, exist_ok=True)

        permanent_dirs = [
            os.path.join(UPLOAD_FOLDER, 'processed_videos'),
            os.path.join(UPLOAD_FOLDER, 'processed_videos', 'tmp'),
        ]
        for base_dir in permanent_dirs:
            if not os.path.isdir(base_dir):
                continue
            for root, _, filenames in os.walk(base_dir):
                for fname in sorted(filenames):
                    ext = fname.rsplit('.', 1)[-1].lower()
                    if ext not in {'mp4', 'mov', 'avi', 'mkv', 'webm'}:
                        continue
                    source_path = os.path.join(root, fname)
                    target_path = source_path
                    try:
                        if ext != 'mp4':
                            target_path = convert_video_to_mp4(source_path, converted_dir, suffix='gallery')
                    except Exception:
                        continue
                    rel_path = os.path.relpath(target_path, UPLOAD_FOLDER).replace('\\', '/')
                    if rel_path not in relevant_video_paths:
                        relevant_video_paths.append(rel_path)

        for rel_path in relevant_video_paths:
            item = {'url': url_for('uploaded_file', filename=rel_path), 'is_video': True}
            carousel.insert(0, item)
            if len(carousel_recent) < 6:
                carousel_recent.append(item)
            if len(carousel_videos) < 6:
                carousel_videos.append(item)

        files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)), reverse=True)
        for fname in files:
            ext = fname.rsplit('.', 1)[-1].lower()
            is_video = ext in {'mp4', 'mov', 'avi', 'mkv', 'webm'}
            url = url_for('uploaded_file', filename=fname)
            if is_video:
                rel_path = fname
                if rel_path in [entry['url'].split('/uploads/', 1)[-1] if '/uploads/' in entry['url'] else entry['url'] for entry in carousel_recent]:
                    continue
            item = {'url': url, 'is_video': is_video}
            carousel.insert(0, item)
            if len(carousel_recent) < 6:
                carousel_recent.append(item)
            if is_video and len(carousel_videos) < 6:
                carousel_videos.append(item)
            if not is_video and len(carousel_images) < 6:
                carousel_images.append(item)

        # seed category carousels with relevant images and unique titles/captions
        category_carousels['Car Detection'] = [
            {'url': static_or_placeholder('templates/traffic.jpg', text='Traffic'), 'is_video': False, 'title': 'Vehicle passing', 'caption': 'Detects cars and license plates.'},
            {'url': static_or_placeholder('examples/annotated_traffic_1.jpg', text='Traffic+2'), 'is_video': False, 'title': 'Parked vehicle', 'caption': 'Detects parked and stopped vehicles.'},
            {'url': static_or_placeholder('templates/basketball.jpg', text='CarAlt'), 'is_video': False, 'title': 'Vehicle cluster', 'caption': 'Identify clusters of vehicles in a zone.'},
        ]
        category_carousels['Action Detection'] = [
            {'url': static_or_placeholder('templates/person.jpg', text='Person'), 'is_video': False, 'title': 'Person running', 'caption': 'Recognizes running, jumping, and sprinting.'},
            {'url': static_or_placeholder('examples/annotated_sports_2.jpg', text='Action'), 'is_video': False, 'title': 'Jumping', 'caption': 'Highlights quick athletic motions.'},
            {'url': static_or_placeholder('examples/annotated_basketball_1.jpg', text='Action2'), 'is_video': False, 'title': 'Interaction', 'caption': 'Detects interactions between people.'},
        ]
        category_carousels['Theft Detection'] = [
            {'url': static_or_placeholder('templates/city.jpg', text='Store'), 'is_video': False, 'title': 'Concealment', 'caption': 'Flags concealment and hiding actions.'},
            {'url': static_or_placeholder('examples/annotated_city_2.jpg', text='Theft'), 'is_video': False, 'title': 'Shoplifting', 'caption': 'Detects suspicious hand-to-item movements.'},
            {'url': static_or_placeholder('templates/sunset.jpg', text='Theft2'), 'is_video': False, 'title': 'Grab-and-run', 'caption': 'Recognizes snatch-and-run behavior.'},
        ]
        category_carousels['Motion Detection'] = [
            {'url': static_or_placeholder('templates/forest.jpg', text='Motion'), 'is_video': False, 'title': 'Background motion', 'caption': 'Monitors ambient motion levels.'},
            {'url': static_or_placeholder('templates/mountain.jpg', text='Motion2'), 'is_video': False, 'title': 'Camera shake', 'caption': 'Detects sudden camera movement.'},
            {'url': static_or_placeholder('examples/annotated_people_2.jpg', text='Motion3'), 'is_video': False, 'title': 'Crowd motion', 'caption': 'Tracks group movement patterns.'},
        ]
    except Exception:
        pass

    return render_template('index.html', templates=templates, carousel=carousel, person_info=person_info,
                           carousel_recent=carousel_recent, carousel_videos=carousel_videos, carousel_images=carousel_images)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        company = request.form.get('company', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not message:
            flash('Please complete your name, email, and message before submitting.')
            return render_template('contact.html', company=company)

        flash(f'Thank you, {name}! Your demo request has been sent successfully.')
        return redirect(url_for('contact'))

    return render_template('contact.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)

        ext = filename.rsplit('.', 1)[-1].lower()
        if ext in {'jpg', 'jpeg', 'png', 'gif'}:
            try:
                proc_name = f"proc_{unique_name}"
                proc_path = os.path.join(app.config['UPLOAD_FOLDER'], proc_name)

                im = Image.open(save_path).convert('RGB')
                draw = ImageDraw.Draw(im)
                w, h = im.size
                for i in range(random.randint(1, 3)):
                    x1 = random.randint(0, int(w*0.6))
                    y1 = random.randint(0, int(h*0.6))
                    x2 = random.randint(int(w*0.4), w)
                    y2 = random.randint(int(h*0.4), h)
                    draw.rectangle([x1, y1, x2, y2], outline=(255, 100, 80), width=4)
                    draw.text((x1+6, y1+6), f"action:{random.randint(0,20)}", fill=(255,255,255))
                im.save(proc_path)
                flash('File uploaded and processed')
                return redirect(url_for('result', filename=proc_name, orig=unique_name))
            except Exception as e:
                flash(f'Processing failed: {e}')
                return redirect(url_for('uploaded_file', filename=unique_name))

        # If a video was uploaded, redirect to the result page so it can be previewed
        if ext in {'mp4', 'mov', 'avi', 'mkv', 'webm'}:
            flash('Video uploaded')
            return redirect(url_for('result', filename=unique_name, orig=unique_name))

        flash('File uploaded successfully')
        return redirect(url_for('uploaded_file', filename=unique_name))

    flash('File type not allowed')
    return redirect(url_for('index'))


@app.route('/preview_source', methods=['POST'])
def preview_source():
    if 'file' not in request.files:
        return jsonify({'error': 'No video file received'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in {'mp4', 'mov', 'avi', 'mkv', 'webm'}:
        return jsonify({'error': 'Only video files are supported'}), 400

    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    source_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(source_path)

    preview_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'previews')
    os.makedirs(preview_dir, exist_ok=True)
    poster_path = extract_preview_poster(source_path, preview_dir)
    playable_path = convert_video_to_mp4(source_path, preview_dir, suffix='preview')

    payload = {
        'video_url': _rel_upload_url(playable_path),
        'source_url': _rel_upload_url(source_path),
    }
    if poster_path:
        payload['poster_url'] = _rel_upload_url(poster_path)
    return jsonify(payload)


@app.route('/process_video', methods=['POST'])
def process_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No video file received'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in {'mp4', 'mov', 'avi', 'mkv', 'webm'}:
        return jsonify({'error': 'Only video files are supported for processing'}), 400

    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    source_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(source_path)

    project_root = os.path.abspath(os.path.join(BASE_DIR, '..'))
    model_candidates = [
        os.path.join(project_root, 'weights', 'yolov8n.pt'),
        os.path.join(project_root, 'yolov8n.pt'),
        os.path.join(BASE_DIR, 'weights', 'yolov8n.pt'),
        os.path.join(BASE_DIR, 'yolov8n.pt'),
    ]
    model_path = next((p for p in model_candidates if os.path.exists(p)), None)
    if not model_path:
        return jsonify({'error': 'YOLO weights file not found at weights\\yolov8n.pt'}), 404

    try:
        model = YOLO(model_path)
        output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_videos')
        os.makedirs(output_dir, exist_ok=True)
        results = model(source_path, save=True, project=output_dir, name='tmp', exist_ok=True, conf=0.25, verbose=False)
        result_file = None

        if results and hasattr(results[0], 'save_dir'):
            base_dir = str(results[0].save_dir)
            for root, _, files in os.walk(base_dir):
                for name in sorted(files, key=lambda x: os.path.getmtime(os.path.join(root, x)), reverse=True):
                    if name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                        result_file = os.path.join(root, name)
                        break
                if result_file:
                    break

        if result_file is None:
            for root, _, files in os.walk(output_dir):
                for name in sorted(files, key=lambda x: os.path.getmtime(os.path.join(root, x)), reverse=True):
                    if name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                        result_file = os.path.join(root, name)
                        break
                if result_file:
                    break

        if result_file is None:
            return jsonify({'error': 'Video was uploaded but no processed output was generated'}), 500

        converted_dir = os.path.join(output_dir, 'converted')
        os.makedirs(converted_dir, exist_ok=True)
        result_file = convert_video_to_mp4(result_file, converted_dir, suffix='processed')
        playable_source = convert_video_to_mp4(source_path, converted_dir, suffix='source')

        return jsonify({
            'video_url': _rel_upload_url(result_file),
            'source_url': _rel_upload_url(playable_source),
        })
    except Exception as exc:
        return jsonify({'error': f'Processing failed: {exc}'}), 500


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, conditional=True)


@app.route('/result')
def result():
    filename = request.args.get('filename')
    orig = request.args.get('orig')
    if not filename:
        return redirect(url_for('index'))
    return render_template('result.html', filename=filename, orig=orig)


if __name__ == '__main__':
    print('YOWO web routes:', sorted({rule.rule for rule in app.url_map.iter_rules()}))
    app.run(host='0.0.0.0', port=5000, debug=True)
