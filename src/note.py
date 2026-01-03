import os
import datetime
import random
from github import Github
import dotenv

dotenv.load_dotenv()
GITHUB_ACCESS_TOKEN = os.environ["GITHUB_ACCESS_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
MEMO_BASE_DIR = os.environ.get("MEMO_BASE_DIR", "seeds")

class NoteRegistry:
    def __init__(self):
        self.g = Github(GITHUB_ACCESS_TOKEN)
        self.repo = self.g.get_repo(f'{GITHUB_USERNAME}/{GITHUB_REPOSITORY}')

    def append(self, content):
        """追記保存"""
        print(f"[Debug] NoteStore.append called with: '{content}'")
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=+9), 'JST'))
        if now.hour < 4:
            now = now - datetime.timedelta(days=1)
        message = f"{now.year}.{now.month}.{now.day}"
        file_path = f"{MEMO_BASE_DIR}/{now.year}/{now.month:02d}/{now.month:02d}{now.day:02d}.md"
        print(f"[Debug] Target file path: {file_path}")

        try:
            print(f"[Debug] Attempting to get existing file...")
            file_contents = self.repo.get_contents(file_path, ref="main")
            existing_content = file_contents.decoded_content.decode()
            new_content = existing_content + "\n\n---\n\n" + content.strip()
            commit = f"Update {message}"
            print(f"[Debug] Updating existing file with commit: {commit}")
            self.repo.update_file(
                file_path, commit, new_content, file_contents.sha, branch="main")
            print(f"File {message} updated.")
        except Exception as e:
            print(f"[Debug] File doesn't exist, creating new file: {e}")
            commit = f"Add {message}"
            formatted_content = content.strip()
            print(f"[Debug] Creating file with content: '{formatted_content}'")
            self.repo.create_file(file_path, commit, formatted_content, branch="main")
            print(f"File {message} created.")

        file_contents = self.repo.get_contents(file_path)
        print(f"[Debug] File URL: {file_contents.html_url}")
        return file_contents.html_url

    def read_random_file(self) -> str:
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=+9), 'JST'))

        start_date = datetime.datetime(2023, 3, 17, tzinfo=datetime.timezone(datetime.timedelta(hours=+9), 'JST'))

        delta = now.date() - start_date.date()
        random_days = random.randint(0, delta.days)
        random_date = start_date + datetime.timedelta(days=random_days)

        year, month, day = random_date.year, random_date.month, random_date.day
        file_path = f"{MEMO_BASE_DIR}/{year}/{month:02d}/{month:02d}{day:02d}.md"

        try:
            file_contents = self.repo.get_contents(file_path)
            content = file_contents.decoded_content.decode()
            return content, year, month, day
        except Exception as e:
            return "No content found.", year, month, day

    def read_file(self, year, month, day) -> str:
        file_path = f"{MEMO_BASE_DIR}/{year}/{month:02d}/{month:02d}{day:02d}.md"

        try:
            file_contents = self.repo.get_contents(file_path)
            content = file_contents.decoded_content.decode()
            return content
        except Exception as e:
            print(f"Error reading file: {e}")
            print(f"No file found for {year}/{month:02d}{day:02d}.md")

    def append_image(self, image_data: bytes, extension: str = "jpg"):
        """画像保存（メモに追記）"""
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=+9), 'JST'))
        if now.hour < 4:
            now = now - datetime.timedelta(days=1)

        # ファイル名: YYYY-MM-DD-HHMMSS.jpg
        timestamp = now.strftime("%Y-%m-%d-%H%M%S")
        image_filename = f"{timestamp}.{extension}"

        # 画像保存先: seeds/2026/01/assets/2026-01-03-143052.jpg
        assets_path = f"{MEMO_BASE_DIR}/{now.year}/{now.month:02d}/assets/{image_filename}"

        commit_message = f"Add image {timestamp}"

        try:
            self.repo.create_file(
                assets_path, commit_message, image_data, branch="main")
            print(f"Image {image_filename} uploaded.")
        except Exception as e:
            print(f"[Error] Failed to upload image: {e}")
            raise

        # メモに画像リンクを追記
        markdown_link = f"![{image_filename}](assets/{image_filename})"
        self.append(markdown_link)

        return assets_path
