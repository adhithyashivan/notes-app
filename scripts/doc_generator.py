# scripts/doc_generator.py

import os
import sys
import json
import time  # For potential rate limiting

# Attempt to import necessary libraries, provide guidance if missing
try:
    import openai
except ImportError:
    print("OpenAI library not found. Please install it: pip install openai")
    sys.exit(1)

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    print("Requests library not found. Please install it: pip install requests")
    sys.exit(1)

# --- Configuration for Ignored Items ---
IGNORED_FOLDERS = {
    "venv", "antenv", ".git", ".github", "__pycache__", "node_modules",
    "build", "dist", "static", "templates", "scripts",
}
IGNORED_FILES = {
    ".gitignore", "LICENSE", "README.md", "requirements.txt", "Pipfile",
    "Pipfile.lock", "poetry.lock", "pyproject.toml", "app.pyc",
}
TARGET_EXTENSIONS = {".py", }

# --- Helper Functions for Ignoring Items ---


def should_ignore_dir(dir_name):
    return dir_name.lower() in IGNORED_FOLDERS


def should_ignore_file(file_name):
    return file_name.lower() in IGNORED_FILES


def has_target_extension(file_name):
    if not TARGET_EXTENSIONS:
        return True
    _, ext = os.path.splitext(file_name)
    return ext.lower() in TARGET_EXTENSIONS

# --- Core Logic Functions ---


def find_files_to_document(code_root_path):
    files_for_documentation = []
    if not os.path.isdir(code_root_path):
        print(
            f"Error: Provided code root path '{code_root_path}' is not a valid directory.")
        return files_for_documentation

    abs_code_root_path = os.path.abspath(code_root_path)
    print(f"Starting scan in: {abs_code_root_path}")
    # ... (optional: print ignored lists and target extensions) ...
    print("-" * 30)

    for root, dirs, files in os.walk(abs_code_root_path, topdown=True):
        dirs[:] = [d for d in dirs if not should_ignore_dir(d)]
        for file_name in files:
            if should_ignore_file(file_name) or not has_target_extension(file_name):
                continue
            files_for_documentation.append(os.path.join(root, file_name))
    return files_for_documentation


def generate_documentation_for_file(file_path, openai_client):
    print(f"\n--- Attempting to generate documentation for: {file_path} ---")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if not content.strip():
            print(f"File {file_path} is empty. Skipping OpenAI call.")
            return f"## Documentation for `{os.path.basename(file_path)}`\n\nFile is empty or contains only whitespace."

        # Max content length consideration for OpenAI (e.g., 80k chars ~ 20k tokens)
        max_chars_for_openai = 80000
        if len(content) > max_chars_for_openai:
            print(
                f"Warning: File {file_path} is very large ({len(content)} chars). Truncating for OpenAI processing.")
            content = content[:max_chars_for_openai] + \
                "\n\n[CONTENT TRUNCATED DUE TO LENGTH]"

        prompt = (
            f"Generate concise technical documentation in Markdown format for the following code file named '{os.path.basename(file_path)}'. "
            "Focus on its purpose, main functions/classes, inputs, outputs, and key logic. "
            "Use standard Markdown for headings, lists, bolding, etc.\n\n"
            f"File Content:\n```\n{content}\n```"
        )
        print(f"Sending content of {os.path.basename(file_path)} to OpenAI...")
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert technical writer assistant specializing in clear and concise code documentation in Markdown format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000  # Increased slightly for potentially longer docs
        )
        documentation = response.choices[0].message.content
        print(
            f"Received documentation from OpenAI for {os.path.basename(file_path)}")
        return documentation
    except openai.APIError as e:
        print(f"OpenAI API Error processing file {file_path}: {e}")
        return f"## Error generating documentation for `{os.path.basename(file_path)}`\n\nOpenAI API Error: {e}"
    except Exception as e:
        print(f"Unexpected error processing file {file_path}: {e}")
        return f"## Error generating documentation for `{os.path.basename(file_path)}`\n\nUnexpected error: {e}"


def get_confluence_page_id(confluence_url, auth, space_key, title):
    search_url = f"{confluence_url.rstrip('/')}/rest/api/content"
    params = {"spaceKey": space_key, "title": title, "expand": "version"}
    try:
        response = requests.get(search_url, auth=auth, params=params, headers={
                                "Accept": "application/json"}, timeout=10)
        response.raise_for_status()
        results = response.json().get('results', [])
        if results:
            return results[0]['id'], results[0]['version']['number']
    except requests.exceptions.RequestException as e:
        print(f"Error searching for Confluence page '{title}': {e}")
    return None, None


