# Thara-ai Production Testing Checklist

> **Version:** 2.0
> **Last Updated:** January 2025
> **Purpose:** Real-world QA testing for production deployment

---

## Quick Navigation

- [Latency Tests](#1-latency-performance-tests)
- [Accuracy Tests](#2-accuracy-tests)
- [Fuzzy Matching Tests](#3-fuzzy-matching--natural-language-tests)
- [Voice Quality Tests](#4-voice-quality-tests)
- [Compatibility Tests](#5-compatibility-tests)
- [Edge Case Tests](#6-edge-case-tests)
- [End-to-End Scenarios](#7-end-to-end-user-scenarios)

---

## 1. Latency / Performance Tests

### Voice Input Latency

| Test | Target | Actual | Pass/Fail |
|------|--------|--------|-----------|
| Mic button response (click to recording) | < 500ms | | [ ] |
| VAD silence detection | 1000ms ± 200ms | | [ ] |
| Recording stop to processing start | < 200ms | | [ ] |
| Audio transcription (5 sec clip) | < 3s | | [ ] |
| Audio transcription (10 sec clip) | < 5s | | [ ] |

### Query Processing Latency

| Test | Target | Actual | Pass/Fail |
|------|--------|--------|-----------|
| Simple query ("total sales") | < 3s | | [ ] |
| Medium query ("top 5 by revenue") | < 5s | | [ ] |
| Complex query ("compare X vs Y") | < 8s | | [ ] |
| Aggregation query ("average profit margin") | < 5s | | [ ] |
| Filter query ("sales above 1000") | < 4s | | [ ] |

### TTS Latency

| Test | Target | Actual | Pass/Fail |
|------|--------|--------|-----------|
| First word playback (short response) | < 1.5s | | [ ] |
| First word playback (long response) | < 2.5s | | [ ] |
| Cache hit playback | < 200ms | | [ ] |
| Tamil TTS first word | < 2s | | [ ] |

### End-to-End Latency

| Test | Target | Actual | Pass/Fail |
|------|--------|--------|-----------|
| Voice question → Voice answer start | < 6s | | [ ] |
| Text question → Text answer | < 4s | | [ ] |
| Voice question → Text + Voice answer | < 8s | | [ ] |

---

## 2. Accuracy Tests

### SQL Generation Accuracy

| Query | Expected SQL Pattern | Correct? |
|-------|---------------------|----------|
| "total sales" | `SUM(Sale_Amount)` or `SUM(Total_Revenue)` | [ ] |
| "total revenue" | `SUM(Total_Revenue)` | [ ] |
| "average order value" | `AVG(...)` | [ ] |
| "count of orders" | `COUNT(*)` | [ ] |
| "top 5 products" | `ORDER BY ... DESC LIMIT 5` | [ ] |
| "bottom 3 branches" | `ORDER BY ... ASC LIMIT 3` | [ ] |
| "sales in November" | `WHERE ... November` or month filter | [ ] |
| "compare categories" | `GROUP BY Category` | [ ] |

### Numeric Accuracy

| Query | Expected Answer | Actual | Match? |
|-------|-----------------|--------|--------|
| "total revenue" | Check against Excel | | [ ] |
| "number of employees" | 120 | | [ ] |
| "number of branches" | 95 | | [ ] |
| "total transactions" | ~12,135 | | [ ] |

### Table Selection Accuracy

| Query | Should Use Table | Actually Used | Correct? |
|-------|------------------|---------------|----------|
| "daily sales" | Daily_Sales_Transactions | | [ ] |
| "monthly summary" | Monthly_Overall_Summary | | [ ] |
| "branch performance" | Branch_Details or Top_20_Branches | | [ ] |
| "employee attendance" | Attendance_Records | | [ ] |
| "payroll info" | Payroll_Summary | | [ ] |
| "department summary" | Department_Summary | | [ ] |

### Response Quality

| Aspect | Test Query | Quality (1-5) | Notes |
|--------|-----------|---------------|-------|
| Clarity | "explain total sales" | | |
| Conciseness | "quick summary" | | |
| Tamil response | "மொத்த விற்பனை" | | |
| Numbers formatting | "show revenue" | | |
| Table formatting | "list all branches" | | |

---

## 3. Fuzzy Matching / Natural Language Tests

### Synonym Recognition

| User Says | Should Match | Works? |
|-----------|--------------|--------|
| "money made" | revenue/sales | [ ] |
| "earnings" | revenue/profit | [ ] |
| "income" | revenue | [ ] |
| "workers" | employees | [ ] |
| "staff" | employees | [ ] |
| "shops" | branches | [ ] |
| "stores" | branches | [ ] |
| "items" | products/SKUs | [ ] |
| "goods" | products | [ ] |
| "best selling" | top by quantity/revenue | [ ] |
| "worst performing" | bottom/lowest | [ ] |
| "most popular" | top by count | [ ] |

### Partial/Misspelled Input

| User Says | Should Understand | Works? |
|-----------|-------------------|--------|
| "totl sales" | total sales | [ ] |
| "revenu" | revenue | [ ] |
| "proffit" | profit | [ ] |
| "employes" | employees | [ ] |
| "attendence" | attendance | [ ] |
| "Tamilnadu" | Tamil Nadu | [ ] |
| "banglore" | Bangalore | [ ] |
| "chenai" | Chennai | [ ] |

### Casual/Conversational Queries

| User Says | Should Work | Works? |
|-----------|-------------|--------|
| "how much did we make?" | total revenue | [ ] |
| "what's our profit like?" | profit summary | [ ] |
| "show me the numbers" | summary/overview | [ ] |
| "give me a breakdown" | category/group breakdown | [ ] |
| "what's happening with sales?" | sales trend/summary | [ ] |
| "anyone absent today?" | attendance check | [ ] |
| "who's not coming?" | absent employees | [ ] |
| "money stuff" | financial summary | [ ] |

### Implicit Context Understanding

| Query Sequence | Expected Behavior | Works? |
|----------------|-------------------|--------|
| Q1: "total sales" → Q2: "break it down by state" | Should break down sales by state | [ ] |
| Q1: "top 5 branches" → Q2: "what about bottom 5?" | Should show bottom 5 branches | [ ] |
| Q1: "November sales" → Q2: "compare to October" | Should compare Nov vs Oct | [ ] |
| Q1: "show employees" → Q2: "only from HR" | Filter to HR department | [ ] |

### Tamil Fuzzy Matching

| User Says (Tamil) | Should Understand | Works? |
|-------------------|-------------------|--------|
| "விற்பனை எவ்வளவு" | total sales | [ ] |
| "லாபம் காட்டு" | show profit | [ ] |
| "யார் லீவு" | who's absent | [ ] |
| "நல்ல பிராஞ்ச்" | top branches | [ ] |
| "கடை வருமானம்" | branch/store revenue | [ ] |

---

## 4. Voice Quality Tests

### Transcription Accuracy

| Speech Type | Test Phrase | Transcribed Correctly? |
|-------------|-------------|------------------------|
| Clear English | "What is the total revenue?" | [ ] |
| Fast English | "Show me top five products" | [ ] |
| Slow English | "Total... sales... for... November" | [ ] |
| Clear Tamil | "மொத்த விற்பனை என்ன?" | [ ] |
| Mixed | "November மாதம் sales காட்டு" | [ ] |
| Numbers | "Sales above five thousand" | [ ] |
| Names | "Sales in Tamil Nadu" | [ ] |

### Accent Tolerance

| Accent | Test Phrase | Understood? |
|--------|-------------|-------------|
| Indian English | "What is the total revenue?" | [ ] |
| South Indian | "Show me the sales data" | [ ] |
| Tamil-accented English | "Top five branches" | [ ] |
| Fast speaker | "Quick summary please" | [ ] |
| Soft speaker | "Total profit" | [ ] |

### Background Noise Handling

| Condition | Test | Works? |
|-----------|------|--------|
| Quiet room | Normal query | [ ] |
| Light background noise | Normal query | [ ] |
| AC/fan noise | Normal query | [ ] |
| Keyboard typing | Normal query | [ ] |
| Music playing softly | Normal query | [ ] |

### TTS Quality

| Aspect | Test | Quality (1-5) |
|--------|------|---------------|
| English clarity | "The total revenue is 50 lakhs" | |
| Number pronunciation | "12,345 rupees" | |
| Tamil pronunciation | "மொத்த விற்பனை" | |
| "Thara" pronunciation | Should say "Tara" not "Thaaraa" | |
| Long response | 3+ sentence response | |
| Speed | Not too fast, not too slow | |

---

## 5. Compatibility Tests

### Browser Compatibility

| Browser | Version | Voice Input | Voice Output | UI | Overall |
|---------|---------|-------------|--------------|-----|---------|
| Chrome | Latest | [ ] | [ ] | [ ] | [ ] |
| Firefox | Latest | [ ] | [ ] | [ ] | [ ] |
| Safari | Latest | [ ] | [ ] | [ ] | [ ] |
| Edge | Latest | [ ] | [ ] | [ ] | [ ] |
| Chrome Mobile | Android | [ ] | [ ] | [ ] | [ ] |
| Safari Mobile | iOS | [ ] | [ ] | [ ] | [ ] |

### Device Compatibility

| Device Type | Voice Works | UI Responsive | Touch Works |
|-------------|-------------|---------------|-------------|
| Desktop (1920x1080) | [ ] | [ ] | N/A |
| Laptop (1366x768) | [ ] | [ ] | N/A |
| Tablet (iPad) | [ ] | [ ] | [ ] |
| Tablet (Android) | [ ] | [ ] | [ ] |
| Phone (iPhone) | [ ] | [ ] | [ ] |
| Phone (Android) | [ ] | [ ] | [ ] |

### Network Conditions

| Condition | Query Works | Voice Works | Acceptable? |
|-----------|-------------|-------------|-------------|
| Fast WiFi (50+ Mbps) | [ ] | [ ] | [ ] |
| Slow WiFi (5 Mbps) | [ ] | [ ] | [ ] |
| 4G Mobile | [ ] | [ ] | [ ] |
| 3G Mobile | [ ] | [ ] | [ ] |
| High latency (200ms+) | [ ] | [ ] | [ ] |

### Microphone Compatibility

| Mic Type | Recording Quality | Transcription Accuracy |
|----------|-------------------|------------------------|
| Laptop built-in | [ ] | [ ] |
| External USB mic | [ ] | [ ] |
| Headset mic | [ ] | [ ] |
| Phone mic | [ ] | [ ] |
| Bluetooth earbuds | [ ] | [ ] |
| AirPods | [ ] | [ ] |

---

## 6. Edge Case Tests

### Input Edge Cases

| Test Case | Expected Behavior | Works? |
|-----------|-------------------|--------|
| Empty query (just spaces) | Show error/prompt | [ ] |
| Very long query (100+ words) | Handle gracefully | [ ] |
| Special characters (!@#$%) | Ignore/handle | [ ] |
| SQL injection attempt | Block/sanitize | [ ] |
| Just numbers "12345" | Ask for clarification | [ ] |
| Just emojis "👍😀" | Handle gracefully | [ ] |
| Repeated words "sales sales sales" | Understand intent | [ ] |

### Voice Edge Cases

| Test Case | Expected Behavior | Works? |
|-----------|-------------------|--------|
| Cough during recording | Ignore/filter | [ ] |
| "Um", "uh" filler words | Ignore fillers | [ ] |
| Clearing throat | Ignore | [ ] |
| Whispered query | Attempt transcription | [ ] |
| Shouted query | Handle volume | [ ] |
| Very short (< 1 sec) | Prompt to retry | [ ] |
| Very long (> 30 sec) | Limit/stop gracefully | [ ] |
| Silence only | Show prompt | [ ] |

### Conversation Edge Cases

| Test Case | Expected Behavior | Works? |
|-----------|-------------------|--------|
| 10+ messages in a row | Memory maintained | [ ] |
| Contradictory follow-up | Ask for clarification | [ ] |
| Completely off-topic | Politely redirect | [ ] |
| "Forget what I said" | Context handling | [ ] |
| Rapid-fire questions | Queue/handle | [ ] |

### Phone Mode Edge Cases

| Test Case | Expected Behavior | Works? |
|-----------|-------------------|--------|
| Click End while TTS playing | Immediate stop | [ ] |
| Click End while transcribing | Cancel processing | [ ] |
| Click End while recording | No processing | [ ] |
| Network drop during conversation | Error message | [ ] |
| Browser tab switch | Continue/pause appropriately | [ ] |
| Phone call interrupt | Handle gracefully | [ ] |

---

## 7. End-to-End User Scenarios

### Scenario 1: Business Owner Morning Check

```
Steps:
1. Open app
2. Ask "How did we do yesterday?"
3. Follow up "Compare to last week"
4. Ask "Any attendance issues?"
5. Say "Thank you" to exit

Expected: Smooth conversation flow, relevant data, natural exit
```

| Step | Works? | Notes |
|------|--------|-------|
| 1 | [ ] | |
| 2 | [ ] | |
| 3 | [ ] | |
| 4 | [ ] | |
| 5 | [ ] | |

### Scenario 2: Sales Analysis Deep Dive

```
Steps:
1. "Show me sales summary"
2. "Which state is best?"
3. "Break down Tamil Nadu by branch"
4. "Top 3 products there"
5. "What's the profit margin?"
```

| Step | Works? | Notes |
|------|--------|-------|
| 1 | [ ] | |
| 2 | [ ] | |
| 3 | [ ] | |
| 4 | [ ] | |
| 5 | [ ] | |

### Scenario 3: Tamil User Experience

```
Steps:
1. "வணக்கம்" (greeting)
2. "மொத்த விற்பனை என்ன?"
3. "சிறந்த கிளை எது?"
4. "ஜனவரி மாத தரவு காட்டு"
5. "நன்றி" (exit)
```

| Step | Works? | Notes |
|------|--------|-------|
| 1 | [ ] | |
| 2 | [ ] | |
| 3 | [ ] | |
| 4 | [ ] | |
| 5 | [ ] | |

### Scenario 4: HR Manager Check

```
Steps:
1. "How many employees do we have?"
2. "Attendance today"
3. "Which department has most absences?"
4. "Show payroll summary"
5. "Who earns the most?"
```

| Step | Works? | Notes |
|------|--------|-------|
| 1 | [ ] | |
| 2 | [ ] | |
| 3 | [ ] | |
| 4 | [ ] | |
| 5 | [ ] | |

### Scenario 5: Phone Mode Conversation

```
Steps:
1. Long-press mic to enter phone mode
2. Ask 3-4 questions in a row without touching screen
3. TTS should respond and auto-resume listening
4. Say "bye" to exit
5. Should exit cleanly without processing
```

| Step | Works? | Notes |
|------|--------|-------|
| 1 | [ ] | |
| 2 | [ ] | |
| 3 | [ ] | |
| 4 | [ ] | |
| 5 | [ ] | |

### Scenario 6: Interrupted Session

```
Steps:
1. Start a query
2. Close browser mid-response
3. Reopen app
4. Previous chat should be preserved
5. Continue conversation naturally
```

| Step | Works? | Notes |
|------|--------|-------|
| 1 | [ ] | |
| 2 | [ ] | |
| 3 | [ ] | |
| 4 | [ ] | |
| 5 | [ ] | |

---

## 8. Test Query Bank

### Sales Queries (Easy)

| # | Query | Expected Result Type |
|---|-------|---------------------|
| 1 | "total sales" | Single number |
| 2 | "total revenue" | Single number |
| 3 | "how much profit" | Single number |
| 4 | "number of transactions" | Count |
| 5 | "average sale amount" | Average |

### Sales Queries (Medium)

| # | Query | Expected Result Type |
|---|-------|---------------------|
| 6 | "top 5 branches" | Table (5 rows) |
| 7 | "sales by state" | Table (grouped) |
| 8 | "monthly trend" | Table/Chart |
| 9 | "category breakdown" | Table (grouped) |
| 10 | "payment mode analysis" | Table |

### Sales Queries (Hard)

| # | Query | Expected Result Type |
|---|-------|---------------------|
| 11 | "compare November to October" | Comparison |
| 12 | "which category grew most" | Analysis |
| 13 | "best performing state by profit margin" | Ranked result |
| 14 | "correlation between quantity and profit" | Analysis |
| 15 | "predict next month" | Projection |

### Attendance Queries

| # | Query | Expected Result Type |
|---|-------|---------------------|
| 16 | "how many employees" | Count |
| 17 | "attendance rate" | Percentage |
| 18 | "who was absent" | List |
| 19 | "department wise attendance" | Table |
| 20 | "payroll summary" | Table |

### Natural Language Queries

| # | Query | Should Understand As |
|---|-------|---------------------|
| 21 | "how's business?" | Overall summary |
| 22 | "what's selling well?" | Top products |
| 23 | "any problems?" | Issues/alerts |
| 24 | "good news?" | Positive metrics |
| 25 | "give me the highlights" | Key insights |

### Tamil Queries

| # | Query | Translation |
|---|-------|-------------|
| 26 | "மொத்த விற்பனை" | Total sales |
| 27 | "லாபம் எவ்வளவு" | How much profit |
| 28 | "சிறந்த பொருள்" | Best product |
| 29 | "மாநிலம் வாரியாக" | State-wise |
| 30 | "இன்று வரவு" | Today's attendance |

---

## 9. Performance Benchmarks

### Target Metrics

| Metric | Target | Acceptable | Current |
|--------|--------|------------|---------|
| Query latency (P50) | < 3s | < 5s | |
| Query latency (P95) | < 6s | < 10s | |
| Transcription accuracy | > 95% | > 90% | |
| SQL accuracy | > 90% | > 85% | |
| TTS first byte | < 1.5s | < 2.5s | |
| Cache hit rate | > 70% | > 50% | |
| Error rate | < 2% | < 5% | |

### Load Testing (Optional)

| Concurrent Users | Response Time | Error Rate |
|------------------|---------------|------------|
| 1 | | |
| 5 | | |
| 10 | | |
| 20 | | |

---

## 10. Sign-Off Checklist

### Critical Items (Must Pass)

- [ ] Voice input works on target browsers
- [ ] Query accuracy > 85% on test queries
- [ ] TTS plays correctly
- [ ] Phone mode End button works immediately
- [ ] Tamil queries understood
- [ ] No crashes on edge cases
- [ ] Response time < 5s for simple queries

### Important Items (Should Pass)

- [ ] Fuzzy matching works for common synonyms
- [ ] Follow-up questions maintain context
- [ ] All 6 end-to-end scenarios pass
- [ ] Works on mobile devices
- [ ] Works on slow network

### Nice-to-Have

- [ ] Works with background noise
- [ ] All accent variations work
- [ ] Tamil relative dates work

---

### Final Scores

| Category | Score | Max |
|----------|-------|-----|
| Latency | /10 | 10 |
| Accuracy | /10 | 10 |
| Fuzzy Matching | /10 | 10 |
| Voice Quality | /10 | 10 |
| Compatibility | /10 | 10 |
| Edge Cases | /10 | 10 |
| E2E Scenarios | /10 | 10 |
| **TOTAL** | /70 | 70 |

### Approval

| Role | Pass/Fail | Signature | Date |
|------|-----------|-----------|------|
| QA Tester | | | |
| Developer | | | |
| Product Owner | | | |

---

**Checklist Version:** 2.0
**Focus:** Latency, Accuracy, Compatibility, Natural Language
**Created:** January 30, 2025
