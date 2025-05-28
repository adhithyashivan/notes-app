import os
import requests  # For Confluence API
import openai   # For OpenAI API
import json
import sys
from requests.auth import HTTPBasicAuth
import time  # For potential rate limiting

# --- Configuration ---
# These values will be injected by the GitHub Actions workflow as environment variables.
# DO NOT HARDCODE SENSITIVE KEYS DIRECTLY IN THE SCRIPT IN A REAL SCENARIO.

# For OpenAI API:
# In GitHub Actions, this would be set from a secret: ${{ secrets.OPENAI_API_KEY }}
# Example value you provided: "ABC1212121" (This is just for illustration)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable not set.")
    # OPENAI_API_KEY = "ABC1212121" # << ONLY FOR LOCAL TESTING, REMOVE FOR CI/CD
    # sys.exit(1) # Uncomment this line in production if key is missing

# For Confluence:
# Your Confluence site base URL (up to '/wiki')
# In GitHub Actions, this would be set from a secret: ${{ secrets.CONFLUENCE_URL }}
# Example based on your provided URL: "https://test-test.atlassian.net/wiki"
CONFLUENCE_BASE_URL = os.environ.get("CONFLUENCE_URL")
if not CONFLUENCE_BASE_URL:
    print("Error: CONFLUENCE_URL environment variable not set.")
    # CONFLUENCE_BASE_URL = "https://test-test.atlassian.net/wiki" # << ONLY FOR LOCAL TESTING
    # sys.exit(1) # Uncomment this line in production if URL is missing

# Your Atlassian account email (used for API authentication with the token)
# In GitHub Actions, this would be set from a secret: ${{ secrets.CONFLUENCE_EMAIL }}
CONFLUENCE_USER_EMAIL = os.environ.get("CONFLUENCE_EMAIL")
if not CONFLUENCE_USER_EMAIL:
    print("Error: CONFLUENCE_EMAIL environment variable not set.")
    # sys.exit(1)

# Your Confluence API Token
# In GitHub Actions, this would be set from a secret: ${{ secrets.CONFLUENCE_API_TOKEN }}
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN")
if not CONFLUENCE_API_TOKEN:
    print("Error: CONFLUENCE_API_TOKEN environment variable not set.")
    # sys.exit(1)

# The Key of your Confluence Space (e.g., "APD" from your URL)
# In GitHub Actions, this would be set from a secret: ${{ secrets.CONFLUENCE_SPACE_KEY }}
CONFLUENCE_SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY")
if not CONFLUENCE_SPACE_KEY:
    print("Error: CONFLUENCE_SPACE_KEY environment variable not set.")
    # CONFLUENCE_SPACE_KEY = "APD" # << ONLY FOR LOCAL TESTING
    # sys.exit(1)

# The root directory of the code to document, relative to the repository root.
# In GitHub Actions, this would be set via an env var in the workflow, e.g., 'app'
CODE_ROOT_DIR_RELATIVE_PATH = os.environ.get(
    "CODE_ROOT_PATH", "app")  # Default to 'app'

# A root page title for all generated docs for this project/run.
# In GitHub Actions, this could be: ${{ github.repository }} - Automated Docs
ROOT_DOC_PROJECT_TITLE = os.environ.get(
    "ROOT_DOC_TITLE", "Project Documentation")

# --- Initialize OpenAI Client ---
# Ensure the API key is set before trying to initialize the client
if OPENAI_API_KEY:
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        client = None  # Ensure client is None if initialization fails
else:
    client = None
    print("OpenAI client not initialized because API key is missing.")


# --- Helper Functions ---

