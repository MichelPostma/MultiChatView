import threading                                                            #Used for running both YouTube and Twitch processes on different threads
import socket                                                               #Used for connecting to Twitch IRC chat    
import re                                                                   #Used to extract chat messages from Twitch IRC chat                    
import tkinter as tk                                                        #Used for window creation
from tkinter import scrolledtext, Toplevel, colorchooser, PhotoImage        #Used to make scrolling chat window, options windows, colored background, window image
import pickle                                                               #Used to create Google token files
import os                                                                   #Used to open and save files
from google_auth_oauthlib.flow import InstalledAppFlow                      #Used to connect to YouTube API for posting
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from selenium import webdriver                                              #Used to create webbrowser to read YouTube chat
from selenium.webdriver.firefox.service import Service                      #Used to allow Firefox selection
from selenium.webdriver.firefox.options import Options                      #Used to set headless operation
from webdriver_manager.firefox import GeckoDriverManager                    #Used to run Firefox
import time                                                                 #Used to pauze YouTube chat refreshes
from bs4 import BeautifulSoup                                               #Used to parse HTML output
from datetime import datetime, date                                         #Used to timestamp YouTube messages

#Future Updates (01-02-2024)
#Error handling of token expiration : RequestError -> Pop-up window that asks or enables deletion of token.pkl
#Error handling of offline stream: KeyError: activeLiveChatID -> Pop-up before going to chat w/ posting to say that stream is not live

#############################################
####      PARAMETER ADJUSTMENTS          ####
#############################################

# Saves Parameters to config.txt
def save_values():
    #Grab all the user-changeable global variables
    global  geometry, font_type, font_size
    #Resave some Variables to ensure they get saved properly
    geometry = geometry_var.get()
    font_type = font_type_var.get()
    font_size = font_size_var.get() 
    #Save the variables to a config.txt file
    with open(CONFIG_FILE, "w") as file:
        file.write(f"{nickname}\n{token}\n{channel}\n{target_id}\n{geometry}\n{bg_color}\n{start_bg}\n{font_type}\n{font_size}\n{font_color}\n{yt_color}\n{twitch_color}\n{post_enabled}")

# Retrieves Saved Parameters from config.txt
def get_saved_values():
    #Retrieve the user variables from the config.txt file if it exists
    try:
        with open(CONFIG_FILE, "r") as file:
            config_data = file.read().splitlines()
        return config_data
    #Default Values for when Config.txt does not yet exist
    except FileNotFoundError:
        return ["username", "token", "#twitchchannel", "yt-id", "450x800", "#052900", "#191b26", "Futura", "18", "white", "red", "purple", "Yes"]  

#Adjustment Menu with related Functions
def edit_window():
    global geometry, bg_color, start_bg, font_type, font_size, font_color, yt_color, twitch_color, root
    edit = Toplevel()
    edit.config(background=start_bg)

    # Background Color Menu
    tk.Label(edit, text="Background Color Menu:", bg=start_bg, fg=font_color,
             font=(font_type, font_size, "bold"), padx=10, pady=8).pack()
    color_button_menu = tk.Button(edit, text="Select", command=lambda: color_pick_menu(edit))
    color_button_menu.pack()

    # Background Color Chat
    tk.Label(edit, text="Background Color Chat:", bg=start_bg, fg=font_color,
             font=(font_type, font_size, "bold"), padx=10, pady=8).pack()
    color_button_chat = tk.Button(edit, text="Select", command=color_pick_chat, state=tk.NORMAL)
    color_button_chat.pack()

    # Window Resolution
    tk.Label(edit, text="Window Resolution:", bg=start_bg, fg=font_color,
        font=(font_type, font_size, "bold"),padx=10, pady=8).pack()
    tk.Entry(edit, textvariable=geometry_var,).pack()

    # Font
    tk.Label(edit, text="Font:", bg=start_bg, fg=font_color,
        font=(font_type, font_size, "bold"),padx=10, pady=8).pack()
    tk.Entry(edit, textvariable=font_type_var,).pack()

    # Font Size
    tk.Label(edit, text="Font Size:", bg=start_bg, fg=font_color,
             font=(font_type, font_size, "bold"), padx=10, pady=8).pack()
    tk.Scale(edit, from_=4, to=40, orient=tk.HORIZONTAL, length=200,
                               variable=font_size_var).pack()

    # Font Color
    tk.Label(edit, text="Font Color:", bg=start_bg, fg=font_color,
             font=(font_type, font_size, "bold"), padx=10, pady=8).pack()
    color_button_font = tk.Button(edit, text="Select", command=color_pick_font)
    color_button_font.pack()

    # YouTube Color
    tk.Label(edit, text="YouTube Color:", bg=start_bg, fg=font_color,
             font=(font_type, font_size, "bold"), padx=10, pady=8).pack()
    color_button_yt = tk.Button(edit, text="Select", command=color_pick_yt)
    color_button_yt.pack()

    # Twitch Color
    tk.Label(edit, text="Twitch Color:", bg=start_bg, fg=font_color,
             font=(font_type, font_size, "bold"), padx=10, pady=8).pack()
    color_button_twitch = tk.Button(edit, text="Select", command=color_pick_twitch)
    color_button_twitch.pack()

    tk.Button(edit, text="Save", command=save_values).pack(pady=20)

