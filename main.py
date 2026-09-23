import os
import base64
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional

app = FastAPI()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

@app.post("/verify")
async def verify_news(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(""),
    image: Optional[str] = Form(None),
    image_base64: Optional[str] = Form(None)
):
    try:
        prompt = """
        Hãy kiểm tra nội dung và xác minh tính đúng sai của thông tin sau:
        1. Tóm tắt ngắn gọn nội dung bài viết.
        2. Kết luận rõ ràng: [CHÍNH XÁC / TIN GIẢ / CẦN KIỂM CHỨNG].
        3. Trình bày ngắn gọn sự thật dựa trên các nguồn báo chí chính thống.
        """

        contents = [prompt]

        # 1. Xử lý phần Văn bản
        if text and text.strip():
            contents.append(f"Văn bản cần kiểm tra:\n{text.strip()}")

        # 2. Xử lý phần Hình ảnh
        image_bytes = None
        mime_type = "image/jpeg"

        if file:
            image_bytes = await file.read()
            mime_type = file.content_type or "image/jpeg"
        else:
            raw_b64 = image_base64 or image
            if raw_b64 and raw_b64.strip():
                clean_b64 = raw_b64.split(",")[-1].strip()
                try:
                    image_bytes = base64.b64decode(clean_b64)
                except Exception as b64_err:
                    print(f"Lỗi b64: {b64_err}")

        if image_bytes:
            contents.append({
                'mime_type': mime_type,
                'data': image_bytes
            })

        if not image_bytes and (not text or not text.strip()):
            return {"status": "error", "message": "Vui lòng gửi kèm hình ảnh hoặc văn bản!"}

        # Cơ chế thử lần lượt các Tên Model Gemini (chống lỗi 404 Model Not Found)
        model_names = ['gemini-1.5-flash-latest', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']
        response = None
        last_error = None

        for m_name in model_names:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(contents)
                if response and response.text:
                    break
            except Exception as err:
                last_error = err
                continue

        if not response or not response.text:
            raise last_error or Exception("Không thể kết nối các mô hình Gemini AI")

        return {
            "status": "success",
            "result": response.text
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi xử lý AI: {str(e)}"
        }
