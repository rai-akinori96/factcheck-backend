import os
import base64
import httpx
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

        prompt = """
        Hãy kiểm tra nội dung và xác minh tính đúng sai của thông tin sau:
        1. Tóm tắt ngắn gọn nội dung bài viết.
        2. Kết luận rõ ràng: [CHÍNH XÁC / TIN GIẢ / CẦN KIỂM CHỨNG].
        3. Trình bày ngắn gọn sự thật dựa trên các nguồn báo chí chính thống.
        """

        parts = [{"text": prompt}]

        if text and text.strip():
            parts.append({"text": f"Văn bản khoanh vùng:\n{text.strip()}"})

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

        # Gửi Header x-goog-api-key chuẩn cho Auth Key AQ...
        headers = {
            "x-goog-api-key": GEMINI_KEY.strip(),
            "Content-Type": "application/json"
        }
        payload = {
            "contents": [{"parts": parts}]
        }

        # Thử các Model tương thích với Auth Key
        models = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]
        last_err = ""

        async with httpx.AsyncClient(timeout=25.0) as client:
            for model_name in models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                res = await client.post(url, headers=headers, json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    try:
                        text_result = data["candidates"][0]["content"]["parts"][0]["text"]
                        return {"status": "success", "result": text_result}
                    except Exception:
                        pass
                else:
                    err_json = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                    last_err = err_json.get("error", {}).get("message", res.text)
                    if "API_KEY_SERVICE_BLOCKED" in str(err_json) or "denied access" in str(err_json):
                        return {
                            "status": "error",
                            "message": "❌ <b>Dự án Google Cloud bị tắt dịch vụ AI!</b><br><br>👉 Vui lòng truy cập <a href='https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com'>console.cloud.google.com/apis/library/generativelanguage.googleapis.com</a> và bấm <b>ENABLE</b> để bật lại."
                        }

        return {
            "status": "error",
            "message": f"Lỗi xử lý AI: {last_err}"
        }

    except Exception as e:
        return {"status": "error", "message": f"Lỗi xử lý: {str(e)}"}
