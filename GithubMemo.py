import os
import datetime
from github import Github
import dotenv

dotenv.load_dotenv()
GITHUB_ACCESS_TOKEN = os.environ["GITHUB_ACCESS_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]

class StockMemo:
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