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
# Folders to completely ignore (and their subfolders)
IGNORED_FOLDERS = {
    "venv",         # Common virtual environment folder
    "antenv",       # Another virtual environment folder name you used
    ".git",         # Git repository data
    ".github",      # GitHub specific files (workflows, etc.)
    "__pycache__",  # Python bytecode cache
    "node_modules",  # Common for JS projects
    "build",
    "dist",
    "static",       # Usually frontend assets, might not need LLM documentation for all files
    "templates",    # HTML templates, might not need LLM documentation for all files
    "scripts",      # Often utility scripts, including this one, can be excluded if desired
    # Add any other top-level or common folders you want to skip entirely
}

# Specific files to ignore by name, regardless of their location (if found)
IGNORED_FILES = {
    ".gitignore",
    "LICENSE",
    "README.md",
    "requirements.txt",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "pyproject.toml",  # Often project config, not source code for LLM
    "app.pyc",      # Example compiled python file
    # Add any other specific file names
}

# File extensions to consider for documentation (e.g., source code)
# Set to None or empty list/set to consider all files not otherwise ignored
TARGET_EXTENSIONS = {
    ".py",
    # ".js", ".html", ".css", # Add other extensions if needed
}

# --- Helper Functions for Ignoring Items ---


def should_ignore_dir(dir_name):
    """Checks if a directory name is in the IGNORED_FOLDERS set."""
    return dir_name.lower() in IGNORED_FOLDERS


def should_ignore_file(file_name):
    """Checks if a file name is in the IGNORED_FILES set."""
    return file_name.lower() in IGNORED_FILES


def has_target_extension(file_name):
    """Checks if the file has one of the TARGET_EXTENSIONS."""
    if not TARGET_EXTENSIONS:  # If no specific extensions, consider all (that are not ignored)
        return True
    _, ext = os.path.splitext(file_name)
    return ext.lower() in TARGET_EXTENSIONS


# --- Core Logic Functions ---
def find_files_to_document(code_root_path):
    """
    Walks through the code_root_path and collects files to be documented,
    respecting the ignore lists.
    """
    files_for_documentation = []

    if not os.path.isdir(code_root_path):
        print(
            f"Error: Provided code root path '{code_root_path}' is not a valid directory.")
        return files_for_documentation

    abs_code_root_path = os.path.abspath(code_root_path)
    print(f"Starting scan in: {abs_code_root_path}")
    print(f"Ignoring folders: {IGNORED_FOLDERS}")
    print(f"Ignoring files: {IGNORED_FILES}")
    print(
        f"Targeting extensions: {TARGET_EXTENSIONS if TARGET_EXTENSIONS else 'All (not ignored)'}")
    print("-" * 30)

    for root, dirs, files in os.walk(abs_code_root_path, topdown=True):
        # --- Directory Exclusion ---
        dirs[:] = [d for d in dirs if not should_ignore_dir(d)]

        relative_path_from_root = os.path.relpath(root, abs_code_root_path)
        display_path = relative_path_from_root if relative_path_from_root != "." else "[root]"
        # print(f"Scanning in: {display_path}") # Verbose logging

        for file_name in files:
            if should_ignore_file(file_name):
                # print(f"  Ignoring specific file: {os.path.join(display_path, file_name)}")
                continue

            if not has_target_extension(file_name):
                # print(f"  Ignoring file due to extension: {os.path.join(display_path, file_name)}")
                continue

            full_path = os.path.join(root, file_name)
            files_for_documentation.append(full_path)
            # print(f"  Collecting: {os.path.join(display_path, file_name)}")

    return files_for_documentation