def color_pick_menu(edit):
    global start_bg, root
    start_bg = colorchooser.askcolor()[1]
    root.config(background=start_bg)

def color_pick_chat():
    global bg_color, root
    bg_color = colorchooser.askcolor()[1]
    root.config(background=bg_color)

def color_pick_font():
    global font_color
    font_color = colorchooser.askcolor()[1]

def color_pick_yt():
    global yt_color
    yt_color = colorchooser.askcolor()[1]

def color_pick_twitch():
    global twitch_color
    twitch_color = colorchooser.askcolor()[1]

#############################################
####      Twitch Chat + Connect          ####
#############################################

# Connects to Twitch IRC via Sockets 
def twitch_connect():
    global sock
    # Establish Socket
    sock = socket.socket()
    sock.connect((SERVER, PORT))                        #Uses Set Connnection Parameters               
    # Send Identification
    sock.send(f"PASS {token}\n".encode('utf-8'))        #Uses Personal OAuth Token from Twitch
    sock.send(f"NICK {nickname}\n".encode('utf-8'))     #Uses Personal Nickname related to OAuth account
    sock.send(f"JOIN {channel}\n".encode('utf-8'))      #Uses Target Twitch channel for Chat
    return sock   

#Retrieves Messages From Twitch Chat
def twitch_chat():
    while True:                                         #As long as the program is running
        resp = sock.recv(2048).decode('utf-8')          #Check for a response
        if resp.startswith('PING'):                     #To keep up connection: respond to any PING messages with PONG
            sock.send("PONG\n".encode('utf-8'))
        elif len(resp) > 0:                             #If a message exists, match it with the chat message structure
            raw = resp.strip()
            match = re.match(r':([^!]+)![^@]+@[^.]+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.*)', raw)
            if match:                                   #If a chat message is found, extract the username and message
                name, message = match.groups()
                message = f": {message}\n"
                root.after(10, update_display, name, message, "twitch")  #Sends name, message and platform indicator to update function


#############################################
####      YouTube Chat + Connect         ####
#############################################

#Returns the API ID for the Livestream based on LS Video ID (in URL)
def get_live_id(ext_id): 
    resp = yt.videos().list(
        part='liveStreamingDetails',
        id=[ext_id]).execute()
    return(resp['items'][0]['liveStreamingDetails']['activeLiveChatId'])

def connect_yt_api():
    #Setup YouTube Connection for API access (Posting Messages to Chat)
    global creds, yt
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as file:
            creds = pickle.load(file)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                SECRETS_FILE, scopes=['https://www.googleapis.com/auth/youtube.force-ssl'])
            flow.run_local_server(port=8080, prompt='consent', authorization_prompt_message='')
            creds = flow.credentials
            with open(TOKEN_FILE,'wb') as file:
                pickle.dump(creds, file)           #Creates a Chat instance given the Video ID of the target stream
    yt = build('youtube', 'v3', credentials= creds)
    return

