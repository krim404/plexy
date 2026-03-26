import requests
import logging

logger = logging.getLogger()

REQUEST_TIMEOUT = 10


class Plexy(object):
    def __init__(self, config):
        """
        Core logic for managing media requests via Seerr API.

        Args:
            config (Config): Bot configuration parameters
        """
        self.config = config
        self.headers = {
            "X-Api-Key": config.seerr_apikey,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _seerr_get(self, path, params=None):
        """Make a GET request to the Seerr API."""
        url = f"{self.config.url}/api/v1{path}"
        return requests.get(url, headers=self.headers, params=params, timeout=REQUEST_TIMEOUT)

    def _seerr_post(self, path, data):
        """Make a POST request to the Seerr API."""
        url = f"{self.config.url}/api/v1{path}"
        return requests.post(url, headers=self.headers, json=data, timeout=REQUEST_TIMEOUT)

    def _seerr_delete(self, path):
        """Make a DELETE request to the Seerr API."""
        url = f"{self.config.url}/api/v1{path}"
        return requests.delete(url, headers=self.headers, timeout=REQUEST_TIMEOUT)

    def getAvailRequests(self, available=True, was="movie"):
        """Return a list of available request IDs or all request data from Seerr."""
        params = {"take": 100}
        if available:
            params["filter"] = "available"

        response = self._seerr_get("/request", params=params)
        json_data = response.json()
        results = json_data.get("results", [])

        filtered = [r for r in results if r.get("type") == was]

        if available:
            return [str(r["id"]) for r in filtered]
        return filtered

    def delAvailRequests(self, availRequests, was="movie"):
        """Delete requests by their IDs."""
        if not availRequests:
            return 0
        for request_id in availRequests:
            self._seerr_delete(f"/request/{request_id}")
        return 1

    def getID(self, title, was: str = "movie"):
        """Get MovieDB ID from the movie title."""
        url = f"https://api.themoviedb.org/3/search/{was}"
        querystring = {
            "api_key": self.config.moviedb_apikey,
            "language": self.config.language,
            "query": title,
        }
        response = requests.get(url, params=querystring, timeout=REQUEST_TIMEOUT)
        json_data = response.json()
        if json_data["total_results"] < 1:
            return "nothing"
        return str(json_data["results"][0]["id"])

    def _get_season_count(self, tmdb_id):
        """Get the number of seasons for a TV show from TMDb."""
        url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
        params = {"api_key": self.config.moviedb_apikey}
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        return response.json().get("number_of_seasons", 1)

    def sendRequest(self, id, was: str = "movie"):
        """Request a specific TMDB ID via Seerr."""
        data = {
            "mediaId": int(id),
            "mediaType": was,
        }
        if was == "tv":
            season_count = self._get_season_count(id)
            data["seasons"] = list(range(1, season_count + 1))
        return self._seerr_post("/request", data)

    def getTitle(self, id, was: str = "movie"):
        """Return German title of a specific MovieDB movie/TV ID."""
        url = f"https://api.themoviedb.org/3/{was}/{id}"
        querystring = {
            "api_key": self.config.moviedb_apikey,
            "language": self.config.language,
        }
        response = requests.get(url, params=querystring, timeout=REQUEST_TIMEOUT)
        if was == "movie":
            return response.json()["title"]
        elif was == "tv":
            return response.json()["name"]

    def requestList(self):
        """Return list of all currently requested movies from Seerr."""
        params = {"take": 100}
        response = self._seerr_get("/request", params=params)
        json_data = response.json()
        results = json_data.get("results", [])

        request_list = []
        for req in results:
            tmdb_id = req.get("media", {}).get("tmdbId")
            media_type = req.get("type", "movie")
            if tmdb_id:
                entry = {
                    "id": str(tmdb_id),
                    "title": self.getTitle(tmdb_id, media_type),
                    "type": media_type,
                }
                request_list.append(entry)
        return request_list

    def getPopularMovies(self, amount):
        """Returns a list of the most popular movies from MovieDB."""
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": self.config.moviedb_apikey,
            "language": self.config.language,
            "sort_by": "popularity.desc",
        }
        json_response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT).json()
        popular_list = [
            (movie["id"], movie["title"]) for movie in json_response["results"][:amount]
        ]
        return popular_list

    def delete_requests(self, was: str = "movie"):
        """Delete all requests which are available."""
        if not self.delAvailRequests(self.getAvailRequests(True, was), was):
            return 0
        return 1
