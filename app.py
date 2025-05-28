from flask import Flask, render_template, request, jsonify
import uuid
import html
from datetime import datetime, timezone

app = Flask(__name__)

# In-memory "database"
notes_db = []
MAX_NOTES = 5

# --- Helper Functions ---


def sanitize_input(input_string, max_length=10000):
    """Basic sanitization: escape HTML and limit length."""
    if not isinstance(input_string, str):
        return ""
    return html.escape(input_string[:max_length])


def is_safe_html_ish(content_from_editor, max_length=20000):
    """
    This is a very basic check.
    A proper solution would involve a robust HTML sanitizer library (like Bleach).
    For this exercise, we're trusting the Quill editor to generate reasonable HTML
    and just doing a length check and basic escape for non-editor fields.
    The content from Quill is intended to be rendered as HTML.
    """
    if not isinstance(content_from_editor, str):
        return ""
    # For content from a rich text editor, we expect HTML.
    # We'll rely on frontend rendering to handle it.
    # Basic length check is still good.
    return content_from_editor[:max_length]


# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/notes', methods=['GET'])
def get_notes():
    # Return notes sorted by timestamp, newest first for blog-like display
    sorted_notes = sorted(notes_db, key=lambda x: x['timestamp'], reverse=True)
    return jsonify(sorted_notes)


@app.route('/api/notes', methods=['POST'])
def add_note():
    global notes_db
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        title = data.get('title')
        content = data.get('content')  # This is HTML content from Quill

        # --- Security Validations ---
        if not title or not isinstance(title, str):
            return jsonify({"error": "Title is required and must be a string"}), 400
        if not content or not isinstance(content, str):
            return jsonify({"error": "Content is required and must be a string"}), 400

        # Sanitize title (plain text)
        sanitized_title = sanitize_input(title, max_length=250)
        if not sanitized_title:
            return jsonify({"error": "Title cannot be empty after sanitization"}), 400

        # "Sanitize" content (HTML from editor) - mostly length check here
        # Trusting Quill for well-formed HTML, but still, length limit.
        # A production system would use a robust HTML sanitizer like Bleach.
        validated_content = is_safe_html_ish(
            content, max_length=20000)  # Generous limit for rich text
        if not validated_content:
            return jsonify({"error": "Content cannot be empty"}), 400

        if len(notes_db) >= MAX_NOTES:
            # 403 Forbidden
            return jsonify({"error": f"Maximum of {MAX_NOTES} notes reached. Consider upgrading to premium to add more."}), 403

        new_note = {
            "id": str(uuid.uuid4()),
            "title": sanitized_title,  # Store sanitized title
            "content": validated_content,  # Store "validated" HTML content
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        notes_db.append(new_note)
        return jsonify(new_note), 201

    except Exception as e:
        app.logger.error(f"Error adding note: {e}")
        return jsonify({"error": "An internal error occurred"}), 500


@app.route('/api/notes/premium-upgrade', methods=['POST'])
def premium_upgrade_attempt():
    global notes_db
    if not notes_db:
        return jsonify({"message": "No notes to delete. Add some notes first!", "deleted": False}), 200

    if len(notes_db) < MAX_NOTES:
        return jsonify({"message": f"You currently have {len(notes_db)} notes. Premium benefits apply when you reach the {MAX_NOTES} notes limit. No action taken.", "deleted": False}), 200

    # Delete the earliest note (oldest timestamp)
    notes_db.sort(key=lambda x: x['timestamp'])  # Sort by oldest first
    deleted_note = notes_db.pop(0)  # Remove the oldest
    return jsonify({
        "message": "Premium features are not yet enabled. As a temporary measure, the oldest note has been deleted to make space.",
        "deleted_note_title": deleted_note.get('title'),
        "deleted": True
    }), 200


@app.route('/<path:path>')  # Catch-all for nav links
def catch_all(path):
    # For now, all other nav links redirect to home
    # In a real app, these would go to 'about.html', 'contact.html' etc.
    app.logger.info(f"Path '{path}' requested, redirecting to home.")
    return render_template('index.html')


if __name__ == '__main__':
    # Use 0.0.0.0 for accessibility in containers/VMs
    app.run(debug=True, host='0.0.0.0', port=5000)
