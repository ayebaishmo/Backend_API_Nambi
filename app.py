from flask import Flask, request, jsonify
from config import genai, MODEL_NAME
from content_fetcher import fetch_multiple_pages

app = Flask(__name__)

SITE_URLS = [
    "https://everything-uganda-website.vercel.app/",
    "https://everything-uganda-website.vercel.app/facts",
    "https://everything-uganda-website.vercel.app/culture",
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
You are helpful company chatbot.
Answer ONLY using the information provided below.
if the answer is not found say you don't know

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