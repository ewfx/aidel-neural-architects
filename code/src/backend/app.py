from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
from main import process_data
from parser1 import parse_transaction_file

app = Flask(__name__)
CORS(app)

processed_df = pd.DataFrame()

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'dataFile' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['dataFile']
        
        if file.filename.endswith('.csv'):
            data = pd.read_csv(file)
            json_data = process_data(data)
        elif file.filename.endswith('.txt'):
            content = file.read().decode('utf-8')            
            data = parse_transaction_file(content)
            json_data = process_data(data)
        else:
            return jsonify({'error': 'Please select a valid CSV or TXT file'}), 400

        return json_data, 200
    except Exception as e:
        return jsonify({'error': 'File upload failed'}), 500

if __name__ == '__main__':
    app.run(debug=True)