# __init__.py for Azure Function (e.g., FormatTeamsNotification)
import logging
import json
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
    except ValueError:
        logging.error("Invalid JSON in request body.")
        req_body = None

    if not req_body:
        try:
            # Fallback for form data if not JSON (less likely from Power Automate)
            req_body = dict(req.form)
        except Exception:  # Broad exception if req.form also fails
            return func.HttpResponse(
                "Please pass data in the request body (JSON or form data)",
                status_code=400
            )

    repo_name = req_body.get('repository_name', 'N/A')
    commit_message = req_body.get('commit_message', 'N/A')
    commit_url = req_body.get('commit_url', '#')
    confluence_page_title = req_body.get('confluence_page_title', 'N/A')
    confluence_page_url = req_body.get('confluence_page_url', '#')
    status = req_body.get('status', 'Updated')  # e.g., "Updated", "Created"

    # --- Construct Adaptive Card JSON ---
    # You can design more complex cards at: https://adaptivecards.io/designer/
    adaptive_card_payload = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",  # Use a recent version
        "body": [
            {
                "type": "TextBlock",
                "text": f"Confluence Documentation {status}",
                "weight": "Bolder",
                "size": "Medium"
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "Repository:",
                        "value": repo_name
                    },
                    {
                        "title": "Confluence Page:",
                        "value": f"[{confluence_page_title}]({confluence_page_url})" if confluence_page_url != '#' else confluence_page_title
                    },
                    {
                        "title": "Commit:",
                        "value": commit_message
                    }
                ]
            }
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "View Commit",
                "url": commit_url
            },
            {
                "type": "Action.OpenUrl",
                "title": "View Confluence Page",
                "url": confluence_page_url
            }
        ]
    }

    return func.HttpResponse(
        body=json.dumps(adaptive_card_payload),
        mimetype="application/json",
        status_code=200
    )
