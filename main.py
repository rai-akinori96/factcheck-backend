import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form

app = FastAPI()
genai.configure(api_key="YOUR_GEMINI_API_KEY")

@app.post("/verify")
async def verify_news(image: UploadFile = File(None), text: str = Form("")):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        if image:
            image_bytes = await image.read()
            cookie_picture = {
                'mime_type': 'image/jpeg',
                'data': image_bytes
            }
            prompt = """
            Hãy đọc văn bản trong ảnh này và xác minh tính đúng sai của thông tin:
            1. Tóm tắt ngắn gọn nội dung bài viết.
            2. Kết luận: [CHÍNH XÁC / SẢN TIN / CẦN KIỂM CHỨNG].
            3. Trình bày ngắn gọn sự thật dựa trên báo chí chính thống.
            """
            response = model.generate_content([prompt, cookie_picture])
            return response.text
        else:
            return "Không nhận được hình ảnh!"
    except Exception as e:
        return f"Lỗi xử lý AI: {str(e)}"
