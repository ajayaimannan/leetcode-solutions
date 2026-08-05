import os
import json
import argparse
import requests
import datetime
import re
import shutil

# Secrets & Environment Variables
SESSION = os.environ.get('LEETCODE_SESSION')
CSRF = os.environ.get('LEETCODE_CSRF')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
LAZYRAION_WEBHOOK = os.environ.get('LAZYRAION_WEBHOOK_URL')

HEADERS = {
    'Cookie': f'LEETCODE_SESSION={SESSION}; csrftoken={CSRF};',
    'x-csrftoken': CSRF,
    'Content-Type': 'application/json',
    'Referer': 'https://leetcode.com'
}

URL = 'https://leetcode.com/graphql'

LANG_MAP = {
    # Core Languages
    'c': {'ext': '.c', 'comment': '//', 'folder': 'C'},
    'cpp': {'ext': '.cpp', 'comment': '//', 'folder': 'Cpp'},
    'java': {'ext': '.java', 'comment': '//', 'folder': 'Java'},
    'python': {'ext': '.py', 'comment': '#', 'folder': 'Python'},
    'python3': {'ext': '.py', 'comment': '#', 'folder': 'Python'},
    'pythondata': {'ext': '.py', 'comment': '#', 'folder': 'Pandas'},
    'csharp': {'ext': '.cs', 'comment': '//', 'folder': 'CSharp'},
    'javascript': {'ext': '.js', 'comment': '//', 'folder': 'JavaScript'},
    'typescript': {'ext': '.ts', 'comment': '//', 'folder': 'TypeScript'},
    'php': {'ext': '.php', 'comment': '//', 'folder': 'PHP'},
    'swift': {'ext': '.swift', 'comment': '//', 'folder': 'Swift'},
    'kotlin': {'ext': '.kt', 'comment': '//', 'folder': 'Kotlin'},
    'dart': {'ext': '.dart', 'comment': '//', 'folder': 'Dart'},
    'golang': {'ext': '.go', 'comment': '//', 'folder': 'Go'},
    'ruby': {'ext': '.rb', 'comment': '#', 'folder': 'Ruby'},
    'scala': {'ext': '.scala', 'comment': '//', 'folder': 'Scala'},
    'rust': {'ext': '.rs', 'comment': '//', 'folder': 'Rust'},
    
    # Functional / Niche Languages
    'racket': {'ext': '.rkt', 'comment': ';', 'folder': 'Racket'},
    'erlang': {'ext': '.erl', 'comment': '%', 'folder': 'Erlang'},
    'elixir': {'ext': '.ex', 'comment': '#', 'folder': 'Elixir'},
    
    # Database / SQL Dialects
    'mysql': {'ext': '.sql', 'comment': '--', 'folder': 'SQL'},
    'mssql': {'ext': '.sql', 'comment': '--', 'folder': 'SQL'},
    'oraclesql': {'ext': '.sql', 'comment': '--', 'folder': 'SQL'},
    'postgresql': {'ext': '.sql', 'comment': '--', 'folder': 'SQL'},
    
    # Scripting
    'bash': {'ext': '.sh', 'comment': '#', 'folder': 'Bash'}
}


def get_problem_number(title_slug):
    """Fetches the exact frontend problem ID from LeetCode."""
    query = """
    query questionTitle($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionFrontendId
      }
    }
    """
    try:
        resp = requests.post(URL, json={'query': query, 'variables': {'titleSlug': title_slug}}, headers=HEADERS, timeout=10)
        return resp.json().get('data', {}).get('question', {}).get('questionFrontendId', '0000')
    except Exception:
        return "0000"

def format_filename(title, question_id):
    """Formats string to: 0001_Two_Sum"""
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    title_underscored = clean_title.strip().replace(' ', '_')
    padded_id = str(question_id).zfill(4)
    return f"{padded_id}_{title_underscored}"

def get_recent_submissions():
    # Step 1: Dynamically fetch your logged-in username
    user_query = """
    query globalData {
      userStatus {
        username
      }
    }
    """
    try:
        user_resp = requests.post(URL, json={'query': user_query}, headers=HEADERS, timeout=15)
        username = user_resp.json().get('data', {}).get('userStatus', {}).get('username')
        
        if not username:
            print("Failed to fetch username. Your session cookie might be expired.")
            return []
            
        # Step 2: Fetch the accepted submissions
        submission_query = """
        query GetRecentSubmissions($username: String!, $limit: Int!) {
          recentAcSubmissionList(username: $username, limit: $limit) {
            id
            title
            titleSlug
            timestamp
            lang
          }
        }
        """
        sub_resp = requests.post(URL, json={'query': submission_query, 'variables': {'username': username, 'limit': 20}}, headers=HEADERS, timeout=15)
        return sub_resp.json().get('data', {}).get('recentAcSubmissionList', [])
        
    except Exception as e:
        print(f"Error fetching submissions: {e}")
        return []

