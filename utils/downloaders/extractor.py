from utils.var import print_status, Colors
import re
from bs4 import BeautifulSoup
import requests, time, re

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

def extract_oneupload_video_source(html_content):
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tags = soup.find_all('script', type='text/javascript')
    for script in script_tags:
        if script.string and 'jwplayer' in script.string:
            url_match = re.search(r'file:"(https?://.*?)"', script.string)
            if url_match:
                m3u8_url = url_match.group(1)
                return m3u8_url
    print_status("Could not extract video source from OneUpload", "warning")
    return None

def extract_vidmoly_video_source(html_content):
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tags = soup.find_all('script', type='text/javascript')
    for script in script_tags:
        if script.string and 'jwplayer' in script.string:
            url_match = re.search(r'file:"(https?://.*?)"', script.string)
            if url_match:
                m3u8_url = url_match.group(1)
                return m3u8_url
    print_status("Could not extract video source from Vidmoly", "warning")
    return None

def resolve_placeholders_from_html(html_content):
    js_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL | re.IGNORECASE)
    if not js_blocks:
        return None
    for js_code in js_blocks:
        url_match = re.search(r'"1b":"([^"]*)"', js_code)
        if not url_match:
            continue
        url_template = url_match.group(1)
        pattern_match = re.search(r'/([a-zA-Z0-9]{2}),([^,]*(?:,[^,]*)*),\.([a-zA-Z0-9]+)', url_template)
        if not pattern_match:
            continue
        placeholders_str = pattern_match.group(2)
        return ',' + placeholders_str +","
    return None
def extract_movearnpre_video_source(embed_url):
    try:
        response = requests.get(embed_url)
        response.raise_for_status()
        html_content = response.text

        placeholder = resolve_placeholders_from_html(html_content)

        script_pattern = r'<script type=[\'"]text/javascript[\'"]>\s*eval\(function.*?\.split\(\'\|\'\)\)\)\s*</script>'
        script_match = re.search(script_pattern, html_content, re.DOTALL)
        
        if not script_match:
            return "Error: Could not find the obfuscated JavaScript script."

        script_content = script_match.group(0)

        split_pattern = r'\'([^\']*)\'\.split\(\'\|\'\)\)\)'
        split_match = re.search(split_pattern, script_content)
        
        if not split_match:
            return "Error: Could not extract split data from script."

        raw_split_data = split_match.group(1).split('|')
        split_data = [item for item in raw_split_data if item.strip()]

        timestamp = None
        file_code = None

        try:
            create_element_index = split_data.index('createElement')
            start_index = max(0, create_element_index - 5)
            end_index = min(len(split_data), create_element_index + 6)
            after_values = [split_data[i] for i in range(create_element_index + 1, end_index)]
            
            if len(after_values) >= 2 and after_values[0].isdigit() and after_values[1].isdigit():
                timestamp = after_values[0]
                file_code = after_values[1]
            else:
                if len(after_values) >= 1 and after_values[0].isdigit():
                    file_code = after_values[0]
                else:
                    file_code_pattern = r"\$\.cookie\('file_id',\s*'(\d+)'"
                    file_code_match = re.search(file_code_pattern, html_content)
                    file_code = file_code_match.group(1) if file_code_match else '29309898'
                
                current_time = int(time.time())
                possible_timestamps = [str(current_time - i) for i in range(5)]
                for value in split_data:
                    if value in possible_timestamps:
                        timestamp = value
                        break
            
            if not timestamp:
                timestamp = str(current_time)

        except ValueError:
            timestamp = str(int(time.time()))
            file_code_pattern = r"\$\.cookie\('file_id',\s*'(\d+)'"
            file_code_match = re.search(file_code_pattern, html_content)
            file_code = file_code_match.group(1) if file_code_match else '29309898'

        if not timestamp or not timestamp.isdigit():
            timestamp = str(int(time.time()))

        if not file_code or not file_code.isdigit():
            file_code = '29309898'

        subdomain = None
        for item in reversed(split_data):
            if item and len(item) >= 10 and item.isalnum():
                subdomain = item.lower()
                break
        
        if not subdomain:
            return "Error: Could not find subdomain matching pattern."

        if len(split_data) >= 2:
            domain = split_data[-2]
            code = split_data[-3]
        else:
            domain = 'ovaltinecdn'
            code = ''

        file_id = embed_url.split('/')[-1] + "_"

        srv = None
        try:
            reload_key_index = split_data.index('reloadKey')
            if reload_key_index + 2 < len(split_data):
                srv = split_data[reload_key_index + 2]
        except ValueError:
            srv_pattern = r"\$\.cookie\('aff',\s*'([^']+)'"
            srv_match = re.search(srv_pattern, html_content)
            srv = srv_match.group(1) if srv_match else '39536'

        if not srv or not srv.strip():
            srv = '39536'

        expiry = None
        hash_value = None
        
        try:
            m3u8_index = split_data.index('m3u8')
            prev_integer_index = -1
            for i in range(m3u8_index - 1, -1, -1):
                if split_data[i].isdigit():
                    prev_integer_index = i
                    break
            
            if prev_integer_index == -1:
                return "Error: Could not find integer before 'm3u8' in split data."

            expiry = split_data[prev_integer_index]
            
            if len(expiry) == 10 and expiry.isdigit():
                timestamp = expiry
            
            hash_components = []
            for i in range(prev_integer_index + 1, m3u8_index):
                hash_components.append(split_data[i])
            
            if not hash_components:
                return "Error: No hash components found between expiry and 'm3u8'."
            
            hash_value = '-'.join(hash_components[::-1])
            
        except ValueError:
            return "Error: Could not find required elements in split data."

        asn = None
        try:
            asn_index = split_data.index('asn')
            if asn_index > 0:
                asn = split_data[asn_index - 1]
        except ValueError:
            asn = '3215'
        
        if not asn or not asn.strip():
            asn = '3215'

        full_subdomain = f"{subdomain}.{domain}"
        constructed_url = (f"https://{full_subdomain}.com/hls2/01/{code}/{file_id}{placeholder}.urlset/master.m3u8"
                          f"?t={hash_value}&s={timestamp}&e=129600&f={file_code}&srv={srv}"
                          f"&i=0.4&sp=500&p1={srv}&p2={srv}&asn={asn}")

        return constructed_url

    except requests.RequestException as e:
        return f"Error fetching URL: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"