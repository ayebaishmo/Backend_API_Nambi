from flask import Blueprint, request, jsonify
from config import genai, MODEL_NAME
from services.content_fetcher import fetch_multiple_pages

chat_bp = Blueprint("chat", __name__)

SITE_URLS = [
    "https://everything-ug.netlify.app/",
    "https://everything-ug.netlify.app/facts",
    "https://everything-ug.netlify.app/culture",
    "https://everything-ug.netlify.app/top-cities/kampala",
    "https://everything-ug.netlify.app/religion",
    "https://everything-ug.netlify.app/travel-tips",
    "https://everything-ug.netlify.app/destinations",
    "https://everything-ug.netlify.app/activities",
    "https://everything-ug.netlify.app/about",
    "https://everything-ug.netlify.app/where-to-stay",
    "https://everything-ug.netlify.app/insights",
    "https://everything-ug.netlify.app/impact",
    "https://everything-ug.netlify.app/holiday-booking"
]

print("Loading website content....")
SITE_CONTENT = fetch_multiple_pages(SITE_URLS)
print("Website Content loaded")


@chat_bp.route("/chat", methods=["POST"])
def chat():
    """
    Chat with Nambi (Everything Uganda chatbot)
    ---
    tags:
      - Chatbot
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            question:
              type: string
              example: "Tell me about Kampala"
    responses:
      200:
        description: Bot response
        schema:
          type: object
          properties:
            answer:
              type: string
    """

    data = request.get_json()

    if not data or "question" not in data:
        return jsonify({"error": "Question is required"}), 400

    question = data["question"]

    try:
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""
You are a chatbot assistant for Everything Uganda.
Your name is Nambi.
Answer using this information plus including all your knowledge base.

COMPANY SITE CONTENT:
{SITE_CONTENT}

USER QUESTION:
{question}
"""

        response = model.generate_content(prompt)

        return jsonify({"answer": response.text})

    except Exception as e:
        return jsonify({
            "error": "Failed to generate response try again later",
            "details": str(e)
        }), 500