#Extracts the author name and message from the HTML message code block
def process_message(message_div):
    global processed_messages               #Use to adjust global processed messages set
    message_id = message_div['id']          #Use id to see if message has been seen
    if message_id not in processed_messages:
        # Extract author name from its related class
        author_name_span = message_div.find('span', class_="style-scope yt-live-chat-author-chip style-scope yt-live-chat-author-chip")
        if not author_name_span:
            author_name_span = message_div.find('span', class_="moderator style-scope yt-live-chat-author-chip style-scope yt-live-chat-author-chip")
        author_name = author_name_span.text.strip() #Only grab the name from messages when it is present
        # Extract message from the related class
        message_element = message_div.find('span', class_='style-scope yt-live-chat-text-message-renderer', id='message')
        message = message_element.text.strip()
        #Process the message to remove unwanted newlines and spaces
        cleaned_text = message.replace("\n", "")
        processed_text = re.sub(r'\s+', ' ', cleaned_text)
        processed_text = f": {processed_text}\n"        #Add newline for chat structure
        # Display the message
        root.after(10, update_display, author_name, processed_text, "youtube")
        # Add the message ID to the set of processed messages
        processed_messages.add(message_id)

#Sets up and Refreshes the Livechat Browser and selects the newest messages for display
def youtube_chat(target_id):
    global processed_messages, latest_time
    url = 'https://www.youtube.com/live_chat?v='+ target_id #Get Livechat URL
    try:
        browser.get(url) # Simulate opening the webpage in the browser
        time.sleep(5)  # Allow some time for JavaScript to execute (adjust as needed)

        while True:
            time.sleep(5)  # Adjust the sleep time as needed
            html = browser.page_source # Extract the updated HTML after JavaScript execution
            soup = BeautifulSoup(html, 'html.parser') # Parse the updated HTML with BeautifulSoup

            # Find all yt-live-chat-text-message-renderer elements which conatin chats
            message_divs = soup.find_all('yt-live-chat-text-message-renderer')
            # Select which messages to process
            for message_div in message_divs:
                #If the Message does not have an author, it is likely a pinned banner
                author_name_span = message_div.find('span', class_="style-scope yt-live-chat-author-chip style-scope yt-live-chat-author-chip")
                if not author_name_span:
                    author_name_span = message_div.find('span', class_="moderator style-scope yt-live-chat-author-chip style-scope yt-live-chat-author-chip")
                if author_name_span:
                    #Get the time of the message to see if its from before the latest time
                    timestamp = message_div.find('span', class_='style-scope yt-live-chat-text-message-renderer', id='timestamp').text.strip()
                    full_time = datetime.combine(date.today(),datetime.strptime(timestamp, "%I:%M %p").time())
                    element_id = message_div.get('id')
                    if latest_time > full_time:             #If the message is from before the start time, remove it
                        browser.execute_script(f"var element = document.getElementById('{element_id}'); element.remove();")
                    if latest_time == full_time:            #If from the same time as latest, process it, then remove it
                        process_message(message_div)
                        browser.execute_script(f"var element = document.getElementById('{element_id}'); element.remove();")
                    elif full_time > latest_time:           #If from later time, update the latest time to current time
                        latest_time = full_time
                        processed_messages.clear()          #Then clear set of processed msgs, which only holds msgs of latest time
                        process_message(message_div)
                        browser.execute_script(f"var element = document.getElementById('{element_id}'); element.remove();")
    finally:
        # Close the browser when done
        browser.quit()
 
#############################################
####                 GUI                 ####
#############################################    

