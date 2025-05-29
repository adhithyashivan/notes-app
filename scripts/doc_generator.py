# scripts/doc_generator.py

import os
import sys
import json
import time
import html
import uuid  # For potential future use, not strictly needed for HTML conversion method

# Attempt to import necessary libraries
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

try:
    import markdown2
except ImportError:
    print("markdown2 library not found. Please install it: pip install markdown2")
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

# --- Helper Functions for Ignoring Items (No change) ---


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
    # ... (No change from previous version) ...
    files_for_documentation = []
    if not os.path.isdir(code_root_path):
        print(
            f"Error: Provided code root path '{code_root_path}' is not a valid directory.")
        return files_for_documentation
    abs_code_root_path = os.path.abspath(code_root_path)
    print(f"Starting scan in: {abs_code_root_path}")
    print("-" * 30)
    for root, dirs, files in os.walk(abs_code_root_path, topdown=True):
        dirs[:] = [d for d in dirs if not should_ignore_dir(d)]
        for file_name in files:
            if should_ignore_file(file_name) or not has_target_extension(file_name):
                continue
            files_for_documentation.append(os.path.join(root, file_name))
    return files_for_documentation


def generate_documentation_for_file(file_path, openai_client):
    # ... (No change to the OpenAI prompt or call from previous version,
    # as it generates the structured Markdown we want) ...
    print(f"\n--- Attempting to generate documentation for: {file_path} ---")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if not content.strip():
            print(f"File {file_path} is empty. Skipping OpenAI call.")
            return (f"**File Overview:**\n\nThis file (`{os.path.basename(file_path)}`) "
                    f"is empty or contains only whitespace.\n")
        max_chars_for_openai = 80000
        if len(content) > max_chars_for_openai:
            print(
                f"Warning: File {file_path} is very large ({len(content)} chars). Truncating for OpenAI processing.")
            content = content[:max_chars_for_openai] + \
                "\n\n[CONTENT TRUNCATED DUE TO LENGTH]"
        prompt = (
            f"Generate technical documentation for the Python code file named '{os.path.basename(file_path)}'. "
            "The documentation should be in Markdown format and strictly follow this structure:\n\n"
            "**File Overview:**\n[A brief, one or two-sentence overview of the file's purpose.]\n\n"
            "**Functions:** (Only if functions are present)\n"
            "**Function:** `function_name(param1: type, param2: type) -> return_type`\n"
            "**Purpose:** [Brief description of what the function does.]\n"
            "**Parameters:** (Only if parameters are present)\n"
            "- `param_name` (type): [Description of the parameter.]\n"
            "**Returns:** (Only if it returns something other than None)\n"
            "- (type): [Description of the return value.]\n"
            "[Repeat for each function, separated by a blank line]\n\n"
            "**Classes:** (Only if classes are present)\n"
            "**Class:** `ClassName`\n"
            "**Purpose:** [Brief description of the class.]\n"
            "**Methods:** (Only if methods are present)\n"
            "**Method:** `method_name(self, param1: type) -> return_type`\n"
            "**Purpose:** [Description.]\n"
            "[Repeat for each class and method, separated by a blank line]\n\n"
            "Ensure all code signatures, parameter names, and class names are enclosed in backticks (`).\n"
            "Use simple Markdown: ** for bold, newlines for separation. Do not use HTML tags.\n"
            f"File Content:\n```python\n{content}\n```"
        )
        print(f"Sending content of {os.path.basename(file_path)} to OpenAI...")
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are an expert technical writer generating structured Markdown documentation for Python code, adhering strictly to the provided format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, max_tokens=2500
        )
        documentation = response.choices[0].message.content
        print(
            f"Received documentation from OpenAI for {os.path.basename(file_path)}")
        return documentation
    except openai.APIError as e:
        print(f"OpenAI API Error processing file {file_path}: {e}")
        return f"**Error:**\n\nOpenAI API Error processing file `{os.path.basename(file_path)}`: {e}\n"
    except Exception as e:
        print(f"Unexpected error processing file {file_path}: {e}")
        return f"**Error:**\n\nUnexpected error processing file `{os.path.basename(file_path)}`: {e}\n"


def get_confluence_page_id(confluence_url, auth, space_key, title):
    # ... (No change from previous version) ...
    search_url = f"{confluence_url.rstrip('/')}/rest/api/content"
    params = {"spaceKey": space_key, "title": title,
              "expand": "version", "limit": 1}
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


