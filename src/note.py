import os
import datetime
import random
import json
from github import Github
from openai import OpenAI
import dotenv

dotenv.load_dotenv()
GITHUB_ACCESS_TOKEN = os.environ["GITHUB_ACCESS_TOKEN"]
GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

class NoteRegistry:
    def __init__(self):
        self.g = Github(GITHUB_ACCESS_TOKEN)
        self.repo = self.g.get_repo(f'{GITHUB_USERNAME}/{GITHUB_REPOSITORY}')

    def write(self, content):
        print(f"[Debug] NoteRegistry.write called with: '{content}'")
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=+9), 'JST'))
        if now.hour < 4:
            now = now - datetime.timedelta(days=1)
        message = f"{now.year}.{now.month}.{now.day}"
        file_path = f"{now.year}/{now.month:02d}/{now.month:02d}{now.day:02d}.md"
        print(f"[Debug] Target file path: {file_path}")
        
        try:
            print(f"[Debug] Attempting to get existing file...")
            file_contents = self.repo.get_contents(file_path)
            existing_content = file_contents.decoded_content.decode()
            new_content = existing_content + "\n" + "- " + content.strip().replace("\n", "\n  ")
            commit = f"Update {message}"
            print(f"[Debug] Updating existing file with commit: {commit}")
            self.repo.update_file(
                file_path, commit, new_content, file_contents.sha, branch="main")
            print(f"File {message} updated.")
        except Exception as e:
            print(f"[Debug] File doesn't exist, creating new file: {e}")
            commit = f"Add {message}"
            formatted_content = "- " + content.strip().replace("\n", "\n  ")
            print(f"[Debug] Creating file with content: '{formatted_content}'")
            self.repo.create_file(file_path, commit, formatted_content, branch="main")
            print(f"File {message} created.")

        file_contents = self.repo.get_contents(file_path)
        print(f"[Debug] File URL: {file_contents.html_url}")
        return file_contents.html_url
    
    def write_qa_pair(self, question, answer):
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=+9), 'JST'))
        if now.hour < 4:
            now = now - datetime.timedelta(days=1)
        message = f"{now.year}.{now.month}.{now.day}"
        file_path = f"{now.year}/{now.month:02d}/{now.month:02d}{now.day:02d}.md"
        
        # 固定インデントレベル
        # 1階層目: メモ (-)
        # 2階層目: 質問 (  -)  
        # 3階層目: 回答 (    -)
        question_indent = "  "    # 常に2スペース
        answer_indent = "    "    # 常に4スペース
        
        # 分析の場合は既に構造化されているので、余分な「-」を追加しない
        if question == "AIによる客観的分析":
            # 分析結果の空行を除去してから処理
            cleaned_answer = '\n'.join(line for line in answer.strip().split('\n') if line.strip())
            qa_content = f"{question_indent}- {question}\n{answer_indent}{cleaned_answer.replace('\n', '\n' + answer_indent)}"
        else:
            qa_content = f"{question_indent}- {question}\n{answer_indent}- {answer.strip().replace('\n', '\n' + answer_indent + '  ')}"
        
        try:
            file_contents = self.repo.get_contents(file_path)
            existing_content = file_contents.decoded_content.decode()
            new_content = existing_content + "\n" + qa_content
            commit = f"Update {message} - Deep dive Q&A"
            self.repo.update_file(
                file_path, commit, new_content, file_contents.sha, branch="main")
            print(f"Q&A added to {message}")
        except Exception as e:
            print(f"Error adding Q&A: {e}")
            commit = f"Add {message} - Deep dive Q&A"
            self.repo.create_file(file_path, commit, qa_content, branch="main")
            print(f"Q&A file {message} created.")
        
        return True

    def read_random_file(self) -> str:
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=+9), 'JST'))

        start_date = datetime.datetime(2023, 3, 17, tzinfo=datetime.timezone(datetime.timedelta(hours=+9), 'JST'))

        delta = now.date() - start_date.date()
        random_days = random.randint(0, delta.days)
        random_date = start_date + datetime.timedelta(days=random_days)

        year, month, day = random_date.year, random_date.month, random_date.day
        file_path = f"{year}/{month:02d}/{month:02d}{day:02d}.md"

        try:
            file_contents = self.repo.get_contents(file_path)
            content = file_contents.decoded_content.decode()
            return content, year, month, day
        except Exception as e:
            return "No content found.", year, month, day

    def read_file(self, year, month, day) -> str:
        file_path = f"{year}/{month:02d}/{month:02d}{day:02d}.md"

        try:
            file_contents = self.repo.get_contents(file_path)
            content = file_contents.decoded_content.decode()
            return content
        except Exception as e:
            print(f"Error reading file: {e}")
            print(f"No file found for {year}/{month:02d}{day:02d}.md")