# Creates GUI window
def create_gui():
    root = tk.Tk()                                      # Instantiates Window
    root.title("Multi-Chat View")                       # Names Window
    root.geometry(geometry)                             # Sets Window Aspect Ratio
    root.config(background=bg_color)                    # Sets Window BG color to Background color

    # Create and set the icon photo after the root window is created
    icon = PhotoImage(file='Logo.png')                  #Only works when logo file is in same folder as program
    root.iconphoto(True, icon)                          #Set Icon on top of Window

    menu=tk.Menu(root)                                                          #Creates Menu
    editmenu=tk.Menu(menu, tearoff=0)                                           #Makes Edit Tab
    editmenu.add_command(label="Adjust Appearance", command=edit_window)        #Creates Adjust Appearance Option 
    menu.add_cascade(menu=editmenu, label="Edit")                               
    root.config(menu=menu)
    return root

# Creates Start Up Window in which Credentials can be added
def create_startup_frame(root):
    global startup, enable_post_var
    #Create the Frame
    startup = tk.Frame(root, background= start_bg)
    startup.pack(fill=tk.BOTH, expand=True)

    # Create entry widgets
    tk.Label(startup, text="Username:", bg=start_bg, fg=font_color,font=(font_type, font_size, "bold"),padx=10, pady=8).pack()
    tk.Entry(startup, textvariable=nickname_var,).pack()
    tk.Label(startup, text="Token:", bg=start_bg, fg=font_color,font=(font_type, font_size, "bold"),padx=10, pady=8).pack()
    tk.Entry(startup, textvariable=token_var, show="*").pack()
    tk.Label(startup, text="Twitch Channel:", bg=start_bg, fg=font_color,font=(font_type, font_size, "bold"),padx=10, pady=8).pack()
    tk.Entry(startup, textvariable=channel_var).pack()
    tk.Label(startup, text="YouTube ID:", bg=start_bg, fg=font_color,font=(font_type, font_size, "bold"),padx=10, pady=8).pack()
    tk.Entry(startup, textvariable=target_id_var).pack()
    tk.Label(startup, text="Enable Posting? Yes/No", bg=start_bg, fg=font_color,font=(font_type, font_size, "bold"),padx=10, pady=8).pack()
    tk.Entry(startup, textvariable=enable_post_var).pack()

    # Create button to save values and restart threads
    tk.Button(startup, text="Save and Connect", command=start_threads,
              bg="white", fg="black",activebackground="black",activeforeground="white").pack(pady=20)
    
    #General Information and Links
    tk.Label(startup, text="Welcome to the Multi-Chat View. This program allows you to view your YouTube and Twitch chat combined, ordered by time of posting. Please enter the correct details above, then click Save & Connect to open your chat.\n\nUsername: The Username of your Twitch account.\n\nToken: OAuth Token for Twitch API access. This can be generated via https://twitchapps.com/tmi/. DON'T SHARE THIS TOKEN WITH OTHERS!\n\nTwitch Channel: The name of channel you want to read the chat from, preceded by # (eg #michelpostma).\n\nYouTube ID: The ID of the YouTube livestream. Can be found in the URL of the livestream page after https://www.youtube.com/watch?v= \n\nEnable Posting: Opens an extra window from which you can post chat messages to both platforms. \nREQUIRES YOUTUBE SIGN IN!",
                bg="#2a2d3f", fg="white", font=(font_type, int(font_size*0.65)), wraplength=400).pack()

# Creates scrollframe in which messages will be displayed
def create_chat_frame(root):
    global chat
    #Create the Chat
    chat = scrolledtext.ScrolledText(root, bg=bg_color, fg=font_color, wrap=tk.WORD, font=(font_type, font_size, "bold"))
    chat.pack(fill=tk.BOTH, expand=True)
    chat.tag_config('youtube', foreground=yt_color)
    chat.tag_config('twitch', foreground=twitch_color)

