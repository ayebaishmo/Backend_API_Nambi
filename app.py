from flask import Flask, request, jsonify
from config import genai, MODEL_NAME

app = Flask(__name__)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "question" not in data:
        return jsonify({"error": "Question is required"}), 400
    
    question = data["question"]

    try:
        model = genai.GenerativeModel(MODEL_NAME)

        response = model.generate_content(
            question
        )
        return jsonify({
            "question": question,
            "answer": response.text
        })
    
    except Exception as e:
        return jsonify({
            "error": "Failed to generate response try again later",
            "details": str(e)
        }), 500
    
if __name__ == "__main__":
    app.run(debug=True)