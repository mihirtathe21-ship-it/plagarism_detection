"""
Plagiarism Detection System - Flask Backend
Supports text files, image OCR, TF-IDF + Semantic BERT similarity
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from api.routes import api_blueprint

app = Flask(__name__)
CORS(app)

app.register_blueprint(api_blueprint, url_prefix='/api')

@app.route('/health')
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
