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
LAZYRAION_WEBHOOK = os.environ.get('LAZYRAION_WEBHOOK_URL')  # e.g. https://api.lazyraion.com/portfolio/leetcode/webhook
WEBHOOK_SECRET = os.environ.get('LEETCODE_WEBHOOK_SECRET')   # shared secret, must match lazyraion-api's LEETCODE_WEBHOOK_SECRET

GITHUB_REPO = 'izqzb/leetcode-solutions'
INDEX_FILE = 'solutions_index.json'

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


def get_username():
    query = """
    query globalData {
      userStatus {
        username
      }
    }
    """
    try:
        resp = requests.post(URL, json={'query': query}, headers=HEADERS, timeout=15)
        return resp.json().get('data', {}).get('userStatus', {}).get('username')
    except Exception as e:
        print(f"Error fetching username: {e}")
        return None


def get_recent_submissions(username):
    query = """
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
    try:
        resp = requests.post(URL, json={'query': query, 'variables': {'username': username, 'limit': 20}}, headers=HEADERS, timeout=15)
        return resp.json().get('data', {}).get('recentAcSubmissionList', [])
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


def get_problem_meta(title_slug):
    """Fetches problem number, difficulty, and topic tags."""
    query = """
    query questionMeta($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionFrontendId
        difficulty
        topicTags {
          name
        }
      }
    }
    """
    try:
        resp = requests.post(URL, json={'query': query, 'variables': {'titleSlug': title_slug}}, headers=HEADERS, timeout=10)
        q = resp.json().get('data', {}).get('question') or {}
        return {
            "id": str(q.get('questionFrontendId', '0000')),
            "difficulty": q.get('difficulty', 'Unknown'),
            "tags": [t['name'] for t in q.get('topicTags', [])],
        }
    except Exception as e:
        print(f"Error fetching problem meta for {title_slug}: {e}")
        return {"id": "0000", "difficulty": "Unknown", "tags": []}


def get_global_stats(username):
    """Difficulty breakdown, streak, and daily submission calendar — sourced
    from LeetCode's own totals (matchedUser), not just what's synced to the
    repo, so this stays accurate even before a problem's file lands."""
    query = """
    query userProfileStats($username: String!) {
      matchedUser(username: $username) {
        submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
        userCalendar {
          streak
          totalActiveDays
          submissionCalendar
        }
      }
    }
    """
    empty = {
        "difficulty": {"Easy": 0, "Medium": 0, "Hard": 0},
        "streak": {"current_streak": 0, "total_active_days": 0},
        "calendar": {},
    }
    try:
        resp = requests.post(URL, json={'query': query, 'variables': {'username': username}}, headers=HEADERS, timeout=15)
        data = resp.json().get('data', {}).get('matchedUser') or {}
        if not data:
            return empty

        diff_counts = {}
        for entry in data.get('submitStatsGlobal', {}).get('acSubmissionNum', []):
            diff_counts[entry['difficulty']] = entry['count']

        cal = data.get('userCalendar') or {}
        calendar = {}
        try:
            raw_cal = json.loads(cal.get('submissionCalendar', '{}') or '{}')
            for ts, count in raw_cal.items():
                date_str = datetime.datetime.utcfromtimestamp(int(ts)).strftime('%Y-%m-%d')
                calendar[date_str] = calendar.get(date_str, 0) + count
        except Exception:
            pass

        return {
            "difficulty": {
                "Easy": diff_counts.get("Easy", 0),
                "Medium": diff_counts.get("Medium", 0),
                "Hard": diff_counts.get("Hard", 0),
            },
            "streak": {
                "current_streak": cal.get('streak', 0),
                "total_active_days": cal.get('totalActiveDays', 0),
            },
            "calendar": calendar,
        }
    except Exception as e:
        print(f"Error fetching global stats: {e}")
        return empty


def format_filename(title, question_id):
    """Formats string to: 0001_Two_Sum"""
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    title_underscored = clean_title.strip().replace(' ', '_')
    padded_id = str(question_id).zfill(4)
    return f"{padded_id}_{title_underscored}"


def archive_legacy_files(folder_name):
    """Moves any file not matching the '0000_Name' convention to an Archive subfolder."""
    if not os.path.exists(folder_name):
        return
    archive_dir = os.path.join(folder_name, 'Archive')
    for file in os.listdir(folder_name):
        file_path = os.path.join(folder_name, file)
        if os.path.isdir(file_path):
            continue
        if not re.match(r'^\d{4}_', file):
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            shutil.move(file_path, os.path.join(archive_dir, file))
            print(f"Archived legacy file: {file}")


def load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_index(index):
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)


def prune_index(index):
    """Drops entries whose file no longer exists at its recorded path —
    covers files that got moved into Archive/ or deleted by hand."""
    for path in list(index.keys()):
        if not os.path.isfile(path):
            del index[path]


