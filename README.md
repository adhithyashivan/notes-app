# QuickNote - A Production-Level Note Taking Website (Demo)

This is a demo note-taking website built with HTML, CSS, JavaScript for the frontend,
and Python (Flask) for the backend. It features a rich text editor, responsive design,
and in-memory storage for up to 5 notes.

## Features

*   **Reactive and Responsive Design:** Adapts to different screen sizes.
*   **Frontend:** HTML, CSS, Vanilla JavaScript.
*   **Backend:** Python (Flask).
*   **Rich Text Editor:** Uses Quill.js (via CDN) for rich text formatting, including code blocks with syntax highlighting.
*   **In-Memory Storage:** Stores up to 5 notes. Attempting to add a 6th note will be blocked.
*   **"Upgrade to Premium":** Clicking this button (when at max notes) simulates an upgrade by deleting the oldest note to make space.
*   **Security Validations:** Basic input sanitization and validation on both frontend and backend.
*   **Blog-like Display:** Notes are displayed below the editor, newest first.
*   **Navbar:** Includes mock navigation links.
*   **Minimal Dependencies:** Uses Flask for Python and Quill.js/Highlight.js via CDN for the frontend.
*   **GitHub Actions:** Includes a workflow to deploy to Azure App Service (Free Tier).

## Project Structure