def get_ai_documentation(file_content, file_path):
    """Generates documentation for a Python file using OpenAI."""
    if not client:
        print(
            f"OpenAI client not available. Skipping AI documentation for {file_path}.")
        return f"Error: OpenAI client not initialized. Could not generate documentation for {file_path}."

    # Enhanced prompt for better structure and Confluence compatibility
    prompt = f"""
    Please act as an expert technical writer. Analyze the following Python code from the file '{file_path}'.
    Generate documentation in Confluence Wiki Markup format.

    The documentation should include:
    1.  *File Overview:* A concise summary of the file's purpose, its main components, and any key dependencies it might imply (at a high level).
    2.  *Classes (if any):* For each class:
        *   Class Name and Signature (e.g., `h3. Class: MyClass(BaseClass)`)
        *   Purpose: A clear description of what the class does.
        *   Key Attributes: Important instance or class variables and their roles.
        *   Methods: For each method (including `__init__`):
            *   Method Signature (e.g., `h4. Method: my_method(self, param1, param2=None)`)
            *   Purpose: What the method does.
            *   Parameters: A list of parameters with their expected types and descriptions (e.g., `* param1 (int): Description of param1.`).
            *   Returns: What the method returns, including type (e.g., `* Returns: (str) Description of return value.`).
    3.  *Functions (if any, not part of a class):* For each function:
        *   Function Signature (e.g., `h3. Function: my_global_function(param1)`)
        *   Purpose: What the function does.
        *   Parameters: A list of parameters with their types and descriptions.
        *   Returns: What the function returns, including type.
    4.  *Usage Example (Optional but Recommended):* If feasible, a brief code snippet showing how to use a key function or class from this file.

    Use Confluence Wiki Markup:
    - Headings: `h1.`, `h2.`, `h3.`, `h4.`
    - Bold: `*text*`
    - Italics: `_text_`
    - Unordered lists: `* item` (star followed by a space)
    - Code blocks: `{{{{code:python}}}} ... {{{{code}}}}` or `{{{{noformat}}}} ... {{{{noformat}}}}` for simple code snippets.

    Here is the code content:
    ---- START OF CODE ----
    {file_content}
    ---- END OF CODE ----

    Provide only the Confluence Wiki Markup content for the page body.
    """
    max_retries = 3
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Or "gpt-4" if you have access and budget
                messages=[
                    {"role": "system", "content": "You are an expert technical writer generating Confluence Wiki Markup documentation for Python code."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except openai.RateLimitError as e:
            print(
                f"OpenAI Rate Limit Error for {file_path}: {e}. Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        except Exception as e:
            print(f"Error calling OpenAI for {file_path}: {e}")
            return f"h2. Error Generating Documentation\n\nAn error occurred while generating AI documentation for {file_path}:\n{{{{noformat}}}}\n{e}\n{{{{noformat}}}}"

    print(
        f"Failed to get documentation from OpenAI for {file_path} after {max_retries} retries.")
    return f"h2. Error Generating Documentation\n\nFailed to retrieve documentation from OpenAI for {file_path} after multiple retries due to rate limiting or other API issues."


def get_confluence_page_id_and_version(title, space_key):
    """Checks if a page with the given title exists and returns its ID and version number."""
    if not CONFLUENCE_BASE_URL or not CONFLUENCE_USER_EMAIL or not CONFLUENCE_API_TOKEN:
        print(
            f"Confluence API credentials or URL not set. Cannot search for page '{title}'.")
        return None, None

    api_url = f"{CONFLUENCE_BASE_URL}/rest/api/content"
    auth = HTTPBasicAuth(CONFLUENCE_USER_EMAIL, CONFLUENCE_API_TOKEN)
    headers = {"Accept": "application/json"}
    params = {"title": title, "spaceKey": space_key, "expand": "version"}

    try:
        response = requests.get(api_url, headers=headers,
                                params=params, auth=auth, timeout=30)
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            page_id = results[0]["id"]
            version_number = results[0]['version']['number']
            print(
                f"Found existing page '{title}' (ID: {page_id}, Version: {version_number})")
            return page_id, version_number
        print(f"Page '{title}' not found in space '{space_key}'.")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"Error checking Confluence page '{title}': {e}")
        if hasattr(response, 'text'):
            print(f"Response content: {response.text}")
        return None, None


def create_or_update_confluence_page(title, body_content, space_key, parent_id=None):
    """Creates or updates a Confluence page."""
    if not CONFLUENCE_BASE_URL or not CONFLUENCE_USER_EMAIL or not CONFLUENCE_API_TOKEN:
        print(
            f"Confluence API credentials or URL not set. Cannot publish page '{title}'.")
        return None

    api_url_base = f"{CONFLUENCE_BASE_URL}/rest/api/content"
    auth = HTTPBasicAuth(CONFLUENCE_USER_EMAIL, CONFLUENCE_API_TOKEN)
    headers = {"Accept": "application/json",
               "Content-Type": "application/json"}

    page_id, current_version = get_confluence_page_id_and_version(
        title, space_key)

    data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "wiki": {  # Using Confluence Wiki Markup
                "value": body_content,
                "representation": "wiki"
            }
        }
    }

    if parent_id:
        # Ensure parent_id is string
        data["ancestors"] = [{"id": str(parent_id)}]

    max_retries = 3
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        try:
            if page_id:  # Update existing page
                data["id"] = page_id
                data["version"] = {"number": current_version + 1}
                api_url_specific = f"{api_url_base}/{page_id}"
                response = requests.put(api_url_specific, headers=headers, data=json.dumps(
                    data), auth=auth, timeout=30)
                action_taken = "Updating"
            else:  # Create new page
                api_url_specific = api_url_base
                response = requests.post(
                    api_url_specific, headers=headers, data=json.dumps(data), auth=auth, timeout=30)
                action_taken = "Creating"

            print(
                f"{action_taken} page '{title}' (Attempt {attempt+1}/{max_retries})...")
            response.raise_for_status()  # Will raise HTTPError for bad responses (4xx or 5xx)

            new_page_id = response.json().get("id")
            print(
                f"Successfully {action_taken.lower()} Confluence page: '{title}' (ID: {new_page_id})")
            return new_page_id

        except requests.exceptions.HTTPError as e:
            print(
                f"HTTP Error {action_taken.lower()} Confluence page '{title}': {e.response.status_code} - {e.response.reason}")
            print(f"Response content: {e.response.text}")
            if e.response.status_code == 409:  # Conflict, likely version mismatch or concurrent edit
                print(
                    "Conflict error (409) detected. Page might have been updated. Re-fetching version...")
                page_id, current_version = get_confluence_page_id_and_version(
                    title, space_key)  # Re-fetch
                if page_id is None:  # Page was deleted in the meantime
                    print("Page seems to have been deleted. Attempting to create.")
                    # Reset page_id to allow creation in next attempt, if any
                    page_id = None
                    current_version = None  # Reset version as well
                    continue  # Retry immediately with create logic
            # For other errors, or if retries exhausted for 409
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(
                    f"Failed to {action_taken.lower()} page '{title}' after {max_retries} attempts.")
                return None
        except requests.exceptions.RequestException as e:  # Other network issues
            print(
                f"Request Error {action_taken.lower()} Confluence page '{title}': {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(
                    f"Failed to {action_taken.lower()} page '{title}' after {max_retries} attempts due to network issues.")
                return None
    return None  # Should be unreachable if loop logic is correct


