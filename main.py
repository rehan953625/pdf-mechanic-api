import os
from fastapi import FastAPI, UploadFile, File, Form, Response
from fastapi.responses import HTMLResponse
import google.generativeai as genai
from PIL import Image
import io
from docx import Document
import pandas as pd

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ye sabhi websites ko allow kar dega
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.6-flash')

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("extractor.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/extract-text")
async def extract_text(
    file: UploadFile = File(...),
    language: str = Form("English")
):
    try:
        file_bytes = await file.read()
        
        # 1. File Type Check Karna
        if file.content_type.startswith('image/'):
            doc_part = Image.open(io.BytesIO(file_bytes))
        elif file.content_type == 'application/pdf':
            # Gemini ke liye PDF data setup
            doc_part = {
                "mime_type": "application/pdf",
                "data": file_bytes
            }
        else:
            return {"status": "error", "message": "Unsupported file! Sirf Image ya PDF upload karein."}
        
        # 2. Prompt me Language Pass Karna
        prompt = f"""
        Extract all the text from this document.
        Translate or provide the output STRICTLY in {language} language.
        Maintain the original paragraphs, line breaks, and structure.
        Do not include any conversational filler, just output the exact extracted text.
        """
        
        # 3. Gemini ko Image ya PDF bhejna
        response = model.generate_content([prompt, doc_part])
        
        return {"status": "success", "text": response.text}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
# 2. API: Download format (TXT, Word, Excel) banane ke liye
@app.post("/api/download-file")
async def download_file(text: str = Form(...), format: str = Form(...)):
    if format == "txt":
        return Response(
            content=text, 
            media_type="text/plain", 
            headers={"Content-Disposition": "attachment; filename=extracted_text.txt"}
        )
    
    elif format == "docx":
        doc = Document()
        doc.add_paragraph(text)
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return Response(
            content=file_stream.getvalue(), 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            headers={"Content-Disposition": "attachment; filename=extracted_document.docx"}
        )
        
    elif format == "xlsx":
        # Simple text to Excel conversion
        lines = text.strip().split('\n')
        # Agar text me tabs hain to columns me batega, warna single column
        data = [line.split('\t') if '\t' in line else [line] for line in lines]
        df = pd.DataFrame(data)
        file_stream = io.BytesIO()
        df.to_excel(file_stream, index=False, header=False)
        file_stream.seek(0)
        return Response(
            content=file_stream.getvalue(), 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            headers={"Content-Disposition": "attachment; filename=extracted_data.xlsx"}
        )
