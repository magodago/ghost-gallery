#!/usr/bin/env python3
"""
MOSAIC GENERATOR — Crea fotomosaicos reales con tus fotos.
Uso:
  python3 mosaic.py "Juanes"                     # descarga target + genera mosaico
  python3 mosaic.py "Juanes" /ruta/target.jpg     # usa imagen local como target
  python3 mosaic.py list                          # lista targets disponibles
"""

import os, sys, json, math, hashlib
from pathlib import Path
from PIL import Image, ImageStat, ImageEnhance
import requests
from io import BytesIO

# ── CONFIG ──
BASE_DIR = Path(__file__).parent.parent  # project root
PHOTOS_DIR = BASE_DIR / "photos"
MOSAICS_DIR = BASE_DIR / "mosaics"
TARGETS_DIR = BASE_DIR / "targets"
CACHE_DIR = BASE_DIR / "cache"
GRID_COLS = 8
GRID_ROWS = 12
TILE_SIZE = 64  # px per tile in output
OUTPUT_SIZE = (GRID_COLS * TILE_SIZE, GRID_ROWS * TILE_SIZE)

os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(MOSAICS_DIR, exist_ok=True)
os.makedirs(TARGETS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ── TARGET IMAGE SOURCES ──
# Map of target names to image search queries or direct URLs
TARGET_SOURCES = {
    # Celebridades
    "juanes": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Juanes_in_2023.jpg/640px-Juanes_in_2023.jpg",
    "messi": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Lionel_Messi_20180626.jpg/640px-Lionel_Messi_20180626.jpg",
    "taylor": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Taylor_Swift_at_the_2024_Golden_Globes_%28cropped%29.jpg/640px-Taylor_Swift_at_the_2024_Golden_Globes_%28cropped%29.jpg",
    "pikachu": "https://upload.wikimedia.org/wikipedia/en/thumb/a/a6/Pok%C3%A9mon_Pikachu_art.svg/640px-Pok%C3%A9mon_Pikachu_art.svg.png",
    "einstein": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Albert_Einstein_Head.jpg/640px-Albert_Einstein_Head.jpg",
    "bob marley": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Bob_Marley_1976.jpg/640px-Bob_Marley_1976.jpg",
    "queen": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Queen_%C2%A9_1984_Jim_Sullivan_-_Queen_2024_cropped.jpg/640px-Queen_%C2%A9_1984_Jim_Sullivan_-_Queen_2024_cropped.jpg",
    "shakira": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Shakira_2023.jpg/640px-Shakira_2023.jpg",
    "iron man": "https://upload.wikimedia.org/wikipedia/en/thumb/4/47/Iron_Man_%28circa_2018%29.png/640px-Iron_Man_%28circa_2018%29.png",
    "dragon": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Chinese_dragon_Shaanxi.jpg/640px-Chinese_dragon_Shaanxi.jpg",
}

# ── HELPERS ──

def avg_color(img):
    """Return (R, G, B) average color of an image."""
    stat = ImageStat.Stat(img)
    return tuple(int(c) for c in stat.mean[:3])

def color_distance(c1, c2):
    """Weighted Euclidean distance between two RGB colors."""
    r, g, b = c1[0]-c2[0], c1[1]-c2[1], c1[2]-c2[2]
    # Weighted for human perception
    return math.sqrt(2*r*r + 4*g*g + 3*b*b)

def download_image(url, path):
    """Download an image from URL and save."""
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert('RGB')
        img.save(path)
        print(f"  ✓ Descargado: {path.name}")
        return True
    except Exception as e:
        print(f"  ✗ Error descargando {url}: {e}")
        return False

def load_or_download_target(name):
    """Get target image path — from local targets directory."""
    target_path = TARGETS_DIR / f"{name.lower().replace(' ', '_')}.jpg"
    if target_path.exists():
        return target_path
    return None

def load_user_photos():
    """Load all user photos from the photos directory."""
    photos = []
    valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
    for f in sorted(PHOTOS_DIR.iterdir()):
        if f.suffix.lower() in valid_exts:
            try:
                img = Image.open(f).convert('RGB')
                # Resize to standard tile size for faster processing
                img = img.resize((TILE_SIZE, TILE_SIZE), Image.LANCZOS)
                photos.append({'path': f.name, 'img': img, 'color': avg_color(img)})
            except Exception as e:
                print(f"  ⚠ Error cargando {f.name}: {e}")
    return photos

def precompute_photo_cache(photos):
    """Save photo color data to JSON cache."""
    cache = [{'path': p['path'], 'color': list(p['color'])} for p in photos]
    with open(CACHE_DIR / 'photo_colors.json', 'w') as f:
        json.dump(cache, f)

def load_photo_cache():
    """Load cached photo data if available."""
    cache_path = CACHE_DIR / 'photo_colors.json'
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    return None

# ── MAIN MOSAIC GENERATOR ──

def generate_mosaic(target_name, target_image_path=None):
    """Generate a photo mosaic for the given target."""
    print(f"\n{'='*50}")
    print(f"  MOSAIC: {target_name}")
    print(f"{'='*50}")

    # 1. Load target image
    if target_image_path:
        target_path = Path(target_image_path)
    else:
        target_path = load_or_download_target(target_name)

    if not target_path or not target_path.exists():
        print(f"  ✗ No se pudo obtener imagen target para: {target_name}")
        return None

    target_img = Image.open(target_path).convert('RGB')
    target_img = target_img.resize(OUTPUT_SIZE, Image.LANCZOS)
    print(f"  ✓ Target cargado: {target_path.name} ({OUTPUT_SIZE[0]}x{OUTPUT_SIZE[1]})")

    # 2. Load user photos
    print(f"  → Cargando fotos desde: {PHOTOS_DIR}")
    photos = load_user_photos()
    if len(photos) < 10:
        print(f"  ✗ Necesitas al menos 10 fotos. Tienes: {len(photos)}")
        print(f"    Pon fotos en: {PHOTOS_DIR}")
        return None

    print(f"  ✓ {len(photos)} fotos cargadas")

    # 3. Divide target into grid tiles
    tile_w = OUTPUT_SIZE[0] // GRID_COLS
    tile_h = OUTPUT_SIZE[1] // GRID_ROWS
    print(f"  → Grid: {GRID_COLS}x{GRID_ROWS} = {GRID_COLS*GRID_ROWS} tiles")

    tiles = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            left = col * tile_w
            upper = row * tile_h
            tile = target_img.crop((left, upper, left + tile_w, upper + tile_h))
            tiles.append({
                'row': row, 'col': col,
                'img': tile,
                'color': avg_color(tile)
            })

    # 4. Match each tile to best user photo
    print(f"  → Asignando fotos a tiles...")
    matched_photos = []
    used_indices = set()

    for tile in tiles:
        best_dist = float('inf')
        best_idx = None
        for i, photo in enumerate(photos):
            if i in used_indices:
                # Allow reuse after using all photos once
                pass
            dist = color_distance(tile['color'], photo['color'])
            if dist < best_dist:
                best_dist = dist
                best_idx = i

        if best_idx is not None:
            used_indices.add(best_idx)
            matched_photos.append(photos[best_idx])
        else:
            matched_photos.append(photos[0])

    # 5. Assemble mosaic
    mosaic = Image.new('RGB', OUTPUT_SIZE, (0, 0, 0))
    for idx, photo in enumerate(matched_photos):
        row = tiles[idx]['row']
        col = tiles[idx]['col']
        left = col * tile_w
        upper = row * tile_h
        # Resize user photo to tile size
        tile_img = photo['img'].resize((tile_w, tile_h), Image.LANCZOS)
        # Adjust brightness to match target tile
        try:
            target_avg = tiles[idx]['color']
            photo_avg = photo['color']
            brightness_ratio = sum(target_avg) / (sum(photo_avg) + 1)
            if 0.3 < brightness_ratio < 3.0:
                enhancer = ImageEnhance.Brightness(tile_img)
                tile_img = enhancer.enhance(brightness_ratio)
        except:
            pass
        mosaic.paste(tile_img, (left, upper))

    # 6. Save mosaic
    safe_name = target_name.lower().replace(' ', '_').replace('.', '')
    mosaic_path = MOSAICS_DIR / f"{safe_name}.jpg"
    mosaic.save(mosaic_path, 'JPEG', quality=90)
    print(f"\n  ✅ MOSAICO GUARDADO: {mosaic_path}")
    print(f"     Tamaño: {mosaic.size[0]}x{mosaic.size[1]}px")
    print(f"     Fotos usadas: {len(matched_photos)}")

    # Also save a thumbnail for the app
    thumb = mosaic.copy()
    thumb.thumbnail((400, 600), Image.LANCZOS)
    thumb_path = MOSAICS_DIR / f"{safe_name}_thumb.jpg"
    thumb.save(thumb_path, 'JPEG', quality=85)
    print(f"     Thumbnail: {thumb_path}")

    # Save metadata
    meta = {
        'target': target_name,
        'grid': [GRID_COLS, GRID_ROWS],
        'photos_used': len(matched_photos),
        'file': f"{safe_name}.jpg",
        'thumb': f"{safe_name}_thumb.jpg",
    }
    with open(MOSAICS_DIR / f"{safe_name}.json", 'w') as f:
        json.dump(meta, f)

    # Show preview as ASCII
    print(f"\n  Preview (8x12):")
    preview = mosaic.resize((GRID_COLS, GRID_ROWS), Image.LANCZOS).convert('L')
    chars = " .:-=+*#%@"
    for r in range(GRID_ROWS):
        line = ""
        for c in range(GRID_COLS):
            lum = preview.getpixel((c, r))
            line += chars[min(lum * len(chars) // 256, len(chars)-1)] * 2
        print(f"    {line}")

    return mosaic_path

# ── BATCH GENERATE ──

def generate_all_targets():
    """Generate mosaics for all configured targets."""
    results = []
    for name in TARGET_SOURCES:
        path = generate_mosaic(name)
        if path:
            results.append({'name': name, 'path': str(path)})
    return results

# ── LIST TARGETS ──

def list_targets():
    """List all available targets and their status."""
    print(f"\n{'='*50}")
    print(f"  TARGETS DISPONIBLES")
    print(f"{'='*50}")
    for name in sorted(TARGET_SOURCES.keys()):
        mosaic_path = MOSAICS_DIR / f"{name.lower().replace(' ', '_')}.jpg"
        status = "✅" if mosaic_path.exists() else "⬜"
        print(f"  {status} {name.title()}")

    print(f"\n  Mosaicos generados: {len(list(MOSAICS_DIR.glob('*.jpg')))}")
    print(f"  Tus fotos: {len(list(PHOTOS_DIR.iterdir())) if PHOTOS_DIR.exists() else 0}")

def serve_mosaic_list():
    """Generate a JSON manifest of available mosaics for the frontend."""
    manifest = []
    for f in MOSAICS_DIR.glob("*.json"):
        with open(f) as fp:
            data = json.load(fp)
            manifest.append(data)
    manifest_path = BASE_DIR / "mosaics" / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"  Manifiesto guardado: {manifest_path}")
    return manifest

# ── CLI ──

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "list":
        list_targets()
    elif cmd == "all":
        generate_all_targets()
        serve_mosaic_list()
    elif cmd == "serve":
        serve_mosaic_list()
    elif cmd == "help":
        print(__doc__)
    else:
        target_name = cmd
        target_path = sys.argv[2] if len(sys.argv) > 2 else None
        path = generate_mosaic(target_name, target_path)
        if path:
            serve_mosaic_list()
