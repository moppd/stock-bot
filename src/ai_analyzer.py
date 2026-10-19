import json
from openai import OpenAI
from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

def generate_market_brief_analysis(market_data: dict, categorized_news: dict) -> dict:
    if not LLM_API_KEY:
        return {
            "market_bias": "เป็นกลาง",
            "headline_th": "รายงานความเคลื่อนไหวตลาดฟิวเจอร์สสหรัฐฯ",
            "overview_th": "ระบบดึงข้อมูลราคาตลาดและข่าวล่าสุดเรียบร้อย แต่ไม่ได้ระบุ LLM_API_KEY",
            "indicators_interpretation_th": None,
            "drivers_th": [],
            "risks_th": [],
            "has_confirmed_events": False,
            "events_or_highlights": {
                "type": "highlights",
                "title": "🔥 ประเด็นสำคัญที่ต้องจับตา",
                "items": [{"topic_th": "ตลาดรอปัจจัยชี้นำใหม่", "detail_th": "ยังไม่มีรายงานตัวเลขเศรษฐกิจหรือข่าวด่วนที่มีน้ำหนักเพียงพอต่อการเปลี่ยนทิศทางตลาด"}]
            },
            "big_tech_news": [],
            "global_news": []
        }

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    system_prompt = """
คุณคือนักวิเคราะห์กลยุทธ์การลงทุนอาวุโส (Senior Market Strategist) สรุปรายงาน US Market Brief ภาษาไทยอย่างมืออาชีพ

กฎเหล็กในการสรุปข่าวและเขียนเนื้อหา:
1. ไม่ต้องใส่ Source หรือ URL ลิงก์ใดๆ ทั้งสิ้นในผลลัพธ์
2. สรุปข่าวให้ 'ครบถ้วน เจาะลึก และเห็นภาพชัดเจน':
   - ไม่ต้องเขียนสั้นหรือรวบรัดเกินไป ให้เขียนอธิบายบริบท ที่มาที่ไป ข้อเท็จจริง ตัวเลขสำคัญ และกลไกที่ส่งผลกระทบต่อตลาดหุ้นหรือกลุ่มอุตสาหกรรมอย่างชัดเจน (ความยาวประมาณ 2-4 บรรทัดต่อประเด็น)
3. ยึดหลักฐานจริง: ห้ามแต่งตัวเลข ข่าว หรือข้อมูลที่ไม่มีใน input โดยเด็ดขาด
4. คำต้องห้าม (Filler Words): หลีกเลี่ยงคำว่า 'ไม่แน่นอน', 'ผันผวน', 'ต้องติดตามต่อไป' ให้ระบุเจาะจงว่าเกิดอะไรขึ้น
5. เมื่อ Futures เคลื่อนไหวใกล้ 0.00% (±0.04%): ห้ามฟันธงว่าเป็นขาขึ้นหรือขาลง ให้ใช้ bias 'เป็นกลาง'
6. หมวดหมู่:
   - Big Tech & AI: ต้องเป็นข่าวบริษัทเทคฯ จริง (NVDA, MSFT, AAPL, ชิป, AI, คลาวด์) ถ้าไม่มีข่าวเข้าเกณฑ์ให้ส่ง []
   - Global Impact: ข่าวเศรษฐกิจโลกที่มีผลต่อหุ้นสหรัฐฯ ถ้าไม่มีข่าวเข้าเกณฑ์ให้ส่ง []
   - Events vs Highlights: ถ้ามีกำหนดการตัวเลขเศรษฐกิจชัดเจน ให้ has_confirmed_events=true ('📅 ประเด็นที่ต้องติดตาม') ถ้าไม่มี ให้ดึงข่าวสำคัญมารายงานเชิงลึก 1-2 ข่าว ('🔥 ประเด็นสำคัญที่ต้องจับตา')

ตอบกลับเป็น Valid JSON ตาม Schema นี้เท่านั้น:
{
  "market_bias": "เชิงบวก" | "เป็นกลาง" | "เชิงลบ" | "ข้อมูลไม่เพียงพอ",
  "headline_th": "พาดหัวสั้น 1 ประโยคบอกสิ่งที่ข้อมูลสะท้อนจริง",
  "overview_th": "ย่อหน้าวิเคราะห์ภาพรวมตลาด 3-4 ประโยค อธิบายราคา ความต่างของดัชนี และปัจจัยขับเคลื่อน",
  "indicators_interpretation_th": "ข้อความตีความ Yield/ดอลลาร์/น้ำมัน 1-2 ประโยค (หรือ null ถ้าไม่มีนัยสำคัญ)",
  "drivers_th": ["ปัจจัยบวก (ระบุปัจจัย + กลไกส่งผลให้ละเอียด)"],
  "risks_th": ["ปัจจัยกดดัน (ระบุปัจจัย + กลไกส่งผลให้ละเอียด)"],
  "has_confirmed_events": true หรือ false,
  "events_or_highlights": {
    "type": "events" | "highlights",
    "title": "📅 ประเด็นที่ต้องติดตาม" หรือ "🔥 ประเด็นสำคัญที่ต้องจับตา",
    "items": [
      {
        "topic_th": "หัวข้อข่าว/ประเด็น",
        "detail_th": "สรุปเนื้อหาข่าวแบบครบถ้วน อธิบายรายละเอียด ข้อเท็จจริง และผลกระทบต่อตลาด"
      }
    ]
  },
  "big_tech_news": [
    {
      "topic_th": "หัวข้อข่าวบริษัทเทคโนโลยี",
      "detail_th": "สรุปเนื้อหาแบบครบถ้วน ข้อเท็จจริงสำคัญ และผลต่อกลุ่มหุ้นหรืออุตสาหกรรม"
    }
  ],
  "global_news": [
    {
      "topic_th": "หัวข้อข่าวเศรษฐกิจโลก",
      "detail_th": "สรุปเนื้อหาแบบครบถ้วน และกลไกที่ส่งผ่านมากระทบต่อตลาดหุ้นสหรัฐฯ"
    }
  ]
}
"""

    payload = {
        "market_data": market_data,
        "categorized_news": categorized_news
    }

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"ข้อมูลสำหรับวิเคราะห์:\n{json.dumps(payload, ensure_ascii=False)}"}
            ],
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "market_bias": "ข้อมูลไม่เพียงพอ",
            "headline_th": "ไม่สามารถสร้างบทวิเคราะห์ฉบับสมบูรณ์ได้",
            "overview_th": f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)[:100]}",
            "indicators_interpretation_th": None,
            "drivers_th": [],
            "risks_th": [],
            "has_confirmed_events": False,
            "events_or_highlights": {
                "type": "highlights",
                "title": "🔥 ประเด็นสำคัญที่ต้องจับตา",
                "items": []
            },
            "big_tech_news": [],
            "global_news": []
        }