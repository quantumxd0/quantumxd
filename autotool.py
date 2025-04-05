import asyncio
import os
import json
import logging
import gc
import platform
import time
from telethon import TelegramClient, events, functions, types
from telethon.errors import UserDeactivatedBanError, FloodWaitError, ChatWriteForbiddenError
from telethon.tl.functions.messages import GetHistoryRequest, ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.account import UpdateProfileRequest
from colorama import init, Fore, Style
from datetime import datetime
import re

# Initialize colorama for colored output
init(autoreset=True)

# Constants and Configuration
CREDENTIALS_FOLDER = 'sessions'
LOGS_FOLDER = 'logs'
CONFIG_FILE = 'config.json'
VERSION = "1.1.0"
AUTO_REPLY_MESSAGE = """
𝙄𝙩𝙨 𝙖𝙙 𝙖𝙘𝙘𝙤𝙪𝙣𝙩 𝙬𝙤𝙧𝙠𝙞𝙣𝙜 𝙛𝙤𝙧 @quantumsera .. 𝙙𝙢 @quantumsera 𝙛𝙤𝙧 𝙙𝙚𝙖𝙡𝙨!
"""

# Create necessary directories
for folder in [CREDENTIALS_FOLDER, LOGS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Set up logging with timestamped log file
log_filename = f'termuxd_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    filename=os.path.join(LOGS_FOLDER, log_filename),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Color themes
class Colors:
    PRIMARY = Fore.CYAN
    SECONDARY = Fore.MAGENTA
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    WARNING = Fore.YELLOW
    INFO = Fore.WHITE
    BANNER = Fore.CYAN
    HIGHLIGHT = Fore.LIGHTYELLOW_EX

def clear_screen():
    """Clear the terminal screen based on OS."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def display_banner():
    """Display the stylish banner and tool information."""
    clear_screen()
    banner = """
 ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗████████╗██╗   ██╗███╗   ███╗     ██╗  ██╗██████╗ 
██╔═══██╗██║   ██║██╔══██╗████╗  ██║╚══██╔══╝██║   ██║████╗ ████║     ╚██╗██╔╝██╔══██╗
██║   ██║██║   ██║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║█████╗╚███╔╝ ██║  ██║
██║▄▄ ██║██║   ██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║╚════╝██╔██╗ ██║  ██║
╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║     ██╔╝ ██╗██████╔╝
 ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝     ╚═╝  ╚═╝╚═════╝ 
    """
    print(Colors.BANNER + banner)
    print(Colors.HIGHLIGHT + "╔" + "═" * 60 + "╗")
    print(Colors.HIGHLIGHT + "║" + Style.BRIGHT + " TELEGRAM AUTO-FORWARDER & AUTO-REPLY TOOL".center(60) + Colors.HIGHLIGHT + "║")
    print(Colors.HIGHLIGHT + "║" + f" Version: {VERSION} | Created by: @Quantumxd".center(60) + Colors.HIGHLIGHT + "║")
    print(Colors.HIGHLIGHT + "╚" + "═" * 60 + "╝\n")

def display_divider():
    """Display a decorative divider line."""
    print(Colors.SECONDARY + "─" * 70)

def display_menu_header(title):
    """Display a styled menu header."""
    display_divider()
    print(Colors.PRIMARY + Style.BRIGHT + f" {title.upper()} ".center(70, "="))
    display_divider()

def display_status(message, status_type="info"):
    """Display a status message with appropriate styling."""
    color = {
        "success": Colors.SUCCESS, "error": Colors.ERROR, 
        "warning": Colors.WARNING, "info": Colors.INFO
    }.get(status_type, Colors.INFO)
    
    prefix = {
        "success": "[✓]", "error": "[✗]", 
        "warning": "[!]", "info": "[i]"
    }.get(status_type, "[i]")
    
    print(f"{color}{prefix} {message}")
    logging.info(f"{status_type.upper()}: {message}")

def save_config(config):
    """Save configuration to the config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Error saving config: {str(e)}")
        return False

def load_config():
    """Load configuration from the config file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
    return {
        "delay_between_rounds": 600, 
        "auto_reply_enabled": True,
        "auto_reply_message": AUTO_REPLY_MESSAGE
    }

def save_credentials(session_name, credentials):
    """Save session credentials to a JSON file."""
    path = os.path.join(CREDENTIALS_FOLDER, f"{session_name}.json")
    try:
        with open(path, "w") as f:
            json.dump(credentials, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Error saving credentials for {session_name}: {str(e)}")
        return False

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

def load_all_sessions():
    """Load all saved session credentials."""
    sessions = {}
    if os.path.exists(CREDENTIALS_FOLDER):
        for file in os.listdir(CREDENTIALS_FOLDER):
            if file.endswith('.json'):
                session_name = file[:-5]  # Remove .json extension
                credentials = load_credentials(session_name)
                if credentials:
                    sessions[session_name] = credentials
    return sessions

async def get_last_saved_message(client):
    """Retrieve the last message from 'Saved Messages'."""
    try:
        saved_messages_peer = await client.get_input_entity('me')
        history = await client(GetHistoryRequest(
            peer=saved_messages_peer, limit=1, offset_id=0,
            offset_date=None, add_offset=0, max_id=0, min_id=0, hash=0
        ))
        return history.messages[0] if history.messages else None
    except Exception as e:
        logging.error(f"Failed to retrieve saved messages: {str(e)}")
        return None

async def save_message_from_link(client, message_link):
    """Extract message from link and save to Saved Messages."""
    try:
        # Parse the message link
        display_status(f"Attempting to save message from link: {message_link}", "info")
        
        if "t.me/c/" in message_link:
            # Private channel format: t.me/c/channel_id/message_id
            parts = message_link.strip().split('/')
            if len(parts) >= 5:
                try:
                    channel_id_str = parts[4]
                    message_id = int(parts[5])
                    
                    # For private channels, the format is slightly different
                    # The actual channel ID is -100{channel_id_str}
                    channel_id = int("-100" + channel_id_str)
                    
                    # Get the message using InputPeerChannel
                    peer = types.InputPeerChannel(channel_id=channel_id, access_hash=0)
                    message = await client.get_messages(peer, ids=message_id)
                    
                    if message:
                        await client.send_message('me', message)
                        display_status("Message saved to Saved Messages successfully!", "success")
                        return True
                    else:
                        display_status("Message not found at specified link.", "error")
                except ValueError as ve:
                    display_status(f"Invalid channel ID or message ID: {str(ve)}", "error")
                except Exception as e:
                    display_status(f"Error processing private channel link: {str(e)}", "error")
        else:
            # Public channel format: t.me/channel_username/message_id
            parts = message_link.strip().split('/')
            if len(parts) >= 4:
                try:
                    channel_username = parts[3]
                    message_id = int(parts[4])
                    
                    # Get message from public channel
                    channel = await client.get_entity(channel_username)
                    message = await client.get_messages(channel, ids=message_id)
                    
                    if message:
                        await client.send_message('me', message)
                        display_status("Message saved to Saved Messages successfully!", "success")
                        return True
                    else:
                        display_status("Message not found at specified link.", "error")
                except ValueError as ve:
                    display_status(f"Invalid channel username or message ID: {str(ve)}", "error")
                except Exception as e:
                    display_status(f"Error processing public channel link: {str(e)}", "error")
        
        # If we get here, the link format was not recognized or another error occurred
        display_status("Invalid message link format or message not accessible.", "error")
        return False
    except Exception as e:
        logging.error(f"Failed to save message from link: {str(e)}")
        display_status(f"Failed to save message from link: {str(e)}", "error")
        return False
        
async def join_groups(session_name):
    """Join groups for a session using addlist or links."""
    display_menu_header(f"JOIN GROUPS - {session_name}")
    
    try:
        credentials = load_credentials(session_name)
        client = TelegramClient(session_name, credentials["api_id"], credentials["api_hash"])
        await client.start(phone=credentials["phone_number"])
        
        print(f"{Colors.PRIMARY}How would you like to join groups?")
        print(f"{Colors.INFO}1. Join from addlist")
        print(f"{Colors.INFO}2. Join from chat links")
        choice = input(f"{Colors.SECONDARY}Enter your choice (1-2): ")
        
        if choice == "1":
            # Join from addlist link
            addlist_link = input(f"{Colors.PRIMARY}Enter addlist link (e.g., https://t.me/addlist/XYZ): ")
            
            if not addlist_link.startswith("https://t.me/addlist/"):
                display_status("Invalid addlist link format. Should start with https://t.me/addlist/", "error")
                await client.disconnect()
                return False
                
            display_status("Processing addlist link...", "info")
            try:
                # Extract hash from link
                addlist_hash = addlist_link.split('/')[-1]
                
                try:
                    # Join the addlist itself first
                    result = await client(ImportChatInviteRequest(addlist_hash))
                    addlist_chat = result.chats[0]
                    display_status(f"Successfully accessed addlist: {getattr(addlist_chat, 'title', 'Addlist')}", "success")
                    
                    # Get messages from the addlist chat
                    messages = await client.get_messages(addlist_chat, limit=100)
                    
                    # Extract chat links from messages
                    all_links = []
                    for msg in messages:
                        if msg.text:
                            # Find all t.me links in the message
                            found_links = re.findall(r'https?://t\.me/(?:\+)?([a-zA-Z0-9_]+)', msg.text)
                            all_links.extend(found_links)
                            # Also find invite links
                            invite_links = re.findall(r'https?://t\.me/joinchat/([a-zA-Z0-9_-]+)', msg.text)
                            all_links.extend(invite_links)
                    
                    display_status(f"Found {len(all_links)} group links in the addlist", "info")
                    
                    if not all_links:
                        display_status("No group links found in the addlist.", "warning")
                        
                        # Remove addlist if requested
                        remove = input(f"{Colors.PRIMARY}Remove the addlist chat? (y/n): ").lower() == 'y'
                        if remove:
                            await client.delete_dialog(addlist_chat)
                            display_status("Addlist chat removed.", "success")
                            
                        await client.disconnect()
                        return False
                    
                    # Join each group
                    joined_count = 0
                    failed_count = 0
                    
                    display_status("Starting to join groups from addlist...", "info")
                    for link in all_links:
                        try:
                            if "joinchat" in link or link.startswith('+'):
                                # Join private group
                                invite_hash = link.split('/')[-1] if "joinchat" in link else link[1:]
                                await client(ImportChatInviteRequest(invite_hash))
                            else:
                                # Join public group
                                await client(JoinChannelRequest(link))
                                
                            joined_count += 1
                            display_status(f"Joined group {joined_count}: {link}", "success")
                            await asyncio.sleep(2)  # Delay to avoid flood wait
                            
                        except FloodWaitError as e:
                            display_status(f"Rate limit exceeded. Waiting for {e.seconds} seconds.", "warning")
                            await asyncio.sleep(e.seconds)
                            # Try again after waiting
                            try:
                                if "joinchat" in link or link.startswith('+'):
                                    invite_hash = link.split('/')[-1] if "joinchat" in link else link[1:]
                                    await client(ImportChatInviteRequest(invite_hash))
                                else:
                                    await client(JoinChannelRequest(link))
                                joined_count += 1
                                display_status(f"Joined group {joined_count}: {link} after waiting", "success")
                            except Exception as e2:
                                failed_count += 1
                                display_status(f"Failed to join {link} after waiting: {str(e2)}", "error")
                                
                        except Exception as e:
                            failed_count += 1
                            display_status(f"Failed to join {link}: {str(e)}", "error")
                    
                    display_status(f"Successfully joined {joined_count} groups from addlist", "success")
                    display_status(f"Failed to join {failed_count} groups", "warning" if failed_count > 0 else "info")
                    
                    # Remove addlist if requested
                    remove = input(f"{Colors.PRIMARY}Remove the addlist chat? (y/n): ").lower() == 'y'
                    if remove:
                        await client.delete_dialog(addlist_chat)
                        display_status("Addlist chat removed.", "success")
                    
                except Exception as e:
                    display_status(f"Error accessing addlist: {str(e)}", "error")
                    await client.disconnect()
                    return False
                
            except Exception as e:
                display_status(f"Error processing addlist: {str(e)}", "error")
                await client.disconnect()
                return False
                
        elif choice == "2":
            print(f"{Colors.PRIMARY}Enter chat links (one per line, press Enter twice to finish):")
            links = []
            
            # Collect links until empty line
            while True:
                link = input()
                if not link:
                    break
                links.append(link)
            
            if not links:
                display_status("No links provided.", "error")
                await client.disconnect()
                return False
            
            # Process and extract actual usernames/hashes from links
            processed_links = []
            for link in links:
                # Extract public usernames
                public_matches = re.findall(r't\.me/([a-zA-Z0-9_]+)', link)
                processed_links.extend(public_matches)
                
                # Extract private invite hashes
                private_matches = re.findall(r't\.me/(?:joinchat|addlist)/([a-zA-Z0-9_-]+)', link)
                processed_links.extend(private_matches)
            
            if not processed_links:
                display_status("No valid links found.", "error")
                await client.disconnect()
                return False
                
            # Join each group in the list
            joined_count = 0
            failed_count = 0
            
            display_status(f"Attempting to join {len(processed_links)} groups...", "info")
            
            for link in processed_links:
                try:
                    # Determine if it's a private or public group link
                    if re.match(r'^[a-zA-Z0-9_-]{22,}$', link):  # Likely a hash for private groups
                        # Join private group
                        await client(ImportChatInviteRequest(link))
                    else:
                        # Join public group
                        await client(JoinChannelRequest(link))
                        
                    joined_count += 1
                    display_status(f"Joined group {joined_count}: {link}", "success")
                    await asyncio.sleep(2)  # Delay to avoid flood wait
                    
                except FloodWaitError as e:
                    display_status(f"Rate limit exceeded. Waiting for {e.seconds} seconds.", "warning")
                    await asyncio.sleep(e.seconds)
                    # Try again after waiting
                    try:
                        if re.match(r'^[a-zA-Z0-9_-]{22,}$', link):
                            await client(ImportChatInviteRequest(link))
                        else:
                            await client(JoinChannelRequest(link))
                        joined_count += 1
                        display_status(f"Joined group {joined_count}: {link} after waiting", "success")
                    except Exception as e2:
                        failed_count += 1
                        display_status(f"Failed to join {link} after waiting: {str(e2)}", "error")
                        
                except Exception as e:
                    failed_count += 1
                    display_status(f"Failed to join {link}: {str(e)}", "error")
            
            display_status(f"Successfully joined {joined_count} groups from links", "success")
            display_status(f"Failed to join {failed_count} groups", "warning" if failed_count > 0 else "info")
            
        else:
            display_status("Invalid choice.", "error")
            await client.disconnect()
            return False
        
        await client.disconnect()
        return True
        
    except Exception as e:
        display_status(f"Error in join_groups: {str(e)}", "error")
        return False
        
async def forward_messages_to_groups(client, last_message, session_name):
    """Forward the provided message to all groups for this session."""
    try:
        display_status(f"Finding groups for {session_name}...", "info")
        dialogs = await client.get_dialogs()
        group_dialogs = [dialog for dialog in dialogs if dialog.is_group]

        if not group_dialogs:
            display_status(f"No groups found for session {session_name}.", "warning")
            return 0

        display_status(f"Found {len(group_dialogs)} groups for session {session_name}", "info")
        
        # Progress display variables
        total_groups = len(group_dialogs)
        success_count = 0
        failure_count = 0
        
        # Forward message to each group once
        for i, dialog in enumerate(group_dialogs, 1):
            group = dialog.entity
            try:
                # Update progress
                print(f"\r{Colors.INFO}Progress: {i}/{total_groups} groups ({i/total_groups*100:.1f}%) - "
                      f"{Colors.SUCCESS}✓:{success_count} {Colors.ERROR}✗:{failure_count}", end="")
                
                await client.forward_messages(group, last_message)
                success_count += 1
                logging.info(f"Message forwarded to {group.title} using {session_name}")
                await asyncio.sleep(0.5)  # Small delay to prevent aggressive sending
                
            except FloodWaitError as e:
                display_status(f"\nRate limit exceeded for {group.title}. Waiting for {e.seconds} seconds.", "warning")
                await asyncio.sleep(e.seconds)
                try:
                    await client.forward_messages(group, last_message)
                    success_count += 1
                    display_status(f"Message forwarded to {group.title} after waiting.", "success")
                except Exception as e2:
                    failure_count += 1
                    logging.error(f"Failed to forward message to {group.title} after waiting: {str(e2)}")
            except Exception as e:
                failure_count += 1
                logging.error(f"Failed to forward message to {group.title}: {str(e)}")
        
        print("\n")  # Add new line after progress display
        display_status(f"Forwarding summary for {session_name}: "
                      f"Success: {success_count}, Failed: {failure_count}", "info")
        return success_count
    except Exception as e:
        logging.error(f"Unexpected error in forward_messages_to_groups for {session_name}: {str(e)}")
        display_status(f"Error processing groups: {str(e)}", "error")
        return 0

async def process_forward_round_existing(client, session_name, config):
    """Process one forwarding round for an already logged in client."""
    try:
        display_status(f"[{session_name}] Processing auto forwarding round...", "info")
        last_message = await get_last_saved_message(client)
        if last_message:
            count = await forward_messages_to_groups(client, last_message, session_name)
            msg = f"[{session_name}] Forwarding round completed. Messages sent: {count}"
            display_status(msg, "success")
            return session_name, "successful", msg, count
        else:
            msg = f"[{session_name}] No last saved message found."
            display_status(msg, "error")
            return session_name, "failed", msg, 0
    except Exception as e:
        msg = f"Error during forwarding round for {session_name}: {str(e)}"
        display_status(msg, "error")
        return session_name, "failed", msg, 0

async def setup_auto_reply(client, session_name, config):
    """Set up auto-reply to incoming private messages for the client in this round."""
    if not config.get("auto_reply_enabled", True):
        display_status(f"Auto-reply disabled for {session_name} as per configuration", "info")
        return
    
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private:
            try:
                await event.reply(config.get("auto_reply_message", AUTO_REPLY_MESSAGE))
                display_status(f"Replied to {event.sender_id} in session {session_name}", "success")
            except FloodWaitError as e:
                display_status(f"Rate limit exceeded when replying. Waiting for {e.seconds} seconds.", "warning")
                await asyncio.sleep(e.seconds)
                await event.reply(config.get("auto_reply_message", AUTO_REPLY_MESSAGE))
            except Exception as e:
                display_status(f"Failed to reply to {event.sender_id}: {str(e)}", "error")

async def process_round(round_num, sessions_info, config):
    """Process a single forwarding round with detailed progress and status reporting."""
    display_menu_header(f"Auto Forwarding Round {round_num}")
    
    clients = {}
    tasks = []
    round_start_time = time.time()

    # Start new client for each session and set up auto reply
    for session_name, credentials in sessions_info.items():
        try:
            display_status(f"[{session_name}] Logging in for this round...", "info")
            client = TelegramClient(session_name, credentials["api_id"], credentials["api_hash"])
            await client.start(phone=credentials["phone_number"])
            display_status(f"[{session_name}] Logged in successfully.", "success")
            await setup_auto_reply(client, session_name, config)
            clients[session_name] = client
        except UserDeactivatedBanError:
            display_status(f"[{session_name}] Login unsuccessful: This session is banned.", "error")
        except Exception as e:
            display_status(f"[{session_name}] Login unsuccessful: {str(e)}", "error")

    if not clients:
        display_status("No valid accounts available for this round.", "error")
        return 0, 0

    # Process auto forwarding concurrently for all sessions
    for session_name, client in clients.items():
        tasks.append(process_forward_round_existing(client, session_name, config))
    results = await asyncio.gather(*tasks)

    # Summary for the round
    successful_sessions = [r[0] for r in results if r[1] == "successful"]
    failed_sessions = [(r[0], r[2]) for r in results if r[1] == "failed"]
    total_messages_sent = sum(r[3] for r in results)

    display_menu_header(f"Summary for Round {round_num}")
    if successful_sessions:
        display_status("Forwarding successful for sessions: " + ", ".join(successful_sessions), "success")
    if failed_sessions:
        for sess, reason in failed_sessions:
            display_status(f"Forwarding failed for {sess}: {reason}", "error")
    
    round_duration = time.time() - round_start_time
    display_status(f"Round {round_num} completed in {round_duration:.2f} seconds", "info")
    display_status(f"Total messages sent: {total_messages_sent}", "info")

    # Disconnect all clients to kill sessions and clear memory usage
    display_status("Terminating all sessions...", "info")
    disconnect_tasks = []
    for session_name, client in clients.items():
        disconnect_tasks.append(client.disconnect())
    await asyncio.gather(*disconnect_tasks)
    gc.collect()
    display_status(f"Round {round_num} completed and sessions terminated.", "success")
    
    return len(successful_sessions), total_messages_sent

async def add_new_session():
    """Add a new session interactively."""
    display_menu_header("ADD NEW SESSION")
    
    try:
        session_name = input(f"{Colors.PRIMARY}Enter session name (e.g., session1): ")
        api_id = int(input(f"{Colors.PRIMARY}Enter API ID: "))
        api_hash = input(f"{Colors.PRIMARY}Enter API hash: ")
        phone_number = input(f"{Colors.PRIMARY}Enter phone number (with country code): ")
        
        credentials = {
            "api_id": api_id,
            "api_hash": api_hash,
            "phone_number": phone_number,
        }
        
        # Test the connection
        display_status("Testing connection...", "info")
        try:
            client = TelegramClient(session_name, api_id, api_hash)
            await client.start(phone=phone_number)
            await client.disconnect()
            if save_credentials(session_name, credentials):
                display_status(f"Session {session_name} added successfully!", "success")
            else:
                display_status("Failed to save session credentials.", "error")
        except Exception as e:
            display_status(f"Connection test failed: {str(e)}", "error")
            return False
        
        return True
    except Exception as e:
        display_status(f"Error adding session: {str(e)}", "error")
        return False

async def get_group_count(session_name):
    """Get the number of joined groups for a session."""
    try:
        credentials = load_credentials(session_name)
        client = TelegramClient(session_name, credentials["api_id"], credentials["api_hash"])
        await client.start(phone=credentials["phone_number"])
        
        dialogs = await client.get_dialogs()
        group_count = len([d for d in dialogs if d.is_group])
        
        await client.disconnect()
        return group_count
    except Exception as e:
        logging.error(f"Error getting group count for {session_name}: {str(e)}")
        return -1

async def update_profile(session_name):
    """Update profile information for a session."""
    display_menu_header(f"UPDATE PROFILE - {session_name}")
    
    try:
        credentials = load_credentials(session_name)
        client = TelegramClient(session_name, credentials["api_id"], credentials["api_hash"])
        await client.start(phone=credentials["phone_number"])
        
        first_name = input(f"{Colors.PRIMARY}Enter new first name (leave empty to skip): ")
        last_name = input(f"{Colors.PRIMARY}Enter new last name (leave empty to skip): ")
        bio = input(f"{Colors.PRIMARY}Enter new bio (leave empty to skip): ")
        
        update_fields = {}
        if first_name:
            update_fields['first_name'] = first_name
        if last_name:
            update_fields['last_name'] = last_name
        if bio:
            update_fields['about'] = bio
            
        if update_fields:
            await client(UpdateProfileRequest(**update_fields))
            display_status("Profile updated successfully!", "success")
        
        # Save message from link option
        save_msg = input(f"{Colors.PRIMARY}Update saved message from link? (y/n): ").lower() == 'y'
        if save_msg:
            link = input(f"{Colors.PRIMARY}Enter Telegram message link: ")
            if await save_message_from_link(client, link):
                display_status("Message saved successfully!", "success")
            else:
                display_status("Failed to save message from link.", "error")
        
        await client.disconnect()
        return True
    except Exception as e:
        display_status(f"Error updating profile: {str(e)}", "error")
        await client.disconnect() if 'client' in locals() else None
        return False


        await client.disconnect()
        return True
    except Exception as e:
        display_status(f"Error joining groups: {str(e)}", "error")
        await client.disconnect() if 'client' in locals() else None
        return False

async def manage_sessions():
    """View, add, or remove sessions."""
    while True:
        display_menu_header("SESSION MANAGEMENT")
        sessions = load_all_sessions()
        
        print(f"{Colors.PRIMARY}Available Sessions:")
        if not sessions:
            print(f"{Colors.WARNING}No sessions found.")
        else:
            for i, (name, _) in enumerate(sessions.items(), 1):
                group_count = await get_group_count(name)
                group_info = f" ({group_count} groups)" if group_count >= 0 else ""
                print(f"{Colors.INFO}{i}. {name}{group_info}")
        
        print(f"\n{Colors.HIGHLIGHT}Select an option:")
        print(f"{Colors.PRIMARY}1. {Style.BRIGHT}ADD NEW SESSION")
        print(f"{Colors.PRIMARY}2. {Style.BRIGHT}REMOVE SESSION")
        print(f"{Colors.PRIMARY}3. {Style.BRIGHT}UPDATE PROFILE & SAVED MESSAGE")
        print(f"{Colors.PRIMARY}4. {Style.BRIGHT}JOIN GROUPS")
        print(f"{Colors.PRIMARY}5. {Style.BRIGHT}BACK TO MAIN MENU")
        
        choice = input(f"\n{Colors.SECONDARY}Enter your choice (1-5): ")
        
        if choice == "1":
            await add_new_session()
        elif choice == "2":
            if not sessions:
                display_status("No sessions available to remove.", "warning")
                await asyncio.sleep(2)
                continue
                
            session_list = list(sessions.keys())
            for i, name in enumerate(session_list, 1):
                print(f"{Colors.INFO}{i}. {name}")
            
            try:
                idx = int(input(f"{Colors.PRIMARY}Enter the number of the session to remove: ")) - 1
                if 0 <= idx < len(session_list):
                    session_to_remove = session_list[idx]
                    path = os.path.join(CREDENTIALS_FOLDER, f"{session_to_remove}.json")
                    session_file = f"{session_to_remove}.session"
                    
                    if os.path.exists(path):
                        os.remove(path)
                    if os.path.exists(session_file):
                        os.remove(session_file)
                    
                    display_status(f"Session {session_to_remove} removed successfully!", "success")
                else:
                    display_status("Invalid selection.", "error")
            except Exception as e:
                display_status(f"Error: {str(e)}", "error")
        elif choice == "3":
            if not sessions:
                display_status("No sessions available to update.", "warning")
                await asyncio.sleep(2)
                continue
                
            session_list = list(sessions.keys())
            for i, name in enumerate(session_list, 1):
                print(f"{Colors.INFO}{i}. {name}")
            
            try:
                idx = int(input(f"{Colors.PRIMARY}Enter the number of the session to update: ")) - 1
                if 0 <= idx < len(session_list):
                    await update_profile(session_list[idx])
                else:
                    display_status("Invalid selection.", "error")
            except Exception as e:
                display_status(f"Error: {str(e)}", "error")
        elif choice == "4":
            if not sessions:
                display_status("No sessions available for joining groups.", "warning")
                await asyncio.sleep(2)
                continue
                
            session_list = list(sessions.keys())
            for i, name in enumerate(session_list, 1):
                print(f"{Colors.INFO}{i}. {name}")
            
            try:
                idx = int(input(f"{Colors.PRIMARY}Enter the number of the session to join groups: ")) - 1
                if 0 <= idx < len(session_list):
                    await join_groups(session_list[idx])
                else:
                    display_status("Invalid selection.", "error")
            except Exception as e:
                display_status(f"Error: {str(e)}", "error")
        elif choice == "5":
            break
        else:
            display_status("Invalid choice. Please try again.", "warning")
        
        await asyncio.sleep(1)

async def configure_settings():
    """Configure application settings."""
    config = load_config()
    
    while True:
        display_menu_header("SETTINGS")
        print(f"{Colors.PRIMARY}Current Settings:")
        print(f"{Colors.INFO}1. Delay between rounds: {config.get('delay_between_rounds', 600)} seconds")
        print(f"{Colors.INFO}2. Auto-reply enabled: {'Yes' if config.get('auto_reply_enabled', True) else 'No'}")
        print(f"{Colors.INFO}3. Auto-reply message: (Preview)")
        print(f"{Colors.SECONDARY}{config.get('auto_reply_message', AUTO_REPLY_MESSAGE)}")
        print(f"\n{Colors.PRIMARY}4. {Style.BRIGHT}SAVE SETTINGS")
        print(f"{Colors.PRIMARY}5. {Style.BRIGHT}BACK TO MAIN MENU")
        
        choice = input(f"\n{Colors.SECONDARY}Enter your choice (1-5): ")
        
        if choice == "1":
            try:
                delay = int(input(f"{Colors.PRIMARY}Enter delay between rounds (in seconds): "))
                if delay < 60:
                    display_status("Delay should be at least 60 seconds to avoid rate limits", "warning")
                else:
                    config["delay_between_rounds"] = delay
                    display_status(f"Delay set to {delay} seconds", "success")
            except ValueError:
                display_status("Please enter a valid number", "error")
        elif choice == "2":
            toggle = input(f"{Colors.PRIMARY}Enable auto-reply? (y/n): ").lower() == 'y'
            config["auto_reply_enabled"] = toggle
            display_status(f"Auto-reply {'enabled' if toggle else 'disabled'}", "success")
        elif choice == "3":
            print(f"{Colors.PRIMARY}Enter new auto-reply message (press Enter twice to finish):")
            message_lines = []
            while True:
                line = input()
                message_lines.append(line)
                if line == "":
                    break
            
            # Join with newlines except the last empty line
            new_message = "\n".join(message_lines[:-1])
            if new_message:  # Don't update if empty
                config["auto_reply_message"] = new_message
                display_status("Auto-reply message updated", "success")
        elif choice == "4":
            if save_config(config):
                display_status("Settings saved successfully!", "success")
            else:
                display_status("Failed to save settings", "error")
        elif choice == "5":
            break
        else:
            display_status("Invalid choice. Please try again.", "warning")
        
        await asyncio.sleep(1)

async def start_auto_forwarder():
    """Start the auto-forwarding process."""
    display_menu_header("AUTO FORWARDING SESSION")
    config = load_config()
    sessions = load_all_sessions()
    
    if not sessions:
        display_status("No sessions found. Please add a session first.", "error")
        await asyncio.sleep(2)
        return
    
    try:
        rounds = int(input(f"{Colors.PRIMARY}Enter number of rounds (0 for infinite): "))
    except ValueError:
        display_status("Invalid input. Using default: 1 round", "warning")
        rounds = 1
    
    round_num = 1
    total_successful_sessions = 0
    total_messages_sent = 0
    
    try:
        while rounds == 0 or round_num <= rounds:
            display_status(f"Starting round {round_num}...", "info")
            successful, messages = await process_round(round_num, sessions, config)
            total_successful_sessions += successful
            total_messages_sent += messages
            
            if rounds == 0 or round_num < rounds:
                delay = config.get("delay_between_rounds", 600)
                display_status(f"Waiting {delay} seconds until next round...", "info")
                for i in range(delay, 0, -10):
                    print(f"\r{Colors.INFO}Next round in: {i} seconds remaining  ", end="")
                    await asyncio.sleep(10)
                print("\r" + " " * 50 + "\r", end="")  # Clear the countdown line
            
            round_num += 1
    except KeyboardInterrupt:
        display_status("Auto-forwarding stopped by user", "warning")
    finally:
        display_menu_header("AUTO FORWARDING SUMMARY")
        display_status(f"Total rounds completed: {round_num - 1}", "info")
        display_status(f"Total successful sessions: {total_successful_sessions}", "info")
        display_status(f"Total messages sent: {total_messages_sent}", "info")
        
        input(f"\n{Colors.SECONDARY}Press Enter to return to main menu...")

async def main():
    """Main application function."""
    while True:
        display_banner()
        print(f"{Colors.HIGHLIGHT}MAIN MENU")
        print(f"{Colors.PRIMARY}1. {Style.BRIGHT}START AUTO FORWARDER")
        print(f"{Colors.PRIMARY}2. {Style.BRIGHT}MANAGE SESSIONS")
        print(f"{Colors.PRIMARY}3. {Style.BRIGHT}SETTINGS")
        print(f"{Colors.PRIMARY}4. {Style.BRIGHT}EXIT")
        
        choice = input(f"\n{Colors.SECONDARY}Enter your choice (1-4): ")
        
        if choice == "1":
            await start_auto_forwarder()
        elif choice == "2":
            await manage_sessions()
        elif choice == "3":
            await configure_settings()
        elif choice == "4":
            display_status("Thank you for using our tool. Goodbye!", "info")
            break
        else:
            display_status("Invalid choice. Please try again.", "warning")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Program terminated by user.")
    except Exception as e:
        print(f"\n{Colors.ERROR}Unhandled error: {str(e)}")
        logging.critical(f"Unhandled error: {str(e)}")
        
