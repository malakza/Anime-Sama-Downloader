import requests
import re
import os
import sys
from tqdm         import    tqdm
from bs4          import    BeautifulSoup
from urllib.parse import    urlparse
import time

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header():
    header = f"""
{Colors.HEADER}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                 ANIME-SAMA VIDEO DOWNLOADER                  ║
║                       Enhanced CLI v2.0                      ║
╚══════════════════════════════════════════════════════════════╝
{Colors.ENDC}
{Colors.OKCYAN}📺 Download anime episodes from anime-sama.fr easily!{Colors.ENDC}
"""
    print(header)

def print_tutorial():
    tutorial = f"""
{Colors.BOLD}{Colors.HEADER}🎓 COMPLETE TUTORIAL - HOW TO USE{Colors.ENDC}
{Colors.BOLD}{'='*65}{Colors.ENDC}

{Colors.OKGREEN}{Colors.BOLD}Step 1: Find Your Anime on Anime-Sama{Colors.ENDC}
├─ 🌐 Visit: {Colors.OKCYAN}https://anime-sama.fr/catalogue/{Colors.ENDC}
├─ 🔍 Search for your desired anime (e.g., "Roshidere")
├─ 📺 Click on the anime title to view seasons
└─ 📂 Navigate to your preferred season and language

{Colors.OKGREEN}{Colors.BOLD}Step 2: Get the Complete URL{Colors.ENDC}
├─ 🎯 Choose your preferred option:
│   ├─ Season (saison1, saison2, etc.)
│   └─ Language (vostfr, vf, etc.)
├─ 📋 Copy the FULL URL from browser address bar
└─ ✅ Example URL format:
    {Colors.OKCYAN}https://anime-sama.fr/catalogue/roshidere/saison1/vostfr/{Colors.ENDC}

{Colors.OKGREEN}{Colors.BOLD}Step 3: Run This Program{Colors.ENDC}
├─ 🚀 Start the downloader
├─ 📝 Paste the complete URL when prompted
├─ ⚡ Program will automatically fetch available episodes
└─ 🎮 Follow the interactive prompts

{Colors.WARNING}{Colors.BOLD}📌 IMPORTANT NOTES:{Colors.ENDC}*
├─ 🔗 URL that will be given for download may not work, follow this.
├─ ✅ Only sendvid.com and video.sibnet.ru sources work
├─ ❌ vidmoly.to and vk.com sources are deprecated
├─ 🔗 URL must be the complete path including season/language
└─ 📁 Videos save to ./videos/ by default (customizable)

{Colors.OKGREEN}{Colors.BOLD}🎯 Example URLs that work:{Colors.ENDC}
├─ https://anime-sama.fr/catalogue/roshidere/saison1/vostfr/
├─ https://anime-sama.fr/catalogue/demon-slayer/saison1/vf/
├─ https://anime-sama.fr/catalogue/attack-on-titan/saison3/vostfr/
└─ https://anime-sama.fr/catalogue/one-piece/saison1/vostfr/

{Colors.BOLD}{'='*65}{Colors.ENDC}
"""
    print(tutorial)

def print_separator(char="─", length=65):
    print(f"{Colors.OKBLUE}{char * length}{Colors.ENDC}")

def print_status(message, status_type="info"):
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "loading": "⏳"
    }
    colors = {
        "info": Colors.OKBLUE,
        "success": Colors.OKGREEN,
        "warning": Colors.WARNING,
        "error": Colors.FAIL,
        "loading": Colors.OKCYAN
    }
    
    icon = icons.get(status_type, "ℹ️")
    color = colors.get(status_type, Colors.OKBLUE)
    print(f"{color}{icon} {message}{Colors.ENDC}")

def fetch_page_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/108.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://sendvid.com/' if 'sendvid.com' in url else 'https://video.sibnet.ru/'
    }
    try:
        print_status("Connecting to server...", "loading")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print_status(f"Failed to connect to {url}: {str(e)}", "error")
        return None

