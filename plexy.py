import requests
import json


class Plexy(object):
    def __init__(self, config):
        """
        Object which contains the core code for managing requests.

        Args:
            config (Config): Bot configuration parameters
        """
        self.config = config

        # Reserved for later development
        if not config.tvdbkey:
            #config.tvdbkey = self.generateKey()
            print(config.tvdbkey)

    def generateKey(self):
        url = "https://api4.thetvdb.com/v4/login"
        payload = '{ "apikey": "' + self.config.tvdb_apikey + '", "pin": "0000"}'
        headers = {
            "content-type": "application/json-patch+json",
            "apikey": self.config.ombi_apikey,
            "accept": "application/json",
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        return response.json()["data"]["token"]

    def getAvailRequests(self, available=True, was="movie"):
        """Return a list of all available movie requests from ombi"""
        url = f"{self.config.url}/api/v1/Request/{was}"

        payload = ""
        headers = {"apikey": self.config.ombi_apikey}

        json_data = json.loads(
            requests.request("GET", url, data=payload, headers=headers).text
        )

        if was == "movie":
            json_list = [str(dict["id"]) for dict in json_data if dict["available"]]
        elif was == "tv":
            json_list = [str(dict["id"]) for dict in json_data if dict["childRequests"][0]["available"]]

        if available:
            return json_list
        return json_data

    def delAvailRequests(self, availRequests, was="movie"):
        """Delete movie request given in the given list"""
        if not availRequests:
            return 0
        for x in availRequests:
            url = self.config.url + "/api/v1/Request/"+was+"/" + x

            payload = ""
            headers = {"request": "", "apikey": self.config.ombi_apikey}

            requests.request("DELETE", url, data=payload, headers=headers)
        return 1

    def getID(self, title, was: str = "movie"):
        """Get MovieDB ID from the movie title"""

        url = f"https://api.themoviedb.org/3/search/{was}"

        querystring = {
            "api_key": self.config.moviedb_apikey,
            "language": self.config.language,
            "query": title,
        }

        response = requests.request("GET", url, params=querystring)

        json_data = json.loads(response.text)
        if json_data["total_results"] < 1:
            return "nothing"

        id = str(json_data["results"][0]["id"])
        return id

    def sendRequest(self, id, was: str = "movie"):
        """Request specific ID via ombi"""
        if was == "movie":
            url = self.config.url + "/api/v1/Request/movie"
            payload = '{ "theMovieDbId": "' + id + '", "languageCode": "'+self.config.language+'"}'
        elif was == "tv":
            url = self.config.url + "/api/v2/Requests/tv"
            payload = '{ "theMovieDbId": "' + id + '", "languageCode": "'+self.config.language+'", "requestAll": true}'


        headers = {
            "content-type": "application/json-patch+json",
            "apikey": self.config.ombi_apikey,
            "accept": "application/json",
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        return response

    def getTitle(self, id, was: str = "movie"):
        """Return German title of a specific MovieDB movie ID"""
        url = f"https://api.themoviedb.org/3/{was}/" + str(id)

        payload = ""
        querystring = {
            "api_key": self.config.moviedb_apikey,
            "language": self.config.language,
        }

        response = requests.get(url, data=payload, params=querystring)
        if was == "movie":
            return response.json()["title"]
        elif was == "tv":
            return response.json()["name"]

    def requestList(self):
        """Return list of currently requested movies from Ombi"""
        url = self.config.url + "/api/v1/Request/movie"

        payload = '[\n  {\n    "id": 0,\n    "title": "string",\n    "overview": "string",\n    "imdbId": "string",\n    "tvDbId": "string",\n    "theMovieDbId": "string",\n    "releaseYear": "string",\n    "addedAt": "2018-12-22T12:05:24.510Z",\n    "quality": "string"\n  }\n]'
        querystring = {"": ""}
        headers = {
            "content-type": "application/json",
            "apikey": self.config.ombi_apikey,
        }

        response = requests.get(url, data=payload, headers=headers, params=querystring)

        requestList = []
        for request in response.json():
            singleMovie = {}
            if request["approved"]:
                singleMovie["id"] = request["theMovieDbId"]
                singleMovie["title"] = self.getTitle(request["theMovieDbId"])
                requestList.append(singleMovie)
        return requestList


    def getPopularMovies(self, amount):
        """Returns a list of the most popular movies from MovieDB"""

        url = "https://api.themoviedb.org/3/discover/movie"

        params = {
            "api_key": self.config.moviedb_apikey,
            "language": self.config.language,
            "sort_by": "popularity.desc",
        }

        json_response = requests.get(url, params=params).json()
        popular_list = [
            (movie["id"], movie["title"]) for movie in json_response["results"][:amount]
        ]
        return popular_list

    def delete_requests(self, was: str = "movie"):
        """Delete all requests from ombi, which are available in Plex"""
        if not self.delAvailRequests(self.getAvailRequests(True, was), was):
            return 0
        else:
            return 1
