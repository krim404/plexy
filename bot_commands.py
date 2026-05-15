from chat_functions import send_text_to_room
from plexy import Plexy


class Command(object):
    def __init__(self, client, store, config, command, room, event):
        """A command made by a user

        Args:
            client (nio.AsyncClient): The client to communicate to matrix with

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            command (str): The command and arguments

            room (nio.rooms.MatrixRoom): The room the command was sent in

            event (nio.events.room_events.RoomMessageText): The event describing the command
        """
        self.client = client
        self.store = store
        self.config = config
        self.command = command
        self.room = room
        self.event = event
        self.args = self.command.split()[1:]
        self.plexy = Plexy(self.config)

    async def process(self):
        """Process the command"""
        if self.command.lower().startswith("ping"):
            await send_text_to_room(self.client, self.room.room_id, "Pong!")
        elif self.command.lower().startswith("commands"):
            await self._show_commands()
        elif self.command.lower().startswith("help"):
            await self._show_help()
        elif self.command.lower().startswith("request"):
            await self._request_old()
        elif self.command.lower().startswith("film"):
            await self._request("movie")
        elif self.command.lower().startswith("serie"):
            await self._request("tv")
        elif self.command.lower().startswith("flist"):
            await self._show_requests("movie")
        elif self.command.lower().startswith("tlist"):
            await self._show_requests("tv")
        elif self.command.lower().startswith("tdelete"):
            await self._delete_requests("tv")
        elif self.command.lower().startswith("fdelete"):
            await self._delete_requests("movie")
        elif self.command.lower().startswith("popular"):
            await self._show_popular_movies()
        else:
            await self._unknown_command()

    async def _show_help(self):
        """Show the Plexy help text"""
        if not self.args:
            text = "Hallo, ich bin **Plexy**. Mit `!plex commands` kannst du dir alle meine Befehle anzeigen lassen."
            await send_text_to_room(self.client, self.room.room_id, text)
            return

    async def _request_old(self):
        """Show deprecation notice for old command"""
        if not self.args:
            text = "Der Befehl hat sich geändert - siehe !plex commands"
            await send_text_to_room(self.client, self.room.room_id, text)
            return

    async def _show_commands(self):
        """Show all available commands"""
        text = "**Verfügbare Befehle**:<br>- `!plex film <Filmname>` -- Fordert einen gewünschten Film an.<br>- `!plex serie <Serienname>` -- Fordert eine gewünschte Serie an.<br>- `!plex flist` -- Listet alle angefragten Filme auf.<br>- `!plex tlist` -- Listet alle angefragten Serien auf.<br>- `!plex fdelete` -- Löscht alle Filmanfragen, die verfügbar sind.<br>- `!plex tdelete` -- Löscht alle Serienanfragen, die verfügbar sind.<br>- `!plex popular <Anzahl>` -- Zeigt aktuell beliebte Filme an."
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _show_requests(self, was: str = "movie"):
        """Shows the movies/TV shows which are currently requested."""
        try:
            requests = self.plexy.getAvailRequests(False, was)
        except Exception:
            await send_text_to_room(self.client, self.room.room_id, "Fehler beim Abrufen der Anfragen.")
            return
        if not requests:
            text = "Aktuell sind keine Inhalte angefragt!"
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        if was == "movie":
            text = "Das sind die aktuell angefragten Filme:"
        elif was == "tv":
            text = "Das sind die aktuell angefragten Serien:"

        for req in requests:
            tmdb_id = req.get("media", {}).get("tmdbId")
            if tmdb_id:
                try:
                    title = self.plexy.getTitle(tmdb_id, was)
                except Exception:
                    title = f"ID {tmdb_id}"
                text = f"{text}<br>- [{title}](https://www.themoviedb.org/{was}/{tmdb_id})"

        await send_text_to_room(self.client, self.room.room_id, text)
        return

    async def _show_popular_movies(self):
        """Shows the most popular movies from MovieDB"""
        text = f"Hey {self.event.sender}, hier sind aktuell beliebte Kinofilme:"
        # Default to three movies if no parameter is given
        try:
            if not self.args:
                movies = self.plexy.getPopularMovies(3)
            else:
                amount = int(self.args[0])
                if amount not in range(1, 16):
                    raise ValueError
                movies = self.plexy.getPopularMovies(amount)
            for x in movies:
                text = f"{text}<br>- [{x[1]}](https://www.themoviedb.org/movie/{x[0]})"
        except ValueError:
            text = "Du hast keine gültige Zahl (1-15) eingegeben."
        except Exception:
            text = "Fehler beim Abrufen der beliebten Filme."

        await send_text_to_room(self.client, self.room.room_id, text)
        return

    async def _request(self, was: str = "movie"):
        """Request a movie or TV show via Seerr"""
        # Output if no film title is given as parameter
        if not self.args:
            text = "Bitte einen Filmtitel angeben :) zum Beispiel `!plex film Deadpool`."
            await send_text_to_room(self.client, self.room.room_id, text)
            return
        requested_title = " ".join(self.args)
        try:
            id = self.plexy.getID(requested_title, was)
        except Exception:
            await send_text_to_room(self.client, self.room.room_id, "Fehler bei der Suche.")
            return

        # If above method returns no movies, send info regarding that
        if id == "nothing":
            await send_text_to_room(
                self.client, self.room.room_id, "Nichts dazu gefunden :("
            )
            return
        # Get German movie title for display reasons
        try:
            title = self.plexy.getTitle(id, was)
        except Exception:
            title = requested_title
        try:
            result = self.plexy.sendRequest(id, was)
            if result.status_code >= 400:
                resp = result.json()
                error_msg = resp.get("error", resp.get("message", "Unbekannter Fehler"))
                text = f"Fehler bei [{title}](https://www.themoviedb.org/{was}/{id}): {error_msg}"
            else:
                text = f"Ich habe [{title}](https://www.themoviedb.org/{was}/{id}) für dich angefordert."
            await send_text_to_room(self.client, self.room.room_id, text)
        except Exception:
            text = "Es trat ein Fehler beim Anfordern des Titels auf."
            await send_text_to_room(self.client, self.room.room_id, text)
        return

    async def _delete_requests(self, was: str = "movie"):
        """Delete all requests which are available"""
        # Check if event.sender is in whitelist, else cancel command
        if (self.config.admin_whitelist_enabled) and (
            self.event.sender not in self.config.admin_whitelist
        ):
            return
        try:
            deleted = self.plexy.delete_requests(was)
        except Exception:
            await send_text_to_room(
                self.client, self.room.room_id, "Fehler beim Löschen der Anfragen."
            )
            return
        if not deleted:
            await send_text_to_room(
                self.client, self.room.room_id, "Es gibt keine Requests zum Löschen!"
            )
            return

        if was == "movie":
            text = f"{self.event.sender}, ich habe folgende Filme gelöscht:"
        elif was == "tv":
            text = f"{self.event.sender}, ich habe folgende Serien gelöscht:"

        for req in deleted:
            tmdb_id = req.get("media", {}).get("tmdbId")
            if tmdb_id:
                try:
                    title = self.plexy.getTitle(tmdb_id, was)
                except Exception:
                    title = f"ID {tmdb_id}"
                text = f"{text}<br>- [{title}](https://www.themoviedb.org/{was}/{tmdb_id})"

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unbekannter Befehl '{self.command}'. Mit `!plex commands` kannst du dir meine Befehle anzeigen lassen.",
        )
