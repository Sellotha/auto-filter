import re
import aiohttp
from io import BytesIO
from PIL import Image

TMDB_SEARCH_URL = "https://api.consumet.org/meta/tmdb/search"
TMDB_INFO_URL = "https://api.consumet.org/meta/tmdb/info"

def clean_title(filename):
    # remove quality + resolution tags
    filename = filename.replace('.', ' ').replace('_', ' ')
    filename = re.sub(r'\b(480p|720p|1080p|2160p|HDRip|BluRay|WEBRip|WEB-DL|DVDRip|x264|HEVC|Hindi|Dual Audio|Original|UNCUT)\b', '', filename, flags=re.IGNORECASE)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename

async def get_movie_details(query, id=False, file=None):
    query = clean_title(file if file else query)

    async with aiohttp.ClientSession() as session:
        async with session.get(TMDB_SEARCH_URL, params={"query": query}) as r:
            data = await r.json()

    if not data or not data.get("results"):
        return None

    movie = data["results"][0]
    tmdb_id = movie.get("id")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{TMDB_INFO_URL}/{tmdb_id}", params={"type": movie.get("type","movie")}) as r:
            info = await r.json()

    return {
        "title": info.get("title") or info.get("name"),
        "year": info.get("releaseDate", "N/A"),
        "genres": ", ".join(info.get("genres", [])),
        "rating": info.get("rating", "N/A"),
        "poster_url": (
            info.get("cover") or 
            info.get("poster") or 
            info.get("image") or 
            (f"https://image.tmdb.org/t/p/w500{info.get('poster_path')}" if info.get("poster_path") else None)
        ),
        "plot": info.get("description", "No description."),
    }

async def fetch_image(url, size=(720, 720)):
    if not url:
        return None

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            content = await response.read()

    img = Image.open(BytesIO(content))
    img = img.resize(size, Image.LANCZOS)
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes
