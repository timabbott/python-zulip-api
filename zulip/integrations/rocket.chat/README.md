# Zulip <--> Rocket.Chat mirror

## Usage

0. `pip install zulip rocketchat_API`

### 1. Zulip endpoint
1. Create a generic Zulip bot
2. (don't forget this step!) Make sure the bot is subscribed to the relevant stream
3. Enter the bot's email and api_key into rocket_mirror_config.py
4. Enter the destination subject and realm into the config file

### 2. Rocket.Chat endpoint
1. Create a user
2. Enter the user's username and password into rocket_mirror_config.py
3. Enter the Rocket.Chat server url into the config file
4. Enter the channel id and channel name to be mirrored into the config file

After the steps above have been completed, run `./rocket.chat-mirror` to start the mirroring.
note: Run the script relative to its directory !
