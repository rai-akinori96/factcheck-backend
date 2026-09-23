import os
import base64
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional

app = FastAPI()

# 1. Tự động lấy GEMINI_API_KEY từ biến môi trường (Environment Variable) trên Render
# Nếu chạy local, bạn có thể thay "YOUR_GEMINI_API_KEY" bằng Key thật để test
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

@app.post("/verify")
async def verify_news(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(""),
    image: Optional[str] = Form(None),
    image_base64: Optional[str] = Form(None)
):
    try:
        # Sử dụng model gemini-1.5-flash có tốc độ phản hồi siêu nhanh (~1-2s)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Hãy kiểm tra nội dung và xác minh tính đúng sai của thông tin sau:
        1. Tóm tắt ngắn gọn nội dung bài viết.
        2. Kết luận rõ ràng: [CHÍNH XÁC / TIN GIẢ / CẦN KIỂM CHỨNG].
        3. Trình bày ngắn gọn sự thật dựa trên các nguồn báo chí chính thống.
        """

        contents = [prompt]

        # 1. Nếu có gửi kèm Văn bản chữ (text)
        if text and text.strip():
            contents.append(f"Văn bản cần kiểm tra:\n{text.strip()}")

        # 2. Xử lý Hình ảnh (Hỗ trợ cả File Upload lẫn chuỗi Base64 từ App Android)
        image_bytes = None
        mime_type = "image/jpeg"

        # Nếu gửi qua File Upload
        if file:
            image_bytes = await file.read()
            mime_type = file.content_type or "image/jpeg"

        # Nếu gửi qua chuỗi Base64 (App Android gửi qua field `image` hoặc `image_base64`)
        else:
            raw_b64 = image_base64 or image
            if raw_b64 and raw_b64.strip():
                # Tách bỏ tiền tố "data:image/jpeg;base64," nếu có
                clean_b64 = raw_b64.split(",")[-1].strip()
                try:
                    image_bytes = base64.b64decode(clean_b64)
                except Exception as b64_err:
                    print(f"Lỗi giải mã Base64: {b64_err}")

        # Thêm dữ liệu ảnh vào nội dung gửi cho Gemini
        if image_bytes:
            contents.append({
                'mime_type': mime_type,
                'data': image_bytes
            })

        # Trường hợp không nhận được cả ảnh lẫn văn bản
        if not image_bytes and (not text or not text.strip()):
            return {"status": "error", "message": "Vui lòng gửi kèm hình ảnh hoặc văn bản!"}

        # Gọi Gemini AI xử lý
        response = model.generate_content(contents)
        
        return {
            "status": "success",
            "result": response.text
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi xử lý AI: {str(e)}"
        }
