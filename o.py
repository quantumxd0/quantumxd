import asyncio
import os
import json
import logging
import gc
from telethon import TelegramClient, events
from telethon.errors import UserDeactivatedBanError, FloodWaitError
from telethon.tl.functions.messages import GetHistoryRequest
from colorama import init, Fore
import pyfiglet

# Initialize colorama for colored output
init(autoreset=True)

# Define session folder
CREDENTIALS_FOLDER = 'sessions'
os.makedirs(CREDENTIALS_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(
    filename='og_flame_service.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Auto-reply message text
AUTO_REPLY_MESSAGE =  """
𝐀𝐧𝐭𝐢-𝐒𝐩𝐚𝐦 𝐖𝐚𝐫𝐧𝐢𝐧𝐠 𝐖𝐞 𝐚𝐫𝐞 𝐍𝐎𝐓 𝐬𝐩𝐚𝐦𝐦𝐢𝐧𝐠 𝐢𝐧 𝐠𝐫𝐨𝐮𝐩𝐬! 𝐄𝐯𝐞𝐫𝐲𝐭𝐡𝐢𝐧𝐠 𝐰𝐞 𝐝𝐨 𝐢𝐬 𝐥𝐞𝐠𝐢𝐭. 𝐁𝐞𝐰𝐚𝐫𝐞 𝐨𝐟 𝐟𝐚𝐥𝐬𝐞 𝐜𝐥𝐚𝐢𝐦𝐬! 

𝐀𝐃 𝐑𝐔𝐍 𝐁𝐘- @oppenheimerxz ✅️

𝐃𝐌:- @oppenheimerxz 𝐟𝐨𝐫 𝐝𝐞𝐚𝐥𝐬!🛍
"""

def display_banner():
    """Display the banner using pyfiglet."""
    print(Fore.RED + pyfiglet.figlet_format("Quantumxd"))
    print(Fore.GREEN + "Made by @Quantumxd\n")

def save_credentials(session_name, credentials):
    """Save session credentials to a JSON file."""
    path = os.path.join(CREDENTIALS_FOLDER, f"{session_name}.json")
    try:
        with open(path, "w") as f:
            json.dump(credentials, f)
    except Exception as e:
        logging.error(f"Error saving credentials for {session_name}: {str(e)}")

def load_credentials(session_name):
    """Load session credentials from a JSON file."""
    path = os.path.join(CREDENTIALS_FOLDER, f"{session_name}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading credentials for {session_name}: {str(e)}")
    return {}

async def get_last_saved_message(client):
    """Retrieve the last message from 'Saved Messages'."""
    try:
        saved_messages_peer = await client.get_input_entity('me')
        history = await client(GetHistoryRequest(
            peer=saved_messages_peer,
            limit=1,
            offset_id=0,
            offset_date=None,
            add_offset=0,
            max_id=0,
            min_id=0,
            hash=0
        ))
        return history.messages[0] if history.messages else None
    except Exception as e:
        logging.error(f"Failed to retrieve saved messages: {str(e)}")
        return None

async def forward_messages_to_groups(client, last_message, session_name):
    """
    Forward the provided message to all groups for this session.
    """
    try:
        dialogs = await client.get_dialogs()
        group_dialogs = [dialog for dialog in dialogs if dialog.is_group]

        if not group_dialogs:
            logging.warning(f"No groups found for session {session_name}.")
            return

        print(Fore.CYAN + f"Found {len(group_dialogs)} groups for session {session_name}")

        # Forward message to each group once
        for dialog in group_dialogs:
            group = dialog.entity
            try:
                await client.forward_messages(group, last_message)
                print(Fore.GREEN + f"Message forwarded to {group.title} using {session_name}")
                logging.info(f"Message forwarded to {group.title} using {session_name}")
            except FloodWaitError as e:
                print(Fore.RED + f"Rate limit exceeded for {group.title}. Waiting for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                await client.forward_messages(group, last_message)
                print(Fore.GREEN + f"Message forwarded to {group.title} after waiting.")
            except Exception as e:
                print(Fore.RED + f"Failed to forward message to {group.title}: {str(e)}")
                logging.error(f"Failed to forward message to {group.title}: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error in forward_messages_to_groups for {session_name}: {str(e)}")

async def process_forward_round_existing(client, session_name):
    """
    Process one forwarding round for an already logged in client.
    Retrieves the last saved message and forwards it to all groups.
    Returns status tuple: (session_name, status, message)
    """
    try:
        print(Fore.CYAN + f"[{session_name}] Processing auto forwarding round...")
        last_message = await get_last_saved_message(client)
        if last_message:
            await forward_messages_to_groups(client, last_message, session_name)
            msg = f"[{session_name}] Forwarding round completed."
            print(Fore.GREEN + msg)
            logging.info(msg)
            return session_name, "successful", msg
        else:
            msg = f"[{session_name}] No last saved message found."
            print(Fore.RED + msg)
            logging.warning(msg)
            return session_name, "failed", msg
    except Exception as e:
        msg = f"Error during forwarding round for {session_name}: {str(e)}"
        print(Fore.RED + msg)
        logging.error(msg)
        return session_name, "failed", msg

async def setup_auto_reply(client, session_name):
    """Set up auto-reply to incoming private messages for the client in this round."""
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private:
            try:
                await event.reply(AUTO_REPLY_MESSAGE)
                print(Fore.GREEN + f"Replied to {event.sender_id} in session {session_name}")
                logging.info(f"Replied to {event.sender_id} in session {session_name}")
            except FloodWaitError as e:
                print(Fore.RED + f"Rate limit exceeded when replying. Waiting for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                await event.reply(AUTO_REPLY_MESSAGE)
            except Exception as e:
                print(Fore.RED + f"Failed to reply to {event.sender_id}: {str(e)}")
                logging.error(f"Failed to reply to {event.sender_id}: {str(e)}")

async def process_round(round_num, sessions_info):
    """Process a single forwarding round:
       - Start new TelegramClient for each session.
       - Set up auto reply (active only during this round).
       - Process auto forwarding.
       - Disconnect all clients to release resources.
    """
    print(Fore.YELLOW + f"\n=== Starting Auto Forwarding Round {round_num} ===")
    clients = {}
    tasks = []

    # Start new client for each session and set up auto reply.
    for session_name, credentials in sessions_info.items():
        try:
            client = TelegramClient(session_name, credentials["api_id"], credentials["api_hash"])
            print(Fore.CYAN + f"[{session_name}] Logging in for this round...")
            await client.start(phone=credentials["phone_number"])
            print(Fore.GREEN + f"[{session_name}] Logged in successfully.")
            await setup_auto_reply(client, session_name)
            clients[session_name] = client
        except UserDeactivatedBanError:
            msg = f"[{session_name}] Login unsuccessful: This session is banned."
            print(Fore.RED + msg)
            logging.warning(msg)
        except Exception as e:
            msg = f"[{session_name}] Login unsuccessful: {str(e)}"
            print(Fore.RED + msg)
            logging.error(msg)

    if not clients:
        print(Fore.RED + "No valid accounts available for this round.")
        return

    # Process auto forwarding concurrently for all sessions.
    for session_name, client in clients.items():
        tasks.append(process_forward_round_existing(client, session_name))
    results = await asyncio.gather(*tasks)

    # Summary for the round
    successful_sessions = [r[0] for r in results if r[1] == "successful"]
    failed_sessions = [(r[0], r[2]) for r in results if r[1] == "failed"]

    print(Fore.GREEN + f"\n=== Summary for Round {round_num} ===")
    if successful_sessions:
        print(Fore.GREEN + "Forwarding successful for sessions: " + ", ".join(successful_sessions))
    if failed_sessions:
        for sess, reason in failed_sessions:
            print(Fore.RED + f"Forwarding failed for {sess}: {reason}")

    # Disconnect all clients to kill sessions and clear memory usage
    disconnect_tasks = []
    for session_name, client in clients.items():
        disconnect_tasks.append(client.disconnect())
    await asyncio.gather(*disconnect_tasks)
    gc.collect()
    print(Fore.GREEN + f"=== Round {round_num} completed and sessions terminated. ===")

async def main():
    """Main function to handle auto forwarding rounds with integrated auto reply.
       Sessions are restarted every round.
    """
    display_banner()
    try:
        num_sessions = int(input("Enter the number of sessions: "))
        if num_sessions <= 0:
            print(Fore.RED + "Number of sessions must be greater than 0.")
            return

        # Gather credentials for all sessions
        sessions_info = {}
        for i in range(1, num_sessions + 1):
            session_name = f"session{i}"
            credentials = load_credentials(session_name)
            if credentials:
                msg = f"[{session_name}] Loaded credentials successfully."
                print(Fore.GREEN + msg)
                logging.info(msg)
            else:
                try:
                    api_id = int(input(Fore.CYAN + f"Enter API ID for {session_name}: "))
                    api_hash = input(Fore.CYAN + f"Enter API hash for {session_name}: ")
                    phone_number = input(Fore.CYAN + f"Enter phone number for {session_name}: ")
                except Exception as e:
                    err_msg = f"Invalid input for {session_name}: {str(e)}"
                    print(Fore.RED + err_msg)
                    logging.error(err_msg)
                    continue

                credentials = {
                    "api_id": api_id,
                    "api_hash": api_hash,
                    "phone_number": phone_number,
                }
                save_credentials(session_name, credentials)
                msg = f"[{session_name}] Credentials saved successfully."
                print(Fore.GREEN + msg)
                logging.info(msg)
            sessions_info[session_name] = credentials

        if not sessions_info:
            print(Fore.RED + "No valid session credentials available to proceed.")
            return

        try:
            rounds = int(input(Fore.MAGENTA + "Enter number of auto forwarding rounds (must be greater than 0, use a high number for indefinite rounds): "))
            if rounds <= 0:
                print(Fore.RED + "Rounds must be greater than 0.")
                return
        except Exception as e:
            print(Fore.RED + f"Invalid rounds input: {str(e)}")
            return

        try:
            delay_between_rounds = int(input(Fore.MAGENTA + "Enter delay (in seconds) between rounds: "))
        except Exception as e:
            print(Fore.RED + f"Invalid delay input: {str(e)}")
            return

        # Run auto forwarding rounds.
        current_round = 1
        while current_round <= rounds:
            await process_round(current_round, sessions_info)
            if current_round < rounds:
                print(Fore.GREEN + f"Waiting {delay_between_rounds} seconds before starting the next round...")
                await asyncio.sleep(delay_between_rounds)
            current_round += 1

        print(Fore.CYAN + "\nAuto forwarding rounds completed.")
        print(Fore.CYAN + "The script will now terminate. To run indefinitely, input a high number for rounds.")
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nScript terminated by user.")
    except Exception as e:
        print(Fore.RED + f"An error occurred in main: {str(e)}")
        logging.error(f"Main error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
    

