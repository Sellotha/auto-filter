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


# ✅ Poster Fetch with Anti-403 User-Agent
async def fetch_image(url, size=(720, 720)):
    if not IMAGE_FETCH or not url:
        return None

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"[×] Poster Fetch Failed: {url} | HTTP {response.status}")
                    return None

                content = await response.read()
                img = Image.open(BytesIO(content)).convert("RGB")
                img = img.resize(size, Image.LANCZOS)
                img_bytes = BytesIO()
                img.save(img_bytes, format="JPEG")
                img_bytes.seek(0)
                return img_bytes

    except Exception as e:
        print(f"[Poster Fetch Error] {e}")
        return None



# ✅ IMDb + Fallback Poster URL
async def get_movie_details(query, id=False, file=None):
    try:
        query = query.strip().lower()

        # extract year
        year = re.findall(r"(19|20)\d{2}", query)
        title = query.replace(year[0], "").strip() if year else query

        results = ia.search_movie(title)
        if not results:
            return None

        # if year matched use that one
        if year:
            results = [m for m in results if str(m.get("year")) == year[0]] or results

        movie = ia.get_movie(results[0].movieID)

        # ✅ P O S T E R   F I X
        poster_url = None
        if "full-size cover url" in movie:
            poster_url = movie["full-size cover url"]
        elif "cover url" in movie:
            poster_url = movie["cover url"]
        else:
            # ✅ TMDB fallback
            search_title = movie.get("title", "").replace(" ", "+")
            poster_url = f"https://image.tmdb.org/t/p/w500/{search_title}.jpg"

        plot = movie.get("plot", ["No Description"])[0]
        if len(plot) > 800:
            plot = plot[:800] + "..."

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
        print(f"[IMDB FETCH ERROR] {e}")
        return None