def markdown_to_confluence_html(markdown_text):
    """Converts Markdown text to basic HTML suitable for Confluence storage format."""
    # Use markdown2 with extras that produce simple HTML
    # 'fenced-code-blocks' for ```python ... ```
    # 'code-friendly' to avoid messing with underscores in code
    # 'tables' if your markdown might include them
    # 'break-on-newline' can be useful for simpler line breaks if desired
    html_output = markdown2.markdown(
        markdown_text,
        extras=["fenced-code-blocks", "code-friendly",
                "tables", "break-on-newline"]
    )
    # Replace <pre><code> with <ac:structured-macro ac:name="code"> for Confluence code blocks
    # This is more robust for syntax highlighting in Confluence if the "code" macro is available
    # Note: language parameter might need adjustment based on Confluence setup
    # For simplicity, let's assume a generic code block or rely on Confluence's auto-detection
    # if it has it for <pre><code>.
    # If the `code` macro is also unknown, then simple `<pre><code>` is the fallback.
    # Let's try simple <pre><code> first, as it's more standard HTML.

    # A common issue is that markdown2 might wrap <pre><code> inside <p>.
    # We need to ensure <pre> is a block element.
    # This is a bit hacky, might need refinement based on markdown2 output.
    html_output = html_output.replace(
        "<p><pre>", "<pre>").replace("</pre></p>", "</pre>")

    return html_output


def create_or_update_confluence_page(confluence_url, auth, space_key, title, markdown_body_content, parent_id=None):
    page_id, current_version = get_confluence_page_id(
        confluence_url, auth, space_key, title)
    rest_url = f"{confluence_url.rstrip('/')}/rest/api/content"

    # --- KEY CHANGE: Convert Markdown to HTML ---
    html_content_for_storage = markdown_to_confluence_html(
        markdown_body_content)
    # --- END OF KEY CHANGE ---

    page_data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": html_content_for_storage,  # Send HTML content
                # Indicate it's storage format (XHTML)
                "representation": "storage"
            }
        }
    }
    if parent_id:
        page_data["ancestors"] = [{"id": str(parent_id)}]

    try:
        http_method = requests.put if page_id else requests.post
        full_url = f"{rest_url}/{page_id}" if page_id else rest_url
        action_word = "Updating" if page_id else "Creating"

        if page_id:
            page_data["id"] = str(page_id)
            page_data["version"] = {"number": current_version + 1}

        print(f"{action_word} Confluence page: '{title}'" +
              (f" (ID: {page_id})" if page_id else ""))
        response = http_method(full_url, auth=auth, json=page_data, headers={
                               "Content-Type": "application/json", "Accept": "application/json"}, timeout=20)
        response.raise_for_status()

        base_url = confluence_url.rstrip('/')
        page_web_ui_path = response.json().get('_links', {}).get('webui', '')
        full_page_link = f"{base_url}{page_web_ui_path}" if page_web_ui_path else "N/A"
        print(
            f"Successfully {action_word.lower().replace('ing', 'ed')} page '{title}'. Link: {full_page_link}")
        return response.json().get('id')

    except requests.exceptions.HTTPError as e:
        print(
            f"HTTP Error during Confluence operation for page '{title}': {e.response.status_code}")
        try:
            print(f"Confluence Error Body: {e.response.json()}")
        except json.JSONDecodeError:
            print(f"Confluence Error Body (not JSON): {e.response.text}")
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
    # ... (rest of environment variable fetching and validation is the same) ...
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

    # --- Root Page Content (still Markdown, converted to HTML by the function) ---
    root_page_markdown_content = (
        f"This page serves as the root for automatically generated documentation for the project.\n\n"
        f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
        f"### Files Documented:\n" +  # Using ### for H3 in Markdown
        "\n".join(
            [f"- `{os.path.relpath(f, abs_code_root_path)}`" for f in files_to_process])
    )
    project_root_page_id = create_or_update_confluence_page(
        confluence_url, confluence_auth, confluence_space_key,
        # Pass Markdown, function will convert
        root_doc_title_env, root_page_markdown_content
    )
    if not project_root_page_id:
        print("Error: Could not create or find the project root page in Confluence. Aborting child page creation.")
        sys.exit(1)
    print(f"Project root page ID: {project_root_page_id}")

    # --- Individual File Page Content (Markdown from AI, converted to HTML by the function) ---
    for file_path in files_to_process:
        relative_file_path = os.path.relpath(file_path, abs_code_root_path)
        print(f"\nProcessing file: {relative_file_path}")

        documentation_markdown_from_ai = generate_documentation_for_file(
            file_path, openai_client)

        if "**Error:**" in documentation_markdown_from_ai or \
           ("is empty" in documentation_markdown_from_ai and f"`{os.path.basename(file_path)}`" in documentation_markdown_from_ai):
            print(
                f"Skipping Confluence update for {relative_file_path} due to generation issue or empty content.")
            continue

        preamble_markdown = (
            f"*Automatically generated documentation for `{relative_file_path}`.*\n\n"
            f"*Last updated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}*\n\n"
            f"---\n\n"  # This will become <hr />
        )
        final_markdown_for_page = preamble_markdown + documentation_markdown_from_ai

        page_title = f"Doc: {relative_file_path.replace(os.sep, ' - ')}"
        create_or_update_confluence_page(
            confluence_url, confluence_auth, confluence_space_key,
            page_title, final_markdown_for_page,  # Pass Markdown, function will convert
            parent_id=project_root_page_id
        )
        time.sleep(3)

    print("\nDoc Generator Script Finished.")
