"""
Comprehensive Test Suite for Thara-AI
Tests 150+ queries in English and Tamil
Generates detailed markdown report
"""

import sys
import io

# Fix Windows encoding for Tamil characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import time
from datetime import datetime
import os

# API_URL = "http://localhost:8000/api/query"  # Local development (commented)
API_URL = "https://asif-mp3-thara-backend-v2.hf.space/api/query"  # Deployed HuggingFace v2

# All test cases organized by category
TEST_CASES = [
    # ==================== DAILY SALES TRANSACTIONS (1-15) ====================
    {"id": 1, "en": "What is the total sale amount across all transactions?", "ta": "அனைத்து transaction-களின் மொத்த sale amount என்ன?", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 2, "en": "Which branch has the highest total sale amount?", "ta": "அதிகமான மொத்த விற்பனை கொண்ட branch எது?", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 3, "en": "How many transactions were made using UPI?", "ta": "UPI மூலம் எத்தனை transactions செய்யப்பட்டுள்ளன?", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 4, "en": "Show total profit amount for each state.", "ta": "ஒவ்வொரு state-க்கும் மொத்த profit amount-ஐ காட்டு.", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 5, "en": "Which category generated the highest profit?", "ta": "அதிக profit உருவாக்கிய category எது?", "category": "Daily Sales", "expected_table": "Category"},
    {"id": 6, "en": "What is the average profit margin percentage?", "ta": "சராசரி profit margin percentage என்ன?", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 7, "en": "List transactions where quantity sold is greater than 10.", "ta": "Quantity 10-க்கு மேல் உள்ள transactions-ஐ காட்டு.", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 8, "en": "What is the total GST collected?", "ta": "மொத்தமாக வசூலிக்கப்பட்ட GST எவ்வளவு?", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 9, "en": "Which SKU has the highest total sales amount?", "ta": "அதிகமான மொத்த விற்பனை கொண்ட SKU எது?", "category": "Daily Sales", "expected_table": "SKU"},
    {"id": 10, "en": "Show sales amount grouped by payment mode.", "ta": "Payment mode அடிப்படையில் sales amount-ஐ காட்டு.", "category": "Daily Sales", "expected_table": "Payment"},
    {"id": 11, "en": "Find the transaction with the highest profit amount.", "ta": "அதிக profit amount கொண்ட transaction எது?", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 12, "en": "What is the total cost amount across all sales?", "ta": "அனைத்து sales-களின் மொத்த cost amount என்ன?", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 13, "en": "Show average unit price by category.", "ta": "Category வாரியாக சராசரி unit price-ஐ காட்டு.", "category": "Daily Sales", "expected_table": "Daily"},
    {"id": 14, "en": "How many unique branches are present?", "ta": "எத்தனை தனித்தனி branches உள்ளன?", "category": "Daily Sales", "expected_table": "Branch"},
    {"id": 15, "en": "Compare total sales between two different states.", "ta": "இரண்டு state-களின் மொத்த sales-ஐ ஒப்பிடு.", "category": "Daily Sales", "expected_table": "State"},

    # ==================== MONTHLY & CATEGORY ANALYSIS (16-30) ====================
    {"id": 16, "en": "What is the total revenue for each month?", "ta": "ஒவ்வொரு மாதத்திற்கும் மொத்த வருமானம் என்ன?", "category": "Monthly Analysis", "expected_table": "Monthly"},
    {"id": 17, "en": "Which month recorded the highest total profit?", "ta": "அதிக profit பெற்ற மாதம் எது?", "category": "Monthly Analysis", "expected_table": "Monthly"},
    {"id": 18, "en": "Show category-wise revenue for each month.", "ta": "ஒவ்வொரு மாதத்திற்கும் category வாரியான revenue-ஐ காட்டு.", "category": "Monthly Analysis", "expected_table": "Monthly_Category"},
    {"id": 19, "en": "Which category has the highest profit margin overall?", "ta": "மொத்தமாக அதிக profit margin கொண்ட category எது?", "category": "Monthly Analysis", "expected_table": "Category"},
    {"id": 20, "en": "What is the total profit for each category?", "ta": "ஒவ்வொரு category-க்கும் மொத்த profit என்ன?", "category": "Monthly Analysis", "expected_table": "Category"},
    {"id": 21, "en": "Compare revenue between two categories.", "ta": "இரண்டு category-களின் revenue-ஐ ஒப்பிடு.", "category": "Monthly Analysis", "expected_table": "Category"},
    {"id": 22, "en": "Which month has the highest number of transactions?", "ta": "அதிக transactions நடந்த மாதம் எது?", "category": "Monthly Analysis", "expected_table": "Monthly"},
    {"id": 23, "en": "Show month-over-month sales growth.", "ta": "மாதம் வாரியாக sales growth-ஐ காட்டு.", "category": "Monthly Analysis", "expected_table": "Monthly_Trend"},
    {"id": 24, "en": "What is the average profit margin per month?", "ta": "ஒவ்வொரு மாதத்திற்கும் சராசரி profit margin என்ன?", "category": "Monthly Analysis", "expected_table": "Monthly_Trend"},
    {"id": 25, "en": "Identify the worst performing category by profit.", "ta": "profit அடிப்படையில் மிகக் குறைந்த category எது?", "category": "Monthly Analysis", "expected_table": "Category"},

    # ==================== BRANCH & STATE PERFORMANCE (31-40) ====================
    {"id": 31, "en": "Which state has the highest total revenue?", "ta": "அதிக மொத்த revenue கொண்ட state எது?", "category": "State Performance", "expected_table": "State"},
    {"id": 32, "en": "Show profit margin by state.", "ta": "State வாரியாக profit margin-ஐ காட்டு.", "category": "State Performance", "expected_table": "State"},
    {"id": 33, "en": "Which branch has the highest profit?", "ta": "அதிக profit கொண்ட branch எது?", "category": "Branch Performance", "expected_table": "Branch"},
    {"id": 34, "en": "Show top 5 branches by revenue.", "ta": "Revenue அடிப்படையில் top 5 branches-ஐ காட்டு.", "category": "Branch Performance", "expected_table": "Branch"},
    {"id": 35, "en": "Compare revenue between two branches.", "ta": "இரண்டு branch-களின் revenue-ஐ ஒப்பிடு.", "category": "Branch Performance", "expected_table": "Branch"},
    {"id": 36, "en": "What is the average profit per branch?", "ta": "ஒவ்வொரு branch-க்கும் சராசரி profit என்ன?", "category": "Branch Performance", "expected_table": "Branch"},
    {"id": 37, "en": "Identify branches with negative profit.", "ta": "நஷ்டம் ஏற்பட்ட branches எவை?", "category": "Branch Performance", "expected_table": "Branch"},
    {"id": 38, "en": "How many branches are there in each state?", "ta": "ஒவ்வொரு state-இல் எத்தனை branches உள்ளன?", "category": "Branch Performance", "expected_table": "Branch"},

    # ==================== PAYMENT, COST & SKU ANALYSIS (41-60) ====================
    {"id": 41, "en": "Which payment mode has the highest transaction count?", "ta": "அதிக transactions கொண்ட payment mode எது?", "category": "Payment Analysis", "expected_table": "Payment"},
    {"id": 42, "en": "Show revenue distribution by payment mode.", "ta": "Payment mode வாரியாக revenue-ஐ காட்டு.", "category": "Payment Analysis", "expected_table": "Payment"},
    {"id": 43, "en": "What is the total cost vs total revenue comparison?", "ta": "மொத்த cost மற்றும் மொத்த revenue ஒப்பீடு என்ன?", "category": "Cost Analysis", "expected_table": "Cost"},
    {"id": 44, "en": "Which month has the highest cost amount?", "ta": "அதிக cost ஏற்பட்ட மாதம் எது?", "category": "Cost Analysis", "expected_table": "Cost"},
    {"id": 45, "en": "Show profit margin trend across quarters.", "ta": "Quarter வாரியாக profit margin trend-ஐ காட்டு.", "category": "Quarterly Analysis", "expected_table": "Quarterly"},
    {"id": 46, "en": "Which quarter generated the highest profit?", "ta": "அதிக profit பெற்ற quarter எது?", "category": "Quarterly Analysis", "expected_table": "Quarterly"},
    {"id": 47, "en": "What is the total profit per quarter?", "ta": "ஒவ்வொரு quarter-க்கும் மொத்த profit என்ன?", "category": "Quarterly Analysis", "expected_table": "Quarterly"},
    {"id": 48, "en": "Which SKU sold the highest number of units?", "ta": "அதிக units விற்கப்பட்ட SKU எது?", "category": "SKU Analysis", "expected_table": "SKU"},
    {"id": 49, "en": "Show top 5 SKUs by total revenue.", "ta": "Revenue அடிப்படையில் top 5 SKU-களை காட்டு.", "category": "SKU Analysis", "expected_table": "SKU"},
    {"id": 50, "en": "Which SKU has the highest profit margin?", "ta": "அதிக profit margin கொண்ட SKU எது?", "category": "SKU Analysis", "expected_table": "SKU"},
    {"id": 51, "en": "Compare revenue and cost for each SKU.", "ta": "ஒவ்வொரு SKU-க்கும் revenue மற்றும் cost-ஐ ஒப்பிடு.", "category": "SKU Analysis", "expected_table": "SKU"},
    {"id": 52, "en": "Identify SKUs that are running at a loss.", "ta": "நஷ்டத்தில் உள்ள SKU-களை கண்டறி.", "category": "SKU Analysis", "expected_table": "SKU"},
    {"id": 53, "en": "What is the average cost per unit across SKUs?", "ta": "அனைத்து SKU-களின் சராசரி cost per unit என்ன?", "category": "SKU Analysis", "expected_table": "SKU"},
    {"id": 54, "en": "Show category-wise SKU profit contribution.", "ta": "Category வாரியாக SKU profit contribution-ஐ காட்டு.", "category": "SKU Analysis", "expected_table": "SKU"},
    {"id": 55, "en": "Which category contributes most to total revenue?", "ta": "மொத்த revenue-க்கு அதிக பங்களிப்பு தரும் category எது?", "category": "Category Analysis", "expected_table": "Category"},
    {"id": 56, "en": "Compare quarterly revenue growth.", "ta": "Quarter வாரியான revenue growth-ஐ ஒப்பிடு.", "category": "Quarterly Analysis", "expected_table": "Quarterly"},
    {"id": 57, "en": "Explain why a particular month has low profit.", "ta": "ஒரு குறிப்பிட்ட மாதத்தில் profit குறைவாக இருப்பதற்கான காரணத்தை விளக்கு.", "category": "Analysis", "expected_table": "Monthly"},
    {"id": 58, "en": "What trends can be observed in sales over time?", "ta": "காலப்போக்கில் sales trend எப்படி உள்ளது?", "category": "Trend Analysis", "expected_table": "Monthly_Trend"},
    {"id": 59, "en": "Which factor affects profit the most: cost or sales?", "ta": "Profit-ஐ அதிகமாக பாதிக்கும் காரணி cost-ஆ அல்லது sales-ஆ?", "category": "Analysis", "expected_table": "Cost"},
    {"id": 60, "en": "Give a high-level business summary of this dataset.", "ta": "இந்த dataset-க்கு ஒரு high-level business summary கொடு.", "category": "Summary", "expected_table": "All"},

    # ==================== GENERIC TREND QUESTIONS (61-70) ====================
    {"id": 61, "en": "Are sales increasing or decreasing in Chennai?", "ta": "சென்னை நகரத்தில் sales உயர்கிறதா குறைகிறதா?", "category": "Trend", "expected_table": "Daily"},
    {"id": 62, "en": "Which state shows a declining sales trend?", "ta": "எந்த state-இல் sales trend குறைந்து வருகிறது?", "category": "Trend", "expected_table": "State"},
    {"id": 63, "en": "Which category shows consistent growth across months?", "ta": "எந்த category மாதம் முழுவதும் நிலையான வளர்ச்சியை காட்டுகிறது?", "category": "Trend", "expected_table": "Category"},
    {"id": 64, "en": "Are profits stable or volatile over time?", "ta": "profit காலப்போக்கில் நிலையானதா அல்லது மாறுபடுகிறதா?", "category": "Trend", "expected_table": "Monthly_Trend"},
    {"id": 65, "en": "Which month had an unusual spike in sales?", "ta": "எந்த மாதத்தில் sales திடீரென அதிகரித்தது?", "category": "Trend", "expected_table": "Monthly"},
    {"id": 66, "en": "Is revenue seasonally higher in certain months?", "ta": "சில மாதங்களில் revenue அதிகமாக இருக்கிறதா?", "category": "Trend", "expected_table": "Monthly"},
    {"id": 67, "en": "Which branch shows declining performance?", "ta": "எந்த branch செயல்திறன் குறைந்து வருகிறது?", "category": "Trend", "expected_table": "Branch"},
    {"id": 68, "en": "Which category is losing revenue month by month?", "ta": "எந்த category மாதம் மாதமாக revenue இழக்கிறது?", "category": "Trend", "expected_table": "Category"},
    {"id": 69, "en": "Are costs rising faster than revenue?", "ta": "revenue-விட cost வேகமாக உயருகிறதா?", "category": "Trend", "expected_table": "Cost"},
    {"id": 70, "en": "Which quarter performed the worst overall?", "ta": "மொத்தமாக எந்த quarter மோசமாக செயல்பட்டது?", "category": "Trend", "expected_table": "Quarterly"},

    # ==================== PROJECTION CHAINS (71-80) ====================
    {"id": 71, "en": "Compare total sales between November and December.", "ta": "நவம்பர் மற்றும் டிசம்பர் மாத sales-ஐ ஒப்பிடு.", "category": "Projection Chain 1", "expected_table": "Monthly"},
    {"id": 72, "en": "If the same trend continues, what could be the projected sales for January?", "ta": "அதே trend தொடர்ந்தால் ஜனவரிக்கான projected sales என்ன?", "category": "Projection Chain 1", "expected_table": "Monthly"},
    {"id": 73, "en": "Show sales trend for Chennai across months.", "ta": "சென்னை நகரத்தின் மாத sales trend-ஐ காட்டு.", "category": "Projection Chain 2", "expected_table": "Daily"},
    {"id": 74, "en": "Based on this trend, estimate next month's sales.", "ta": "இந்த trend அடிப்படையில் அடுத்த மாத sales-ஐ மதிப்பிடு.", "category": "Projection Chain 2", "expected_table": "Daily"},
    {"id": 75, "en": "Show category-wise sales for the last three months.", "ta": "கடந்த மூன்று மாதங்களுக்கான category வாரியான sales-ஐ காட்டு.", "category": "Projection Chain 3", "expected_table": "Category"},
    {"id": 76, "en": "If the top category continues this pattern, what is the expected sales next month?", "ta": "முன்னணி category இதே pattern தொடர்ந்தால் அடுத்த மாத sales என்ன?", "category": "Projection Chain 3", "expected_table": "Category"},
    {"id": 77, "en": "Compare revenue for a branch between two consecutive months.", "ta": "ஒரு branch-ன் தொடர்ச்சியான இரண்டு மாத revenue-ஐ ஒப்பிடு.", "category": "Projection Chain 4", "expected_table": "Branch"},
    {"id": 78, "en": "Project the next month's revenue assuming similar change.", "ta": "அதே மாற்றம் தொடர்ந்தால் அடுத்த மாத revenue-ஐ கணிக்கவும்.", "category": "Projection Chain 4", "expected_table": "Branch"},
    {"id": 79, "en": "Show last 3 months sales for a SKU.", "ta": "ஒரு SKU-க்கு கடந்த 3 மாத sales-ஐ காட்டு.", "category": "Projection Chain 5", "expected_table": "SKU"},
    {"id": 80, "en": "If this trend continues, what could be the sales next month?", "ta": "இந்த trend தொடர்ந்தால் அடுத்த மாத sales என்ன?", "category": "Projection Chain 5", "expected_table": "SKU"},

    # ==================== FOLLOW-UP CHAINS (81-90) ====================
    {"id": 81, "en": "What is the total sales in Tamil Nadu?", "ta": "தமிழ்நாட்டில் மொத்த sales என்ன?", "category": "Follow-up Chain 1", "expected_table": "State"},
    {"id": 82, "en": "Is it higher or lower compared to Karnataka?", "ta": "கர்நாடகாவுடன் ஒப்பிடும்போது இது அதிகமா குறைவா?", "category": "Follow-up Chain 1", "expected_table": "State"},
    {"id": 83, "en": "Which category has the highest total sales?", "ta": "அதிக மொத்த sales கொண்ட category எது?", "category": "Follow-up Chain 2", "expected_table": "Category"},
    {"id": 84, "en": "Did sales for this category increase or decrease over time?", "ta": "இந்த category-க்கு sales காலப்போக்கில் அதிகரித்ததா குறைந்ததா?", "category": "Follow-up Chain 2", "expected_table": "Category"},
    {"id": 85, "en": "Which branch has the highest revenue overall?", "ta": "மொத்தமாக அதிக revenue கொண்ட branch எது?", "category": "Follow-up Chain 3", "expected_table": "Branch"},
    {"id": 86, "en": "Is this branch performing better or worse than the average branch?", "ta": "இந்த branch மற்ற branch-களின் சராசரியை விட சிறப்பாக செயல்படுகிறதா அல்லது இல்லை?", "category": "Follow-up Chain 3", "expected_table": "Branch"},
    {"id": 87, "en": "Which payment mode has the highest sales amount?", "ta": "அதிக sales amount கொண்ட payment mode எது?", "category": "Follow-up Chain 4", "expected_table": "Payment"},
    {"id": 88, "en": "Has the usage of this payment mode increased over the months?", "ta": "இந்த payment mode பயன்பாடு மாதங்களாக உயர்ந்ததா?", "category": "Follow-up Chain 4", "expected_table": "Payment"},
    {"id": 89, "en": "Which SKU has the highest total revenue?", "ta": "அதிக மொத்த revenue கொண்ட SKU எது?", "category": "Follow-up Chain 5", "expected_table": "SKU"},
    {"id": 90, "en": "Is this SKU's sales trend consistently increasing?", "ta": "இந்த SKU-ன் sales trend தொடர்ந்து உயருகிறதா?", "category": "Follow-up Chain 5", "expected_table": "SKU"},

    # ==================== TWISTY/ADVANCED ANALYTICS (91-95) ====================
    {"id": 91, "en": "Which state moved from being a top 3 revenue contributor in the early months to a bottom 3 contributor in the later months?", "ta": "ஆரம்ப மாதங்களில் top 3 revenue contributor ஆக இருந்தாலும், பின்னர் மாதங்களில் bottom 3 ஆக மாறிய state எது?", "category": "Advanced", "expected_table": "State"},
    {"id": 92, "en": "Is there any category that ranks high in total sales amount but low in total profit amount?", "ta": "மொத்த sales amount அதிகமாக இருந்தாலும், மொத்த profit குறைவாக உள்ள category ஏதேனும் உள்ளதா?", "category": "Advanced", "expected_table": "Category"},
    {"id": 93, "en": "Are there branches where more than 50% of total sales come from a single payment mode?", "ta": "ஒரே payment mode மூலம் 50%-க்கு மேல் sales வரும் branches ஏதேனும் உள்ளதா?", "category": "Advanced", "expected_table": "Branch"},
    {"id": 94, "en": "Among the top 5 SKUs by revenue, which SKU has the highest cost relative to its revenue?", "ta": "Revenue அடிப்படையில் top 5 SKU-களில், revenue-க்கு ஒப்பிடும்போது அதிக cost கொண்ட SKU எது?", "category": "Advanced", "expected_table": "SKU"},
    {"id": 95, "en": "Is there any month where sales increased compared to the previous month, but profit decreased?", "ta": "முந்தைய மாதத்துடன் ஒப்பிடும்போது sales உயர்ந்தாலும், profit குறைந்த மாதம் ஏதேனும் உள்ளதா?", "category": "Advanced", "expected_table": "Monthly"},

    # ==================== EDGE CASES & ERROR HANDLING (96-105) ====================
    {"id": 96, "en": "Show me XYZ department", "ta": None, "category": "Edge Case", "expected_table": None, "expect_error": True},
    {"id": 97, "en": "Sales in Mars", "ta": None, "category": "Edge Case", "expected_table": None, "expect_error": True},
    {"id": 98, "en": "Dhoti sales in January", "ta": None, "category": "Edge Case", "expected_table": "Daily", "expect_error": False},
    {"id": 99, "en": "abcdefg", "ta": None, "category": "Edge Case", "expected_table": None, "expect_error": True},
    {"id": 100, "en": "Show me nothing", "ta": None, "category": "Edge Case", "expected_table": None, "expect_error": True},
    {"id": 101, "en": "What is the sales of product ABC123?", "ta": None, "category": "Edge Case", "expected_table": "SKU", "expect_error": False},
    {"id": 102, "en": "Revenue for branch Timbuktu", "ta": None, "category": "Edge Case", "expected_table": None, "expect_error": True},
    {"id": 103, "en": "Employee named Superman", "ta": None, "category": "Edge Case", "expected_table": None, "expect_error": True},
    {"id": 104, "en": "Attendance for February 2020", "ta": None, "category": "Edge Case", "expected_table": None, "expect_error": True},
    {"id": 105, "en": "Hello, how are you?", "ta": "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?", "category": "Greeting", "expected_table": None, "is_greeting": True},
]


