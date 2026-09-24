import os
import json
import base64
import urllib.request
import urllib.error
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional

app = FastAPI()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def extract_gemini_text(data):
    """Trích xuất đầy đủ văn bản từ câu trả lời có chứa Google Search Grounding"""
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p.get("text", "").strip() for p in parts if p.get("text")]
        return "\n\n".join(text_parts).strip()
    except Exception:
        return ""

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

        # Prompt Quy Tắc Nghiêm Ngặt & Tích Hợp Google Search Grounding
        prompt = """
        [BỐI CẢNH HỆ THỐNG]
        Bạn là một AI kiểm tra sự thật (Fact-check) chuyên nghiệp. Bạn có khả năng tự động cập nhật và suy luận dòng thời gian thực tế dựa trên các kết quả tìm kiếm (Google Search Grounding) mới nhất.

        [QUY TRÌNH TƯ DUY NGẦM (INTERNAL LOGIC)]
        - Khi nhận được câu hỏi, bạn phải ngầm hiểu dòng thời gian dựa trên các tin tức và sự kiện mới nhất vừa tìm kiếm được trên mạng để đưa ra thông tin đúng thời điểm.
        - Tuyệt đối không được lấy dữ liệu tĩnh cũ kỹ trong bộ nhớ (ví dụ: các sự kiện cũ năm 2024) để khẳng định cho trạng thái hiện tại. 
        - Nếu không chắc chắn hoặc không có kết quả tìm kiếm mới, hãy ngầm hiểu là mình thiếu thông tin và báo lỗi, tuyệt đối không được tự bịa đặt (ảo giác).

        [QUY TẮC HIỂN THỊ KẾT QUẢ (OUTPUT RESTRICTIONS)]
        - TRỰC TIẾP & KHÁCH QUAN: Chỉ trả về kết quả phân tích sự thật của thông tin được yêu cầu.
        - BẢO MẬT THỜI GIAN: Tuyệt đối KHÔNG hiển thị các câu từ, mốc thời gian hệ thống, hoặc các cụm từ khẳng định thời gian hiện tại (Ví dụ CẤM viết: "Tính đến năm 2026...", "Hiện tại là...", "Hôm nay là ngày...", "Dữ liệu cập nhật mới nhất ngày..."). Người dùng chỉ cần câu trả lời đúng.
        - KHÔNG CHÀO HỎI, KHÔNG RƯỜM RÀ: Bỏ hoàn toàn các câu "Chào bạn", "Mình là...".
        - CẤU TRÚC KẾT QUẢ:
          1. Trả lời / Phân tích trực tiếp trọng tâm thông tin khoanh vùng.
          2. Kết luận độ tin cậy: [CHÍNH XÁC / TIN GIẢ / CẦN KIỂM CHỨNG].
          3. Tóm tắt sự thật ngắn gọn dựa trên báo chí chính thống.
        """

        parts = [{"text": prompt}]

        if text and text.strip():
            parts.append({"text": f"Nội dung/Câu hỏi khoanh vùng:\n{text.strip()}"})

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

        payload_with_tools = json.dumps({
            "contents": [{"parts": parts}],
            "tools": [{"google_search": {}}]
        }).encode('utf-8')

        payload_plain = json.dumps({
            "contents": [{"parts": parts}]
        }).encode('utf-8')

        headers = {
            "x-goog-api-key": GEMINI_KEY.strip(),
            "Content-Type": "application/json",
            "User-Agent": "FactAI-App/1.0"
        }

        models = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]
        last_err = ""

        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            
            # Thử 1: Kích hoạt Google Search Grounding thời gian thực
            req = urllib.request.Request(url, data=payload_with_tools, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=25) as response:
                    res_body = response.read().decode('utf-8')
                    data = json.loads(res_body)
                    text_result = extract_gemini_text(data)
                    if text_result:
                        return {"status": "success", "result": text_result}
            except Exception:
                pass

            # Thử 2: Plain Payload nếu không bật tools
            req_plain = urllib.request.Request(url, data=payload_plain, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req_plain, timeout=25) as response:
                    res_body = response.read().decode('utf-8')
                    data = json.loads(res_body)
                    text_result = extract_gemini_text(data)
                    if text_result:
                        return {"status": "success", "result": text_result}
            except urllib.error.HTTPError as http_err:
                err_body = http_err.read().decode('utf-8')
                last_err = err_body
                if "API_KEY_SERVICE_BLOCKED" in err_body or "denied access" in err_body:
                    return {
                        "status": "error",
                        "message": "❌ <b>Dự án Google Cloud bị tắt dịch vụ AI!</b><br><br>👉 Vui lòng mở <a href='https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com'>console.cloud.google.com/apis/library/generativelanguage.googleapis.com</a> và bấm <b>ENABLE</b> để bật lại."
                    }
            except Exception as e2:
                last_err = str(e2)

        return {
            "status": "error",
            "message": f"Lỗi xử lý AI: {last_err or 'Không có dữ liệu trả về'}"
        }

    except Exception as e:
        return {"status": "error", "message": f"Lỗi xử lý: {str(e)}"}