def generate_stats_file(index, global_stats):
    language_breakdown = {}
    unique_numbers = set()
    solutions_list = []

    for entry in index.values():
        language_breakdown[entry['language']] = language_breakdown.get(entry['language'], 0) + 1
        unique_numbers.add(entry['id'])
        solutions_list.append(entry)

    solutions_list.sort(key=lambda e: e.get('timestamp', ''), reverse=True)

    stats_payload = {
        "status": "success",
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "total_solved": len(solutions_list),
        "unique_problems": len(unique_numbers),
        "languages": language_breakdown,
        "difficulty": global_stats["difficulty"],
        "streak": global_stats["streak"],
        "calendar": global_stats["calendar"],
        "recent_solutions": solutions_list[:5],
        "solutions": solutions_list,
        "repo": f"https://github.com/{GITHUB_REPO}",
    }

    with open('stats.json', 'w') as f:
        json.dump(stats_payload, f, indent=2)

    return stats_payload


def notify_lazyraion_api(payload):
    """Safely notifies lazyraion-api if server is online. Fails silently if server is down."""
    if not LAZYRAION_WEBHOOK:
        return
    headers = {}
    if WEBHOOK_SECRET:
        headers['X-Webhook-Secret'] = WEBHOOK_SECRET
    try:
        requests.post(LAZYRAION_WEBHOOK, json=payload, headers=headers, timeout=5)
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
    username = get_username()
    if not username:
        send_telegram("\u274c *LeetCode Sync Failed*\n\nCouldn't resolve your username \u2014 `LEETCODE_SESSION` is likely expired. Re-extract cookies and update the repo secrets.")
        return

    submissions = get_recent_submissions(username)
    index = load_index()
    new_syncs = 0
    processed_folders = set()

    for sub in submissions:
        lang_slug = sub['lang']
        if lang_slug not in LANG_MAP:
            continue

        lang_info = LANG_MAP[lang_slug]
        folder_name = lang_info['folder']

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

        meta = get_problem_meta(sub['titleSlug'])
        question_id = meta['id']
        file_name = format_filename(sub['title'], question_id) + lang_info['ext']
        file_path = os.path.join(folder_name, file_name)

        comment = lang_info['comment']
        header = (
            f"{comment} Problem: {question_id}. {sub['title']}\n"
            f"{comment} Difficulty: {meta['difficulty']}\n"
            f"{comment} Language: {folder_name}\n"
            f"{comment} Timestamp: \"{timestamp_str}\"\n\n"
        )
        full_code = header + code

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

        index[file_path] = {
            "id": question_id,
            "title": sub['title'],
            "language": folder_name,
            "difficulty": meta['difficulty'],
            "tags": meta['tags'],
            "timestamp": timestamp_str,
            "file": file_path,
            "github_url": f"https://github.com/{GITHUB_REPO}/blob/main/{file_path}",
        }

    prune_index(index)
    save_index(index)

    global_stats = get_global_stats(username)
    stats_data = generate_stats_file(index, global_stats)
    notify_lazyraion_api(stats_data)

    if new_syncs > 0:
        msg = (
            f"\u26a1 *LeetCode Sync Complete*\n\n"
            f"Added or Updated `{new_syncs}` solutions.\n"
            f"Total Solved: `{stats_data['total_solved']}` ({stats_data['unique_problems']} unique)\n"
            f"Difficulty: E `{stats_data['difficulty']['Easy']}` / M `{stats_data['difficulty']['Medium']}` / H `{stats_data['difficulty']['Hard']}`\n"
            f"Streak: `{stats_data['streak']['current_streak']}` days"
        )
        send_telegram(msg)
    else:
        print("No new or updated solutions found.")


def mode_stats():
    username = get_username()
    index = load_index()
    global_stats = get_global_stats(username) if username else {
        "difficulty": {"Easy": 0, "Medium": 0, "Hard": 0},
        "streak": {"current_streak": 0, "total_active_days": 0},
        "calendar": {},
    }
    stats = generate_stats_file(index, global_stats)
    notify_lazyraion_api(stats)

    msg = (
        f"\U0001F4CA *Current Stats*\n\n"
        f"Total Solved: `{stats['total_solved']}` ({stats['unique_problems']} unique)\n"
        f"Difficulty: E `{stats['difficulty']['Easy']}` / M `{stats['difficulty']['Medium']}` / H `{stats['difficulty']['Hard']}`\n"
        f"Streak: `{stats['streak']['current_streak']}` days ({stats['streak']['total_active_days']} active days total)\n\n"
        f"*Languages:*\n"
    )
    for lang, count in stats['languages'].items():
        msg += f"\u2022 `{lang}`: {count}\n"
    send_telegram(msg)


def mode_revision():
    index = load_index()
    if not index:
        send_telegram("\u274c No solved problems found for revision yet.")
        return
    import random
    entry = random.choice(list(index.values()))
    msg = (
        f"\U0001F9E0 *Daily DSA Revision Challenge*\n\n"
        f"\U0001F4CC *Problem:* `{entry['id']}. {entry['title']}`\n"
        f"\U0001F4C1 *Language:* `{entry['language']}`\n"
        f"\U0001F3AF *Difficulty:* `{entry['difficulty']}`\n\n"
        f"\U0001F4A1 Recall the core pattern and the Time/Space complexity before you look:\n"
        f"{entry['github_url']}"
    )
    send_telegram(msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['sync', 'stats', 'revision'], default='sync')
    args = parser.parse_args()

    if args.mode == 'sync':
        mode_sync()
    elif args.mode == 'stats':
        mode_stats()
    else:
        mode_revision()
