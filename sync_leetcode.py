import os
import requests
import datetime
import re

SESSION = os.environ.get('LEETCODE_SESSION')
CSRF = os.environ.get('LEETCODE_CSRF')

HEADERS = {
    'Cookie': f'LEETCODE_SESSION={SESSION}; csrftoken={CSRF};',
    'x-csrftoken': CSRF,
    'Content-Type': 'application/json',
    'Referer': 'https://leetcode.com'
}

URL = 'https://leetcode.com/graphql'

# Map LeetCode language slugs to file extensions and comment syntaxes
LANG_MAP = {
    'java': {'ext': '.java', 'comment': '//'},
    'python3': {'ext': '.py', 'comment': '#'},
    'python': {'ext': '.py', 'comment': '#'},
    'cpp': {'ext': '.cpp', 'comment': '//'},
    'c': {'ext': '.c', 'comment': '//'},
    'javascript': {'ext': '.js', 'comment': '//'}
}

def get_recent_submissions():
    query = """
    query GetRecentSubmissions($limit: Int!) {
      recentAcSubmissionList(username: "", limit: $limit) {
        id
        title
        titleSlug
        timestamp
        lang
      }
    }
    """
    response = requests.post(URL, json={'query': query, 'variables': {'limit': 20}}, headers=HEADERS)
    return response.json().get('data', {}).get('recentAcSubmissionList', [])

def get_submission_code(sub_id):
    query = """
    query submissionDetails($id: Int!) {
      submissionDetails(submissionId: $id) {
        code
      }
    }
    """
    response = requests.post(URL, json={'query': query, 'variables': {'id': sub_id}}, headers=HEADERS)
    return response.json().get('data', {}).get('submissionDetails', {}).get('code', '')

def format_filename(title):
    # Removes special characters and replaces spaces with underscores
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    return clean_title.replace(' ', '_')

def main():
    submissions = get_recent_submissions()
    
    for sub in submissions:
        lang_slug = sub['lang']
        if lang_slug not in LANG_MAP:
            continue
            
        lang_info = LANG_MAP[lang_slug]
        code = get_submission_code(sub['id'])
        
        if not code:
            continue

        # Format Timestamp
        dt = datetime.datetime.fromtimestamp(int(sub['timestamp']))
        timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Inject timestamp in quotes
        comment_prefix = lang_info['comment']
        injected_code = f'{comment_prefix} Timestamp: "{timestamp_str}"\n\n{code}'
        
        # Create Directory based on Language (e.g., "Java")
        folder_name = lang_slug.capitalize()
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            
        # Format File Name (e.g., Java/Two_Sum.java)
        file_name = f"{format_filename(sub['title'])}{lang_info['ext']}"
        file_path = os.path.join(folder_name, file_name)
        
        # Skip if file already exists to avoid unnecessary commits
        if os.path.exists(file_path):
            continue
            
        with open(file_path, 'w') as f:
            f.write(injected_code)
        print(f"Saved: {file_path}")

if __name__ == "__main__":
    main()

