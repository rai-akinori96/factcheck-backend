import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional

app = FastAPI()

# Thay YOUR_GEMINI_API_KEY bằng API Key thật của bạn
genai.configure(api_key="YOUR_GEMINI_API_KEY")

@app.post("/verify")
async def verify_news(
    image: Optional[UploadFile] = File(None), 
    text: Optional[str] = Form("")
):
    try:
        # Sửa tên model chuẩn gemini-1.5-flash
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Hãy kiểm tra nội dung và xác minh tính đúng sai của thông tin sau:
        1. Tóm tắt ngắn gọn nội dung bài viết.
        2. Kết luận rõ ràng: [CHÍNH XÁC / TIN GIẢ / CẦN KIỂM CHỨNG].
        3. Trình bày ngắn gọn sự thật dựa trên các nguồn báo chí chính thống.
        """

        contents = [prompt]

        # Nếu có gửi kèm văn bản
        if text and text.strip():
            contents.append(f"Văn bản cần kiểm tra:\n{text}")

        # Nếu có gửi kèm hình ảnh
        if image:
            image_bytes = await image.read()
            mime_type = image.content_type or 'image/jpeg'
            
            image_part = {
                'mime_type': mime_type,
                'data': image_bytes
            }
            contents.append(image_part)

        # Trường hợp không gửi cả ảnh lẫn text
        if not image and (not text or not text.strip()):
            return {"status": "error", "message": "Vui lòng gửi kèm hình ảnh hoặc văn bản!"}

        # Gọi Gemini API
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
