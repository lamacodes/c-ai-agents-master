"""
menu_agent / order_agent 가 사용하는 메뉴 조회 function tool.

LLM 이 메뉴/가격을 지어내지 않도록, 답변에 필요한 정보는 반드시 이 tool 을 통해
menu_data 의 단일 출처에서 가져오게 한다.
"""

from agents import function_tool

# pyrefly: ignore [missing-import]
from menu_data import get_full_menu, find_menu_item


@function_tool
def show_full_menu() -> str:
    """전체 메뉴(메인/사이드/음료)를 가격, 설명, 태그, 알레르기 정보와 함께 반환한다.
    고객이 '메뉴 보여줘', 'what's on the menu' 처럼 전체 메뉴를 물을 때 사용한다."""
    return get_full_menu()


@function_tool
def lookup_menu_item(query: str) -> str:
    """특정 메뉴를 이름(로마자 또는 한글, 예: 'bibimbap' 또는 '비빔밥')으로 검색해
    가격, 설명, 태그, 알레르기 정보를 반환한다. 특정 요리의 재료/가격/알레르기를
    물을 때 사용한다."""
    return find_menu_item(query)
