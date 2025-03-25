import requests
import csv
import os
import time
import logging
import random
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv
import google.generativeai as genai
import re  # For semantic version parsing

# Load environment variables from .env file
load_dotenv()

# Configure logging to a file for detailed execution tracking
logging.basicConfig(filename='bootstrap_analyzer.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Gemini API setup - API Key is loaded from environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logging.error("Environment variable GOOGLE_API_KEY not found. Ensure it's set in .env file.")
    raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in .env file.")
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro') # Initialize Gemini Pro model

# GitHub API setup - Token and repository details from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    logging.error("Environment variable GITHUB_TOKEN not found. Ensure it's set in .env file.")
    raise ValueError("GITHUB_TOKEN not found in environment variables. Please set it in .env file.")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "twbs")  # Default owner: Twitter Bootstrap (twbs)
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "bootstrap")  # Default repo: bootstrap
GITHUB_HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'}

# Analysis Parameters - Customizable via environment variables or defaults
VALUE_KEYWORDS = ["accessibility", "inclusive", "community"] # Keywords for value discussions
TOP_CONTRIBUTOR_COUNT = int(os.getenv("TOP_CONTRIBUTOR_COUNT", 10)) # Analyze top 10 contributors by commit count
NUM_COMMITS_TO_FETCH = int(os.getenv("NUM_COMMITS_TO_FETCH", 5000)) # Limit commit fetching for API efficiency
ISSUES_PER_PAGE = int(os.getenv("ISSUES_PER_PAGE", 100))
COMMENTS_PER_ISSUE = int(os.getenv("COMMENTS_PER_ISSUE", 100))
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", 1))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
JITTER_DELAY = float(os.getenv("JITTER_DELAY", 0.5))


