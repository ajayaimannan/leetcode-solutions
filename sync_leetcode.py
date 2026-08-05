
import os
import json
import argparse
import requests
import datetime
import re

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
    'java': {'ext': '.java', 'comment': '//', 'folder': 'Java'},
    'python3': {'ext': '.py', 'comment': '#', 'folder': 'Python'},
    'python': {'ext': '.py', 'comment': '#', 'folder': 'Python'},
    'cpp': {'ext': '.cpp', 'comment': '//', 'folder': 'Cpp'},
    'c': {'ext': '.c', 'comment': '//', 'folder': 'C'},
    'javascript': {'ext': '.js', 'comment': '//', 'folder': 'JavaScript'}
}

def format_filename(title):
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    return clean_title.replace(' ', '_')

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
            print("Failed to fetch username. Your LEETCODE_SESSION cookie might be expired.")
            return []
            
        # Step 2: Fetch the accepted submissions for that specific username
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

def generate_stats_file():
    """Generates stats.json for lazyraion-api to consume."""
    language_breakdown = {}
    total_files = 0
    recent_files = []

    for item in os.listdir('.'):
        if os.path.isdir(item) and not item.startswith('.'):
            files = [f for f in os.listdir(item) if os.path.isfile(os.path.join(item, f))]
            if files:
                language_breakdown[item] = len(files)
                total_files += len(files)
                # Ensure we only pick up actual solution files for recent history
                for f in files:
                    recent_files.append({"title": f.rsplit('.', 1)[0].replace('_', ' '), "language": item, "file": f"{item}/{f}"})

    stats_payload = {
        "status": "success",
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "total_solved": total_files,
        "languages": language_breakdown,
        "recent_solutions": recent_files[-5:]  # Attach last 5 for portfolio widgets
    }

    with open('stats.json', 'w') as f:
        json.dump(stats_payload, f, indent=2)

    return stats_payload

def notify_lazyraion_api(payload):
    """Safely notifies lazyraion-api if server is online. Fails silently if server is down."""
    if not LAZYRAION_WEBHOOK:
        return
    try:
        requests.post(LAZYRAION_WEBHOOK, json=payload, timeout=5)
        print("Successfully notified lazyraion-api.")
    except Exception as e:
        print(f"lazyraion-api server currently unreachable. Continuing without error: {e}")

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram notification failed: {e}")

def mode_sync():
    submissions = get_recent_submissions()
    new_syncs = 0

    for sub in submissions:
        lang_slug = sub['lang']
        if lang_slug not in LANG_MAP:
            continue
            
        lang_info = LANG_MAP[lang_slug]
        code = get_submission_code(sub['id'])
        if not code:
            continue

        dt = datetime.datetime.fromtimestamp(int(sub['timestamp']))
        timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        folder_name = lang_info['folder']
        file_name = f"{format_filename(sub['title'])}{lang_info['ext']}"
        file_path = os.path.join(folder_name, file_name)

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        comment = lang_info['comment']
        header = f"{comment} Problem: {sub['title']}\n{comment} Language: {folder_name}\n{comment} Timestamp: \"{timestamp_str}\"\n\n"
        full_code = header + code

        # Smart overwrite logic: Checks if code is new or an optimized version
        is_new_or_updated = True
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                existing_code = f.read()
            if existing_code == full_code:
                is_new_or_updated = False # Code is identical, skip writing

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