def generate_documentation_for_file(file_path, openai_client):
    """
    Generates documentation for a single file using OpenAI.
    IMPLEMENT THE ACTUAL OPENAI LOGIC HERE.
    """
    print(f"\n--- Attempting to generate documentation for: {file_path} ---")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if not content.strip():
            print(
                f"File {file_path} is empty or contains only whitespace. Skipping.")
            return f"## Documentation for `{os.path.basename(file_path)}`\n\nFile is empty."

        # Basic check for very large files to avoid huge API costs / long processing
        # OpenAI models have token limits. Max ~16k tokens for gpt-3.5-turbo-16k, ~128k for gpt-4-turbo
        # 1 token is roughly 4 chars in English. A 100k char file is ~25k tokens.
        if len(content) > 80000:  # Adjust based on your model and budget (e.g. 80k chars ~ 20k tokens)
            print(
                f"Warning: File {file_path} is very large ({len(content)} chars). Truncating for OpenAI processing.")
            # Consider summarizing locally first or processing in chunks if this is common
            content = content[:80000] + "\n\n[CONTENT TRUNCATED DUE TO LENGTH]"

        prompt = (
            f"Generate concise technical documentation for the following code file named '{os.path.basename(file_path)}'. "
            "Focus on its purpose, main functions/classes, inputs, outputs, and key logic. "
            "Format the output in Markdown.\n\n"
            f"File Content:\n```\n{content}\n```"
        )

        # --- OpenAI API Call (IMPLEMENT THIS) ---
        print(f"Sending content of {os.path.basename(file_path)} to OpenAI...")
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Or "gpt-4-turbo" or your preferred model
            messages=[
                {"role": "system", "content": "You are an expert technical writer assistant specializing in clear and concise code documentation in Markdown format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more factual/deterministic output
            max_tokens=1500  # Adjust based on expected documentation length
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
    """Helper to check if a page exists and get its ID."""
    search_url = f"{confluence_url.rstrip('/')}/rest/api/content"
    params = {
        "spaceKey": space_key,
        "title": title,
        "expand": "version"  # To get version number for updates
    }
    try:
        response = requests.get(search_url, auth=auth, params=params, headers={
                                "Content-Type": "application/json"}, timeout=10)
        response.raise_for_status()
        results = response.json().get('results', [])
        if results:
            return results[0]['id'], results[0]['version']['number']
    except requests.exceptions.RequestException as e:
        print(f"Error searching for Confluence page '{title}': {e}")
    return None, None


def create_or_update_confluence_page(confluence_url, auth, space_key, title, body_content, parent_id=None):
    """
    Creates or updates a page in Confluence.
    IMPLEMENT THE ACTUAL CONFLUENCE LOGIC HERE.
    """
    page_id, current_version = get_confluence_page_id(
        confluence_url, auth, space_key, title)
    rest_url = f"{confluence_url.rstrip('/')}/rest/api/content"

    page_data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {  # Use storage format for Markdown (needs conversion or a macro)
                # For true Markdown, you might need a Markdown macro or pre-convert to Confluence storage format
                "value": body_content,
                "representation": "storage"  # Or "wiki" if you provide wiki markup
            }
        }
    }
    if parent_id:
        page_data["ancestors"] = [{"id": parent_id}]

    try:
        if page_id:  # Update existing page
            page_data["id"] = page_id
            page_data["version"] = {"number": current_version + 1}
            print(f"Updating Confluence page: '{title}' (ID: {page_id})")
            response = requests.put(f"{rest_url}/{page_id}", auth=auth, json=page_data, headers={
                                    "Content-Type": "application/json"}, timeout=15)
        else:  # Create new page
            print(f"Creating Confluence page: '{title}'")
            response = requests.post(rest_url, auth=auth, json=page_data, headers={
                                     "Content-Type": "application/json"}, timeout=15)

        response.raise_for_status()
        print(
            f"Successfully {'updated' if page_id else 'created'} page '{title}'. Link: {response.json().get('_links', {}).get('webui', '')}")
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

    # Retrieve secrets and config from environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    confluence_url = os.getenv("CONFLUENCE_URL")
    confluence_email = os.getenv("CONFLUENCE_EMAIL")
    confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN")
    confluence_space_key = os.getenv("CONFLUENCE_SPACE_KEY")
    root_doc_title_env = os.getenv("ROOT_DOC_TITLE", "Project Documentation")
    code_root_path_env = os.getenv("CODE_ROOT_PATH", ".")

    required_vars_messages = {
        "OPENAI_API_KEY": "OpenAI API Key is missing.",
        "CONFLUENCE_URL": "Confluence URL is missing.",
        "CONFLUENCE_EMAIL": "Confluence Email is missing.",
        "CONFLUENCE_API_TOKEN": "Confluence API Token is missing.",
        "CONFLUENCE_SPACE_KEY": "Confluence Space Key is missing.",
    }
    missing_vars = [msg for var,
                    msg in required_vars_messages.items() if not os.getenv(var)]
    if missing_vars:
        for msg in missing_vars:
            print(f"Error: {msg}")
        sys.exit(1)

    # --- Initialize API Clients ---
    try:
        openai_client = openai.OpenAI(api_key=openai_api_key)
        confluence_auth = HTTPBasicAuth(confluence_email, confluence_api_token)
        # Test OpenAI client (optional, but good for quick feedback)
        # openai_client.models.list()
        print("OpenAI client initialized.")
        print(
            f"Confluence authentication configured for URL: {confluence_url}")
    except Exception as e:
        print(f"Error initializing API clients: {e}")
        sys.exit(1)

    print(f"Code root path from env: {code_root_path_env}")
    abs_code_root_path = os.path.abspath(code_root_path_env)

    # 1. Find files to document
    files_to_process = find_files_to_document(abs_code_root_path)

    if not files_to_process:
        print("No files found to document after applying ignore rules. Exiting.")
        sys.exit(0)

    print(f"\nFound {len(files_to_process)} files to document:")
    for f_path in files_to_process:
        print(f"  - {os.path.relpath(f_path, abs_code_root_path)}")

    # 2. Create/Update a root Confluence page for this project's documentation
    print(
        f"\nEnsuring root documentation page: '{root_doc_title_env}' in space '{confluence_space_key}'")
    # The body for the root page can be simple.
    # If you send Markdown here, Confluence needs to be able to render it.
    # Using a simple text or a Confluence macro for {markdown} is safer.
    # For this example, we'll assume you have a markdown macro or are okay with plain text + Markdown code blocks.
    root_page_body_content = (
        f"<p>This page serves as the root for automatically generated documentation for the project.</p>"
        f"<p>Last updated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>"
        f"ac:name=\"markdown\">"  # Example of starting a markdown macro
        f"### Files Documented:\n"
        + "\n".join([f"- `{os.path.relpath(f, abs_code_root_path)}`" for f in files_to_process]) +
        f"</ac:name>"  # Example of closing a markdown macro
    )

    # A more robust approach for Confluence storage format for Markdown:
    # confluence_markdown_macro_template = '<ac:structured-macro ac:name="markdown" ac:schema-version="1"><ac:plain-text-body><![CDATA[\n{markdown_content}\n]]></ac:plain-text-body></ac:structured-macro>'
    # root_page_body_content = confluence_markdown_macro_template.format(markdown_content="### Overview\nThis is the root page...")

    project_root_page_id = create_or_update_confluence_page(
        confluence_url,
        confluence_auth,
        confluence_space_key,
        root_doc_title_env,
        root_page_body_content  # This needs to be in Confluence Storage Format or use a macro
    )

    if not project_root_page_id:
        print("Error: Could not create or find the project root page in Confluence. Aborting child page creation.")
        sys.exit(1)

    print(f"Project root page ID: {project_root_page_id}")

    # 3. Generate documentation for each file and publish as child pages
    for file_path in files_to_process:
        relative_file_path = os.path.relpath(file_path, abs_code_root_path)
        print(f"\nProcessing file: {relative_file_path}")

        documentation_markdown = generate_documentation_for_file(
            file_path, openai_client)

        if "Error generating documentation" in documentation_markdown:
            print(
                f"Skipping Confluence update for {relative_file_path} due to generation error.")
            continue

        # Prepare content for Confluence (wrap Markdown in macro if needed)
        # This is a common way to put Markdown into Confluence storage format
        confluence_page_body = (
            f"<p><em>Automatically generated documentation for <code>{relative_file_path}</code>.</em></p>"
            f"<p><em>Last updated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}</em></p><hr/>"
            # Assuming your Markdown from OpenAI is Confluence-friendly or you'll use a macro.
            f"{documentation_markdown}"
            # For more complex Markdown, convert to Confluence Storage Format.
        )
        # Example using the markdown macro explicitly:
        # confluence_page_body = confluence_markdown_macro_template.format(markdown_content=documentation_markdown)

        # e.g., "Doc: src - my_module.py"
        page_title = f"Doc: {relative_file_path.replace(os.sep, ' - ')}"

        create_or_update_confluence_page(
            confluence_url,
            confluence_auth,
            confluence_space_key,
            page_title,
            confluence_page_body,
            parent_id=project_root_page_id
        )
        # Basic rate limiting to avoid overwhelming Confluence or hitting API limits
        time.sleep(2)

    print("\nDoc Generator Script Finished.")
