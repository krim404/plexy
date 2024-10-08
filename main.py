#!/usr/bin/env python3

import logging
import asyncio
import time
from nio import AsyncClient, AsyncClientConfig, RoomMessageText, InviteEvent, SyncError
from callbacks import Callbacks
from config import Config
from storage import Storage

logger = logging.getLogger(__name__)


async def main():
    # Read config file
    config = Config("/opt/config/config.yaml")

    # Configure the database
    store = Storage(config.database_filepath)

    # Configuration options for the AsyncClient
    client_config = AsyncClientConfig(max_limit_exceeded=0, max_timeouts=0)

    # Initialize the matrix client
    client = AsyncClient(
        config.homeserver_url,
        config.user_id,
        device_id=config.device_id,
        config=client_config,
    )

    # Assign an access token to the bot instead of logging in and creating a new device
    client.access_token = config.access_token

    # Set up event callbacks
    callbacks = Callbacks(client, store, config)
    client.add_event_callback(callbacks.message, (RoomMessageText,))
    client.add_event_callback(callbacks.invite, (InviteEvent,))

    # Retrieve the last sync token if it exists
    token = store.get_sync_token()

    # Sync loop
    while True:
        time.sleep(1)
        
        # Sync with the server
        sync_response = await client.sync(timeout=30000, full_state=True, since=token)

        # Check if the sync had an error
        if type(sync_response) == SyncError:
            logger.warning("Error in client sync: %s", sync_response.message)
            continue

        # Save the latest sync token
        token = sync_response.next_batch
        if token:
            store.save_sync_token(token)


asyncio.get_event_loop().run_until_complete(main())