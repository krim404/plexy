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
        """Return request data filtered by media type.

        If available=True, only requests with media.status AVAILABLE (5) or
        PARTIALLY_AVAILABLE (4) are returned.
        """
        params = {"take": 100}

        response = self._seerr_get("/request", params=params)
        json_data = response.json()
        results = json_data.get("results", [])

        logger.info(
            "Seerr /request: http_status=%s total_results=%d type_filter=%s",
            response.status_code, len(results), was
        )

        filtered = [r for r in results if r.get("type") == was]
        logger.info("Requests of type %s: %d", was, len(filtered))

        if not available:
            return filtered

        # media.status: 1=UNKNOWN 2=PENDING 3=PROCESSING 4=PARTIALLY_AVAILABLE 5=AVAILABLE
        deletable = []
        for r in filtered:
            media_status = r.get("media", {}).get("status")
            tmdb_id = r.get("media", {}).get("tmdbId")
            if media_status in (4, 5):
                deletable.append(r)
                logger.info(
                    "Deletable request: id=%s tmdbId=%s media.status=%s",
                    r.get("id"), tmdb_id, media_status,
                )
            else:
                logger.info(
                    "Skipped request: id=%s tmdbId=%s media.status=%s",
                    r.get("id"), tmdb_id, media_status,
                )
        return deletable

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
        """Delete all available requests. Returns list of successfully deleted request dicts."""
        deletable = self.getAvailRequests(True, was)
        if not deletable:
            logger.info("No deletable requests for type %s", was)
            return []
        deleted = []
        for r in deletable:
            request_id = r["id"]
            response = self._seerr_delete(f"/request/{request_id}")
            logger.info(
                "Deleted request id=%s http_status=%s",
                request_id, response.status_code,
            )
            if response.status_code < 400:
                deleted.append(r)
        return deleted
