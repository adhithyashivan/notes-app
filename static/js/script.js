document.addEventListener('DOMContentLoaded', () => {
    const noteForm = document.getElementById('noteForm');
    const noteTitleInput = document.getElementById('noteTitle');
    const notesContainer = document.getElementById('notesContainer');
    const premiumUpgradeBtn = document.getElementById('premiumUpgradeBtn');
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    const formErrorEl = document.getElementById('formError');
    const notesInfoEl = document.getElementById('notesInfo');
    const charCountEl = document.getElementById('charCount');
    const MAX_CONTENT_LENGTH = 20000; // Same as backend

    // --- Initialize Quill Editor ---
    // Define the toolbar options
    const toolbarOptions = [
        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
        [{ 'font': [] }],
        ['bold', 'italic', 'underline', 'strike'],        // toggled buttons
        ['blockquote', 'code-block'],

        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
        [{ 'script': 'sub'}, { 'script': 'super' }],      // superscript/subscript
        [{ 'indent': '-1'}, { 'indent': '+1' }],          // outdent/indent
        [{ 'direction': 'rtl' }],                         // text direction

        [{ 'color': [] }, { 'background': [] }],          // dropdown with defaults from theme
        [{ 'align': [] }],

        ['link', 'image', 'video'], // image and video might require server-side handling for uploads in a real app

        ['clean']                                         // remove formatting button
    ];

    // Configure highlight.js for Quill
    hljs.configure({
        languages: ['javascript', 'python', 'java', 'c', 'cpp', 'sql', 'html', 'css', 'xml', 'json', 'bash', 'plaintext']
    });

    const quill = new Quill('#editor', {
        modules: {
            syntax: {
                highlight: text => hljs.highlightAuto(text).value
            }, // Enable syntax module
            toolbar: toolbarOptions
        },
        theme: 'snow',
        placeholder: 'Compose your note...'
    });

    // Update char count
    quill.on('text-change', () => {
        const textLength = quill.getLength() - 1; // Quill counts newline as 1 char
        charCountEl.textContent = `Characters: ${textLength} / ${MAX_CONTENT_LENGTH}`;
        if (textLength > MAX_CONTENT_LENGTH) {
            charCountEl.style.color = 'var(--danger-color)';
        } else {
            charCountEl.style.color = 'var(--secondary-color)';
        }
    });


    // --- Navbar Toggle ---
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
    }

    // --- API Helper ---
    async function apiRequest(url, method = 'GET', body = null) {
        const options = {
            method,
            headers: {}
        };
        if (body) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                // Try to parse error message from backend
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    // If no JSON, use status text
                    errorData = { error: response.statusText };
                }
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            // If response has no content (e.g. 204 No Content or 201 from POST without explicit return)
            if (response.status === 204 || response.headers.get("content-length") === "0") {
                return null; 
            }
            return await response.json();
        } catch (error) {
            console.error(`API Request Error (${method} ${url}):`, error);
            throw error; // Re-throw to be caught by caller
        }
    }

    // --- Display Messages ---
    function showFormError(message) {
        formErrorEl.textContent = message;
        formErrorEl.style.display = 'block';
    }
    function clearFormError() {
        formErrorEl.textContent = '';
        formErrorEl.style.display = 'none';
    }
    function showNotesInfo(message, type = 'info') {
        notesInfoEl.textContent = message;
        notesInfoEl.className = `info-message ${type}`; // Add type for styling (e.g., 'error', 'success')
        notesInfoEl.style.display = 'block';
    }
    function clearNotesInfo() {
        notesInfoEl.textContent = '';
        notesInfoEl.style.display = 'none';
    }


    // --- Load and Display Notes ---
    async function fetchAndDisplayNotes() {
        clearNotesInfo();
        try {
            const notes = await apiRequest('/api/notes');
            notesContainer.innerHTML = ''; // Clear existing notes
            if (notes && notes.length > 0) {
                notes.forEach(note => {
                    const noteElement = createNoteElement(note);
                    notesContainer.appendChild(noteElement);
                });
            } else {
                showNotesInfo('No notes yet. Add your first note above!');
            }
        } catch (error) {
            showNotesInfo(`Error fetching notes: ${error.message}`, 'error');
        }
    }

    function createNoteElement(note) {
        const div = document.createElement('div');
        div.className = 'note-card';
        div.dataset.id = note.id;

        const titleEl = document.createElement('h3');
        titleEl.textContent = note.title; // Use textContent for title to prevent XSS

        const contentEl = document.createElement('div');
        contentEl.className = 'note-card-content';
        // The content from Quill is HTML, so we set innerHTML.
        // This is generally safe as Quill is designed to produce sanitized HTML.
        // Backend also does a basic check.
        contentEl.innerHTML = note.content;

        const timestampEl = document.createElement('p');
        timestampEl.className = 'note-card-timestamp';
        timestampEl.textContent = `Created: ${new Date(note.timestamp).toLocaleString()}`;

        div.appendChild(titleEl);
        div.appendChild(contentEl);
        div.appendChild(timestampEl);
        return div;
    }

    // --- Handle Note Submission ---
    if (noteForm) {
        noteForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            clearFormError();

            const title = noteTitleInput.value.trim();
            const contentHTML = quill.root.innerHTML; // Get HTML content from Quill
            const contentTextLength = quill.getLength() - 1;

            // --- Frontend Validations ---
            if (!title) {
                showFormError('Title is required.');
                noteTitleInput.focus();
                return;
            }
            if (title.length > 200) {
                showFormError('Title cannot exceed 200 characters.');
                noteTitleInput.focus();
                return;
            }
            if (contentTextLength === 0) { // Quill's getLength() returns 1 for an empty editor
                showFormError('Content cannot be empty.');
                quill.focus();
                return;
            }
            if (contentTextLength > MAX_CONTENT_LENGTH) {
                showFormError(`Content is too long. Max ${MAX_CONTENT_LENGTH} characters. Current: ${contentTextLength}`);
                quill.focus();
                return;
            }


            try {
                await apiRequest('/api/notes', 'POST', { title, content: contentHTML });
                noteTitleInput.value = '';
                quill.setContents([]); // Clear Quill editor
                charCountEl.textContent = `Characters: 0 / ${MAX_CONTENT_LENGTH}`; // Reset char count
                fetchAndDisplayNotes(); // Refresh notes list
                showNotesInfo('Note added successfully!', 'success');
                setTimeout(clearNotesInfo, 3000); // Clear after 3s
            } catch (error) {
                showFormError(`Error adding note: ${error.message}`);
            }
        });
    }

    // --- Handle Premium Upgrade Button ---
    if (premiumUpgradeBtn) {
        premiumUpgradeBtn.addEventListener('click', async () => {
            clearFormError();
            try {
                const result = await apiRequest('/api/notes/premium-upgrade', 'POST');
                showNotesInfo(result.message, result.deleted ? 'success' : 'info');
                if (result.deleted) {
                    fetchAndDisplayNotes(); // Refresh notes if one was deleted
                }
                // No need to clear this message immediately, let user read it.
            } catch (error) {
                showNotesInfo(`Upgrade attempt failed: ${error.message}`, 'error');
            }
        });
    }

    // --- Initial Load ---
    fetchAndDisplayNotes();
});