class SocraticAI:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.system_prompt = """
■ CONTEXT
You are a Socratic thinking partner facilitating hierarchical deep-dive conversations.

■ ROLE
Generate up to 5 concise, high-leverage questions that propel the dialogue to new depth.

■ THINKING PROCESS  ★必ず順守
1. **Trace the thread** – Summarize the logical flow so far in your head:  
   themes, assumptions, contradictions, decisions.
2. **Spot the gaps** – Locate areas that are vague, controversial, or unexplored.
3. **Map to categories** – Pick *different* categories below for each question  
   (no duplicates unless <5 questions are produced).
4. **Craft & test** – For each question, ask yourself:  
   - Does it reference a prior answer or tension?  
   - Does it demand specificity or expose implications?  
   - Will it likely move the conversation forward?  
If not, rewrite.

■ INPUT
You always receive the entire conversation tree, including:
• Memo / notes
• All previous Q&A pairs

When previous Q&A is provided:
- Analyze the complete thought progression from memo → questions → answers
- Identify emerging themes, contradictions, or unexplored angles
- Generate questions that synthesize previous insights and explore new depths
- Consider how each answer reveals new aspects worth exploring

■ QUESTION CATEGORIES
• Clarify    – Define terms or narrow the scope
• Cause      – Uncover motives or root causes  
• Impact     – Explore consequences, benefits, or risks
• Alternative– Surface other options or opposing views
• Evidence   – Seek supporting facts, data, or precedents
• Action     – Identify next steps, experiments, or plans
• Meta – Examine the framing of the question itself, test its relevance, and recalibrate the inquiry’s direction
• Values – Surface ethical principles, stakeholder values, and normative implications to ensure alignment and fairness

Your questions should:
1. Reference and build on previous answers
2. Explore connections between different parts of the conversation
3. Push for greater specificity or broader implications
4. Challenge assumptions that emerged
5. Synthesize insights into new inquiry directions

■ OUTPUT FORMAT
• Format: JSON  
  {
    "questions": [
      {"type": "Clarify",    "q": "（120文字以内の日本語質問）"},
      …
    ]
  }
• Language: Japanese only  
• Length: ≤120 full-width characters / question  
• Avoid yes-or-no questions; aim for open, probing inquiries.  

Remember: challenge assumptions, connect dots, expand horizons.
"""

    def generate_analysis(self, memo, qa_history=None, user_context=None):
        analysis_prompt = """
■ CONTEXT
You are an objective analytical assistant who distills the user’s memo and Q&A history into clear, actionable insight.

■ ROLE
Read the entire conversation (original memo + full Q&A thread + any user context) and produce a concise, neutral analysis that helps the user see patterns, blind spots, and next-step implications.

■ INPUT
• Original memo / thought  
• Complete Q&A conversation history (if any)  
• Additional user context (if provided)

■ ANALYSIS APPROACH
1. Pattern Recognition – Detect themes, contradictions, and recurring ideas.  
2. Depth Assessment – Gauge how thoroughly each theme has been explored.  
3. Gap Analysis – Highlight untested assumptions or missing angles.  
4. Perspective Synthesis – Connect disparate points across the dialogue.  
5. Objective Insight – Offer neutral observations on thinking habits.

■ ANALYSIS THEMES  ─ always cover all five
A. ギャップと未検証仮説 (Gaps & Untested Hypotheses)
   • Purpose: Reveal silent assumptions and untouched areas.
   • Question Tips: Ask “What evidence would falsify this?” or “Which assumption remains untested?”

B. 論拠の質とエビデンス強度 (Evidence Quality)
   • Purpose: Evaluate credibility of data and reasoning.
   • Question Tips: Probe source reliability, sample size, counter-evidence.

C. ステークホルダー多面視点 (Stakeholder Perspectives)
   • Purpose: Surface viewpoints of all relevant actors.
   • Question Tips: “How would X perceive this?” or “Whose incentives differ?”

D. 認知バイアスと感情トーン (Cognitive Bias & Emotional Tone)
   • Purpose: Detect bias or emotive language that skews judgement.
   • Question Tips: Invite role-reversal, devil’s-advocate framing.

E. 実行可能性とインパクト (Feasibility vs. Impact)
   • Purpose: Weigh practicality against expected value.
   • Question Tips: Compare effort-to-benefit ratios, outline minimal viable tests.

■ OUTPUT FORMAT
Return Japanese only, full-width characters total, structured exactly like:

- ギャップと未検証仮説  
  - …
- 論拠の質とエビデンス強度  
  - …
- ステークホルダー多面視点  
  - …
- 認知バイアスと感情トーン  
  - …
- 実行可能性とインパクト  
  - …

Guidelines:
• Use “- …” for each bullet (no extra sections, no numbering changes).  
• Keep each bullet crisp and insight-rich; avoid repetition.  
• Do not exceed 1500 characters overall; aim for 300 characters per theme.  
• Provide no extra commentary before or after the structured list.

Remember: stay neutral, connect dots, and surface the most valuable angles for sharper future questioning.
"""
        
        try:
            print(f"[Debug] Generating analysis for memo: '{memo}'")
            if qa_history:
                print(f"[Debug] Including Q&A history for analysis: {qa_history}")
            if user_context:
                print(f"[Debug] Additional user context: {user_context}")
            
            # コンテキストを構築
            if qa_history and len(qa_history) > 0:
                context = f"Original memo: {memo}\n\n■ Complete conversation history:\n"
                for i, qa in enumerate(qa_history, 1):
                    context += f"Q{i}: {qa['question']}\nA{i}: {qa['answer']}\n\n"
            else:
                context = f"Memo: {memo}"
            
            if user_context:
                context += f"\n■ Additional context from user:\n{user_context}"
            
            print(f"[Debug] System prompt for analysis: {analysis_prompt}")
            print(f"[Debug] User prompt for analysis: {context}")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": analysis_prompt},
                    {"role": "user", "content": context}
                ],
            )
            
            analysis = response.choices[0].message.content
            print(f"[Debug] AI Analysis: {analysis}")
            return analysis
            
        except Exception as e:
            print(f"Error generating analysis: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_questions(self, memo, qa_history=None, regenerate=False):
        try:
            print(f"[Debug] Generating questions for memo: '{memo}'")
            if qa_history:
                print(f"[Debug] Including Q&A history: {qa_history}")
            if regenerate:
                print(f"[Debug] Regenerating questions with different approach")
            
            # コンテキストを構築
            if qa_history and len(qa_history) > 0:
                context = f"Original memo: {memo}\n\n ■ Conversation flow (hierarchical thinking process):\n"
                
                # 階層的な文脈を構築
                for i, qa in enumerate(qa_history, 1):
                    context += f"Level {i+1} Question: {qa['question']}\n"
                    context += f"Level {i+2} Answer: {qa['answer']}\n\n"
                
                if regenerate:
                    context += f"The user requested regeneration of questions. Based on the complete conversation above, "
                    context += "generate DIFFERENT questions that explore alternative angles, challenge different assumptions, "
                    context += "or approach the topic from completely new perspectives. Avoid repeating similar question styles."
                else:
                    context += f"Based on the complete hierarchical conversation above (memo + {len(qa_history)} rounds of Q&A), "
                    context += "generate new questions that build upon ALL previous insights and dive even deeper into the topic. "
                    context += "The new questions should consider the entire conversation thread and explore new dimensions or go deeper into established themes."
            else:
                if regenerate:
                    context = f"Memo: {memo}\n\nThe user requested regeneration. Generate different questions with alternative perspectives and approaches."
                else:
                    context = f"Memo: {memo}"
            
            print(f"[Debug] Generated context: {context}")
            print(f"[Debug] System prompt: {self.system_prompt}")
            print(f"[Debug] User prompt: {context}")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context}
                ],
            )
            
            questions_json = response.choices[0].message.content
            print(f"[Debug] Raw OpenAI response: {questions_json}")
            
            questions_data = json.loads(questions_json)
            print(f"[Debug] Parsed JSON: {questions_data}")
            
            # 応答形式を確認し、適切に処理
            if isinstance(questions_data, dict):
                if "questions" in questions_data:
                    questions = questions_data["questions"]
                elif "items" in questions_data:
                    questions = questions_data["items"]
                else:
                    # 辞書の値がリストの場合、それを使用
                    for key, value in questions_data.items():
                        if isinstance(value, list):
                            questions = value
                            break
                    else:
                        print(f"[Error] Unexpected response format: {questions_data}")
                        return []
            elif isinstance(questions_data, list):
                questions = questions_data
            else:
                print(f"[Error] Unexpected response type: {type(questions_data)}")
                return []
            
            print(f"[Debug] Final questions: {questions}")
            return questions
            
        except Exception as e:
            print(f"Error generating questions: {e}")
            import traceback
            traceback.print_exc()
            return []

class DeepDiveSession:
    def __init__(self):
        self.sessions = {}
        self.max_rounds = 10
    
    def start_session(self, user_id, memo):
        session_id = f"{user_id}_{datetime.datetime.now().timestamp()}"
        self.sessions[session_id] = {
            "original_memo": memo,
            "round": 0,
            "questions": [],
            "qa_pairs": []
        }
        return session_id
    
    def get_session(self, session_id):
        return self.sessions.get(session_id)
    
    def is_session_complete(self, session_id):
        session = self.get_session(session_id)
        return session and session["round"] >= self.max_rounds
    
    def add_qa_pair(self, session_id, question, answer):
        session = self.get_session(session_id)
        if session:
            session["qa_pairs"].append({"question": question, "answer": answer})
            session["round"] += 1
    
    def end_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]       
