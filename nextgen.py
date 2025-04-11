import asyncio
import os
import json
import logging
import gc
import platform
import time
import psutil
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

def clear_memory():
    """Force garbage collection and clear memory."""
    gc.collect()
    
    # Try to clear memory more aggressively if psutil is available
    try:
        process = psutil.Process(os.getpid())
        for _ in range(3):  # Try multiple times for better results
            gc.collect()
            
        display_status(f"Memory cleared. Current usage: {process.memory_info().rss / 1024 / 1024:.2f} MB", "info")
    except ImportError:
        display_status("Psutil not available, using basic memory cleanup", "warning")
    except Exception as e:
        logging.error(f"Error during memory cleanup: {str(e)}")

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
                
            # Periodically clear memory during forwarding
            if i % 50 == 0:
                gc.collect()
        
        print("\n")  # Add new line after progress display
        display_status(f"Forwarding summary for {session_name}: "
                      f"Success: {success_count}, Failed: {failure_count}", "info")
        return success_count
    except Exception as e:
        logging.error(f"Unexpected error in forward_messages_to_groups for {session_name}: {str(e)}")
        display_status(f"Error processing groups: {str(e)}", "error")
        return 0

async def process_single_session(session_name, credentials, config):
    """Process forwarding for a single session and clean up properly."""
    client = None
    messages_sent = 0
    result_status = "failed"
    result_message = ""
    
    try:
        # Create a fresh client and log in
        display_status(f"[{session_name}] Logging in...", "info")
        client = TelegramClient(session_name, credentials["api_id"], credentials["api_hash"])
        await client.start(phone=credentials["phone_number"])
        display_status(f"[{session_name}] Logged in successfully.", "success")
        
        # Setup auto-reply if enabled
        if config.get("auto_reply_enabled", True):
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
        
        # Get the last saved message
        display_status(f"[{session_name}] Retrieving last saved message...", "info")
        last_message = await get_last_saved_message(client)
        
        if last_message:
            # Forward to all groups
            messages_sent = await forward_messages_to_groups(client, last_message, session_name)
            result_status = "successful"
            result_message = f"[{session_name}] Forwarding completed. Messages sent: {messages_sent}"
            display_status(result_message, "success")
        else:
            result_message = f"[{session_name}] No last saved message found."
            display_status(result_message, "error")
            
    except UserDeactivatedBanError:
        result_message = f"[{session_name}] This account is banned."
        display_status(result_message, "error")
    except Exception as e:
        result_message = f"Error during forwarding for {session_name}: {str(e)}"
        display_status(result_message, "error")
    finally:
        # Properly disconnect client and clean up
        if client:
            display_status(f"[{session_name}] Disconnecting client...", "info")
            try:
                await client.disconnect()
                display_status(f"[{session_name}] Client disconnected properly.", "success")
            except Exception as e:
                logging.error(f"Error disconnecting client for {session_name}: {str(e)}")
        
        # Force garbage collection for this session
        client = None
        last_message = None
        clear_memory()
        
    return session_name, result_status, result_message, messages_sent