def get_github_token():
    """Helper function to get GitHub token from environment variables (for consistency)."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logging.error("GITHUB_TOKEN environment variable is not set.")
        print("Error: GITHUB_TOKEN environment variable is not set. Check your .env file.")
        return None
    return github_token


def fetch_releases_branches_milestones_labels(owner, repo, github_token):
    """Fetches releases, branches, milestones, and labels data from GitHub API."""
    headers = {'Authorization': f'token {github_token}'}
    url_base = f"https://api.github.com/repos/{owner}/{repo}"
    endpoints = {
        "releases": f"{url_base}/releases",
        "branches": f"{url_base}/branches",
        "milestones": f"{url_base}/milestones",
        "labels": f"{url_base}/labels"
    }
    data = {}
    for name, url in endpoints.items():
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data[name] = response.json()
            logging.info(f"Successfully fetched {name} data from GitHub API.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching {name} data from GitHub API: {e}")
            print(f"Error fetching {name} data: {e}") # Inform user about fetch errors
            data[name] = None  # Indicate fetch failure

    return data


def analyze_semantic_versioning(releases_data):
    """Analyzes releases for semantic versioning and categorizes them."""
    major_releases, minor_releases, patch_releases = 0, 0, 0
    non_semver_releases = []

    if releases_data and isinstance(releases_data, list):
        for release in releases_data:
            version = release['tag_name']
            match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", version) # Match with or without 'v' prefix
            if match:
                major, minor, patch = map(int, match.groups())
                if major > 0: major_releases += 1
                elif minor > 0: minor_releases += 1
                else: patch_releases += 1
            else:
                non_semver_releases.append(version)
    return major_releases, minor_releases, patch_releases, non_semver_releases


def fetch_commits(owner, repo, github_token, num_commits_to_fetch):
    """Fetches commit data from GitHub API (corrected to handle None author)."""
    commits_data = []
    page = 1
    commits_per_page = 100 # Max allowed by GitHub API
    total_commits_fetched = 0

    while total_commits_fetched < num_commits_to_fetch:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {'per_page': commits_per_page, 'page': page}
        headers = {'Authorization': f'token {github_token}'}

        retries = 0
        delay = DELAY_SECONDS

        while retries <= MAX_RETRIES:
            try:
                logging.info(f"Fetching commits page {page}...")
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                commits = response.json()

                if not commits:
                    logging.info("No more commits found.")
                    return commits_data

                for commit in commits:
                    author_data = commit.get('author')
                    author_login = None
                    if author_data is None:
                        author_login = "N/A (Author data missing)"
                        logging.warning(f"Commit {commit.get('sha', 'N/A')} missing 'author' data.")
                    else:
                        author_login = author_data.get('login', 'N/A')


                    commits_data.append({
                        'author_name': commit['commit']['author']['name'],
                        'author_login': author_login,
                        'files_modified': [f['filename'] for f in commit['files']] if 'files' in commit else [],
                        'commit_date': commit['commit']['author']['date']
                    })
                    total_commits_fetched += 1

                logging.info(f"Fetched {len(commits)} commits from page {page}. Total fetched: {total_commits_fetched}/{num_commits_to_fetch}")
                page += 1
                break # Success, break retry loop

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching commits page {page}, retry {retries + 1}/{MAX_RETRIES}: {e}")
                if retries < MAX_RETRIES:
                    time.sleep(delay + random.uniform(0, JITTER_DELAY))
                    delay *= 2
                else:
                    logging.error(f"Max retries reached for commits page {page}. Aborting page fetch.")
                    return None # Indicate page fetch failure

            retries += 1
        else: # else block for while retries loop
            logging.error(f"Failed to fetch commits page {page} after {MAX_RETRIES} retries. Aborting fetch.")
            return None # Abort entire fetch if page consistently fails

        if total_commits_fetched >= num_commits_to_fetch:
            logging.info(f"Reached desired number of commits ({num_commits_to_fetch}). Stopping fetch.")
            break # Break if reached commit limit

    return commits_data


def fetch_issues_and_comments(owner, repo, github_token, issues_per_page=100, comments_per_issue=100):
    """Fetches issues and their comments from GitHub API (implementation from previous improved script)."""
    issues_comments_data = []
    page = 1

    while True: # Loop to fetch issues page by page
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        params = {'per_page': issues_per_page, 'page': page, 'state': 'closed'} # Fetch closed issues
        headers = {'Authorization': f'token {github_token}'}

        retries = 0
        delay = DELAY_SECONDS

        while retries <= MAX_RETRIES:
            try:
                logging.info(f"Fetching issues page {page}...")
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                issues = response.json()

                if not issues:
                    logging.info("No more issues found.")
                    return issues_comments_data # No more issues, return fetched data

                for issue in issues:
                    issue_data = {
                        'issue_number': issue['number'],
                        'issue_title': issue['title'],
                        'issue_body': issue.get('body', ''), # Handle potential None body
                        'author_login': issue['user']['login'],
                        'created_at': issue['created_at'], # Added issue creation date
                        'comments': []
                    }
                    comments = fetch_comments_for_issue(owner, repo, github_token, issue['number'], comments_per_issue) # Fetch comments for each issue
                    issue_data['comments'] = comments
                    issues_comments_data.append(issue_data)

                logging.info(f"Fetched {len(issues)} issues from page {page}.")
                page += 1
                break # Success, break retry loop

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching issues page {page}, retry {retries + 1}/{MAX_RETRIES}: {e}")
                if retries < MAX_RETRIES:
                    time.sleep(delay + random.uniform(0, JITTER_DELAY))
                    delay *= 2
                else:
                    logging.error(f"Max retries reached for issues page {page}. Aborting page fetch.")
                    return None # Indicate page fetch failure

            retries += 1
        else: # else block for while retries loop
            logging.error(f"Failed to fetch issues page {page} after {MAX_RETRIES} retries. Aborting fetch.")
            return None # Abort entire fetch if page consistently fails


def fetch_comments_for_issue(owner, repo, github_token, issue_number, comments_per_issue=100):
    """Fetches comments for a specific issue (implementation from previous improved script)."""
    comments_data = []
    page = 1
    while True: # Loop to fetch comments page by page
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
        params = {'per_page': comments_per_issue, 'page': page}
        headers = {'Authorization': f'token {github_token}'}

        retries = 0
        delay = DELAY_SECONDS

        while retries <= MAX_RETRIES:
            try:
                logging.info(f"Fetching comments page {page} for issue {issue_number}...")
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                comments = response.json()

                if not comments:
                    logging.info(f"No more comments found for issue {issue_number}.")
                    return comments_data # No more comments, return fetched data

                for comment in comments:
                    comments_data.append({
                        'author_login': comment['user']['login'],
                        'comment_body': comment['body'],
                        'created_at': comment['created_at'] # Added comment creation date
                    })

                logging.info(f"Fetched {len(comments)} comments from page {page} for issue {issue_number}.")
                page += 1
                break # Success, break retry loop

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching comments page {page} for issue {issue_number}, retry {retries + 1}/{MAX_RETRIES}: {e}")
                if retries < MAX_RETRIES:
                    time.sleep(delay + random.uniform(0, JITTER_DELAY))
                    delay *= 2
                else:
                    logging.error(f"Max retries reached for comments page {page} issue {issue_number}. Aborting comment fetch.")
                    return None # Indicate comment fetch failure

            retries += 1
        else: # else block for while retries loop
            logging.error(f"Failed to fetch comments page {page} for issue {issue_number} after {MAX_RETRIES} retries. Aborting comment fetch.")
            return None # Abort comment fetch if page consistently fails


def analyze_contributor_roles(commits_data, top_n=10):
    """Analyzes commit data to determine contributor roles (simplified - implementation from previous improved script)."""
    contributor_commit_count = Counter(commit['author_login'] for commit in commits_data)
    top_contributors_by_commits = contributor_commit_count.most_common(top_n)
    top_contributor_logins = [login for login, count in top_contributors_by_commits]

    contributor_file_types = {}
    for login in top_contributor_logins:
        file_type_counts = Counter()
        for commit in commits_data:
            if commit['author_login'] == login:
                for file_path in commit['files_modified']:
                    file_extension = os.path.splitext(file_path)[1].lower()
                    if file_extension: # Only count if there is an extension
                        file_type_counts[file_extension] += 1
        contributor_file_types[login] = file_type_counts.most_common(5) # Top 5 file types

    return top_contributors_by_commits, contributor_file_types


def analyze_value_discussions_gemini(issues_comments_data, value_keywords, gemini_model):
    """Analyzes issue titles, bodies, and comments for value-related keywords using Gemini API (implementation from previous improved script)."""
    contributor_value_mentions = {}
    for issue_data in issues_comments_data:
        text_to_analyze = f"Issue Title: {issue_data['issue_title']}\nIssue Body: {issue_data['issue_body']}\n"
        for comment in issue_data['comments']:
            text_to_analyze += f"Comment: {comment['comment_body']}\n"

        prompt = f"""Analyze the following text and determine if it discusses any of these values: {', '.join(value_keywords)}.
        Return 'yes' if any of the values are discussed, or 'no' if not. Just return 'yes' or 'no'."""

        try:
            response = gemini_model.generate_content(prompt)
            if response.text.strip().lower() == 'yes':
                for keyword in value_keywords:
                    if keyword in response.text.lower(): # Optional: Check if keyword mentioned in Gemini's response
                        contributor_login = issue_data['author_login'] # Issue author is considered contributor
                        if contributor_login not in contributor_value_mentions:
                            contributor_value_mentions[contributor_login] = set()
                        contributor_value_mentions[contributor_login].add(keyword) # Track mentioned keywords
                        for comment in issue_data['comments']: # Comment authors also considered contributors
                            comment_author_login = comment['author_login']
                            if comment_author_login not in contributor_value_mentions:
                                contributor_value_mentions[comment_author_login] = set()
                            contributor_value_mentions[comment_author_login].add(keyword)

        except Exception as e:
            logging.error(f"Gemini API error during value discussion analysis for issue {issue_data['issue_number']}: {e}")
            print(f"Gemini API error for issue {issue_data['issue_number']}: {e}") # Inform user of Gemini API errors


def get_contributor_contribution_period(issues_comments_data, contributor_login):
    """Calculates the contribution period for a given contributor (more accurate using issue & comment dates)."""
    contribution_dates = []
    for issue_data in issues_comments_data:
        if issue_data['author_login'] == contributor_login:
            contribution_dates.append(datetime.fromisoformat(issue_data['created_at'].replace('Z', '+00:00'))) # Issue creation date
        for comment in issue_data['comments']:
            if comment['author_login'] == contributor_login:
                contribution_dates.append(datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00'))) # Comment creation date

    if not contribution_dates:
        return None, None # No contributions found

    first_contribution = min(contribution_dates)
    last_contribution = max(contribution_dates)
    return first_contribution, last_contribution


def generate_report(releases_data, major_releases, minor_releases, patch_releases, non_semver_releases,
                    branches_data, milestones_data, labels_data,
                    top_contributors_by_commits, contributor_file_types, contributor_value_mentions, issues_comments_data,
                    output_file="bootstrap_comprehensive_report.txt"):
    """Generates a comprehensive report combining release strategy, roles, and turnover analysis."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Bootstrap Repository Comprehensive Analysis Report\n")
        f.write("-------------------------------------------------------\n\n")

        # Release Strategy Section (using data from generate_release_strategy_report)
        f.write("1. Release Strategy and Change Management:\n")
        f.write("-------------------------------------------\n")
        f.write("Bootstrap follows Semantic Versioning (MAJOR.MINOR.PATCH).\n")
        f.write(f"- MAJOR Releases: {major_releases} (incompatible changes)\n")
        f.write(f"- MINOR Releases: {minor_releases} (new features, compatible)\n")
        f.write(f"- PATCH Releases: {patch_releases} (bug/security fixes)\n")
        if non_semver_releases:
            f.write("\nNon-Semantic Version Releases:\n")
            for version in non_semver_releases:
                f.write(f"  - {version}\n")
        if branches_data and isinstance(branches_data, list):
            f.write(f"\nTotal Branches: {len(branches_data)}\n")
        if milestones_data and isinstance(milestones_data, list):
            f.write(f"\nTotal Milestones: {len(milestones_data)}\n")
        if labels_data and isinstance(labels_data, list):
            f.write(f"\nTotal Labels: {len(labels_data)}\n\n")

        # Contributor Roles Section (using data from generate_report function previously)
        f.write("\n2. Contributor Roles Analysis:\n")
        f.write("------------------------------\n")
        f.write("Top Contributors by Commit Count:\n")
        for login, commit_count in top_contributors_by_commits:
            f.write(f"- {login}: {commit_count} commits\n")
            f.write("  Top File Types Modified (by commits):\n")
            for file_type, count in contributor_file_types.get(login, []):
                f.write(f"    - {file_type}: {count} times\n")
            f.write("\n")

        # Value Discussions and Contribution Period Section (using data from generate_report previously and contribution period)
        f.write("\n3. Value-Related Discussions and Contribution Period:\n")
        f.write("---------------------------------------------------\n")
        if contributor_value_mentions:
            f.write("Contributors Involved in Value-Related Discussions:\n")
            for login, keywords in contributor_value_mentions.items():
                f.write(f"- {login}: Mentioned values - {', '.join(keywords)}\n")
                first_contribution, last_contribution = get_contributor_contribution_period(issues_comments_data, login)
                if first_contribution and last_contribution:
                    duration = last_contribution - first_contribution
                    f.write(f"  Contribution Period: From {first_contribution.strftime('%Y-%m-%d')} to {last_contribution.strftime('%Y-%m-%d')} (Duration: {duration.days} days)\n")
                else:
                    f.write("  Contribution Period: N/A\n") # Indicate if contribution period unavailable
            f.write("\n")
        else:
            f.write("No contributors found involved in value-related discussions.\n\n")

        f.write("\n--- End of Comprehensive Report ---\n")

    print(f"Comprehensive report saved to {output_file}")
    logging.info(f"Comprehensive report saved to {output_file}")