def get_submission_code(sub_id):
    query = """
    query submissionDetails($id: Int!) {
      submissionDetails(submissionId: $id) {
        code
      }
    }
    """
    try:
        response = requests.post(URL, json={'query': query, 'variables': {'id': sub_id}}, headers=HEADERS, timeout=15)
        return response.json().get('data', {}).get('submissionDetails', {}).get('code', '')
    except Exception as e:
        print(f"Error fetching code for {sub_id}: {e}")
        return ''

def archive_legacy_files(folder_name):
    """Moves any file not matching the new '0000_Name' convention to an Archive subfolder."""
    if not os.path.exists(folder_name):
        return
        
    archive_dir = os.path.join(folder_name, 'Archive')
    
    for file in os.listdir(folder_name):
        file_path = os.path.join(folder_name, file)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
            
        # If the file does NOT start with 4 digits and an underscore, move it to Archive
        if not re.match(r'^\d{4}_', file):
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            shutil.move(file_path, os.path.join(archive_dir, file))
            print(f"Archived legacy file: {file}")

def generate_stats_file():
    language_breakdown = {}
    total_files = 0
    recent_files = []

    for item in os.listdir('.'):
        if os.path.isdir(item) and not item.startswith('.'):
            files = [f for f in os.listdir(item) if os.path.isfile(os.path.join(item, f))]
            if files:
                language_breakdown[item] = len(files)
                total_files += len(files)
                for f in files:
                    recent_files.append({"title": f.rsplit('.', 1)[0].replace('_', ' '), "language": item, "file": f"{item}/{f}"})

    stats_payload = {
        "status": "success",
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "total_solved": total_files,
        "languages": language_breakdown,
        "recent_solutions": recent_files[-5:]
    }

    with open('stats.json', 'w') as f:
        json.dump(stats_payload, f, indent=2)

    return stats_payload

def notify_lazyraion_api(payload):
    if not LAZYRAION_WEBHOOK:
        return
    try:
        requests.post(LAZYRAION_WEBHOOK, json=payload, timeout=5)
    except Exception:
        pass

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def mode_sync():
    submissions = get_recent_submissions()
    new_syncs = 0
    processed_folders = set()

    for sub in submissions:
        lang_slug = sub['lang']
        if lang_slug not in LANG_MAP:
            continue
            
        lang_info = LANG_MAP[lang_slug]
        folder_name = lang_info['folder']
        
        # Ensure folder exists and clean up legacy files before writing anything new
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        if folder_name not in processed_folders:
            archive_legacy_files(folder_name)
            processed_folders.add(folder_name)
            
        code = get_submission_code(sub['id'])
        if not code:
            continue

        dt = datetime.datetime.fromtimestamp(int(sub['timestamp']))
        timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        # Fetch problem number and format universal name
        question_id = get_problem_number(sub['titleSlug'])
        file_name = format_filename(sub['title'], question_id) + lang_info['ext']
        file_path = os.path.join(folder_name, file_name)

        comment = lang_info['comment']
        header = f"{comment} Problem: {question_id}. {sub['title']}\n{comment} Language: {folder_name}\n{comment} Timestamp: \"{timestamp_str}\"\n\n"
        full_code = header + code

        # Smart overwrite
        is_new_or_updated = True
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                existing_code = f.read()
            if existing_code == full_code:
                is_new_or_updated = False 

        if is_new_or_updated:
            with open(file_path, 'w') as f:
                f.write(full_code)
            new_syncs += 1
            print(f"Saved/Updated: {file_path}")

    stats_data = generate_stats_file()
    notify_lazyraion_api(stats_data)

    if new_syncs > 0:
        msg = f"⚡ *LeetCode Sync Complete*\n\nAdded or Updated `{new_syncs}` solutions.\nTotal Solved: `{stats_data['total_solved']}`"
        send_telegram(msg)
    else:
        print("No new or updated solutions found.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['sync', 'stats'], default='sync')
    args = parser.parse_args()

    if args.mode == 'sync':
        mode_sync()
    else:
        stats = generate_stats_file()
        msg = f"📊 *Current Stats*\n\nTotal Solved: `{stats['total_solved']}`\n\n*Languages:*\n"
        for lang, count in stats['languages'].items():
            msg += f"• `{lang}`: {count}\n"
        send_telegram(msg)
