import os
import re
import datetime
from github import Github
import dotenv

dotenv.load_dotenv()
GITHUB_ACCESS_TOKEN = os.environ["GITHUB_ACCESS_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
DAILY_BASE_DIR = os.environ.get("DAILY_BASE_DIR", "daily")


class DailyRegistry:
    """日記用ストア（上書き保存）"""
    # 日付パターン: YYYY/MM/DD または YYYY-MM-DD
    DATE_PATTERN = re.compile(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})')

    def __init__(self):
        self.g = Github(GITHUB_ACCESS_TOKEN)
        self.repo = self.g.get_repo(f'{GITHUB_USERNAME}/{GITHUB_REPOSITORY}')

    def save(self, content):
        """上書き保存（メッセージ内の日付を使用）"""
        # メッセージから日付を抽出
        match = self.DATE_PATTERN.match(content)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            # 日付行を除去
            content = content[match.end():].lstrip('\n')
        else:
            # 日付がない場合は現在日時を使用
            now = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=+9), 'JST'))
            if now.hour < 4:
                now = now - datetime.timedelta(days=1)
            year, month, day = now.year, now.month, now.day

        message = f"{year}.{month}.{day}"
        file_path = f"{DAILY_BASE_DIR}/{year}/{month:02d}/{month:02d}{day:02d}.md"

        try:
            file_contents = self.repo.get_contents(file_path, ref="main")
            commit = f"{DAILY_BASE_DIR}: Update {message}"
            self.repo.update_file(
                file_path, commit, content.strip(), file_contents.sha, branch="main")
            print(f"Diary {message} updated.")
        except Exception:
            commit = f"{DAILY_BASE_DIR}: Add {message}"
            self.repo.create_file(file_path, commit, content.strip(), branch="main")
            print(f"Diary {message} created.")

        file_contents = self.repo.get_contents(file_path)
        return file_contents.html_url

    def read_file(self, year, month, day) -> str:
        file_path = f"{DAILY_BASE_DIR}/{year}/{month:02d}/{month:02d}{day:02d}.md"

        try:
            file_contents = self.repo.get_contents(file_path)
            content = file_contents.decoded_content.decode()
            return content
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