def main():
    """Main function to orchestrate Bootstrap comprehensive analysis and report generation."""
    github_token = get_github_token()
    if not github_token:
        return

    logging.info("Starting Bootstrap comprehensive repository analysis...")
    print("Starting Bootstrap comprehensive repository analysis...")

    # Fetch data for Release Strategy Analysis
    release_mgmt_data = fetch_releases_branches_milestones_labels(GITHUB_REPO_OWNER, GITHUB_REPO_NAME, github_token)

    # Analyze Release Strategy
    major_releases, minor_releases, patch_releases, non_semver_releases = analyze_semantic_versioning(release_mgmt_data.get('releases'))

    # Fetch data for Contributor Analysis (in parallel or series, depending on needs)
    commits_data = fetch_commits(GITHUB_REPO_OWNER, GITHUB_REPO_NAME, github_token, NUM_COMMITS_TO_FETCH)
    issues_comments_data = fetch_issues_and_comments(GITHUB_REPO_OWNER, GITHUB_REPO_NAME, github_token, ISSUES_PER_PAGE, COMMENTS_PER_ISSUE)

    # Analyze Contributor Roles and Value Discussions
    top_contributors_by_commits, contributor_file_types = analyze_contributor_roles(commits_data, TOP_CONTRIBUTOR_COUNT) if commits_data else ([], {})
    contributor_value_mentions = analyze_value_discussions_gemini(issues_comments_data, VALUE_KEYWORDS, gemini_model) if issues_comments_data else {}


    # Generate Comprehensive Report
    generate_report(
        release_mgmt_data.get('releases'), major_releases, minor_releases, patch_releases, non_semver_releases,
        release_mgmt_data.get('branches'), release_mgmt_data.get('milestones'), release_mgmt_data.get('labels'),
        top_contributors_by_commits, contributor_file_types, contributor_value_mentions, issues_comments_data,
        output_file="bootstrap_comprehensive_analysis_report.txt"
    )


    logging.info("Bootstrap repository comprehensive analysis completed. Comprehensive report generated.")
    print("Bootstrap repository comprehensive analysis completed. Comprehensive report generated.")


if __name__ == "__main__":
    main()