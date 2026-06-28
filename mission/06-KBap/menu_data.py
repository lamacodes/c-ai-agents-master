"""
K-Bap 메뉴 데이터.

외국인 여행객 대상 한식 다이닝. 음식명은 로마자(한글) 병기.
가격 단위: KRW(원). 알레르기/식이 정보 포함.

이 데이터는 menu_agent / order_agent 가 function tool 을 통해 조회한다.
LLM 이 메뉴를 지어내지 않도록(환각 방지) 단일 출처로 사용한다.
"""

# category: main / side / drink
MENU = [
    # ----- Mains -----
    {
        "id": "bibimbap",
        "name_en": "Bibimbap",
        "name_ko": "돌솥비빔밥",
        "category": "main",
        "price": 14000,
        "description": "Sizzling stone-pot rice with seasonal vegetables and gochujang.",
        "tags": ["vegetarian-option", "spicy-adjustable"],
        "allergens": ["egg", "soy", "sesame"],
        "tip": "Mix everything well with the gochujang before eating.",
    },
    {
        "id": "bulgogi",
        "name_en": "Bulgogi",
        "name_ko": "불고기",
        "category": "main",
        "price": 24000,
        "description": "Thin slices of Korean beef marinated in sweet soy sauce.",
        "tags": ["popular"],
        "allergens": ["soy", "gluten", "sesame"],
        "tip": "Wrap a piece in lettuce with rice and ssamjang for the full experience.",
    },
    {
        "id": "kimchi_jjigae",
        "name_en": "Kimchi-jjigae",
        "name_ko": "김치찌개",
        "category": "main",
        "price": 13000,
        "description": "Hearty stew of aged kimchi and pork, served bubbling hot.",
        "tags": ["spicy"],
        "allergens": ["pork", "soy"],
        "tip": "Spoon the broth over rice — that's how locals enjoy it.",
    },
    {
        "id": "galbijjim",
        "name_en": "Galbi-jjim",
        "name_ko": "갈비찜",
        "category": "main",
        "price": 32000,
        "description": "Braised Korean beef short ribs with jujube and chestnut.",
        "tags": ["premium", "signature"],
        "allergens": ["soy", "gluten", "sesame"],
        "tip": "Our most premium dish — tender enough to fall off the bone.",
    },
    # ----- Sides -----
    {
        "id": "kimchi_platter",
        "name_en": "Kimchi Platter",
        "name_ko": "모둠김치",
        "category": "side",
        "price": 6000,
        "description": "Assortment of napa cabbage kimchi and radish kkakdugi.",
        "tags": ["vegan", "spicy"],
        "allergens": ["seafood"],
        "tip": "Fermented and probiotic — a Korean staple at every meal.",
    },
    {
        "id": "japchae",
        "name_en": "Japchae",
        "name_ko": "잡채",
        "category": "side",
        "price": 11000,
        "description": "Stir-fried glass noodles with vegetables and beef.",
        "tags": ["gluten-free", "vegetarian-option"],
        "allergens": ["soy", "sesame"],
        "tip": "Can be made without beef on request for a vegetarian version.",
    },
    # ----- Drinks -----
    {
        "id": "makgeolli",
        "name_en": "Makgeolli",
        "name_ko": "막걸리",
        "category": "drink",
        "price": 9000,
        "description": "Traditional unfiltered rice wine, lightly sparkling and milky.",
        "tags": ["alcoholic"],
        "allergens": ["gluten"],
        "tip": "Stir gently before pouring. Pairs wonderfully with kimchi-jjigae.",
    },
    {
        "id": "sikhye",
        "name_en": "Sikhye",
        "name_ko": "식혜",
        "category": "drink",
        "price": 5000,
        "description": "Sweet traditional rice punch, served chilled.",
        "tags": ["non-alcoholic", "vegan"],
        "allergens": [],
        "tip": "A refreshing sweet finish to your meal.",
    },
    {
        "id": "sujeonggwa",
        "name_en": "Sujeonggwa",
        "name_ko": "수정과",
        "category": "drink",
        "price": 5000,
        "description": "Spiced cinnamon and ginger punch with dried persimmon.",
        "tags": ["non-alcoholic", "vegan"],
        "allergens": [],
        "tip": "Naturally caffeine-free and warming.",
    },
    {
        "id": "yuja_tea",
        "name_en": "Yuja Tea",
        "name_ko": "유자차",
        "category": "drink",
        "price": 6000,
        "description": "Warm citron tea, sweet and fragrant.",
        "tags": ["non-alcoholic", "vegan"],
        "allergens": [],
        "tip": "Rich in vitamin C — soothing on a cold day.",
    },
]

CATEGORY_LABELS = {
    "main": "메인 (Mains)",
    "side": "사이드 (Sides)",
    "drink": "음료 (Drinks)",
}

# 재료/알레르기 한글 라벨 — '한글(영어)' 표기를 위해 사용
ALLERGEN_KO = {
    "egg": "계란",
    "soy": "대두",
    "sesame": "참깨",
    "gluten": "글루텐",
    "pork": "돼지고기",
    "seafood": "해산물",
}

# 식이/특징 태그 한글 라벨
TAG_KO = {
    "vegetarian-option": "채식 가능",
    "spicy-adjustable": "맵기 조절 가능",
    "spicy": "매움",
    "popular": "인기",
    "premium": "프리미엄",
    "signature": "시그니처",
    "vegan": "비건",
    "gluten-free": "글루텐프리",
    "alcoholic": "주류",
    "non-alcoholic": "무알코올",
}


def _bilingual(value, mapping):
    """'한글(영어)' 형태로 표기. 매핑에 없으면 영어만."""
    ko = mapping.get(value)
    return f"{ko} ({value})" if ko else value


def _format_item(item):
    """메뉴 1개를 사람이 읽기 좋은 한 줄로 변환. ('한글(영어)' 표기)"""
    price = f"₩{item['price']:,}"
    name = f"{item['name_ko']} ({item['name_en']})"
    line = f"- {name} — {price}: {item['description']}"
    if item["tags"]:
        tags = ", ".join(_bilingual(t, TAG_KO) for t in item["tags"])
        line += f" [태그: {tags}]"
    if item["allergens"]:
        allergens = ", ".join(_bilingual(a, ALLERGEN_KO) for a in item["allergens"])
        line += f" [알레르기: {allergens}]"
    return line


def get_full_menu() -> str:
    """전체 메뉴를 카테고리별로 정리한 문자열로 반환."""
    blocks = []
    for category, label in CATEGORY_LABELS.items():
        items = [i for i in MENU if i["category"] == category]
        if not items:
            continue
        lines = "\n".join(_format_item(i) for i in items)
        blocks.append(f"## {label}\n{lines}")
    return "\n\n".join(blocks)


def find_menu_item(query: str) -> str:
    """이름(로마자/한글)에 query 가 포함된 메뉴 항목들을 반환. 없으면 안내."""
    q = query.strip().lower()
    matches = [
        i
        for i in MENU
        if q in i["name_en"].lower()
        or q in i["name_ko"].lower()
        or q in i["id"].lower()
    ]
    if not matches:
        return f"No menu item matched '{query}'. Use the full menu to see available dishes."
    return "\n".join(_format_item(i) for i in matches)
