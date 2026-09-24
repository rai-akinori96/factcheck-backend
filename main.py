import os
import json
import base64
import urllib.request
import urllib.error
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional

app = FastAPI()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

@app.post("/verify")
async def verify_news(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(""),
    image: Optional[str] = Form(None),
    image_base64: Optional[str] = Form(None)
):
    try:
        if not GEMINI_KEY or not GEMINI_KEY.strip():
            return {
                "status": "error",
                "message": "⚠️ Thiếu GEMINI_API_KEY trên Render!"
            }

        # Prompt BẮT BUỘC bỏ hoàn toàn chào hỏi rườm rà
        prompt = """
        Bạn là hệ thống AI phân tích dữ liệu màn hình.
        QUY TẮC BẮT BUỘC:
        - TUYỆT ĐỐI KHÔNG chào hỏi, KHÔNG giới thiệu tên (Cấm hoàn toàn các câu như "Chào bạn!", "Mình là FactAI...", "Xin chào...").
        - Trả lời TRỰC TIẾP VÀO TRỌNG TÂM câu hỏi hoặc kết quả phân tích nội dung được khoanh vùng.
        - Trình bày ngắn gọn, rõ ràng theo cấu trúc:
          1. Phân tích / Trả lời trực tiếp nội dung khoanh vùng.
          2. Kết luận độ tin cậy: [CHÍNH XÁC / TIN GIẢ / CẦN KIỂM CHỨNG] (nếu là bài báo/tin tức).
          3. Giải thích ngắn gọn lý do.
        """

        parts = [{"text": prompt}]

        if text and text.strip():
            parts.append({"text": f"Nội dung/Câu hỏi:\n{text.strip()}"})

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
            b64_str = base64.b64encode(image_bytes).decode('utf-8')
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64_str
                }
            })

        if len(parts) == 1:
            return {"status": "error", "message": "Vui lòng khoanh vùng văn bản hoặc hình ảnh!"}

        payload = json.dumps({"contents": [{"parts": parts}]}).encode('utf-8')

        headers = {
            "x-goog-api-key": GEMINI_KEY.strip(),
            "Content-Type": "application/json",
            "User-Agent": "FactAI-App/1.0"
        }

        # Thử các Model Gemini tương thích
        models = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]
        last_err = ""

        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=25) as response:
                    res_body = response.read().decode('utf-8')
                    data = json.loads(res_body)
                    text_result = data["candidates"][0]["content"]["parts"][0]["text"]
                    return {"status": "success", "result": text_result}
            except urllib.error.HTTPError as http_err:
                err_body = http_err.read().decode('utf-8')
                last_err = err_body
                if "API_KEY_SERVICE_BLOCKED" in err_body or "denied access" in err_body:
                    return {
                        "status": "error",
                        "message": "❌ <b>Dự án Google Cloud bị tắt dịch vụ AI!</b><br><br>👉 Vui lòng mở <a href='https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com'>console.cloud.google.com/apis/library/generativelanguage.googleapis.com</a> và bấm <b>ENABLE</b> để bật lại."
                    }
            except Exception as e:
                last_err = str(e)

        return {
            "status": "error",
            "message": f"Lỗi xử lý AI: {last_err}"
        }

    except Exception as e:
        return {"status": "error", "message": f"Lỗi xử lý: {str(e)}"}
