import os
from fastapi import FastAPI, UploadFile, File
from google import genai
from google.genai import types

app = FastAPI()

# Khởi tạo Gemini Client (Cần set biến môi trường GEMINI_API_KEY)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.post("/verify")
async def verify_claim(file: UploadFile = File(...)):
    image_bytes = await file.read()

    prompt = """
    Bạn là chuyên gia kiểm chứng thông tin (Fact-checker).
    1. Đọc hình ảnh màn hình này và trích xuất nội dung/tuyên bố chính.
    2. Đánh giá xem nội dung là ĐÚNG, SAI, hay CẦN CẢNH BÁO.
    3. Giải thích ngắn gọn 2-3 câu lý do dựa trên thông tin chính thống.
    Format trả về dạng JSON:
    {
      "status": "ĐÚNG" hoặc "SAI" hoặc "CẦN CẢNH BÁO",
      "confidence": "90%",
      "summary": "Nội dung giải thích...",
      "sources": ["Nguồn tham khảo nếu có"]
    }
    """

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt
        ]
    )

    return {"result": response.text}