def create_or_update_confluence_page(confluence_url, auth, space_key, title, markdown_body_content, parent_id=None):
    """
    Creates or updates a page in Confluence, wrapping the markdown_body_content
    in Confluence's Markdown macro for proper rendering.
    """
    page_id, current_version = get_confluence_page_id(
        confluence_url, auth, space_key, title)
    rest_url = f"{confluence_url.rstrip('/')}/rest/api/content"

    # Wrap the Markdown content in the Confluence Markdown macro (storage format)
    confluence_storage_content = (
        f'<ac:structured-macro ac:name="markdown" ac:schema-version="1">'
        f'  <ac:plain-text-body><![CDATA[{markdown_body_content}]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )

    page_data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": confluence_storage_content,
                "representation": "storage"
            }
        }
    }
    if parent_id:
        page_data["ancestors"] = [{"id": parent_id}]

    try:
        http_method = requests.put if page_id else requests.post
        full_url = f"{rest_url}/{page_id}" if page_id else rest_url
        action_word = "Updating" if page_id else "Creating"

        if page_id:
            page_data["id"] = page_id
            page_data["version"] = {"number": current_version + 1}

        print(f"{action_word} Confluence page: '{title}'" +
              (f" (ID: {page_id})" if page_id else ""))
        response = http_method(full_url, auth=auth, json=page_data, headers={
                               "Content-Type": "application/json", "Accept": "application/json"}, timeout=20)
        response.raise_for_status()

        # Construct full web UI link
        base_url = confluence_url.rstrip('/')
        page_web_ui_path = response.json().get('_links', {}).get('webui', '')
        full_page_link = f"{base_url}{page_web_ui_path}" if page_web_ui_path else "N/A"
        print(
            f"Successfully {action_word.lower().replace('ing', 'ed')} page '{title}'. Link: {full_page_link}")
        return response.json().get('id')

    except requests.exceptions.HTTPError as e:
        print(
            f"HTTP Error during Confluence operation for page '{title}': {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(
            f"Request Error during Confluence operation for page '{title}': {e}")
    except Exception as e:
        print(
            f"Unexpected error during Confluence operation for page '{title}': {e}")
    return None


# --- Main Execution ---
if __name__ == "__main__":
    print("Doc Generator Script Started")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    confluence_url = os.getenv("CONFLUENCE_URL")
    confluence_email = os.getenv("CONFLUENCE_EMAIL")
    confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN")
    confluence_space_key = os.getenv("CONFLUENCE_SPACE_KEY")
    root_doc_title_env = os.getenv("ROOT_DOC_TITLE", "Project Documentation")
    code_root_path_env = os.getenv("CODE_ROOT_PATH", ".")

    required_vars = {"OPENAI_API_KEY": openai_api_key, "CONFLUENCE_URL": confluence_url,
                     "CONFLUENCE_EMAIL": confluence_email, "CONFLUENCE_API_TOKEN": confluence_api_token,
                     "CONFLUENCE_SPACE_KEY": confluence_space_key}
    missing_vars_details = [k for k, v in required_vars.items() if not v]
    if missing_vars_details:
        print(
            f"Error: Missing required environment variables: {', '.join(missing_vars_details)}")
        sys.exit(1)

    try:
        openai_client = openai.OpenAI(api_key=openai_api_key)
        confluence_auth = HTTPBasicAuth(confluence_email, confluence_api_token)
        print("OpenAI client initialized.")
        print(
            f"Confluence authentication configured for URL: {confluence_url}")
    except Exception as e:
        print(f"Error initializing API clients: {e}")
        sys.exit(1)

    abs_code_root_path = os.path.abspath(code_root_path_env)
    files_to_process = find_files_to_document(abs_code_root_path)

    if not files_to_process:
        print("No files found to document. Exiting.")
        sys.exit(0)

    print(f"\nFound {len(files_to_process)} files to document:")
    for f_path in files_to_process:
        print(f"  - {os.path.relpath(f_path, abs_code_root_path)}")

    # Create/Update the root Confluence page
    root_page_markdown_content = (
        f"This page serves as the root for automatically generated documentation for the project.\n\n"
        f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
        f"### Files Documented:\n" +
        "\n".join(
            [f"- `{os.path.relpath(f, abs_code_root_path)}`" for f in files_to_process])
    )
    project_root_page_id = create_or_update_confluence_page(
        confluence_url, confluence_auth, confluence_space_key,
        root_doc_title_env, root_page_markdown_content
    )
    if not project_root_page_id:
        print("Error: Could not create or find the project root page in Confluence. Aborting child page creation.")
        sys.exit(1)
    print(f"Project root page ID: {project_root_page_id}")

    # Generate documentation for each file and publish as child pages
    for file_path in files_to_process:
        relative_file_path = os.path.relpath(file_path, abs_code_root_path)
        print(f"\nProcessing file: {relative_file_path}")

        documentation_markdown_from_ai = generate_documentation_for_file(
            file_path, openai_client)
        if "Error generating documentation" in documentation_markdown_from_ai or \
           "File is empty" in documentation_markdown_from_ai:  # Also skip empty file docs for Confluence
            print(
                f"Skipping Confluence update for {relative_file_path} due to generation issue or empty content.")
            continue

        # Combine preamble with AI's markdown for the Confluence page body
        final_markdown_for_page = (
            f"*Automatically generated documentation for `{relative_file_path}`.*\n\n"
            f"*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}*\n\n"
            f"---\n\n"
            f"{documentation_markdown_from_ai}"
        )

        page_title = f"Doc: {relative_file_path.replace(os.sep, ' - ')}"
        create_or_update_confluence_page(
            confluence_url, confluence_auth, confluence_space_key,
            page_title, final_markdown_for_page, parent_id=project_root_page_id
        )
        time.sleep(2)  # Basic rate limiting

    print("\nDoc Generator Script Finished.")