async def process_round(round_num, sessions_info, config):
    """Process a single forwarding round with parallel forwarding across sessions."""
    display_menu_header(f"Auto Forwarding Round {round_num}")
    
    round_start_time = time.time()
    total_messages_sent = 0
    successful_sessions = []
    failed_sessions = []
    
    # Load all sessions at once
    clients = {}
    last_messages = {}
    display_status(f"Loading all {len(sessions_info)} sessions at once...", "info")
    
    # First, initialize all clients and get their last messages
    for session_name, credentials in sessions_info.items():
        try:
            # Create client and log in
            display_status(f"[{session_name}] Logging in...", "info")
            client = TelegramClient(session_name, credentials["api_id"], credentials["api_hash"])
            await client.start(phone=credentials["phone_number"])
            
            # Setup auto-reply if enabled
            if config.get("auto_reply_enabled", True):
                @client.on(events.NewMessage(incoming=True))
                async def handler(event):
                    if event.is_private:
                        try:
                            await event.reply(config.get("auto_reply_message", AUTO_REPLY_MESSAGE))
                            display_status(f"Replied to {event.sender_id} in session {session_name}", "success")
                        except Exception as e:
                            display_status(f"Failed to reply to {event.sender_id}: {str(e)}", "error")
            
            # Get last saved message
            last_message = await get_last_saved_message(client)
            if last_message:
                clients[session_name] = client
                last_messages[session_name] = last_message
                display_status(f"[{session_name}] Loaded successfully with last saved message", "success")
            else:
                display_status(f"[{session_name}] No last saved message found", "error")
                await client.disconnect()
        except Exception as e:
            display_status(f"Failed to load {session_name}: {str(e)}", "error")
            failed_sessions.append((session_name, f"Failed to load: {str(e)}"))
    
    if not clients:
        display_status("No sessions could be loaded. Aborting round.", "error")
        return 0, 0
    
    display_status(f"Successfully loaded {len(clients)}/{len(sessions_info)} sessions", "info")
    
    # Create tasks for parallel forwarding
    forwarding_tasks = []
    for session_name, client in clients.items():
        task = asyncio.create_task(
            forward_messages_to_groups(client, last_messages[session_name], session_name)
        )
        forwarding_tasks.append((session_name, task))
    
    # Wait for all forwarding tasks to complete
    display_status(f"Starting parallel forwarding for {len(forwarding_tasks)} sessions...", "info")
    for session_name, task in forwarding_tasks:
        try:
            messages_sent = await task
            total_messages_sent += messages_sent
            if messages_sent > 0:
                successful_sessions.append(session_name)
                display_status(f"[{session_name}] Forwarded {messages_sent} messages successfully", "success")
            else:
                failed_sessions.append((session_name, "No messages were sent"))
                display_status(f"[{session_name}] No messages were sent", "warning")
        except Exception as e:
            failed_sessions.append((session_name, str(e)))
            display_status(f"[{session_name}] Error during forwarding: {str(e)}", "error")
    
    # Disconnect all clients
    for session_name, client in clients.items():
        try:
            await client.disconnect()
            display_status(f"[{session_name}] Disconnected successfully", "success")
        except Exception as e:
            display_status(f"Error disconnecting {session_name}: {str(e)}", "error")
    
    # Show final round summary
    display_menu_header(f"Summary for Round {round_num}")
    if successful_sessions:
        display_status("Forwarding successful for sessions: " + ", ".join(successful_sessions), "success")
    if failed_sessions:
        for sess, reason in failed_sessions:
            display_status(f"Forwarding failed for {sess}: {reason}", "error")
    
    round_duration = time.time() - round_start_time
    display_status(f"Round {round_num} completed in {round_duration:.2f} seconds", "info")
    display_status(f"Total messages sent: {total_messages_sent}", "info")
    
    # Final memory cleanup after the round
    clients = {}
    last_messages = {}
    clear_memory()
    display_status("Memory cleared after round completion", "success")
    
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
        clear_memory()
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
        clear_memory()
        return True
    except Exception as e:
        display_status(f"Error updating profile: {str(e)}", "error")
        if 'client' in locals() and client:
            await client.disconnect()
        clear_memory()
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
        print(f"{Colors.PRIMARY}4. {Style.BRIGHT}BACK TO MAIN MENU")
        
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
            break
        else:
            display_status("Invalid choice. Please try again.", "warning")
        
        clear_memory()
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
            
            # Clear screen and memory after round
            clear_screen()
            clear_memory()
            display_banner()
            
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
        
        # Clear memory after each major operation
        clear_memory()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Program terminated by user.")
    except Exception as e:
        print(f"\n{Colors.ERROR}Unhandled error: {str(e)}")
        logging.critical(f"Unhandled error: {str(e)}")
        