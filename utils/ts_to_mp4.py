from utils.var import print_status, Colors
from moviepy.editor import VideoFileClip

def convert_ts_to_mp4(ts_file, mp4_file):
    if VideoFileClip is None:
        print_status("moviepy is not installed. Cannot convert to .mp4. Install it using 'pip install moviepy'.", "error")
        return False
    try:
        print_status(f"Converting {ts_file} to {mp4_file}... This may take some time.", "loading")
        video = VideoFileClip(ts_file)
        video.write_videofile(mp4_file, codec="libx264", audio_codec="aac")
        video.close()
        print_status(f"Successfully converted to {mp4_file}", "success")
        return True
    except Exception as e:
        print_status(f"Error converting to .mp4: {str(e)}", "error")
        return False
