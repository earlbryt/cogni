from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from schema_extract import extract_text_from_pdf, extract_schema_from_text
import tempfile
from dotenv import load_dotenv

# Load environment variables at startup
load_dotenv()

app = FastAPI()

# Create a directory for static files if it doesn't exist
os.makedirs("static", exist_ok=True)

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_upload_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PDF Text & Schema Extractor</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; }
            .loading-spinner {
                border: 3px solid #f3f3f3;
                border-radius: 50%;
                border-top: 3px solid #3b82f6;
                width: 24px;
                height: 24px;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .fade-enter-active, .fade-leave-active {
                transition: opacity 0.3s ease;
            }
            .fade-enter-from, .fade-leave-to {
                opacity: 0;
            }
        </style>
    </head>
    <body class="bg-gray-50 min-h-screen">
        <div id="app" class="container mx-auto px-4 py-8 max-w-6xl">
            <header class="text-center mb-12">
                <h1 class="text-4xl font-semibold text-gray-800 mb-2">PDF Text & Schema Extractor</h1>
                <p class="text-gray-600">Upload a PDF to extract text and generate a JSON schema</p>
            </header>

            <div class="bg-white rounded-lg shadow-lg p-6 mb-8">
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">Upload PDF</label>
                    <div class="flex items-center justify-center w-full">
                        <label class="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
                            <div class="flex flex-col items-center justify-center pt-5 pb-6">
                                <svg class="w-8 h-8 mb-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                </svg>
                                <p class="mb-2 text-sm text-gray-500"><span class="font-semibold">Click to upload</span> or drag and drop</p>
                                <p class="text-xs text-gray-500">PDF files only</p>
                            </div>
                            <input type="file" class="hidden" accept=".pdf" @change="handleFileUpload" ref="fileInput">
                        </label>
                    </div>
                </div>

                <div v-if="loading" class="flex items-center justify-center space-x-2 my-4">
                    <div class="loading-spinner"></div>
                    <span class="text-gray-600">Processing...</span>
                </div>

                <div v-if="error" class="bg-red-50 border-l-4 border-red-500 p-4 my-4">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                            </svg>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-red-700">{{ error }}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="result" class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Extracted Text Panel -->
                <div class="bg-white rounded-lg shadow-lg p-6">
                    <h2 class="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                        <svg class="w-5 h-5 mr-2 text-blue-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                            <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd" />
                        </svg>
                        Extracted Text
                    </h2>
                    <div class="bg-gray-50 rounded-lg p-4 max-h-[500px] overflow-y-auto">
                        <pre class="text-sm text-gray-700 whitespace-pre-wrap">{{ result.text }}</pre>
                    </div>
                </div>

                <!-- JSON Schema Panel -->
                <div class="bg-white rounded-lg shadow-lg p-6">
                    <h2 class="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                        <svg class="w-5 h-5 mr-2 text-green-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm3.293 1.293a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 01-1.414-1.414L7.586 10 5.293 7.707a1 1 0 010-1.414zM11 12a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd" />
                        </svg>
                        JSON Schema
                    </h2>
                    <div class="bg-gray-50 rounded-lg p-4 max-h-[500px] overflow-y-auto">
                        <pre class="text-sm text-gray-700 whitespace-pre-wrap">{{ JSON.stringify(result.schema, null, 2) }}</pre>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const { createApp, ref } = Vue

            createApp({
                setup() {
                    const fileInput = ref(null)
                    const loading = ref(false)
                    const error = ref(null)
                    const result = ref(null)

                    async function handleFileUpload(event) {
                        const file = event.target.files[0]
                        if (!file) return

                        loading.value = true
                        error.value = null
                        result.value = null

                        const formData = new FormData()
                        formData.append('file', file)

                        try {
                            const response = await fetch('/upload', {
                                method: 'POST',
                                body: formData
                            })

                            if (!response.ok) {
                                throw new Error('Upload failed')
                            }

                            result.value = await response.json()
                        } catch (err) {
                            error.value = 'Failed to process the PDF. Please try again.'
                            console.error(err)
                        } finally {
                            loading.value = false
                        }
                    }

                    return {
                        fileInput,
                        loading,
                        error,
                        result,
                        handleFileUpload
                    }
                }
            }).mount('#app')
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
        extracted_text = extract_text_from_pdf.invoke(temp_path)
        
        # Extract schema from the text
        schema = extract_schema_from_text.invoke(extracted_text)
        
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