#Creates window where messages to chat can be posted
def create_post_window():
    post_window = Toplevel(root)
    post_window.title("Post Message")
    post_window.geometry("300x150")  # Adjust the size as needed

    # Header
    tk.Label(post_window, text="Type your message", font=(font_type, font_size, "bold")).pack()

    # Text input
    message_entry = tk.Entry(post_window, font=(font_type, font_size))
    message_entry.pack(pady=10)

    # Button to post message
    post_button = tk.Button(post_window, text="Post", command=lambda: post_msg(message_entry.get()))
    post_button.pack(pady=10)
    # Function to clear the input field after posting
    def clear_entry():
        message_entry.delete(0, tk.END)

    post_button.config(command=lambda: [post_msg(message_entry.get()), clear_entry()])
    

#############################################
####        Program Functionality        ####
############################################# 

#Starts YouTube and Twitch Chats with specified Params 
def start_threads():
    global nickname, token, channel, target_id, sock, twitch_thread, youtube_thread, root, startup,live_id, post_enabled
    #Retrieve the User Params
    nickname = nickname_var.get()
    token = token_var.get()
    channel = channel_var.get()
    target_id = target_id_var.get()
    post_enabled = enable_post_var.get()

    if post_enabled.lower() == "yes":
        connect_yt_api()
        live_id = get_live_id(target_id)  #Extract YouTube API Livechat ID for chat messaging  
        create_post_window()
    
    # Save values to the file
    save_values()
    
    # Restart Twitch and YouTube connections
    sock = twitch_connect()
    
    # Restart threads
    twitch_thread = threading.Thread(target=twitch_chat)
    youtube_thread = threading.Thread(target=lambda: youtube_chat(target_id))
    twitch_thread.start()
    youtube_thread.start()

    #Remove the Startup Menu and create the Chat Window
    startup.destroy() 
    create_chat_frame(root)

#Function that posts the message to YouTube and Twitch
def post_msg(message):
    #Post to YouTube
    request = yt.liveChatMessages().insert(
        part="snippet",
        body={
          "snippet": {
            "type": "textMessageEvent",
            "liveChatId": live_id,
            "textMessageDetails": {
              "messageText": message
            }
          }
        }
    )
    request.execute()
    #Post to Twitch
    sock.send(f"PRIVMSG {channel} :{message}\n".encode('utf-8'))
    
#Updates the Chat Window with Messages
def update_display(name, message, platform):
    chat.insert(tk.END, name, platform)
    chat.see(tk.END)
    chat.insert(tk.END, message)
    chat.see(tk.END)
                 
#Associated Files
TOKEN_FILE = "token.pkl"
SECRETS_FILE = "client_secrets.json"
CONFIG_FILE = "config.txt"

#Set Twitch Connection Parameters
SERVER = 'irc.chat.twitch.tv'  # Twitch Connection Server
PORT = 6667                     # Twitch Connection Port

#Instantiated None Variable for Stability
chat = None  
creds = None  
yt = None
sock = None
sock_lock = threading.Lock()
live_id = '' #YouTube API Livechat ID for posting chats

#Prepare browser for YouTube Chat Reading
options = Options()
options.add_argument('--headless')  # Add this line to avoid some rendering issues in headless mode
browser = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
processed_messages = set()
latest_time = datetime.now()

#Variables Loaded from Config
nickname, token, channel, target_id, geometry, bg_color, start_bg, font_type = get_saved_values()[:8]
font_size = int(get_saved_values()[8])
font_color, yt_color, twitch_color, post_enabled = get_saved_values()[9:]

#Create GUI
root = create_gui()

# Create Tk Variables
nickname_var = tk.StringVar()
token_var = tk.StringVar()
channel_var = tk.StringVar()
target_id_var = tk.StringVar()
geometry_var = tk.StringVar()
font_type_var = tk.StringVar()
font_size_var = tk.IntVar()
enable_post_var = tk.StringVar()

# Set Tk Variable Values
nickname_var.set(nickname)
token_var.set(token)
channel_var.set(channel)
target_id_var.set(target_id)
geometry_var.set(geometry)
font_type_var.set(font_type)
font_size_var.set(font_size)
enable_post_var.set(post_enabled)


#Launch the Menu
create_startup_frame(root) 
    
#Run GUI
root.mainloop()