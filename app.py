from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from schema_extract import extract_text_from_pdf, extract_schema_from_text
import tempfile

app = FastAPI()

# Create a directory for static files if it doesn't exist
os.makedirs("static", exist_ok=True)

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_upload_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Text and Schema Extractor</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            .upload-form {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            .file-input {
                padding: 10px;
                border: 2px dashed #ccc;
                border-radius: 4px;
            }
            .submit-button {
                background-color: #007bff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .submit-button:hover {
                background-color: #0056b3;
            }
            .result-container {
                display: flex;
                gap: 20px;
                margin-top: 20px;
            }
            .result-box {
                flex: 1;
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 4px;
                border: 1px solid #dee2e6;
            }
            .result-box h3 {
                margin-top: 0;
                color: #495057;
            }
            #extractedText, #schemaResult {
                white-space: pre-wrap;
                font-family: monospace;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PDF Text and Schema Extractor</h1>
            <div class="upload-form">
                <input type="file" id="pdfFile" accept=".pdf" class="file-input">
                <button onclick="uploadFile()" class="submit-button">Extract Text and Schema</button>
            </div>
            <div class="result-container">
                <div class="result-box">
                    <h3>Extracted Text</h3>
                    <div id="extractedText"></div>
                </div>
                <div class="result-box">
                    <h3>JSON Schema</h3>
                    <pre id="schemaResult"></pre>
                </div>
            </div>
        </div>

        <script>
        async function uploadFile() {
            const fileInput = document.getElementById('pdfFile');
            const extractedTextDiv = document.getElementById('extractedText');
            const schemaResultDiv = document.getElementById('schemaResult');
            
            if (!fileInput.files.length) {
                alert('Please select a PDF file first');
                return;
            }

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);

            try {
                extractedTextDiv.textContent = 'Extracting text...';
                schemaResultDiv.textContent = 'Generating schema...';
                
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                extractedTextDiv.textContent = data.text;
                schemaResultDiv.textContent = JSON.stringify(data.schema, null, 2);
            } catch (error) {
                extractedTextDiv.textContent = 'Error: ' + error.message;
                schemaResultDiv.textContent = 'Error: Failed to generate schema';
            }
        }
        </script>
    </body>
    </html>
    """

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Create a temporary file to store the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # Extract text from the PDF
        extracted_text = extract_text_from_pdf(temp_path)
        
        # Extract schema from the text
        schema = extract_schema_from_text(extracted_text)
        
        return {
            "text": extracted_text,
            "schema": schema
        }
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
