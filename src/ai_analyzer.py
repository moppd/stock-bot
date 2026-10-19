import json
from openai import OpenAI
from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

def generate_market_outlook(market_data: dict, news_items: list) -> dict:
    if not LLM_API_KEY:
        return {
            "market_bias": "Neutral",
            "headline_th": "รายงานตลาดฟิวเจอร์สสหรัฐฯ (สรุปแบบไม่มี AI)",
            "overview_th": "ระบบดึงข้อมูลราคาและข่าวสำเร็จ (ไม่ได้ตั้งค่า LLM Key)",
            "drivers_th": ["ติดตามการประกาศตัวเลขเศรษฐกิจ"],
            "risks_th": ["ความผันผวนของอัตราผลตอบแทนพันธบัตร"],
            "watch_events_th": ["การเปิดตลาดปกติคืนนี้"]
        }

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    system_prompt = (
        "คุณคือ Senior US Financial Market Analyst หน้าที่คือวิเคราะห์ US Index Futures และข่าว "
        "สรุปรายงานเป็นภาษาไทยในรูปแบบ JSON เท่านั้น ห้ามแต่งข้อมูลที่ไม่มีในอินพุตเด็ดขาด\n"
        "รูปแบบ Schema:\n"
        "{\n"
        '  "market_bias": "Bullish" | "Neutral" | "Bearish" | "ข้อมูลไม่เพียงพอ",\n'
        '  "headline_th": "พาดหัวสั้นกระชับภาษาไทย",\n'
        '  "overview_th": "สรุปภาพรวมภาษาไทย 2-3 ประโยค",\n'
        '  "drivers_th": ["ปัจจัยหนุน 1"],\n'
        '  "risks_th": ["ปัจจัยเสี่ยง 1"],\n'
        '  "watch_events_th": ["สิ่งที่ต้องจับตา 1"]\n'
        "}"
    )

    user_payload = {
        "futures_data": market_data["futures"],
        "indicators": market_data["indicators"],
        "news": news_items
    }

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"ข้อมูล:\n{json.dumps(user_payload, ensure_ascii=False)}"}
            ],
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "market_bias": "ข้อมูลไม่เพียงพอ",
            "headline_th": "ไม่สามารถประมวลผลบทวิเคราะห์ได้",
            "overview_th": f"เกิดข้อผิดพลาดในการเรียก AI: {str(e)[:100]}",
            "drivers_th": ["-"],
            "risks_th": ["-"],
            "watch_events_th": ["-"]
        }
