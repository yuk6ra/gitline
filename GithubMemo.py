import os
import datetime
import random
from github import Github
import dotenv

dotenv.load_dotenv()
GITHUB_ACCESS_TOKEN = os.environ["GITHUB_ACCESS_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]

class MemoRegistry:
    def __init__(self):
        self.g = Github(GITHUB_ACCESS_TOKEN)
        self.repo = self.g.get_repo(f'{GITHUB_USERNAME}/{GITHUB_REPOSITORY}')

    def write_memo(self, content):
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=+9), 'JST'))
        if now.hour < 4:
            now = now - datetime.timedelta(days=1)
        message = f"{now.year}.{now.month}.{now.day}"
        file_path = f"{now.year}/{now.month:02d}{now.day:02d}.md"
        try:
            file_contents = self.repo.get_contents(file_path)
            existing_content = file_contents.decoded_content.decode()
            new_content = existing_content + "\n" + "- " + content.strip().replace("\n", "\n  ")
            commit = f"Update {message}"
            self.repo.update_file(
                file_path, commit, new_content, file_contents.sha, branch="main")
            print(f"File {message} updated.")
        except Exception as e:
            print(f"Create a file: {e}")
            commit = f"Add {message}"
            self.repo.create_file(file_path, commit, "- " + content.strip().replace("\n", "\n  "), branch="main")
            print(f"File {message} created.")

        file_contents = self.repo.get_contents(file_path)
        print(file_contents.html_url)
        return file_contents.html_url

    def read_random_file(self) -> str:
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=+9), 'JST'))

        start_date = datetime.datetime(2023, 3, 17, tzinfo=datetime.timezone(datetime.timedelta(hours=+9), 'JST'))

        delta = now.date() - start_date.date()
        random_days = random.randint(0, delta.days)
        random_date = start_date + datetime.timedelta(days=random_days)

        year, month, day = random_date.year, random_date.month, random_date.day
        file_path = f"{year}/{month:02d}{day:02d}.md"

        try:
            file_contents = self.repo.get_contents(file_path)
            content = file_contents.decoded_content.decode()
            print(f"Contents of file {year}/{month:02d}{day:02d}.md:\n{content}")
            return content, year, month, day
        except Exception as e:
            print(f"Error reading file: {e}")
            print(f"No file found for {year}/{month:02d}{day:02d}.md")