def query_api(text, session_id="test_session"):
    """Send query to API and return response with timing"""
    start_time = time.time()
    try:
        response = requests.post(
            API_URL,
            json={"text": text, "session_id": session_id},
            timeout=120
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "data": data,
                "time": elapsed,
                "status_code": response.status_code
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "time": elapsed,
                "status_code": response.status_code
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out (>120s)",
            "time": 120,
            "status_code": None
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "error": str(e),
            "time": elapsed,
            "status_code": None
        }


def evaluate_response(test_case, response):
    """Evaluate if the response is acceptable"""
    if not response["success"]:
        if test_case.get("expect_error"):
            return "PASS", "Expected error/empty response"
        return "FAIL", f"API Error: {response.get('error', 'Unknown')}"

    data = response["data"]

    # Check for greeting
    if test_case.get("is_greeting"):
        if data.get("explanation") and len(data.get("explanation", "")) > 10:
            return "PASS", "Greeting response received"
        return "FAIL", "No greeting response"

    # Check for error in response
    if data.get("error"):
        if test_case.get("expect_error"):
            return "PASS", "Expected error received"
        return "FAIL", f"Response error: {data.get('error')}"

    # Check for explanation text
    explanation = data.get("explanation", "") or data.get("text", "")
    if not explanation or explanation.strip() == "":
        if test_case.get("expect_error"):
            return "PASS", "Expected empty response"
        return "FAIL", "No explanation provided"

    # Check for data
    result_data = data.get("data", [])
    row_count = len(result_data) if result_data else 0

    # For edge cases expecting errors
    if test_case.get("expect_error"):
        # If we got a valid response for an error case, that's actually OK
        # as long as the system handled it gracefully
        if row_count == 0 and ("sorry" in explanation.lower() or "couldn't" in explanation.lower() or "no data" in explanation.lower()):
            return "PASS", "Gracefully handled invalid query"
        elif row_count > 0:
            return "WARN", f"Got {row_count} rows for edge case"

    # Normal query evaluation
    if row_count == 0 and not test_case.get("expect_error"):
        # Some queries might legitimately return 0 rows
        if "no data" in explanation.lower() or "couldn't find" in explanation.lower():
            return "WARN", "No data found"
        return "WARN", "Empty result set"

    return "PASS", f"{row_count} rows returned"


