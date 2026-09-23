import os
import base64
import json
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional

app = FastAPI()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

@app.post("/verify")
async def verify_news(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(""),
    image: Optional[str] = Form(None),
    image_base64: Optional[str] = Form(None)
):
    try:
        if not GEMINI_KEY:
            return {"status": "error", "message": "⚠️ Thiếu GEMINI_API_KEY trên Render!"}

        # Prompt Google Lens chuyên biệt kiểm chứng tin tức
        prompt = """
        Bạn là hệ thống kiểm chứng tin tức thông minh FactAI Lens.
        Hãy phân tích hình ảnh/văn bản được chọn và tìm kiếm thông tin thực tế trên Google Search.

        Yêu cầu trả về định dạng HTML gọn gàng gồm:
        1. <b>[KẾT LUẬN]</b>: <span style="color:#34A853">🟢 CHÍNH XÁC</span> hoặc <span style="color:#EA4335">🔴 TIN GIẢ / XUYÊN TẠC</span> hoặc <span style="color:#FBBC05">🟡 CẦN KIỂM CHỨNG</span>
        2. <b>[TÓM TẮT SỰ THẬT]</b>: Trình bày ngắn gọn trong 2-3 câu sự thật dựa trên báo chí chính thống.
        3. <b>[NGUỒN ĐỐI SOÁT]</b>: Trích dẫn tên tờ báo hoặc đường link kiểm chứng nếu có.
        """

        contents = [prompt]

        if text and text.strip():
            contents.append(f"Văn bản khoanh vùng:\n{text.strip()}")

        image_bytes = None
        if file:
            image_bytes = await file.read()
        else:
            raw_b64 = image_base64 or image
            if raw_b64 and raw_b64.strip():
                clean_b64 = raw_b64.split(",")[-1].strip()
                try:
                    image_bytes = base64.b64decode(clean_b64)
                except Exception:
                    pass

        if image_bytes:
            contents.append({'mime_type': 'image/jpeg', 'data': image_bytes})

        if not image_bytes and (not text or not text.strip()):
            return {"status": "error", "message": "Vui lòng khoanh vùng văn bản hoặc hình ảnh!"}

        # Tích hợp Google Search Grounding (Tìm kiếm thông tin thực tế trên Google)
        try:
            model = genai.GenerativeModel('gemini-1.5-flash', tools=[{"google_search": {}}])
            response = model.generate_content(contents)
        except Exception:
            # Fallback nếu model không hỗ trợ tool
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(contents)

        if not response or not response.text:
            return {"status": "error", "message": "Không nhận được phản hồi từ AI"}

        return {
            "status": "success",
            "result": response.text
        }

    except Exception as e:
        return {"status": "error", "message": f"Lỗi xử lý: {str(e)}"}
