import re
import aiohttp
from io import BytesIO
from PIL import Image
from info import IMAGE_FETCH
from imdb import Cinemagoer

ia = Cinemagoer()

def list_to_str(lst):
    if lst:
        return ", ".join(map(str, lst))
    return ""

# ✅ Poster Fetch with User-Agent Fix
async def fetch_image(url, size=(720, 720)):
    if not IMAGE_FETCH or not url:
        return None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    data = await response.read()
                    img = Image.open(BytesIO(data)).convert("RGB")  # ✅ Fix WebP/JPEG issues
                    img = img.resize(size, Image.LANCZOS)
                    byte_arr = BytesIO()
                    img.save(byte_arr, format="JPEG")
                    byte_arr.seek(0)
                    return byte_arr
                else:
                    print(f"[Poster Fetch] Failed: HTTP {response.status}")
    except Exception as e:
        print(f"[Poster Fetch Error] {e}")
    return None

# ✅ Movie Details Fetch
async def get_movie_details(query, id=False, file=None):
    try:
        query = query.strip().lower()

        year = re.findall(r"[1-2]\d{3}$", query)
        title = query.replace(year[0], "").strip() if year else query

        movie_list = ia.search_movie(title, results=10)
        if not movie_list:
            return None

        if year:
            movie_list = [m for m in movie_list if str(m.get("year")) == year[0]] or movie_list

        movie = ia.get_movie(movie_list[0].movieID)

        plot = movie.get("plot", ["No Description"])[0]
        if len(plot) > 800:
            plot = plot[:800] + "..."

        # ✅ Poster selection fallback chain
        poster_url = (
            movie.get('cover url') or
            movie.get('full-size cover url') or
            movie.get('thumbnail url')
        )

        return {
            "title": movie.get("title"),
            "year": movie.get("year"),
            "genres": list_to_str(movie.get("genres")),
            "languages": list_to_str(movie.get("languages")),
            "director": list_to_str(movie.get("director")),
            "cast": list_to_str(movie.get("cast")),
            "runtime": list_to_str(movie.get("runtimes")),
            "plot": plot,
            "rating": movie.get("rating"),
            "poster_url": poster_url,
            "url": f"https://www.imdb.com/title/tt{movie.movieID}"
        }

    except Exception as e:
        print(f"[IMDB Fetch Error] {e}")
        return None
