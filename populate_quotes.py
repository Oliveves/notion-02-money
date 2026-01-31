import os
import json
import time
import sys
import urllib.request
import urllib.error

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

QUOTES = [
    "규칙 1: 절대로 돈을 잃지 마라. 규칙 2: 규칙 1을 절대 잊지 마라. - 워렌 버핏",
    "시장은 당신이 부를 유지할 수 있는 것보다 더 오랫동안 비이성적일 수 있다. - 존 메이너드 케인스",
    "가장 큰 위험은 위험을 감수하지 않는 것이다. - 마크 저커버그",
    "투자란 철저한 분석을 통해 원금의 안전과 적절한 수익을 보장하는 행위다. - 벤저민 그레이엄",
    "가격은 당신이 지불하는 것이고, 가치는 당신이 얻는 것이다. - 워렌 버핏",
    "남들이 욕심을 부릴 때 두려워하고, 남들이 두려워할 때 욕심을 부려라. - 워렌 버핏",
    "단기적으로 시장은 투표기계지만, 장기적으로는 체중계다. - 벤저민 그레이엄",
    "손절매는 트레이더의 생명 보험이다. - 제시 리버모어",
    "시장을 이기려 하지 마라. 시장은 항상 옳다. - 에드 세이코타",
    "추세는 당신의 친구다. (The trend is your friend.)",
    "소문에 사서 뉴스에 팔아라.",
    "달걀을 한 바구니에 담지 마라.",
    "무릎에서 사서 어깨에서 팔아라.",
    "자신이 무엇을 하고 있는지 모르는 것이 위험이다. - 워렌 버핏",
    "인내심 없는 사람의 돈은 인내심 있는 사람에게로 흘러간다. - 워렌 버핏",
    "10년 이상 보유할 주식이 아니라면 단 10분도 보유하지 마라. - 워렌 버핏",
    "성공적인 투자는 지능지수(IQ)가 아니라 기질(Temperament)에 달려있다.",
    "비관론자는 명성을 얻고, 낙관론자는 부를 얻는다.",
    "떨어지는 칼날을 잡지 마라.",
    "확신이 서지 않을 때는 아무것도 하지 마라. - 제시 리버모어",
    "수익을 내는 것보다 손실을 줄이는 것이 더 중요하다. - 폴 튜더 존스",
    "기회는 준비된 자에게 찾아온다.",
    "가난하게 태어난 것은 당신의 잘못이 아니지만, 가난하게 죽는 것은 당신의 잘못이다. - 빌 게이츠",
    "복리는 세계 8대 불가사의다. - 알베르트 아인슈타인",
    "현금도 하나의 종목이다.",
    "매수해야 할 이유는 하나지만, 매도해야 할 이유는 수십 가지다.",
    "주식시장은 적극적인 자에게서 참을성 있는 자에게로 돈이 넘어가도록 설계되어 있다. - 워렌 버핏",
    "훌륭한 기업을 적당한 가격에 사는 것이, 평범한 기업을 싼 가격에 사는 것보다 낫다. - 워렌 버핏",
    "위험은 자신이 무엇을 하는지 모르는 데서 온다. - 워렌 버핏",
    "투자는 160의 아이큐가 130의 아이큐를 이기는 게임이 아니다. - 워렌 버핏",
    "절대로 빚내서 투자하지 마라.",
    "모두가 주식 이야기를 하면 고점이고, 아무도 주식 이야기를 하지 않으면 저점이다.",
    "쉬는 것도 투자다.",
    "급등주는 급락할 확률이 높다.",
    "자신의 판단을 믿어라. 남의 말을 듣고 투자하면 남 탓만 하게 된다.",
    "기록하지 않는 매매는 도박이다.",
    "목표 수익률과 손절가를 미리 정하고 진입해라.",
    "평균으로의 회귀를 잊지 마라.",
    "공포에 사서 환희에 팔아라.",
    "재무제표를 읽을 수 없다면 주식에 투자하지 마라.",
    "시장의 타이밍을 맞추려 하지 말고, 시장에 머물러라.",
    "작은 수익에 만족하라. 티끌 모아 태산이다.",
    "손실을 인정하는 법을 배워라. 그래야 다음 기회가 있다.",
    "자신만의 투자 원칙을 세우고 반드시 지켜라.",
    "감정에 휘둘리면 필패한다. 기계처럼 매매하라.",
    "분산 투자는 무지(Ignorance)를 보호하는 수단이다. - 워렌 버핏",
    "가장 좋은 투자 대상은 바로 당신 자신이다. - 워렌 버핏",
    "뉴스를 보지 마라. 가격을 봐라.",
    "진정한 트레이더는 시세판을 보며 희로애락을 느끼지 않는다.",
    "내일의 시장은 아무도 모른다. 대응만이 살 길이다."
]

def create_page(token, db_id, content):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Payload: Title + Body Paragraph
    # We add content to both Title (for easier view in DB) and Body (for script compatibility)
    # Actually, script looks at Body first, then Title.
    # Title has length limit. Paragraph works better for long quotes.
    # But usually keeping Title is good for 'Name' column.
    
    # Truncate title if too long, put full text in body
    title_text = content
    if len(title_text) > 80:
        title_text = content[:77] + "..."
        
    payload = {
        "parent": { "database_id": db_id },
        "properties": {
            # Assuming default title property is "Name" or "이름" or "제목"
            # We can try "Name" first, creating pages usually defaults to "Name" or "title" key if specific schema used.
            # But safer to specify the property key if known.
            # However, create endpoint allows omitting property key if we specify valid Title property object... 
            # actually we need the key.
            # Let's guess "이름", "Name", "제목", "Title" mapping
            # Or simplified: Most simple databases have "Name" as key.
            # If failed, we will catch error.
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{ "text": { "content": content } }]
                }
            }
        ]
    }
    
    payload["properties"]["이름"] = {
        "title": [
            {
                "text": { "content": title_text }
            }
        ]
    }

    data_json = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_json, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"Success.")
                return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"Failed to create page. Status: {e.code}, Reason: {e.reason}, Body: {err_body}")
        
    except Exception as e:
        print(f"Error: {e}")
        
    return False

def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set.")
        sys.exit(1)
        
    db_id = "2f90d907-031e-80b6-a49b-d2b34e29359d"
    
    print(f"Inserting {len(QUOTES)} quotes via Notion API...")
    
    success_count = 0
    for i, quote in enumerate(QUOTES):
        # Progress
        print(f"[{i+1}/{len(QUOTES)}] Adding: {quote[:20]}...")
        if create_page(token, db_id, quote):
            success_count += 1
        
        # Rate limit friendly sleep
        time.sleep(0.4) 
        
    print(f"Finished. Successfully added {success_count} entries.")

if __name__ == "__main__":
    main()