def run_tests():
    """Run all test cases and collect results"""
    results = []
    total_tests = len(TEST_CASES) * 2  # EN + TA for most

    print("=" * 70)
    print("THARA-AI COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"Total test cases: {len(TEST_CASES)}")
    print(f"Testing against: {API_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Test English queries
    print("\n[PHASE 1] Testing English Queries...")
    print("-" * 50)

    for i, test in enumerate(TEST_CASES):
        print(f"[{i+1:3}/{len(TEST_CASES)}] {test['en'][:50]}...", end=" ", flush=True)

        response = query_api(test["en"], f"test_en_{test['id']}")
        status, reason = evaluate_response(test, response)

        result = {
            "id": test["id"],
            "category": test["category"],
            "language": "EN",
            "query": test["en"],
            "status": status,
            "reason": reason,
            "time": response["time"],
            "explanation": ((response.get("data") or {}).get("explanation") or "")[:500] if response["success"] else response.get("error", ""),
            "row_count": len((response.get("data") or {}).get("data") or []) if response["success"] else 0,
            "table_used": ((response.get("data") or {}).get("plan") or {}).get("table", "") if response["success"] else "",
            "query_type": ((response.get("data") or {}).get("plan") or {}).get("query_type", "") if response["success"] else ""
        }
        results.append(result)

        status_icon = "OK" if status == "PASS" else ("WARN" if status == "WARN" else "FAIL")
        print(f"{status_icon} ({result['time']:.1f}s)")

    # Test Tamil queries
    print("\n[PHASE 2] Testing Tamil Queries...")
    print("-" * 50)

    tamil_tests = [t for t in TEST_CASES if t.get("ta")]
    for i, test in enumerate(tamil_tests):
        # Use ASCII-safe label with Tamil text sent to API
        print(f"[{i+1:3}/{len(tamil_tests)}] TA#{test['id']}...", end=" ", flush=True)

        response = query_api(test["ta"], f"test_ta_{test['id']}")
        status, reason = evaluate_response(test, response)

        result = {
            "id": test["id"],
            "category": test["category"],
            "language": "TA",
            "query": test["ta"],
            "status": status,
            "reason": reason,
            "time": response["time"],
            "explanation": ((response.get("data") or {}).get("explanation") or "")[:500] if response["success"] else response.get("error", ""),
            "row_count": len((response.get("data") or {}).get("data") or []) if response["success"] else 0,
            "table_used": ((response.get("data") or {}).get("plan") or {}).get("table", "") if response["success"] else "",
            "query_type": ((response.get("data") or {}).get("plan") or {}).get("query_type", "") if response["success"] else ""
        }
        results.append(result)

        status_icon = "OK" if status == "PASS" else ("WARN" if status == "WARN" else "FAIL")
        print(f"{status_icon} ({result['time']:.1f}s)")

    return results


def generate_markdown_report(results):
    """Generate detailed markdown report"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Calculate statistics
    total = len(results)
    passed = len([r for r in results if r["status"] == "PASS"])
    warned = len([r for r in results if r["status"] == "WARN"])
    failed = len([r for r in results if r["status"] == "FAIL"])

    en_results = [r for r in results if r["language"] == "EN"]
    ta_results = [r for r in results if r["language"] == "TA"]

    en_passed = len([r for r in en_results if r["status"] == "PASS"])
    ta_passed = len([r for r in ta_results if r["status"] == "PASS"])

    avg_time = sum(r["time"] for r in results) / len(results) if results else 0

    # Group by category
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    report = f"""# Thara-AI Comprehensive Test Report

**Generated:** {timestamp}
**API Endpoint:** {API_URL}
**Total Tests:** {total}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {total} |
| **Passed** | {passed} ({passed*100/total:.1f}%) |
| **Warnings** | {warned} ({warned*100/total:.1f}%) |
| **Failed** | {failed} ({failed*100/total:.1f}%) |
| **Avg Response Time** | {avg_time:.2f}s |

### By Language

| Language | Total | Passed | Pass Rate |
|----------|-------|--------|-----------|
| English | {len(en_results)} | {en_passed} | {en_passed*100/len(en_results):.1f}% |
| Tamil | {len(ta_results)} | {ta_passed} | {ta_passed*100/len(ta_results):.1f}% |

---

## Results by Category

"""

    for cat, cat_results in sorted(categories.items()):
        cat_passed = len([r for r in cat_results if r["status"] == "PASS"])
        cat_total = len(cat_results)

        report += f"""### {cat}

**Pass Rate:** {cat_passed}/{cat_total} ({cat_passed*100/cat_total:.1f}%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
"""
        for r in cat_results:
            query_short = r["query"][:40] + "..." if len(r["query"]) > 40 else r["query"]
            query_short = query_short.replace("|", "\\|").replace("\n", " ")

            explanation_short = r["explanation"][:80] + "..." if len(r["explanation"]) > 80 else r["explanation"]
            explanation_short = explanation_short.replace("|", "\\|").replace("\n", " ")

            status_emoji = "PASS" if r["status"] == "PASS" else ("WARN" if r["status"] == "WARN" else "FAIL")

            table_short = r["table_used"][-30:] if len(r["table_used"]) > 30 else r["table_used"]

            report += f"| {r['id']} | {r['language']} | {query_short} | {status_emoji} | {r['time']:.1f}s | {r['row_count']} | {table_short} | {explanation_short} |\n"

        report += "\n"

    # Detailed Results Section
    report += """---

## Detailed Test Results

"""

    for r in results:
        status_emoji = "PASS" if r["status"] == "PASS" else ("WARN" if r["status"] == "WARN" else "FAIL")

        report += f"""### Test #{r['id']} ({r['language']}) - {status_emoji}

**Category:** {r['category']}
**Query:** {r['query']}
**Time:** {r['time']:.2f}s
**Rows:** {r['row_count']}
**Table Used:** {r['table_used']}
**Query Type:** {r['query_type']}

**Response:**
> {r['explanation'][:500]}{"..." if len(r['explanation']) > 500 else ""}

---

"""

    # Failed Tests Section
    failed_tests = [r for r in results if r["status"] == "FAIL"]
    if failed_tests:
        report += """## Failed Tests Summary

| ID | Lang | Query | Reason |
|----|------|-------|--------|
"""
        for r in failed_tests:
            query_short = r["query"][:50] + "..." if len(r["query"]) > 50 else r["query"]
            query_short = query_short.replace("|", "\\|")
            report += f"| {r['id']} | {r['language']} | {query_short} | {r['reason']} |\n"

    return report


def main():
    print("\n" + "=" * 70)
    print("Starting Comprehensive Test Suite...")
    print("=" * 70 + "\n")

    # Run tests
    results = run_tests()

    # Generate report
    print("\n" + "=" * 70)
    print("Generating Markdown Report...")
    print("=" * 70)

    report = generate_markdown_report(results)

    # Save report
    report_path = os.path.join(os.path.dirname(__file__), "..", "TEST_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved to: {report_path}")

    # Also save JSON results
    json_path = os.path.join(os.path.dirname(__file__), "..", "test_results_full.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"JSON results saved to: {json_path}")

    # Print summary
    total = len(results)
    passed = len([r for r in results if r["status"] == "PASS"])
    warned = len([r for r in results if r["status"] == "WARN"])
    failed = len([r for r in results if r["status"] == "FAIL"])

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests:  {total}")
    print(f"Passed:       {passed} ({passed*100/total:.1f}%)")
    print(f"Warnings:     {warned} ({warned*100/total:.1f}%)")
    print(f"Failed:       {failed} ({failed*100/total:.1f}%)")
    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
