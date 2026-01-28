from flask import Flask, request, jsonify
from config import genai, MODEL_NAME
from content_fetcher import fetch_multiple_pages
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SITE_URLS = [
    "https://everything-ug.netlify.app/",
    "https://everything-ug.netlify.app/facts",
    "https://everything-ug.netlify.app/culture",
    "https://everything-ug.netlify.app/top-cities/kampala",
    "https://everything-ug.netlify.app/religion",
    "https://everything-ug.netlify.app/travel-tips",
    "https://everything-ug.netlify.app/destinations",
    "https://everything-ug.netlify.app/activities",
    "https://everything-uganda-website.vercel.app/about"
    
]

print("Loading website content....")
SITE_CONTENT = fetch_multiple_pages(SITE_URLS)
print("Website Content loaded")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "question" not in data:
        return jsonify({"error": "Question is required"}), 400
    
    question = data["question"]

    try:
        model = genai.GenerativeModel(MODEL_NAME)

        prompt = f"""
You are a chatbot assistant for Everything Uganda.
Answer using ONLY the information from the website content below.
Give a detailed, well-explained answer.

COMPANY SITE CONTENT:
{SITE_CONTENT}

USER QUESTION: 
{question}"""

        response = model.generate_content(
            prompt
        )
        return jsonify({
            "answer": response.text
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to generate response try again later",
            "details": str(e)
        }), 500
    
if __name__ == "__main__":
    app.run(debug=True)