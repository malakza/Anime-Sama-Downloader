import re
import os
import sys
try:
    from moviepy.editor           import VideoFileClip
except ImportError:
    print("Warning: moviepy is not installed. Install it using 'pip install moviepy' for .mp4 conversion.")
    VideoFileClip = None

from concurrent.futures import ThreadPoolExecutor, as_completed


from utils.var                    import Colors, print_status, print_separator, print_header, print_tutorial
from utils.parsers                import parse_ts_segments
from utils.ts_to_mp4              import convert_ts_to_mp4
from utils.fetch                  import fetch_episodes, fetch_video_source
from utils.downloaders.downloader import download_video
from utils.stuff                  import print_episodes, get_player_choice, get_episode_choice
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



def download_episode(episode_num, url, video_source, anime_name, save_dir, use_ts_threading=False, threaded_mp4=False,):
    if not video_source:
        print_status(f"Could not extract video source for episode {episode_num}", "error")
        return False, None
    
    print_separator()
    print_status(f"Processing episode: {episode_num}", "info")
    print_status(f"Source: {url[:60]}...", "info")
    
    save_path = os.path.join(save_dir, f"{anime_name}_episode_{episode_num}.mp4")
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}⬇️ DOWNLOADING EPISODE {episode_num}{Colors.ENDC}")
    print_separator()
    
    success, output_path = download_video(video_source, save_path, use_ts_threading=use_ts_threading)
    if not success:
        print_status(f"Failed to download episode {episode_num}", "error")
        return False, None
    
    print_separator()
    
    if 'm3u8' in video_source and output_path.endswith('.ts'):
        print_status(f"Video saved as {output_path} (MPEG-TS format, playable in VLC or similar players)", "success")
        if VideoFileClip:
            if  threaded_mp4:
                convert = 'y'
            else:
                convert = input(f"{Colors.BOLD}Convert episode {episode_num} to .mp4 format? This may take some time (y/n, default: n): {Colors.ENDC}").strip().lower()
            if convert in ['y', 'yes', '1']:
                if convert_ts_to_mp4(output_path, save_path):
                    print_status(f"Episode {episode_num} successfully saved to: {save_path}", "success")
                    try:
                        os.remove(output_path)
                        print_status(f"Removed temporary .ts file: {output_path}", "info")
                    except Exception as e:
                        print_status(f"Could not remove temporary .ts file: {str(e)}", "warning")
                else:
                    print_status(f"Conversion failed for episode {episode_num}, keeping .ts file: {output_path}", "error")
                    return False, output_path
            else:
                print_status(f"Keeping .ts file for episode {episode_num}: {output_path}", "info")
                return True, output_path
        else:
            print_status("moviepy not installed, keeping .ts file", "warning")
            return True, output_path
    else:
        print_status(f"Episode {episode_num} successfully saved to: {save_path}", "success")
        return True, save_path

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
        
        episode_indices = get_episode_choice(episodes, player_choice)
        if episode_indices is None:
            return 1
        
        save_dir = get_save_directory()
        
        if isinstance(episode_indices, int):
            episode_indices = [episode_indices]
        
        urls = [episodes[player_choice][index] for index in episode_indices]
        episode_numbers = [index + 1 for index in episode_indices]
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}🎬 PROCESSING EPISODES{Colors.ENDC}")
        print_separator()
        print_status(f"Player: {player_choice}", "info")
        print_status(f"Episodes selected: {', '.join(map(str, episode_numbers))}", "info")
        
        video_sources = fetch_video_source(urls)
        if not video_sources:
            print_status("Could not extract video sources for selected episodes", "error")
            return 1
        
        if isinstance(video_sources, str):
            video_sources = [video_sources]
        
        use_threading = False
        use_ts_threading = False
        automatic_mp4 = False
        if len(episode_indices) > 1:
            thread_choice = input(f"{Colors.BOLD}Download all episodes simultaneously (threaded) or sequentially? (t/1/y = yes / s = no , default: s): {Colors.ENDC}").strip().lower()
            use_threading = thread_choice in ['t', 'threaded', '1', 'y', 'yes']
            if any('m3u8' in src for src in video_sources if src):
                ts_thread_choice = input(f"{Colors.BOLD}M3U8 sources detected. Download .ts files simultaneously (threaded) or sequentially? (t/1/y = yes / s = no , default: s): {Colors.ENDC}").strip().lower()
                use_ts_threading = ts_thread_choice in ['t', 'threaded', '1', 'y', 'yes']
        
        elif len(episode_indices) == 1:
            if any('m3u8' in src for src in video_sources if src):
                ts_thread_choice = input(f"{Colors.BOLD}M3U8 sources detected. Download .ts files simultaneously (threaded) or sequentially? (t/1/y = yes / s = no , default: s): {Colors.ENDC}").strip().lower()
                use_ts_threading = ts_thread_choice in ['t', 'threaded', '1', 'y', 'yes']



        if len(episode_indices) > 1 and any('m3u8' in src for src in video_sources if src):
            auto_mp4_choice = input(f"{Colors.BOLD}Convert all .ts files to .mp4 automatically after download? (t/1/y = yes / s = no , default: s): {Colors.ENDC}").strip().lower()
            use_threading = auto_mp4_choice in ['t', 'threaded', '1', 'y', 'yes']
            if automatic_mp4 and not VideoFileClip:
                print_status("moviepy not installed, cannot convert to .mp4. Install it using 'pip install moviepy'", "warning")
                automatic_mp4 = False

        elif len(episode_indices) == 1 and any('m3u8' in src for src in video_sources if src):
            auto_mp4_choice = input(f"{Colors.BOLD}Convert .ts file to .mp4 automatically after download? (t/1/y = yes / s = no , default: s): {Colors.ENDC}").strip().lower()
            automatic_mp4 = auto_mp4_choice in ['t', 'threaded', '1', 'y', 'yes']
            if automatic_mp4 and not VideoFileClip:
                print_status("moviepy not installed, cannot convert to .mp4. Install it using 'pip install moviepy'", "warning")
                automatic_mp4 = False

        failed_downloads = 0
        if use_threading:
            print_status("Starting threaded downloads...", "info")
            with ThreadPoolExecutor() as executor:
                future_to_episode = {
                    executor.submit(download_episode, ep_num, url, video_src, anime_name, save_dir, use_ts_threading, automatic_mp4): ep_num
                    for ep_num, url, video_src in zip(episode_numbers, urls, video_sources)
                }
                for future in as_completed(future_to_episode):
                    ep_num = future_to_episode[future]
                    try:
                        success, _ = future.result()
                        if not success:
                            failed_downloads += 1
                    except Exception as e:
                        print_status(f"Episode {ep_num} generated an exception: {str(e)}", "error")
                        failed_downloads += 1
        else:
            for episode_num, url, video_source in zip(episode_numbers, urls, video_sources):
                success, _ = download_episode(episode_num, url, video_source, anime_name, save_dir, use_ts_threading, automatic_mp4)
                if not success:
                    failed_downloads += 1
        
        print_separator()
        if failed_downloads == 0:
            print_status("All downloads completed successfully! Enjoy watching! 🎉", "success")
            return 0
        else:
            print_status(f"Completed with {failed_downloads} failed downloads", "warning")
            return 1
        
    except KeyboardInterrupt:
        print_status("\n\nProgram interrupted by user", "error")
        return 1
    except Exception as e:
        print_status(f"Unexpected error: {str(e)}", "error")
        return 1

if __name__ == "__main__":
    sys.exit(main())