def process_directory_recursively(current_dir_abs_path, space_key, current_confluence_parent_id, code_base_dir_abs_path):
    """
    Recursively processes directories and files to generate documentation.
    Creates corresponding parent/child pages in Confluence.
    `current_dir_abs_path`: Absolute path of the directory currently being processed.
    `code_base_dir_abs_path`: Absolute path of the root directory for documentation (e.g., .../workspace/app).
    """
    print(f"Processing directory: {current_dir_abs_path}")

    # Sort items to ensure consistent page ordering
    items_in_dir = sorted(os.listdir(current_dir_abs_path))

    for item_name in items_in_dir:
        item_abs_path = os.path.join(current_dir_abs_path, item_name)
        # Path relative to the initial CODE_ROOT_DIR_RELATIVE_PATH (e.g., "utils/calculator.py" or "main.py")
        item_relative_to_code_base = os.path.relpath(
            item_abs_path, code_base_dir_abs_path)

        if os.path.isdir(item_abs_path):
            # Create a Confluence page for this subdirectory
            # Title format: "Project Root Title: path / to / subdir"
            dir_page_title = f"{ROOT_DOC_PROJECT_TITLE}: {item_relative_to_code_base.replace(os.sep, ' / ')}"
            print(f"  Creating/Updating directory page: '{dir_page_title}'")

            # Simple content for directory page
            dir_content = f"h1. Directory: {item_name}\n\nThis page contains documentation for modules and subdirectories within '{item_name}'."

            new_parent_id_for_children = create_or_update_confluence_page(
                dir_page_title,
                dir_content,
                space_key,
                current_confluence_parent_id
            )

            if new_parent_id_for_children:
                process_directory_recursively(
                    item_abs_path, space_key, new_parent_id_for_children, code_base_dir_abs_path)
            else:
                print(
                    f"  Skipping subdirectory '{item_abs_path}' due to error creating/updating its Confluence page.")

        elif item_name.endswith(".py"):
            print(f"  Processing Python file: {item_abs_path}")
            # Title format: "Project Root Title: path/to/file.py"
            file_page_title = f"{ROOT_DOC_PROJECT_TITLE}: {item_relative_to_code_base}"

            try:
                with open(item_abs_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                if not file_content.strip():
                    print(f"  Skipping empty file: {item_abs_path}")
                    continue

                print(
                    f"    Generating AI documentation for: '{file_page_title}'")
                ai_doc_content = get_ai_documentation(
                    file_content, item_relative_to_code_base)

                if ai_doc_content:
                    print(
                        f"    Publishing documentation to Confluence for: '{file_page_title}'")
                    create_or_update_confluence_page(
                        file_page_title,
                        ai_doc_content,
                        space_key,
                        current_confluence_parent_id
                    )
                else:
                    print(
                        f"    No documentation content generated by AI for {item_abs_path}")

            except Exception as e:
                print(f"  Error processing file {item_abs_path}: {e}")
        else:
            print(f"  Skipping non-Python file or non-directory: {item_name}")


# --- Main Execution ---
if __name__ == "__main__":
    # Basic check for essential configs
    if not all([OPENAI_API_KEY, CONFLUENCE_BASE_URL, CONFLUENCE_USER_EMAIL, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY]):
        print("CRITICAL ERROR: One or more essential environment variables for API access are missing.")
        print("Required: OPENAI_API_KEY, CONFLUENCE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY")
        sys.exit(1)  # Exit if critical credentials are not found

    if not client:  # Check if OpenAI client was initialized
        print("CRITICAL ERROR: OpenAI client could not be initialized. Check API key and network.")
        sys.exit(1)

    print("Starting documentation generation process...")
    print(f"  Project Title for Docs: {ROOT_DOC_PROJECT_TITLE}")
    print(f"  Confluence Space Key: {CONFLUENCE_SPACE_KEY}")
    print(f"  Relative Code Path to Document: '{CODE_ROOT_DIR_RELATIVE_PATH}'")

    # Create/get the main project root page in Confluence.
    # All other pages will be children of this page (or children of its directory sub-pages).
    project_root_page_body = f"h1. {ROOT_DOC_PROJECT_TITLE}\n\nThis page is the root for automatically generated documentation for the project. It covers code found in the '{CODE_ROOT_DIR_RELATIVE_PATH}' directory."

    # The "homepageId=111111" in your example URL (https://test-test.atlassian.net/wiki/spaces/APD/overview?homepageId=111111)
    # refers to the ID of the *Space Homepage*. If you want your ROOT_DOC_PROJECT_TITLE page to be a child of the Space Homepage,
    # you need to pass its ID as parent_id.
    # However, finding the Space Homepage ID programmatically can be tricky.
    # For simplicity, this script creates ROOT_DOC_PROJECT_TITLE directly under the space root (no parent_id).
    # If you want it under a specific existing page (like the space homepage), you'd need to:
    # 1. Manually find that page's ID in Confluence (often visible in the URL when editing, or via API).
    # 2. Pass that ID as an environment variable, e.g., CONFLUENCE_ROOT_PARENT_ID_FOR_PROJECT.
    # For now, we are not using a parent for the main project root page. It will appear at the top level of the space page tree.

    # CONFLUENCE_OVERVIEW_PAGE_ID = "111111" # Example based on your URL, if you wanted to make it a child of this
    # Better to pass this via env var if needed.

    print(
        f"Creating/Updating the main project documentation page: '{ROOT_DOC_PROJECT_TITLE}'")
    project_root_confluence_page_id = create_or_update_confluence_page(
        ROOT_DOC_PROJECT_TITLE,
        project_root_page_body,
        CONFLUENCE_SPACE_KEY
        # parent_id=CONFLUENCE_OVERVIEW_PAGE_ID # << Uncomment and set if you want it as a child of specific page
    )

    if project_root_confluence_page_id:
        print(
            f"Successfully created/updated project root page. ID: {project_root_confluence_page_id}")

        # Resolve the absolute path to the code directory to be documented
        # In GitHub Actions, GITHUB_WORKSPACE is the root of your checked-out repo.
        # Default to current dir if not in GHA
        github_workspace = os.environ.get("GITHUB_WORKSPACE", ".")
        code_to_document_abs_path = os.path.abspath(
            os.path.join(github_workspace, CODE_ROOT_DIR_RELATIVE_PATH))

        print(f"Absolute path to document: {code_to_document_abs_path}")

        if os.path.isdir(code_to_document_abs_path):
            # Start recursive processing. Files/dirs directly under code_to_document_abs_path
            # will become children of project_root_confluence_page_id.
            process_directory_recursively(
                code_to_document_abs_path,
                CONFLUENCE_SPACE_KEY,
                project_root_confluence_page_id,
                code_to_document_abs_path  # This is the base for relative path calculations
            )
            print("Documentation generation process completed.")
        else:
            print(
                f"Error: The specified code path '{code_to_document_abs_path}' (from relative '{CODE_ROOT_DIR_RELATIVE_PATH}') is not a valid directory.")
            sys.exit(1)
    else:
        print(
            f"CRITICAL ERROR: Failed to create or update the main project documentation page: '{ROOT_DOC_PROJECT_TITLE}'. Aborting.")
        sys.exit(1)
