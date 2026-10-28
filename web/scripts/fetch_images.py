import os
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_TEMPLATES = os.path.join(BASE, 'static', 'templates')
STATIC_EXAMPLES = os.path.join(BASE, 'static', 'examples')
os.makedirs(STATIC_TEMPLATES, exist_ok=True)
os.makedirs(STATIC_EXAMPLES, exist_ok=True)

images = {
    # templates
    'templates/sunset.jpg': 'https://images.unsplash.com/photo-1501973801540-537f08ccae7b?auto=format&fit=crop&w=800&q=80',
    'templates/city.jpg': 'https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=800&q=80',
    'templates/traffic.jpg': 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=800&q=80',
    'templates/basketball.jpg': 'https://images.unsplash.com/photo-1517649763962-0c623066013b?auto=format&fit=crop&w=800&q=80',
    'templates/person.jpg': 'https://images.unsplash.com/photo-1531123414780-f98e8a05b5d8?auto=format&fit=crop&w=800&q=80',
    # examples (annotated style placeholders)
    'examples/annotated_person_1.jpg': 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=800&q=80',
    'examples/annotated_traffic_1.jpg': 'https://images.unsplash.com/photo-1508057198894-247b23fe5ade?auto=format&fit=crop&w=800&q=80',
    'examples/annotated_basketball_1.jpg': 'https://images.unsplash.com/photo-1521412644187-c49fa049e84d?auto=format&fit=crop&w=800&q=80',
}

def download(url, outpath):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(outpath, 'wb') as f:
            f.write(r.content)
        print('Saved', outpath)
    except Exception as e:
        print('Failed', url, e)

if __name__ == '__main__':
    for rel, url in images.items():
        out = os.path.join(BASE, 'static', rel)
        outdir = os.path.dirname(out)
        os.makedirs(outdir, exist_ok=True)
        download(url, out)