def extract_sendvid_video_source(html_content):
    if not html_content:
        return None
    video_source_pattern = r'var\s+video_source\s*=\s*"([^"]+)"'
    match = re.search(video_source_pattern, html_content)
    if match:
        return match.group(1)
    print_status("Could not extract video source from SendVid", "warning")
    return None

def extract_sibnet_video_source(html_content):
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all('script', type='text/javascript')
    for script in scripts:
        if 'player.src' in script.text:
            match = re.search(r'player\.src\(\[\{.*src:\s*"([^"]+)"', script.text)
            if match:
                video_source = match.group(1)
                if video_source.startswith('//'):
                    video_source = f"https:{video_source}"
                elif not video_source.startswith('https://'):
                    video_source = f"https://video.sibnet.ru{video_source}"
                return video_source
    print_status("Could not extract video source from Sibnet", "warning")
    return None

def get_sibnet_redirect_location(video_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/108.0',
        'Accept': 'video/webm,video/mp4,video/*;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://video.sibnet.ru/'
    }
    try:
        response = requests.get(video_url, headers=headers, allow_redirects=False, timeout=10)
        if response.status_code == 302:
            redirect_url = response.headers.get('location')
            if redirect_url.startswith('//'):
                redirect_url = f"https:{redirect_url}"
            return redirect_url
        print_status(f"Expected redirect (302), got {response.status_code}", "warning")
        return None
    except requests.RequestException as e:
        print_status(f"Failed to get redirect location: {str(e)}", "error")
        return None

def fetch_video_source(url):
    print_status(f"Processing video URL: {url[:50]}...", "loading")
    html_content = fetch_page_content(url)
    if not html_content:
        return None

    if 'sendvid.com' in url:
        return extract_sendvid_video_source(html_content)
    elif 'video.sibnet.ru' in url:
        video_source = extract_sibnet_video_source(html_content)
        if video_source:
            print_status("Getting direct download link...", "loading")
            redirect_location = get_sibnet_redirect_location(video_source)
            return redirect_location
        return None
    else:
        print_status("Unsupported video source. Only sendvid.com and video.sibnet.ru are supported.", "error")
        return None

def download_video(video_url, save_path):
    print_status(f"Starting download: {os.path.basename(save_path)}", "loading")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/108.0',
        'Accept': 'video/webm,video/mp4,video/*;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://sendvid.com/' if 'sendvid' in video_url else 'https://video.sibnet.ru/'
    }
    try:
        response = requests.get(video_url, stream=True, headers=headers, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        
        if response.status_code != 200:
            print_status(f"Download failed with status code: {response.status_code}", "error")
            return False
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            with tqdm(
                total=total_size, 
                unit='B', 
                unit_scale=True, 
                desc=f"📥 {os.path.basename(save_path)}",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            ) as pbar:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        print_status(f"Download completed successfully!", "success")
        return True
    except Exception as e:
        print_status(f"Download failed: {str(e)}", "error")
        return False

def fetch_episodes(base_url):
    js_url = base_url.rstrip('/') + '/episodes.js'
    print_status("Fetching episode list...", "loading")
    
    try:
        response = requests.get(js_url, timeout=15)
        response.raise_for_status()
        js_content = response.text
    except Exception as e:
        print_status(f"Failed to fetch episodes.js: {str(e)}", "error")
        return None

    pattern = re.compile(r'var\s+(eps\d+)\s*=\s*\[([^\]]*)\];', re.MULTILINE)
    matches = pattern.findall(js_content)
    episodes = {}
    
    for name, content in matches:
        player_num = re.search(r'\d+', name).group()
        player_name = f"Player {player_num}"
        urls = re.findall(r"'(https?://[^']+)'", content)
        episodes[player_name] = urls
    
    if episodes:
        print_status(f"Found {len(episodes)} players with episodes!", "success")
    else:
        print_status("No episodes found in episodes.js", "error")
    
    return episodes

def print_episodes(episodes):
    print(f"\n{Colors.BOLD}{Colors.HEADER}📺 AVAILABLE EPISODES{Colors.ENDC}")
    print_separator("=")
    
    for category, urls in episodes.items():
        print(f"\n{Colors.BOLD}{Colors.OKCYAN}🎮 {category}:{Colors.ENDC} ({len(urls)} episodes)")
        print_separator("─", 40)
        
        for i, url in enumerate(urls, start=1):
            if 'vidmoly.to' in url or "vk.com" in url:
                print(f"{Colors.FAIL}  {i:2d}. Episode {i} - {url[:60]}... ❌ DEPRECATED{Colors.ENDC}")
            elif 'sendvid.com' in url:
                print(f"{Colors.OKGREEN}  {i:2d}. Episode {i} - SendVid ✅{Colors.ENDC}")
            elif 'video.sibnet.ru' in url:
                print(f"{Colors.OKGREEN}  {i:2d}. Episode {i} - Sibnet ✅{Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}  {i:2d}. Episode {i} - Unknown source ⚠️{Colors.ENDC}")

def get_player_choice(episodes):
    print(f"\n{Colors.BOLD}{Colors.HEADER}🎮 SELECT PLAYER{Colors.ENDC}")
    print_separator()
    
    available_players = list(episodes.keys())
    for i, player in enumerate(available_players, 1):
        working_episodes = sum(1 for url in episodes[player] 
                             if 'sendvid.com' in url or 'video.sibnet.ru' in url)
        total_episodes = len(episodes[player])
        print(f"{Colors.OKCYAN}  {i}. {player} ({working_episodes}/{total_episodes} working episodes){Colors.ENDC}")
    
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Enter player number (1-{len(available_players)}) or type player name: {Colors.ENDC}").strip()
            
            if choice.isdigit():
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(available_players):
                    return available_players[choice_idx]
                else:
                    print_status(f"Please enter a number between 1 and {len(available_players)}", "error")
            else:
                player_input = choice.lower()
                if player_input.isdigit():
                    player_choice = f"Player {player_input}"
                elif player_input.startswith("player") and player_input[6:].isdigit():
                    player_choice = f"Player {player_input[6:]}"
                elif player_input.replace(" ", "").startswith("player") and player_input.replace(" ", "")[6:].isdigit():
                    player_choice = f"Player {player_input.replace(' ', '')[6:]}"
                else:
                    player_choice = choice.title()
                
                if player_choice in episodes:
                    return player_choice
                else:
                    print_status("Invalid player choice. Try again.", "error")
        except KeyboardInterrupt:
            print_status("\nOperation cancelled by user", "error")
            return None
        except Exception:
            print_status("Invalid input. Please try again.", "error")

def get_episode_choice(episodes, player_choice):
    print(f"\n{Colors.BOLD}{Colors.HEADER}📺 SELECT EPISODE - {player_choice}{Colors.ENDC}")
    print_separator()
    
    num_episodes = len(episodes[player_choice])
    working_episodes = []
    
    for i, url in enumerate(episodes[player_choice], 1):
        if 'sendvid.com' in url or 'video.sibnet.ru' in url:
            working_episodes.append(i)
            source_type = "SendVid" if 'sendvid.com' in url else "Sibnet"
            print(f"{Colors.OKGREEN}  {i:2d}. Episode {i} - {source_type} ✅{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}  {i:2d}. Episode {i} - Deprecated ❌{Colors.ENDC}")
    
    if not working_episodes:
        print_status("No working episodes found for this player!", "error")
        return None
    
    print(f"\n{Colors.OKCYAN}Available episodes: {len(working_episodes)} out of {num_episodes}{Colors.ENDC}")
    
    while True:
        try:
            episode_input = input(f"\n{Colors.BOLD}Enter episode number (1-{num_episodes}): {Colors.ENDC}").strip()
            episode_num = int(episode_input)
            
            if 1 <= episode_num <= num_episodes:
                episode_url = episodes[player_choice][episode_num - 1]
                if 'vidmoly.to' in episode_url or 'vk.com' in episode_url:
                    print_status("This episode source is deprecated and cannot be downloaded", "error")
                    continue
                return episode_num - 1
            else:
                print_status(f"Episode number must be between 1 and {num_episodes}", "error")
        except KeyboardInterrupt:
            print_status("\nOperation cancelled by user", "error")
            return None
        except ValueError:
            print_status("Invalid episode number. Please enter a number.", "error")

def extract_anime_name(base_url):
    match = re.search(r'catalogue/([^/]+)/', base_url)
    if match:
        return match.group(1)
    return "episode"

def get_save_directory():
    print(f"\n{Colors.BOLD}{Colors.HEADER}📁 SAVE LOCATION{Colors.ENDC}")
    print_separator()
    
    default_dir = "./videos"
    save_dir = input(f"{Colors.OKCYAN}Enter directory to save videos (default: {default_dir}): {Colors.ENDC}").strip()
    
    if not save_dir:
        save_dir = default_dir
    
    try:
        os.makedirs(save_dir, exist_ok=True)
        print_status(f"Save directory set to: {os.path.abspath(save_dir)}", "success")
        return save_dir
    except Exception as e:
        print_status(f"Cannot create directory {save_dir}: {str(e)}", "error")
        print_status(f"Using default directory: {default_dir}", "info")
        os.makedirs(default_dir, exist_ok=True)
        return default_dir

def validate_anime_sama_url(url):
    if not url.startswith("https://anime-sama.fr/catalogue/"):
        return False, "URL must start with https://anime-sama.fr/catalogue/"
    
    if not url.rstrip('/').count('/') >= 5:
        return False, "URL must include anime name, season, and language (e.g., /catalogue/anime/saison1/vostfr/)"
    
    return True, ""

def main():
    try:
        print_header()
        
        show_tutorial = input(f"{Colors.BOLD}Show tutorial? (y/n, default: n): {Colors.ENDC}").strip().lower()
        if show_tutorial in ['y', 'yes', '1']:
            print_tutorial()
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}🔗 ANIME-SAMA URL INPUT{Colors.ENDC}")
        print_separator()
        
        while True:
            base_url = input(f"{Colors.BOLD}Enter the complete anime-sama URL: {Colors.ENDC}").strip()
            
            if not base_url:
                print_status("URL cannot be empty", "error")
                continue
                
            is_valid, error_msg = validate_anime_sama_url(base_url)
            if not is_valid:
                print_status(error_msg, "error")
                print_status("Example: https://anime-sama.fr/catalogue/roshidere/saison1/vostfr/", "info")
                continue
            
            break
        
        anime_name = extract_anime_name(base_url)
        print_status(f"Detected anime: {anime_name}", "info")
        
        episodes = fetch_episodes(base_url)
        if not episodes:
            print_status("Failed to fetch episodes. Please check the URL and try again.", "error")
            return 1
        
        print_episodes(episodes)
        
        player_choice = get_player_choice(episodes)
        if not player_choice:
            return 1
        
        episode_index = get_episode_choice(episodes, player_choice)
        if episode_index is None:
            return 1
        
        save_dir = get_save_directory()
        
        url = episodes[player_choice][episode_index]
        episode_num = episode_index + 1
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}🎬 PROCESSING EPISODE{Colors.ENDC}")
        print_separator()
        print_status(f"Player: {player_choice}", "info")
        print_status(f"Episode: {episode_num}", "info")
        print_status(f"Source: {url[:60]}...", "info")
        
        video_source = fetch_video_source(url)
        if not video_source:
            print_status(f"Could not extract video source for episode {episode_num}", "error")
            return 1
        
        save_path = os.path.join(save_dir, f"{anime_name}_episode_{episode_num}.mp4")
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}⬇️ DOWNLOADING{Colors.ENDC}")
        print_separator()
        
        if download_video(video_source, save_path):
            print_separator()
            print_status(f"Video successfully saved to: {save_path}", "success")
            print_status("Download complete! Enjoy watching! 🎉", "success")
        else:
            print_status(f"Failed to download episode {episode_num}", "error")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print_status("\n\nProgram interrupted by user", "error")
        return 1
    except Exception as e:
        print_status(f"Unexpected error: {str(e)}", "error")
        return 1

if __name__ == "__main__":
    sys.exit(main())
