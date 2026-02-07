# Thara-AI Comprehensive Test Report

**Generated:** 2026-02-07 06:56:27
**API Endpoint:** http://localhost:8000/api/query
**Total Tests:** 187

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 187 |
| **Passed** | 174 (93.0%) |
| **Warnings** | 13 (7.0%) |
| **Failed** | 0 (0.0%) |
| **Avg Response Time** | 6.95s |

### By Language

| Language | Total | Passed | Pass Rate |
|----------|-------|--------|-----------|
| English | 98 | 91 | 92.9% |
| Tamil | 89 | 83 | 93.3% |

---

## Results by Category

### Advanced

**Pass Rate:** 10/10 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 91 | EN | Which state moved from being a top 3 rev... | PASS | 7.7s | 100 | Sales_Daily_Sales_Transactions | Looking at this, no state fits that description perfectly. Sales fluctuate, but ... |
| 92 | EN | Is there any category that ranks high in... | PASS | 5.0s | 10 | t_1_Sales_Category_Performance | Looking at this, some categories have high total revenue but might not translate... |
| 93 | EN | Are there branches where more than 50% o... | PASS | 8.1s | 100 | Sales_Daily_Sales_Transactions | Looking at this, yes, there are branches where a single payment mode accounts fo... |
| 94 | EN | Among the top 5 SKUs by revenue, which S... | PASS | 7.7s | 5 | ataset_1_Sales_SKU_Performance | Looking at this, Accessories top the revenue charts at about 51 lakhs. Sarees ar... |
| 95 | EN | Is there any month where sales increased... | PASS | 7.9s | 100 | Sales_Daily_Sales_Transactions | Looking at the data, there are months where sales increased but profit decreased... |
| 91 | TA | ஆரம்ப மாதங்களில் top 3 revenue contribut... | PASS | 8.4s | 50 | Sales_Daily_Sales_Transactions | இதைப் பார்த்தால், தெலுங்கானா அந்த விளக்கத்திற்குப் பொருந்துகிறது. அது ஆரம்பத்தில... |
| 92 | TA | மொத்த sales amount அதிகமாக இருந்தாலும், ... | PASS | 6.4s | 10 | t_1_Sales_Category_Performance | சரி, எந்தப் பிரிவில் அதிக விற்பனை இருந்தும் குறைந்த லாபம் உள்ளதா என்று கேட்கிறீர... |
| 93 | TA | ஒரே payment mode மூலம் 50%-க்கு மேல் sal... | PASS | 9.2s | 100 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, ஆம், சில கிளைகளில் ஒரு குறிப்பிட்ட பணப் பரிவர்த்தனை முறை ஐ... |
| 94 | TA | Revenue அடிப்படையில் top 5 SKU-களில், re... | PASS | 8.7s | 5 | Sales_Daily_Sales_Transactions | இதனைப் பார்க்கும்போது, SKU_NWR_பூஜ்யம் பூஜ்யம் இரண்டு ஆனது முதல் ஐந்து SKUs மத்த... |
| 95 | TA | முந்தைய மாதத்துடன் ஒப்பிடும்போது sales உ... | PASS | 8.2s | 100 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, விற்பனை அதிகரித்த ஆனால் லாபம் குறைந்த எந்த மாதமும் இல்லை. ... |

### Analysis

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 57 | EN | Explain why a particular month has low p... | PASS | 6.9s | 168 | Sales_Daily_Sales_Transactions | Looking at this, the sales trend is pretty stable overall. It started around 1.9... |
| 59 | EN | Which factor affects profit the most: co... | PASS | 6.9s | 100 | Sales_Daily_Sales_Transactions | Looking at the numbers, sales seems to drive profit more than cost. Higher sales... |
| 57 | TA | ஒரு குறிப்பிட்ட மாதத்தில் profit குறைவாக... | PASS | 8.9s | 100 | Sales_Daily_Sales_Transactions | தரவைப் பார்க்கும்போது, ​​எந்த மாதத்தைப் பற்றிக் கேட்கிறீர்கள் என்று தெரியாமல் கு... |
| 59 | TA | Profit-ஐ அதிகமாக பாதிக்கும் காரணி cost-ஆ... | PASS | 8.2s | 100 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, விற்பனை செலவைக் காட்டிலும் லாபத்தில் அதிக தாக்கத்தை ஏற்படு... |

### Branch Performance

**Pass Rate:** 10/12 (83.3%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 33 | EN | Which branch has the highest profit? | PASS | 6.7s | 1 | Dataset_1_Sales_Branch_Details | Nashik branch has the highest profit, around 1.9 lakhs. Not bad, right? |
| 34 | EN | Show top 5 branches by revenue. | PASS | 6.5s | 5 | Dataset_1_Sales_Branch_Details | Looking at this, Nellore branch is leading with about 5.7 lakhs in revenue. Hyde... |
| 35 | EN | Compare revenue between two branches. | PASS | 7.3s | 2 | Dataset_1_Sales_Branch_Details | Looking at this, the revenue is almost identical between the two branches, both ... |
| 36 | EN | What is the average profit per branch? | PASS | 6.5s | 95 | Dataset_1_Sales_Branch_Details | Looking at this, the average profit per branch is about 1.5 lakhs. It's calculat... |
| 37 | EN | Identify branches with negative profit. | WARN | 5.5s | 0 | Dataset_1_Sales_Branch_Details | No luck with that one! The data might be under a different name - want me to hel... |
| 38 | EN | How many branches are there in each stat... | PASS | 6.3s | 12 | Dataset_1_Sales_Branch_Details | Looking at this, Tamil Nadu has the most branches, with about 28. Karnataka foll... |
| 33 | TA | அதிக profit கொண்ட branch எது? | PASS | 8.3s | 1 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கையில், நாசிக் கிளை அதிக லாபம் ஈட்டியுள்ளது. அதன் மொத்த லாபம் சுமார்... |
| 34 | TA | Revenue அடிப்படையில் top 5 branches-ஐ கா... | PASS | 9.1s | 5 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கும்போது, நெல்லூர் கிளை சுமார் ஐந்தரை இலட்சத்து எழுபதாயிரம் வருவாயுட... |
| 35 | TA | இரண்டு branch-களின் revenue-ஐ ஒப்பிடு. | PASS | 9.6s | 2 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கும்போது, கிளை ஏ மற்றும் கிளை பி ஆகிய இரண்டிற்கும் சுமார் இரண்டு கோட... |
| 36 | TA | ஒவ்வொரு branch-க்கும் சராசரி profit என்ன... | PASS | 9.4s | 50 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கும்போது, நாசிக் கிளை ஏறத்தாழ ஒன்று புள்ளி ஒன்பது லட்சத்தில் மிக அதி... |
| 37 | TA | நஷ்டம் ஏற்பட்ட branches எவை? | WARN | 7.4s | 0 | Dataset_1_Sales_Branch_Details | சரியான பலன் கிடைக்கவில்லை! அந்தத் தரவு வேறொரு பெயரில் இருக்கலாம் - நான் உனக்கு அ... |
| 38 | TA | ஒவ்வொரு state-இல் எத்தனை branches உள்ளன? | PASS | 8.5s | 12 | Dataset_1_Sales_Branch_Details | சரி, தமிழ்நாடு தான் மிக அதிகமான கிளைகளைக் கொண்டுள்ளது, சுமார் இருபத்தி எட்டு கிள... |

### Category Analysis

**Pass Rate:** 2/2 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 55 | EN | Which category contributes most to total... | PASS | 4.6s | 10 | t_1_Sales_Category_Performance | Sorry about that. Looking at this, the average unit price across SKUs varies. It... |
| 55 | TA | மொத்த revenue-க்கு அதிக பங்களிப்பு தரும்... | PASS | 5.5s | 10 | t_1_Sales_Category_Performance | இதைப் பார்க்கும்போது, அனைத்து SKUs க்கும் சராசரி அலகு விலை சுமார் நானூற்று இருபத... |

### Cost Analysis

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 43 | EN | What is the total cost vs total revenue ... | PASS | 7.4s | 2 | Dataset_1_Sales_Branch_Details | Looking at this, total revenue is significantly higher than total cost. The tota... |
| 44 | EN | Which month has the highest cost amount? | PASS | 6.4s | 1 | _Sales_Monthly_Overall_Summary | Okay, September 2025 has the highest total cost at about 16 lakhs. That's the pe... |
| 43 | TA | மொத்த cost மற்றும் மொத்த revenue ஒப்பீடு... | PASS | 10.1s | 2 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கும்போது, மொத்த வருவாய் மொத்த செலவை விட கணிசமாக அதிகமாக உள்ளது. வருவ... |
| 44 | TA | அதிக cost ஏற்பட்ட மாதம் எது? | PASS | 10.8s | 1 | _Sales_Monthly_Overall_Summary | இதைப் பார்க்கும்போது, செப்டம்பர் இரண்டாயிரத்து இருபத்தைந்து அதிக செலவைக் கொண்டிர... |

### Daily Sales

**Pass Rate:** 30/30 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 1 | EN | What is the total sale amount across all... | PASS | 6.9s | 1 | Sales_Daily_Sales_Transactions | Looking at this, the total sale amount across all transactions is about 5.5 cror... |
| 2 | EN | Which branch has the highest total sale ... | PASS | 6.8s | 1 | Dataset_1_Sales_Branch_Details | Looking at this, Jodhpur branch has the highest total sale amount. It's around 3... |
| 3 | EN | How many transactions were made using UP... | PASS | 6.8s | 1 | Sales_Daily_Sales_Transactions | Looking at this, there were about 2.4 thousand transactions made using UPI. That... |
| 4 | EN | Show total profit amount for each state. | PASS | 7.2s | 12 | Dataset_1_Sales_Branch_Details | Looking at this, Tamil Nadu is leading in total profit with about 39.9 lakhs. Ka... |
| 5 | EN | Which category generated the highest pro... | PASS | 4.8s | 10 | t_1_Sales_Category_Performance | Looking at this, TN_023 branch is generating the highest profit, with about 8.8 ... |
| 6 | EN | What is the average profit margin percen... | PASS | 6.4s | 100 | Sales_Daily_Sales_Transactions | Looking at this, the average profit margin is about 60 percent. It's consistent ... |
| 7 | EN | List transactions where quantity sold is... | PASS | 7.2s | 100 | Sales_Daily_Sales_Transactions | Looking at this, these are transactions where more than 10 items were sold. For ... |
| 8 | EN | What is the total GST collected? | PASS | 7.0s | 1 | Sales_Daily_Sales_Transactions | Looking at this, the total GST collected is about 5.5 crores. That's based on ov... |
| 9 | EN | Which SKU has the highest total sales am... | PASS | 7.0s | 1 | Sales_Daily_Sales_Transactions | Looking at this, SKU_SAR_003 has the highest total sales amount. It's sitting at... |
| 10 | EN | Show sales amount grouped by payment mod... | PASS | 6.9s | 5 | Sales_Daily_Sales_Transactions | Looking at this, cheque is the most used payment mode with sales around 1.1 cror... |
| 11 | EN | Find the transaction with the highest pr... | PASS | 4.9s | 5 | Sales_Daily_Sales_Transactions | Sorry about that. Looking at this, cheque payments lead with about 1.1 crore, fo... |
| 12 | EN | What is the total cost amount across all... | PASS | 6.8s | 1 | Sales_Daily_Sales_Transactions | Looking at this, the total cost amount across all sales is about 2.2 crores. The... |
| 13 | EN | Show average unit price by category. | PASS | 4.9s | 1 | t_1_Sales_Category_Performance | Sorry about that. Looking at this, the total cost across all sales is about 43 l... |
| 14 | EN | How many unique branches are present? | PASS | 6.7s | 1 | Dataset_1_Sales_Branch_Details | Looking at this, there are 95 unique branches present in the dataset. The Branch... |
| 15 | EN | Compare total sales between two differen... | PASS | 5.3s | 2 | Dataset_1_Sales_Branch_Details | Looking at this, the total sales between the two states are almost the same, aro... |
| 1 | TA | அனைத்து transaction-களின் மொத்த sale amo... | PASS | 7.0s | 1 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, "டிம்பக்டு" என்று பொருந்தக்கூடிய எந்த கிளைக்கும் வருவாய் த... |
| 2 | TA | அதிகமான மொத்த விற்பனை கொண்ட branch எது? | PASS | 9.0s | 1 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கும்போது, ஜோத்பூர் கிளை அதிக மொத்த விற்பனையைக் கொண்டுள்ளது. இது ஏறக்... |
| 3 | TA | UPI மூலம் எத்தனை transactions செய்யப்பட்... | PASS | 9.3s | 1 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, UPI மூலம் சுமார் இரண்டாயிரத்து நானூறு பரிவர்த்தனைகள் நடந்த... |
| 4 | TA | ஒவ்வொரு state-க்கும் மொத்த profit amount... | PASS | 10.6s | 12 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கையில், மொத்த லாபத்தில் தமிழ்நாடு சுமார் நாற்பது லட்சம் ரூபாயுடன் மு... |
| 5 | TA | அதிக profit உருவாக்கிய category எது? | PASS | 6.2s | 10 | t_1_Sales_Category_Performance | இதைப் பார்க்கும்போது, டிஎன் பூஜ்ஜியம் இருபத்தி மூன்று கிளை சுமார் எட்டு லட்சத்து... |
| 6 | TA | சராசரி profit margin percentage என்ன? | PASS | 9.8s | 100 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, சராசரி லாப வரம்பு சுமார் அறுபது சதவீதம். இது எல்லா இடங்களி... |
| 7 | TA | Quantity 10-க்கு மேல் உள்ள transactions-... | PASS | 10.7s | 100 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, இவை பத்து பொருட்களுக்கு மேல் உள்ள பரிவர்த்தனைகள். உதாரணமாக... |
| 8 | TA | மொத்தமாக வசூலிக்கப்பட்ட GST எவ்வளவு? | PASS | 9.9s | 1 | Sales_Daily_Sales_Transactions | இதனைப் பார்க்கும்போது, வசூலிக்கப்பட்ட மொத்த ஜிஎஸ்டி ஏறத்தாழ ஐந்து புள்ளி ஐந்து க... |
| 9 | TA | அதிகமான மொத்த விற்பனை கொண்ட SKU எது? | PASS | 10.7s | 10 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கையில், சேலைகள் ஏறக்குறைய ஒரு கோடியே இருபத்தைந்து லட்சம் விற்பனையுடன... |
| 10 | TA | Payment mode அடிப்படையில் sales amount-ஐ... | PASS | 11.3s | 5 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, காசோலை கொடுப்பனவுகள் ஏறத்தாழ ஒன்று புள்ளி ஒன்று கோடி உடன் ... |
| 11 | TA | அதிக profit amount கொண்ட transaction எது... | PASS | 7.3s | 5 | Sales_Daily_Sales_Transactions | சரியா, காசோலை செலுத்துதல்கள் ஏறத்தாழ ஒரு கோடியே பத்து இலட்சம் விற்பனையுடன் முன்ன... |
| 12 | TA | அனைத்து sales-களின் மொத்த cost amount என... | PASS | 10.3s | 1 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, அனைத்து விற்பனைகளுக்கான மொத்த செலவுத் தொகை சுமார் இரண்டு க... |
| 13 | TA | Category வாரியாக சராசரி unit price-ஐ காட... | PASS | 6.2s | 1 | t_1_Sales_Category_Performance | இதைப் பார்க்கையில், அனைத்து விற்பனைகளின் மொத்த விலை சுமார் நாற்பத்திரண்டு லட்சத்... |
| 14 | TA | எத்தனை தனித்தனி branches உள்ளன? | PASS | 9.2s | 1 | Dataset_1_Sales_Branch_Details | சற்று கவனியுங்கள், இந்த தரவுத் தொகுப்பில் தொண்ணூற்று ஐந்து தனித்துவமான கிளைகள் உ... |
| 15 | TA | இரண்டு state-களின் மொத்த sales-ஐ ஒப்பிடு... | PASS | 8.0s | 2 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கும்போது, மாநிலம் அ ஏறத்தாழ எழுபது லட்சம் விற்பனையில் முன்னணியில் உள... |

### Edge Case

**Pass Rate:** 6/9 (66.7%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 96 | EN | Show me XYZ department | PASS | 6.7s | 0 | _Attendance_Attendance_Records | Oops! Looks like there's no data matching that. Maybe try a different date range... |
| 97 | EN | Sales in Mars | WARN | 6.0s | 100 | _Attendance_Attendance_Records | Okay, this shows attendance records filtered to just the Sales department. There... |
| 98 | EN | Dhoti sales in January | PASS | 8.5s | 1 | Sales_Daily_Sales_Transactions | Looking at this, there were no Dhoti sales in January of 2025. The data shows ze... |
| 99 | EN | abcdefg | PASS | 3.0s | 0 |  | Hey! Great to see you! What would you like to look at today? |
| 100 | EN | Show me nothing | WARN | 4.9s | 100 | Sales_Daily_Sales_Transactions | Okay, I've got nothing to show from the data. Is there anything specific you'd l... |
| 101 | EN | What is the sales of product ABC123? | WARN | 6.4s | 0 | Sales_Daily_Sales_Transactions | Hmm, I couldn't find any data for that! Want to try a different filter or spelli... |
| 102 | EN | Revenue for branch Timbuktu | PASS | 6.6s | 0 | Dataset_1_Sales_Branch_Details | Hmm, I couldn't find any data for that! Want to try a different filter or spelli... |
| 103 | EN | Employee named Superman | PASS | 3.0s | 0 |  | Hey! Great to see you! What would you like to look at today? |
| 104 | EN | Attendance for February 2020 | PASS | 2.0s | 0 |  | Okay, February - noted! Now, what can I help you find? |

### Follow-up Chain 1

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 81 | EN | What is the total sales in Tamil Nadu? | PASS | 7.3s | 1 | Sales_Daily_Sales_Transactions | Looking at this, total sales in Tamil Nadu is about 46 lakhs. That's based on ov... |
| 82 | EN | Is it higher or lower compared to Karnat... | PASS | 5.4s | 2 | Sales_Daily_Sales_Transactions | Karnataka is slightly higher. Sales in Karnataka are about 47.3 lakhs, compared ... |
| 81 | TA | தமிழ்நாட்டில் மொத்த sales என்ன? | PASS | 9.5s | 1 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, ​​தமிழ்நாட்டில் மொத்த விற்பனை சுமார் நாற்பத்தி ஆறு லட்சங்க... |
| 82 | TA | கர்நாடகாவுடன் ஒப்பிடும்போது இது அதிகமா க... | PASS | 9.5s | 2 | aset_1_Sales_State_Performance | இதைப் பார்க்கும்போது, மொத்த மதிப்பு கர்நாடகாவை விட அதிகமாக உள்ளது. ஒட்டுமொத்த மத... |

### Follow-up Chain 2

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 83 | EN | Which category has the highest total sal... | PASS | 5.3s | 2 | t_1_Sales_Category_Performance | Looking at this, the total sales is about 1.2 crore, which is much higher than K... |
| 84 | EN | Did sales for this category increase or ... | PASS | 5.3s | 2 | t_1_Sales_Category_Performance | Looking at this, sales decreased compared to Karnataka. The current value is abo... |
| 83 | TA | அதிக மொத்த sales கொண்ட category எது? | PASS | 6.6s | 2 | t_1_Sales_Category_Performance | இதைப் பார்க்கும்போது, எல்லா பிராந்தியங்களிலும் மொத்த விற்பனை சுமார் ஒரு கோடியே இ... |
| 84 | TA | இந்த category-க்கு sales காலப்போக்கில் அ... | PASS | 7.0s | 2 | t_1_Sales_Category_Performance | இதைப் பார்க்கும்போது, "All"க்கான விற்பனை கர்நாடகாவை விட அதிகமாக உள்ளது. கர்நாடகா... |

### Follow-up Chain 3

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 85 | EN | Which branch has the highest revenue ove... | PASS | 3.3s | 2 | t_1_Sales_Category_Performance | Looking at this, the current value is higher than Karnataka's. It's about 1.2 cr... |
| 86 | EN | Is this branch performing better or wors... | PASS | 5.4s | 2 | t_1_Sales_Category_Performance | Looking at this, this branch is underperforming compared to the average. Its sal... |
| 85 | TA | மொத்தமாக அதிக revenue கொண்ட branch எது? | PASS | 7.8s | 1 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கும்போது, ஜோத்பூர் கிளை அதிக மொத்த வருவாயைக் கொண்டுள்ளது. இது சுமார்... |
| 86 | TA | இந்த branch மற்ற branch-களின் சராசரியை வ... | PASS | 6.0s | 1 | Sales_Daily_Sales_Transactions | பயனருக்கு குழப்பம் இருப்பதாக தெரிகிறது.  இதைப் பார்க்கும்போது, ஃபரிதாபாத் கிளை அ... |

### Follow-up Chain 4

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 87 | EN | Which payment mode has the highest sales... | PASS | 7.1s | 1 | _1_Sales_Payment_Mode_Analysis | Looking at this, cash is the most popular payment method. Total revenue from cas... |
| 88 | EN | Has the usage of this payment mode incre... | PASS | 7.3s | 5 | Sales_Daily_Sales_Transactions | Looking at the payment modes, they're all pretty stable. Cash saw the biggest in... |
| 87 | TA | அதிக sales amount கொண்ட payment mode எது... | PASS | 8.3s | 1 | _1_Sales_Payment_Mode_Analysis | இதைப் பார்க்கும்போது, ரொக்கம் அதிகம் பயன்படுத்தப்படும் கட்டண முறையாகும், இதன் வர... |
| 88 | TA | இந்த payment mode பயன்பாடு மாதங்களாக உயர... | PASS | 9.2s | 5 | Sales_Daily_Sales_Transactions | கட்டண முறைகளை பார்க்கும்போது, அவை பெரும்பாலும் நிலையாக இருக்கின்றன. ரொக்கம் மிகப... |

### Follow-up Chain 5

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 89 | EN | Which SKU has the highest total revenue? | PASS | 6.8s | 10 | Sales_Daily_Sales_Transactions | Looking at this, Sarees are the top performer with sales of about 1.25 crores. E... |
| 90 | EN | Is this SKU's sales trend consistently i... | PASS | 6.2s | 24 | Sales_Daily_Sales_Transactions | Looking at this, the sales trend for all SKUs is generally stable. For example, ... |
| 89 | TA | அதிக மொத்த revenue கொண்ட SKU எது? | PASS | 8.4s | 10 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, புடவைகள் தோராயமாக ஒன்று புள்ளி இரண்டு ஐந்து கோடி ரூபாயில் ... |
| 90 | TA | இந்த SKU-ன் sales trend தொடர்ந்து உயருகி... | PASS | 8.5s | 168 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, விற்பனை போக்கு ஒட்டுமொத்தமாக நிலையாக உள்ளது. இது சுமார் மூ... |

### Greeting

**Pass Rate:** 2/2 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 105 | EN | Hello, how are you? | PASS | 2.9s | 0 |  | I'm doing well, thanks for asking! How can I help you with your data today? |
| 105 | TA | வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்? | PASS | 3.0s | 0 |  | வணக்கம்! நான் நல்லா இருக்கேன், நன்றி! நீங்க எப்படி இருக்கீங்க? Enna data paakanu... |

### Monthly Analysis

**Pass Rate:** 20/20 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 16 | EN | What is the total revenue for each month... | PASS | 6.7s | 6 | _Sales_Monthly_Overall_Summary | Looking at this, September had the highest total revenue at about 40 lakhs. Reve... |
| 17 | EN | Which month recorded the highest total p... | PASS | 6.7s | 1 | _Sales_Monthly_Overall_Summary | Looking at this, September 2025 recorded the highest total profit. It was about ... |
| 18 | EN | Show category-wise revenue for each mont... | PASS | 4.7s | 1 | t_1_Sales_Category_Performance | Alright, TN_023 branch is the top performer with a total profit of about 8.8 lak... |
| 19 | EN | Which category has the highest profit ma... | PASS | 4.7s | 1 | t_1_Sales_Category_Performance | Looking at this, TN_023 branch is the top performer with a total profit of about... |
| 20 | EN | What is the total profit for each catego... | PASS | 4.6s | 1 | t_1_Sales_Category_Performance | Looking at this, TN_023 branch recorded the highest total profit. It's around 8.... |
| 21 | EN | Compare revenue between two categories. | PASS | 7.3s | 2 | t_1_Sales_Category_Performance | Looking at this, the revenue is almost the same for both categories. Each catego... |
| 22 | EN | Which month has the highest number of tr... | PASS | 7.1s | 1 | Sales_Daily_Sales_Transactions | Okay, so October 2025 has the highest number of transactions. The count is aroun... |
| 23 | EN | Show month-over-month sales growth. | PASS | 7.1s | 168 | Sales_Daily_Sales_Transactions | Looking at this, sales are pretty stable overall. It started around 3.3 lakhs an... |
| 24 | EN | What is the average profit margin per mo... | PASS | 6.6s | 6 | _Sales_Monthly_Overall_Summary | Looking at this, the average profit margin is consistently around 60 percent eac... |
| 25 | EN | Identify the worst performing category b... | PASS | 4.9s | 1 | t_1_Sales_Category_Performance | Looking at this, the average profit margin per month is about 60 percent. That's... |
| 16 | TA | ஒவ்வொரு மாதத்திற்கும் மொத்த வருமானம் என்... | PASS | 9.3s | 6 | _Sales_Monthly_Overall_Summary | சரி, இதோ மொழிபெயர்ப்பு:  இதைப் பார்க்கும்போது, செப்டம்பர் மாதம் நாற்பது லட்ச ரூப... |
| 17 | TA | அதிக profit பெற்ற மாதம் எது? | PASS | 8.7s | 1 | _Sales_Monthly_Overall_Summary | இதைப் பார்த்தால், செப்டம்பர் இரண்டாயிரத்து இருபத்தைந்து அதிக லாபம் ஈட்டிய மாதம்.... |
| 18 | TA | ஒவ்வொரு மாதத்திற்கும் category வாரியான r... | PASS | 6.9s | 10 | t_1_Sales_Category_Performance | இதைப் பார்க்கும்போது, அனைத்து வகைகளிலும் அறுபது சதவீத லாப வரம்பு உள்ளது. உள்ளாடை... |
| 19 | TA | மொத்தமாக அதிக profit margin கொண்ட catego... | PASS | 6.6s | 10 | t_1_Sales_Category_Performance | இதைப் பார்க்கும்போது, உள்ளாடைகளுக்கு சுமார் பன்னிரெண்டு லட்சத்து இருபதாயிரம் ரூப... |
| 20 | TA | ஒவ்வொரு category-க்கும் மொத்த profit என்... | PASS | 6.6s | 10 | t_1_Sales_Category_Performance | இதைப் பார்க்கையில், உள்ளாடைகள் தோராயமாக பன்னிரண்டு லட்சத்து இருபதாயிரம் வருவாய் ... |
| 21 | TA | இரண்டு category-களின் revenue-ஐ ஒப்பிடு. | PASS | 6.7s | 10 | t_1_Sales_Category_Performance | இதைப் பார்க்கும்போது, உள்ளாடைகள் மற்றும் ஆண்களுக்கான டி-ஷர்ட்டுகள் அதிக வருவாயைக... |
| 22 | TA | அதிக transactions நடந்த மாதம் எது? | PASS | 9.2s | 1 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, அக்டோபர் இரண்டாயிரத்து இருபத்தைந்து அதிகமான பரிவர்த்தனைகளை... |
| 23 | TA | மாதம் வாரியாக sales growth-ஐ காட்டு. | PASS | 9.5s | 168 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, விற்பனை ஒட்டுமொத்தமாக மிகவும் நிலையாக உள்ளது. இது தோராயமாக... |
| 24 | TA | ஒவ்வொரு மாதத்திற்கும் சராசரி profit marg... | PASS | 9.9s | 6 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, சராசரி லாப வரம்பு மாதம் மாதம் ஏறக்குறைய நிலையாக உள்ளது. இத... |
| 25 | TA | profit அடிப்படையில் மிகக் குறைந்த catego... | PASS | 6.0s | 10 | t_1_Sales_Category_Performance | இதைப் பார்க்கும்போது, சராசரி இலாப வரம்பு அனைத்து வகைகளிலும் அறுபது சதவீதம் ஆகும்... |

### Payment Analysis

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 41 | EN | Which payment mode has the highest trans... | PASS | 4.6s | 12 | Sales_Daily_Sales_Transactions | Looking at this, Tamil Nadu has the most branches, with about 28. Karnataka's ne... |
| 42 | EN | Show revenue distribution by payment mod... | PASS | 6.7s | 5 | _1_Sales_Payment_Mode_Analysis | Looking at this, Cash and UPI are the top payment modes, each generating about 1... |
| 41 | TA | அதிக transactions கொண்ட payment mode எது... | PASS | 10.1s | 1 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, காசோலை அதிக பரிவர்த்தனைகளைக் கொண்ட செலுத்தும் முறையாக உள்ள... |
| 42 | TA | Payment mode வாரியாக revenue-ஐ காட்டு. | PASS | 9.9s | 5 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, காசோலை செலுத்துதல்கள் சுமார் ஒரு கோடியே பதினொரு இலட்சத்துட... |

### Projection Chain 1

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 71 | EN | Compare total sales between November and... | PASS | 6.3s | 2 | Sales_Daily_Sales_Transactions | Looking at this, December sales are slightly higher than November. December's at... |
| 72 | EN | If the same trend continues, what could ... | PASS | 2.0s | 1 |  | Based on current trends, January sales would be around 0. The stable trend sugge... |
| 71 | TA | நவம்பர் மற்றும் டிசம்பர் மாத sales-ஐ ஒப்... | PASS | 10.6s | 2 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, டிசம்பர் மாத விற்பனை நவம்பர் மாதத்தை விட சற்று அதிகமாக உள்... |
| 72 | TA | அதே trend தொடர்ந்தால் ஜனவரிக்கான project... | PASS | 2.0s | 1 |  | தற்போதைய போக்கின் அடிப்படையில், January விற்பனை சுமார் 0 ஆக இருக்கும் என்று எதிர... |

### Projection Chain 2

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 73 | EN | Show sales trend for Chennai across mont... | PASS | 6.9s | 36 | Sales_Daily_Sales_Transactions | Looking at this, Chennai sales show a decreasing trend. It started around 5.4 th... |
| 74 | EN | Based on this trend, estimate next month... | PASS | 2.1s | 1 |  | Based on current trends, Next Month sales would be around 0. That's about around... |
| 73 | TA | சென்னை நகரத்தின் மாத sales trend-ஐ காட்ட... | PASS | 9.2s | 36 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, சென்னையில் விற்பனை போக்கு குறைந்து வருகிறது, ஆனால் குறைந்த... |
| 74 | TA | இந்த trend அடிப்படையில் அடுத்த மாத sales... | PASS | 2.0s | 1 |  | தற்போதைய போக்கின் அடிப்படையில், Next Period விற்பனை சுமார் 0 ஆக இருக்கும் என்று ... |

### Projection Chain 3

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 75 | EN | Show category-wise sales for the last th... | PASS | 4.5s | 10 | t_1_Sales_Category_Performance | Looking at this, the sales trend is decreasing. It started around 13.8 lakhs and... |
| 76 | EN | If the top category continues this patte... | PASS | 4.7s | 10 | t_1_Sales_Category_Performance | Looking at this, the top category sales are decreasing. If the trend continues, ... |
| 75 | TA | கடந்த மூன்று மாதங்களுக்கான category வாரி... | PASS | 5.8s | 10 | t_1_Sales_Category_Performance | சரி, இந்த டிரெண்ட் படி பார்த்தால், விற்பனை குறைந்து வருகிறது. ஆரம்பத்தில் சுமார்... |
| 76 | TA | முன்னணி category இதே pattern தொடர்ந்தால்... | PASS | 5.8s | 10 | t_1_Sales_Category_Performance | சரி, இந்த trend தொடர்ந்தால், அடுத்த மாத sales சுமார் ஒன்பது லட்சத்து முப்பதாயிரம... |

### Projection Chain 4

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 77 | EN | Compare revenue for a branch between two... | PASS | 7.3s | 2 | Sales_Daily_Sales_Transactions | Looking at this, the revenue is stable between the two months. It's around 5.4 c... |
| 78 | EN | Project the next month's revenue assumin... | PASS | 2.0s | 1 |  | Based on current trends, Next Month sales would be around 0. The stable trend su... |
| 77 | TA | ஒரு branch-ன் தொடர்ச்சியான இரண்டு மாத re... | PASS | 9.7s | 2 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, இந்த மாதம் வருவாய் சற்று அதிகரித்துள்ளது. இது சுமார் ஒரு ச... |
| 78 | TA | அதே மாற்றம் தொடர்ந்தால் அடுத்த மாத reven... | PASS | 2.0s | 1 |  | தற்போதைய போக்கின் அடிப்படையில், Next Period விற்பனை சுமார் 0 ஆக இருக்கும் என்று ... |

### Projection Chain 5

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 79 | EN | Show last 3 months sales for a SKU. | PASS | 6.9s | 168 | Sales_Daily_Sales_Transactions | Looking at this, sales are pretty stable. Started around 3.3 lakhs, ended at 3.4... |
| 80 | EN | If this trend continues, what could be t... | PASS | 2.1s | 1 |  | Based on the strong trend, Next Month sales would be around about 3.4 lakhs. Tha... |
| 79 | TA | ஒரு SKU-க்கு கடந்த 3 மாத sales-ஐ காட்டு. | PASS | 8.9s | 168 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கையில், விற்பனை போக்கு மிகவும் நிலையானதாக இருக்கிறது. இது ஏறத்தாழ மூ... |
| 80 | TA | இந்த trend தொடர்ந்தால் அடுத்த மாத sales ... | PASS | 2.1s | 1 |  | வலுவான போக்கின் அடிப்படையில், Next Period விற்பனை சுமார் about 3.4 lakhs ஆக இருக... |

### Quarterly Analysis

**Pass Rate:** 6/8 (75.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 45 | EN | Show profit margin trend across quarters... | PASS | 6.5s | 3 | _1_Sales_Quarterly_Performance | Looking at this, the profit margin trend is decreasing. It started around 71 lak... |
| 46 | EN | Which quarter generated the highest prof... | PASS | 6.3s | 1 | _1_Sales_Quarterly_Performance | Looking at this, Q3 2025 generated the highest profit. It's about 71 lakhs. Not ... |
| 47 | EN | What is the total profit per quarter? | PASS | 6.4s | 3 | _1_Sales_Quarterly_Performance | Looking at this, Q3 2025 had the highest profit at about 71 lakhs. However, prof... |
| 56 | EN | Compare quarterly revenue growth. | PASS | 6.8s | 3 | _1_Sales_Quarterly_Performance | Looking at this, there's a decreasing trend in quarterly revenue. It dropped sig... |
| 45 | TA | Quarter வாரியாக profit margin trend-ஐ கா... | WARN | 8.0s | 0 | _1_Sales_Quarterly_Performance | சாரி! அப்படிப் பொருந்தும் தரவு எதுவும் இருப்பதாகத் தெரியவில்லை. ஒருவேளை வேறு தேத... |
| 46 | TA | அதிக profit பெற்ற quarter எது? | PASS | 8.6s | 1 | _1_Sales_Quarterly_Performance | இதைப் பார்க்கும்போது, மூன்றாம் காலாண்டு இரண்டாயிரத்து இருபத்தி ஐந்தில் அதிக லாபம... |
| 47 | TA | ஒவ்வொரு quarter-க்கும் மொத்த profit என்ன... | PASS | 8.9s | 3 | _1_Sales_Quarterly_Performance | சரி, ஒவ்வொரு காலாண்டுக்கான மொத்த லாபத்தைப் பார்க்கும்போது, Q3 இரண்டாயிரத்து இருப... |
| 56 | TA | Quarter வாரியான revenue growth-ஐ ஒப்பிடு... | WARN | 8.1s | 0 | _1_Sales_Quarterly_Performance | சரி! நீங்கள் கொடுத்த வாக்கியத்தை தமிழுக்கு மாற்றுகிறேன். அனைத்து எண்களையும் தமி... |

### SKU Analysis

**Pass Rate:** 12/14 (85.7%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 48 | EN | Which SKU sold the highest number of uni... | PASS | 7.4s | 10 | Sales_Daily_Sales_Transactions | Looking at this, Sarees sold the highest number of units, with a quantity of aro... |
| 49 | EN | Show top 5 SKUs by total revenue. | PASS | 6.7s | 5 | Sales_Daily_Sales_Transactions | Looking at this, Sarees are the top-selling SKU with sales of about 1.25 crores.... |
| 50 | EN | Which SKU has the highest profit margin? | PASS | 6.3s | 1 | ataset_1_Sales_SKU_Performance | Looking at this, the Dhoti SKU with ID SKU_DHT_001 has the highest profit margin... |
| 51 | EN | Compare revenue and cost for each SKU. | PASS | 6.4s | 24 | ataset_1_Sales_SKU_Performance | Looking at this, revenue is significantly higher than cost for each SKU. For exa... |
| 52 | EN | Identify SKUs that are running at a loss... | WARN | 5.9s | 0 | Sales_Daily_Sales_Transactions | Aww, nothing came up for that search! Let's try tweaking the criteria - what do ... |
| 53 | EN | What is the average cost per unit across... | PASS | 6.5s | 24 | ataset_1_Sales_SKU_Performance | Looking at this, the average cost per unit across all SKUs is about 280 rupees. ... |
| 54 | EN | Show category-wise SKU profit contributi... | PASS | 4.3s | 10 | t_1_Sales_Category_Performance | Looking at this, the average unit price across SKUs varies. It ranges from about... |
| 48 | TA | அதிக units விற்கப்பட்ட SKU எது? | PASS | 8.5s | 1 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, SKU_MTS_பூஜ்யம் பூஜ்யம் ஒன்று அதிக யூனிட்கள் விற்பனையாகியு... |
| 49 | TA | Revenue அடிப்படையில் top 5 SKU-களை காட்ட... | PASS | 11.1s | 5 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, சேலைகள் சுமார் ஒரு கோடியே இருபத்தி ஐந்து லட்சம் வருவாயுடன்... |
| 50 | TA | அதிக profit margin கொண்ட SKU எது? | PASS | 8.8s | 1 | ataset_1_Sales_SKU_Performance | இதைப் பார்க்கும்போது, தோத்தி SKU, ID SKU_DHT_பூஜ்ஜியம் பூஜ்ஜியம் ஒன்று, அறுபது ச... |
| 51 | TA | ஒவ்வொரு SKU-க்கும் revenue மற்றும் cost-... | PASS | 9.4s | 100 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, ஒவ்வொரு SKU-வுக்கும் வருவாய் செலவை விட அதிகமாக உள்ளது. உதா... |
| 52 | TA | நஷ்டத்தில் உள்ள SKU-களை கண்டறி. | WARN | 3.3s | 0 |  | வணக்கம்! நஷ்டத்தில் உள்ள SKU-களை பார்க்கலாமா? இதோ results: நஷ்டத்தில் உள்ள முதல்... |
| 53 | TA | அனைத்து SKU-களின் சராசரி cost per unit எ... | PASS | 10.3s | 100 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, அனைத்து SKUக்களுக்கான ஒரு யூனிட்டின் சராசரி விலை சுமார் ஆய... |
| 54 | TA | Category வாரியாக SKU profit contribution... | PASS | 5.5s | 10 | t_1_Sales_Category_Performance | இதைப் பார்த்தால், அனைத்து எஸ்கே யூக்களுக்கான சராசரி அலகு விலை சுமார் நானூற்று நா... |

### State Performance

**Pass Rate:** 4/4 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 31 | EN | Which state has the highest total revenu... | PASS | 6.5s | 1 | aset_1_Sales_State_Performance | Looking at this, West Bengal has the highest total revenue. It's sitting at abou... |
| 32 | EN | Show profit margin by state. | PASS | 6.7s | 12 | Dataset_1_Sales_Branch_Details | Looking at this, Tamil Nadu has the highest profit margin at about 1700 percent.... |
| 31 | TA | அதிக மொத்த revenue கொண்ட state எது? | PASS | 8.8s | 1 | aset_1_Sales_State_Performance | பயனர் தமிழில் கேட்பது போல் தெரிகிறது, அதனால் நான் ஆங்கிலத்தில் பதிலளிக்கிறேன், ஆ... |
| 32 | TA | State வாரியாக profit margin-ஐ காட்டு. | PASS | 8.8s | 12 | Dataset_1_Sales_Branch_Details | இதைப் பார்க்கும்போது, தமிழ்நாடு ஏறக்குறைய பதினேழு லட்சத்தில் அதிக லாப வரம்பைக் க... |

### Summary

**Pass Rate:** 2/2 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 60 | EN | Give a high-level business summary of th... | PASS | 4.8s | 10 | Sales_Monthly_Category_Summary | Looking at this, Inner Wear is the top performer with a profit of about 2.8 lakh... |
| 60 | TA | இந்த dataset-க்கு ஒரு high-level busines... | PASS | 5.9s | 10 | Sales_Monthly_Category_Summary | இதைப் பார்க்கையில், உள்ளாடை ஏறக்குறைய நான்கு புள்ளி ஆறு லட்சம் வருவாயுடன் முதல் ... |

### Trend

**Pass Rate:** 16/20 (80.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 61 | EN | Are sales increasing or decreasing in Ch... | PASS | 6.6s | 36 | Sales_Daily_Sales_Transactions | Looking at this, Chennai sales show a decreasing trend. It started around 5.4 th... |
| 62 | EN | Which state shows a declining sales tren... | PASS | 7.0s | 12 | Sales_Daily_Sales_Transactions | Actually, no state shows a declining sales trend - all are stable. Tamil Nadu's ... |
| 63 | EN | Which category shows consistent growth a... | WARN | 3.6s | 0 | t_1_Sales_Category_Performance | No luck with that one! The data might be under a different name - want me to hel... |
| 64 | EN | Are profits stable or volatile over time... | PASS | 7.1s | 168 | Sales_Daily_Sales_Transactions | Looking at this, profits are pretty stable overall. They started around 1.97 lak... |
| 65 | EN | Which month had an unusual spike in sale... | PASS | 6.4s | 168 | Sales_Daily_Sales_Transactions | Looking at this, October 2025 had an unusual spike in sales. The peak was around... |
| 66 | EN | Is revenue seasonally higher in certain ... | PASS | 6.5s | 168 | Sales_Daily_Sales_Transactions | Looking at this, the sales trend is pretty stable. It started around 3.3 lakhs a... |
| 67 | EN | Which branch shows declining performance... | PASS | 7.3s | 93 | Sales_Daily_Sales_Transactions | Looking at this, Tiruppur shows the most decline. It went down about 94 percent,... |
| 68 | EN | Which category is losing revenue month b... | WARN | 3.6s | 0 | t_1_Sales_Category_Performance | Hmm, I couldn't find any data for that! Want to try a different filter or spelli... |
| 69 | EN | Are costs rising faster than revenue? | PASS | 7.3s | 2 | Sales_Daily_Sales_Transactions | Looking at this, revenue is rising faster than cost. Revenue is about 5.5 crores... |
| 70 | EN | Which quarter performed the worst overal... | PASS | 3.0s | 2 | Sales_Daily_Sales_Transactions | Looking at this, costs are rising much faster than revenue. Costs increased abou... |
| 61 | TA | சென்னை நகரத்தில் sales உயர்கிறதா குறைகிற... | PASS | 8.7s | 36 | Sales_Daily_Sales_Transactions | சென்னை பார்க்கும்போது, விற்பனை பொதுவாகக் குறைந்து வருகிறது. இது சுமார் ஐந்தாயிரத... |
| 62 | TA | எந்த state-இல் sales trend குறைந்து வருக... | PASS | 9.6s | 93 | Sales_Daily_Sales_Transactions | சரி, எனக்கு கிடைத்த தகவல் இதுதான். கிளைகளில், திருப்பூர் தொண்ணூற்று நான்கு சதவீத... |
| 63 | TA | எந்த category மாதம் முழுவதும் நிலையான வள... | WARN | 4.8s | 0 | t_1_Sales_Category_Performance | ம்ம்ம், எனக்கான எந்த விவரமும் கிடைக்கவில்லை! வேறொரு வடிகட்டியை அல்லது எழுத்துக்க... |
| 64 | TA | profit காலப்போக்கில் நிலையானதா அல்லது மா... | PASS | 8.9s | 168 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, லாபப் போக்கு மிகவும் நிலையானதாக இருக்கிறது. இது சுமார் ஒன்... |
| 65 | TA | எந்த மாதத்தில் sales திடீரென அதிகரித்தது... | PASS | 9.3s | 168 | Sales_Daily_Sales_Transactions | சரி, அக்டோபர் மாதத்தின் நடுப்பகுதியில் விற்பனை திடீரென அதிகரித்தது. உச்சம் அக்டோ... |
| 66 | TA | சில மாதங்களில் revenue அதிகமாக இருக்கிறத... | PASS | 8.6s | 168 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, வருவாய் போக்கு ஒட்டுமொத்தமாக மிகவும் நிலையாக உள்ளது. இது ச... |
| 67 | TA | எந்த branch செயல்திறன் குறைந்து வருகிறது... | PASS | 8.9s | 93 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, திருப்பூர்தான் மிகவும் மோசமான சரிவைக் காட்டுகிறது. இது சும... |
| 68 | TA | எந்த category மாதம் மாதமாக revenue இழக்க... | WARN | 4.7s | 0 | t_1_Sales_Category_Performance | சரி! அப்படித் தோன்றுகிறது, அந்த விவரங்களுடன் பொருந்தும் எந்தத் தரவும் இல்லை. ஒரு... |
| 69 | TA | revenue-விட cost வேகமாக உயருகிறதா? | PASS | 8.7s | 2 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, வருவாய் செலவை விட வேகமாக அதிகரிக்கிறது. வருவாய் சுமார் நூற... |
| 70 | TA | மொத்தமாக எந்த quarter மோசமாக செயல்பட்டது... | PASS | 8.6s | 1 | _1_Sales_Quarterly_Performance | சரி, இதை பார்க்கும்போது, முதல் காலாண்டு இரண்டாயிரத்து இருபத்தி ஆறு மிக மோசமாக செ... |

### Trend Analysis

**Pass Rate:** 2/2 (100.0%)

| ID | Lang | Query | Status | Time | Rows | Table | Response |
|----|------|-------|--------|------|------|-------|----------|
| 58 | EN | What trends can be observed in sales ove... | PASS | 7.0s | 168 | Sales_Daily_Sales_Transactions | Looking at this, sales are pretty stable overall. They started around 3.3 lakhs ... |
| 58 | TA | காலப்போக்கில் sales trend எப்படி உள்ளது? | PASS | 9.0s | 168 | Sales_Daily_Sales_Transactions | இதைப் பார்க்கும்போது, விற்பனை போக்கு ஒட்டுமொத்தமாக மிகவும் நிலையானதாக இருக்கிறது... |

---

## Detailed Test Results

### Test #1 (EN) - PASS

**Category:** Daily Sales
**Query:** What is the total sale amount across all transactions?
**Time:** 6.90s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> Looking at this, the total sale amount across all transactions is about 5.5 crores. That's based on over 12 thousand transactions.

---

### Test #2 (EN) - PASS

**Category:** Daily Sales
**Query:** Which branch has the highest total sale amount?
**Time:** 6.80s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** extrema_lookup

**Response:**
> Looking at this, Jodhpur branch has the highest total sale amount. It's around 3.2 lakhs.

---

### Test #3 (EN) - PASS

**Category:** Daily Sales
**Query:** How many transactions were made using UPI?
**Time:** 6.80s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> Looking at this, there were about 2.4 thousand transactions made using UPI. That's based on the transaction data we have.

---

### Test #4 (EN) - PASS

**Category:** Daily Sales
**Query:** Show total profit amount for each state.
**Time:** 7.19s
**Rows:** 12
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> Looking at this, Tamil Nadu is leading in total profit with about 39.9 lakhs. Karnataka follows with roughly 18.4 lakhs, and Andhra Pradesh is around 15.5 lakhs.

---

### Test #5 (EN) - PASS

**Category:** Daily Sales
**Query:** Which category generated the highest profit?
**Time:** 4.81s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** rank

**Response:**
> Looking at this, TN_023 branch is generating the highest profit, with about 8.8 lakhs. AP_004 is next, with roughly 8.6 lakhs in profit.

---

### Test #6 (EN) - PASS

**Category:** Daily Sales
**Query:** What is the average profit margin percentage?
**Time:** 6.35s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> Looking at this, the average profit margin is about 60 percent. It's consistent across the board. Not bad, right?

---

### Test #7 (EN) - PASS

**Category:** Daily Sales
**Query:** List transactions where quantity sold is greater than 10.
**Time:** 7.18s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** filter

**Response:**
> Looking at this, these are transactions where more than 10 items were sold. For example, transaction `TXN_000019` in Vadodara sold 13 Sarees.

---

### Test #8 (EN) - PASS

**Category:** Daily Sales
**Query:** What is the total GST collected?
**Time:** 7.04s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> Looking at this, the total GST collected is about 5.5 crores. That's based on over 12 thousand transactions, with individual amounts ranging from about 200 to around 22 thousand.

---

### Test #9 (EN) - PASS

**Category:** Daily Sales
**Query:** Which SKU has the highest total sales amount?
**Time:** 6.97s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** extrema_lookup

**Response:**
> Looking at this, SKU_SAR_003 has the highest total sales amount. It's sitting at around 22 thousand. Not bad, right?

---

### Test #10 (EN) - PASS

**Category:** Daily Sales
**Query:** Show sales amount grouped by payment mode.
**Time:** 6.92s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> Looking at this, cheque is the most used payment mode with sales around 1.1 crore. Card, UPI and Online modes are close behind, each with sales of about 1.1 crore.

---

### Test #11 (EN) - PASS

**Category:** Daily Sales
**Query:** Find the transaction with the highest profit amount.
**Time:** 4.85s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> Sorry about that. Looking at this, cheque payments lead with about 1.1 crore, followed closely by card payments at about 1.1 crore as well. UPI, online, and cash payments are all around 1.08 crore.

---

### Test #12 (EN) - PASS

**Category:** Daily Sales
**Query:** What is the total cost amount across all sales?
**Time:** 6.76s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> Looking at this, the total cost amount across all sales is about 2.2 crores. The individual cost amounts range from about 80 to around 8900.

---

### Test #13 (EN) - PASS

**Category:** Daily Sales
**Query:** Show average unit price by category.
**Time:** 4.89s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** aggregation_on_subset

**Response:**
> Sorry about that. Looking at this, the total cost across all sales is about 43 lakhs. The costs ranged from about 3.2 lakhs to about 5.9 lakhs.

---

### Test #14 (EN) - PASS

**Category:** Daily Sales
**Query:** How many unique branches are present?
**Time:** 6.67s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** aggregation_on_subset

**Response:**
> Looking at this, there are 95 unique branches present in the dataset. The Branch IDs range from AP_001 to WB_004.

---

### Test #15 (EN) - PASS

**Category:** Daily Sales
**Query:** Compare total sales between two different states.
**Time:** 5.33s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** comparison

**Response:**
> Looking at this, the total sales between the two states are almost the same, around 2.4 crores each. So, there's no real difference in sales performance between them.

---

### Test #16 (EN) - PASS

**Category:** Monthly Analysis
**Query:** What is the total revenue for each month?
**Time:** 6.65s
**Rows:** 6
**Table Used:** Dataset_1_Sales_Monthly_Overall_Summary
**Query Type:** rank

**Response:**
> Looking at this, September had the highest total revenue at about 40 lakhs. Revenue was pretty consistent overall, ranging from about 39 lakhs down to 38.5 lakhs.

---

### Test #17 (EN) - PASS

**Category:** Monthly Analysis
**Query:** Which month recorded the highest total profit?
**Time:** 6.66s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Monthly_Overall_Summary
**Query Type:** extrema_lookup

**Response:**
> Looking at this, September 2025 recorded the highest total profit. It was about 24 lakhs. Not bad, right?

---

### Test #18 (EN) - PASS

**Category:** Monthly Analysis
**Query:** Show category-wise revenue for each month.
**Time:** 4.71s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** rank

**Response:**
> Alright, TN_023 branch is the top performer with a total profit of about 8.8 lakhs. Not bad, right?

---

### Test #19 (EN) - PASS

**Category:** Monthly Analysis
**Query:** Which category has the highest profit margin overall?
**Time:** 4.71s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** rank

**Response:**
> Looking at this, TN_023 branch is the top performer with a total profit of about 8.8 lakhs. Not bad, right?

---

### Test #20 (EN) - PASS

**Category:** Monthly Analysis
**Query:** What is the total profit for each category?
**Time:** 4.61s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** rank

**Response:**
> Looking at this, TN_023 branch recorded the highest total profit. It's around 8.8 lakhs.

---

### Test #21 (EN) - PASS

**Category:** Monthly Analysis
**Query:** Compare revenue between two categories.
**Time:** 7.34s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** comparison

**Response:**
> Looking at this, the revenue is almost the same for both categories. Each category generated about 1.2 crore in revenue. So, it's a pretty even split.

---

### Test #22 (EN) - PASS

**Category:** Monthly Analysis
**Query:** Which month has the highest number of transactions?
**Time:** 7.10s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> Okay, so October 2025 has the highest number of transactions. The count is around 2.3 thousand.

---

### Test #23 (EN) - PASS

**Category:** Monthly Analysis
**Query:** Show month-over-month sales growth.
**Time:** 7.06s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, sales are pretty stable overall. It started around 3.3 lakhs and ended at 3.4 lakhs. There was a peak in October around 4.6 lakhs.

---

### Test #24 (EN) - PASS

**Category:** Monthly Analysis
**Query:** What is the average profit margin per month?
**Time:** 6.63s
**Rows:** 6
**Table Used:** Dataset_1_Sales_Monthly_Overall_Summary
**Query Type:** list

**Response:**
> Looking at this, the average profit margin is consistently around 60 percent each month. It's been stable across all the months we've got data for.

---

### Test #25 (EN) - PASS

**Category:** Monthly Analysis
**Query:** Identify the worst performing category by profit.
**Time:** 4.89s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** aggregation_on_subset

**Response:**
> Looking at this, the average profit margin per month is about 60 percent. That's based on 10 months of data, with margins consistently at 60 percent.

---

### Test #31 (EN) - PASS

**Category:** State Performance
**Query:** Which state has the highest total revenue?
**Time:** 6.51s
**Rows:** 1
**Table Used:** Dataset_1_Sales_State_Performance
**Query Type:** extrema_lookup

**Response:**
> Looking at this, West Bengal has the highest total revenue. It's sitting at about 17.8 lakhs. That's the top performer!

---

### Test #32 (EN) - PASS

**Category:** State Performance
**Query:** Show profit margin by state.
**Time:** 6.66s
**Rows:** 12
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> Looking at this, Tamil Nadu has the highest profit margin at about 1700 percent. Karnataka follows with a profit margin of around 720 percent.

---

### Test #33 (EN) - PASS

**Category:** Branch Performance
**Query:** Which branch has the highest profit?
**Time:** 6.65s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** extrema_lookup

**Response:**
> Nashik branch has the highest profit, around 1.9 lakhs. Not bad, right?

---

### Test #34 (EN) - PASS

**Category:** Branch Performance
**Query:** Show top 5 branches by revenue.
**Time:** 6.45s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> Looking at this, Nellore branch is leading with about 5.7 lakhs in revenue. Hyderabad is next at around 5 lakhs.

---

### Test #35 (EN) - PASS

**Category:** Branch Performance
**Query:** Compare revenue between two branches.
**Time:** 7.28s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** comparison

**Response:**
> Looking at this, the revenue is almost identical between the two branches, both at about 2.42 crores. So, there's no real difference in revenue performance.

---

### Test #36 (EN) - PASS

**Category:** Branch Performance
**Query:** What is the average profit per branch?
**Time:** 6.47s
**Rows:** 95
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** list

**Response:**
> Looking at this, the average profit per branch is about 1.5 lakhs. It's calculated from 95 branches. Not bad, right?

---

### Test #37 (EN) - WARN

**Category:** Branch Performance
**Query:** Identify branches with negative profit.
**Time:** 5.53s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** filter

**Response:**
> No luck with that one! The data might be under a different name - want me to help you explore?

---

### Test #38 (EN) - PASS

**Category:** Branch Performance
**Query:** How many branches are there in each state?
**Time:** 6.32s
**Rows:** 12
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> Looking at this, Tamil Nadu has the most branches, with about 28. Karnataka follows with around 12 branches.

---

### Test #41 (EN) - PASS

**Category:** Payment Analysis
**Query:** Which payment mode has the highest transaction count?
**Time:** 4.59s
**Rows:** 12
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> Looking at this, Tamil Nadu has the most branches, with about 28. Karnataka's next with 12, followed by Maharashtra and Andhra Pradesh, both at 10.

---

### Test #42 (EN) - PASS

**Category:** Payment Analysis
**Query:** Show revenue distribution by payment mode.
**Time:** 6.72s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Payment_Mode_Analysis
**Query Type:** rank

**Response:**
> Looking at this, Cash and UPI are the top payment modes, each generating about 1 crore. Online and Card payments are also significant, bringing in around 99 lakhs and 88 lakhs respectively.

---

### Test #43 (EN) - PASS

**Category:** Cost Analysis
**Query:** What is the total cost vs total revenue comparison?
**Time:** 7.42s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** comparison

**Response:**
> Looking at this, total revenue is significantly higher than total cost. The total revenue is about 2.42 crores, while the total cost is around 92 lakhs. That's a difference of about 1.5 crores!

---

### Test #44 (EN) - PASS

**Category:** Cost Analysis
**Query:** Which month has the highest cost amount?
**Time:** 6.45s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Monthly_Overall_Summary
**Query Type:** extrema_lookup

**Response:**
> Okay, September 2025 has the highest total cost at about 16 lakhs. That's the peak for cost amount in the dataset.

---

### Test #45 (EN) - PASS

**Category:** Quarterly Analysis
**Query:** Show profit margin trend across quarters.
**Time:** 6.49s
**Rows:** 3
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** trend

**Response:**
> Looking at this, the profit margin trend is decreasing. It started around 71 lakhs and dropped to about 13 lakhs. That's a decrease of roughly 82 percent.

---

### Test #46 (EN) - PASS

**Category:** Quarterly Analysis
**Query:** Which quarter generated the highest profit?
**Time:** 6.31s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** extrema_lookup

**Response:**
> Looking at this, Q3 2025 generated the highest profit. It's about 71 lakhs. Not bad, right?

---

### Test #47 (EN) - PASS

**Category:** Quarterly Analysis
**Query:** What is the total profit per quarter?
**Time:** 6.40s
**Rows:** 3
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** rank

**Response:**
> Looking at this, Q3 2025 had the highest profit at about 71 lakhs. However, profit dropped significantly to about 12.6 lakhs in Q1 2026.

---

### Test #48 (EN) - PASS

**Category:** SKU Analysis
**Query:** Which SKU sold the highest number of units?
**Time:** 7.43s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> Looking at this, Sarees sold the highest number of units, with a quantity of around 10.9 thousand. Ladies Wear is a close second, also at about 10.9 thousand.

---

### Test #49 (EN) - PASS

**Category:** SKU Analysis
**Query:** Show top 5 SKUs by total revenue.
**Time:** 6.69s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> Looking at this, Sarees are the top-selling SKU with sales of about 1.25 crores. Ethnic Kurtas are next, at around 75 lakhs.

---

### Test #50 (EN) - PASS

**Category:** SKU Analysis
**Query:** Which SKU has the highest profit margin?
**Time:** 6.32s
**Rows:** 1
**Table Used:** Dataset_1_Sales_SKU_Performance
**Query Type:** extrema_lookup

**Response:**
> Looking at this, the Dhoti SKU with ID SKU_DHT_001 has the highest profit margin. It's sitting pretty at about 60 percent!

---

### Test #51 (EN) - PASS

**Category:** SKU Analysis
**Query:** Compare revenue and cost for each SKU.
**Time:** 6.44s
**Rows:** 24
**Table Used:** Dataset_1_Sales_SKU_Performance
**Query Type:** list

**Response:**
> Looking at this, revenue is significantly higher than cost for each SKU. For example, SKU_DHT_001 has a revenue of about 14 lakhs, while its cost is around 5.5 lakhs.

---

### Test #52 (EN) - WARN

**Category:** SKU Analysis
**Query:** Identify SKUs that are running at a loss.
**Time:** 5.86s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** filter

**Response:**
> Aww, nothing came up for that search! Let's try tweaking the criteria - what do you think?

---

### Test #53 (EN) - PASS

**Category:** SKU Analysis
**Query:** What is the average cost per unit across SKUs?
**Time:** 6.53s
**Rows:** 24
**Table Used:** Dataset_1_Sales_SKU_Performance
**Query Type:** list

**Response:**
> Looking at this, the average cost per unit across all SKUs is about 280 rupees. The costs seem to range between 180 to 340 rupees per unit.

---

### Test #54 (EN) - PASS

**Category:** SKU Analysis
**Query:** Show category-wise SKU profit contribution.
**Time:** 4.25s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> Looking at this, the average unit price across SKUs varies. It ranges from about 250 to around 675.

---

### Test #55 (EN) - PASS

**Category:** Category Analysis
**Query:** Which category contributes most to total revenue?
**Time:** 4.55s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> Sorry about that. Looking at this, the average unit price across SKUs varies. It ranges from about 250 to around 675.

---

### Test #56 (EN) - PASS

**Category:** Quarterly Analysis
**Query:** Compare quarterly revenue growth.
**Time:** 6.81s
**Rows:** 3
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** trend

**Response:**
> Looking at this, there's a decreasing trend in quarterly revenue. It dropped significantly from about 1.2 crores in July 2025 to around 21 lakhs in January 2026. That's a decrease of roughly 82 percent.

---

### Test #57 (EN) - PASS

**Category:** Analysis
**Query:** Explain why a particular month has low profit.
**Time:** 6.93s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, the sales trend is pretty stable overall. It started around 1.97 lakhs and ended around 2.06 lakhs, but there was a peak in October at about 2.74 lakhs. There also seems to be an unusual spike.

---

### Test #58 (EN) - PASS

**Category:** Trend Analysis
**Query:** What trends can be observed in sales over time?
**Time:** 6.97s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, sales are pretty stable overall. They started around 3.3 lakhs and ended at 3.4 lakhs. There was a peak around mid-October at about 4.6 lakhs.

---

### Test #59 (EN) - PASS

**Category:** Analysis
**Query:** Which factor affects profit the most: cost or sales?
**Time:** 6.93s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> Looking at the numbers, sales seems to drive profit more than cost. Higher sales months consistently show better margins - cost is pretty stable.

---

### Test #60 (EN) - PASS

**Category:** Summary
**Query:** Give a high-level business summary of this dataset.
**Time:** 4.85s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Monthly_Category_Summary
**Query Type:** list

**Response:**
> Looking at this, Inner Wear is the top performer with a profit of about 2.8 lakhs. Dhoti and Kids Wear also contribute significantly, each with profits around 1.8 lakhs. Overall, the business seems healthy!

---

### Test #61 (EN) - PASS

**Category:** Trend
**Query:** Are sales increasing or decreasing in Chennai?
**Time:** 6.58s
**Rows:** 36
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, Chennai sales show a decreasing trend. It started around 5.4 thousand and ended at 3.2 thousand. There was a peak in October around 12.7 thousand.

---

### Test #62 (EN) - PASS

**Category:** Trend
**Query:** Which state shows a declining sales trend?
**Time:** 7.01s
**Rows:** 12
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Actually, no state shows a declining sales trend - all are stable. Tamil Nadu's sales went from about 3.5 lakhs to 2.4 lakhs, but it's still considered stable.

---

### Test #63 (EN) - WARN

**Category:** Trend
**Query:** Which category shows consistent growth across months?
**Time:** 3.61s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** trend

**Response:**
> No luck with that one! The data might be under a different name - want me to help you explore?

---

### Test #64 (EN) - PASS

**Category:** Trend
**Query:** Are profits stable or volatile over time?
**Time:** 7.11s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, profits are pretty stable overall. They started around 1.97 lakhs and ended at 2.06 lakhs. There was a peak in October at about 2.7 lakhs.

---

### Test #65 (EN) - PASS

**Category:** Trend
**Query:** Which month had an unusual spike in sales?
**Time:** 6.42s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, October 2025 had an unusual spike in sales. The peak was around 4.6 lakhs on October 17th.

---

### Test #66 (EN) - PASS

**Category:** Trend
**Query:** Is revenue seasonally higher in certain months?
**Time:** 6.48s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, the sales trend is pretty stable. It started around 3.3 lakhs and ended at 3.4 lakhs. There was a peak around October 17th at about 4.6 lakhs.

---

### Test #67 (EN) - PASS

**Category:** Trend
**Query:** Which branch shows declining performance?
**Time:** 7.27s
**Rows:** 93
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, Tiruppur shows the most decline. It went down about 94 percent, from around 24 thousand to about 1.5 thousand.

---

### Test #68 (EN) - WARN

**Category:** Trend
**Query:** Which category is losing revenue month by month?
**Time:** 3.56s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** trend

**Response:**
> Hmm, I couldn't find any data for that! Want to try a different filter or spelling?

---

### Test #69 (EN) - PASS

**Category:** Trend
**Query:** Are costs rising faster than revenue?
**Time:** 7.26s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** comparison

**Response:**
> Looking at this, revenue is rising faster than cost. Revenue is about 5.5 crores, while cost is around 2.2 crores - that's a difference of about 150 percent.

---

### Test #70 (EN) - PASS

**Category:** Trend
**Query:** Which quarter performed the worst overall?
**Time:** 3.04s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** comparison

**Response:**
> Looking at this, costs are rising much faster than revenue. Costs increased about 150 percent more than revenue. That's a pretty big difference!

---

### Test #71 (EN) - PASS

**Category:** Projection Chain 1
**Query:** Compare total sales between November and December.
**Time:** 6.33s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** comparison

**Response:**
> Looking at this, December sales are slightly higher than November. December's at about 1 crore, compared to November's 99 lakhs - that's an increase of roughly 1 percent.

---

### Test #72 (EN) - PASS

**Category:** Projection Chain 1
**Query:** If the same trend continues, what could be the projected sales for January?
**Time:** 2.04s
**Rows:** 1
**Table Used:** 
**Query Type:** 

**Response:**
> Based on current trends, January sales would be around 0. The stable trend suggests values will remain similar.

---

### Test #73 (EN) - PASS

**Category:** Projection Chain 2
**Query:** Show sales trend for Chennai across months.
**Time:** 6.93s
**Rows:** 36
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, Chennai sales show a decreasing trend. It started around 5.4 thousand and ended at 3.2 thousand. There was a peak in October at about 12.7 thousand.

---

### Test #74 (EN) - PASS

**Category:** Projection Chain 2
**Query:** Based on this trend, estimate next month's sales.
**Time:** 2.07s
**Rows:** 1
**Table Used:** 
**Query Type:** 

**Response:**
> Based on current trends, Next Month sales would be around 0. That's about around 3 thousand (100%) down from current.

---

### Test #75 (EN) - PASS

**Category:** Projection Chain 3
**Query:** Show category-wise sales for the last three months.
**Time:** 4.54s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** trend

**Response:**
> Looking at this, the sales trend is decreasing. It started around 13.8 lakhs and ended at about 8.5 lakhs. If this trend continues, next month's sales could be around 8.1 lakhs.

---

### Test #76 (EN) - PASS

**Category:** Projection Chain 3
**Query:** If the top category continues this pattern, what is the expected sales next month?
**Time:** 4.66s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** trend

**Response:**
> Looking at this, the top category sales are decreasing. If the trend continues, next month's sales for Ethnic Kurtas would be around 14 lakhs, about 39 thousand less than this month.

---

### Test #77 (EN) - PASS

**Category:** Projection Chain 4
**Query:** Compare revenue for a branch between two consecutive months.
**Time:** 7.34s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** comparison

**Response:**
> Looking at this, the revenue is stable between the two months. It's around 5.4 crores in both the previous and current month. No change there!

---

### Test #78 (EN) - PASS

**Category:** Projection Chain 4
**Query:** Project the next month's revenue assuming similar change.
**Time:** 2.04s
**Rows:** 1
**Table Used:** 
**Query Type:** 

**Response:**
> Based on current trends, Next Month sales would be around 0. The stable trend suggests values will remain similar.

---

### Test #79 (EN) - PASS

**Category:** Projection Chain 5
**Query:** Show last 3 months sales for a SKU.
**Time:** 6.89s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, sales are pretty stable. Started around 3.3 lakhs, ended at 3.4 lakhs. There was a peak in October around 4.6 lakhs.

---

### Test #80 (EN) - PASS

**Category:** Projection Chain 5
**Query:** If this trend continues, what could be the sales next month?
**Time:** 2.06s
**Rows:** 1
**Table Used:** 
**Query Type:** 

**Response:**
> Based on the strong trend, Next Month sales would be around about 3.4 lakhs. That's about 17.97 (0%) up from current.

---

### Test #81 (EN) - PASS

**Category:** Follow-up Chain 1
**Query:** What is the total sales in Tamil Nadu?
**Time:** 7.25s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> Looking at this, total sales in Tamil Nadu is about 46 lakhs. That's based on over a thousand transactions, with individual sales ranging from about 320 to around 21 thousand.

---

### Test #82 (EN) - PASS

**Category:** Follow-up Chain 1
**Query:** Is it higher or lower compared to Karnataka?
**Time:** 5.38s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** comparison

**Response:**
> Karnataka is slightly higher. Sales in Karnataka are about 47.3 lakhs, compared to Tamil Nadu's 46.3 lakhs. That's a difference of around one lakh.

---

### Test #83 (EN) - PASS

**Category:** Follow-up Chain 2
**Query:** Which category has the highest total sales?
**Time:** 5.32s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** comparison

**Response:**
> Looking at this, the total sales is about 1.2 crore, which is much higher than Karnataka's sales of about 35 lakhs. That's a decrease of roughly 70 percent.

---

### Test #84 (EN) - PASS

**Category:** Follow-up Chain 2
**Query:** Did sales for this category increase or decrease over time?
**Time:** 5.33s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** comparison

**Response:**
> Looking at this, sales decreased compared to Karnataka. The current value is about 1.2 crore, while Karnataka is at about 35 lakhs - a decrease of roughly 70 percent.

---

### Test #85 (EN) - PASS

**Category:** Follow-up Chain 3
**Query:** Which branch has the highest revenue overall?
**Time:** 3.29s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** comparison

**Response:**
> Looking at this, the current value is higher than Karnataka's. It's about 1.2 crores compared to about 35 lakhs in Karnataka, so a pretty big difference.

---

### Test #86 (EN) - PASS

**Category:** Follow-up Chain 3
**Query:** Is this branch performing better or worse than the average branch?
**Time:** 5.44s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** comparison

**Response:**
> Looking at this, this branch is underperforming compared to the average. Its sales are about 1.2 crore, while the average branch hits about 12 lakhs. That's a decrease of roughly 90 percent.

---

### Test #87 (EN) - PASS

**Category:** Follow-up Chain 4
**Query:** Which payment mode has the highest sales amount?
**Time:** 7.06s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Payment_Mode_Analysis
**Query Type:** extrema_lookup

**Response:**
> Looking at this, cash is the most popular payment method. Total revenue from cash payments is about 1.09 crores.

---

### Test #88 (EN) - PASS

**Category:** Follow-up Chain 4
**Query:** Has the usage of this payment mode increased over the months?
**Time:** 7.30s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at the payment modes, they're all pretty stable. Cash saw the biggest increase, up about 187 percent, while UPI decreased by about 66 percent.

---

### Test #89 (EN) - PASS

**Category:** Follow-up Chain 5
**Query:** Which SKU has the highest total revenue?
**Time:** 6.83s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> Looking at this, Sarees are the top performer with sales of about 1.25 crores. Ethnic Kurtas come in second, with roughly 75 lakhs in sales.

---

### Test #90 (EN) - PASS

**Category:** Follow-up Chain 5
**Query:** Is this SKU's sales trend consistently increasing?
**Time:** 6.23s
**Rows:** 24
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> Looking at this, the sales trend for all SKUs is generally stable. For example, SKU_IWR_001 starts around 6 thousand and ends around 16 thousand. So, there aren't any consistently increasing trends.

---

### Test #91 (EN) - PASS

**Category:** Advanced
**Query:** Which state moved from being a top 3 revenue contributor in the early months to a bottom 3 contributor in the later months?
**Time:** 7.68s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> Looking at this, no state fits that description perfectly. Sales fluctuate, but no state consistently moved from top to bottom.

---

### Test #92 (EN) - PASS

**Category:** Advanced
**Query:** Is there any category that ranks high in total sales amount but low in total profit amount?
**Time:** 5.04s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> Looking at this, some categories have high total revenue but might not translate to high profit. For example, Inner Wear has a total revenue of about 12 lakhs, but its profit amount might be lower compared to other categories. Checking the profit margins for each category would give a clearer picture.

---

### Test #93 (EN) - PASS

**Category:** Advanced
**Query:** Are there branches where more than 50% of total sales come from a single payment mode?
**Time:** 8.07s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> Looking at this, yes, there are branches where a single payment mode accounts for over 50 percent of sales. For example, in Warangal, most transactions are done via cash.

---

### Test #94 (EN) - PASS

**Category:** Advanced
**Query:** Among the top 5 SKUs by revenue, which SKU has the highest cost relative to its revenue?
**Time:** 7.68s
**Rows:** 5
**Table Used:** Dataset_1_Sales_SKU_Performance
**Query Type:** rank

**Response:**
> Looking at this, Accessories top the revenue charts at about 51 lakhs. Sarees are next, with roughly 28 lakhs in revenue.

---

### Test #95 (EN) - PASS

**Category:** Advanced
**Query:** Is there any month where sales increased compared to the previous month, but profit decreased?
**Time:** 7.89s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> Looking at the data, there are months where sales increased but profit decreased. For example, in some months sales went up by around 10 thousand, but profit dropped by about 5 thousand.

---

### Test #96 (EN) - PASS

**Category:** Edge Case
**Query:** Show me XYZ department
**Time:** 6.75s
**Rows:** 0
**Table Used:** Dataset_2_Attendance_Attendance_Records
**Query Type:** filter

**Response:**
> Oops! Looks like there's no data matching that. Maybe try a different date range or check the spelling?

---

### Test #97 (EN) - WARN

**Category:** Edge Case
**Query:** Sales in Mars
**Time:** 5.98s
**Rows:** 100
**Table Used:** Dataset_2_Attendance_Attendance_Records
**Query Type:** filter

**Response:**
> Okay, this shows attendance records filtered to just the Sales department. There are 100 records in total. The data includes the date, employee ID, name, check-in/out times, status, and hours worked.

---

### Test #98 (EN) - PASS

**Category:** Edge Case
**Query:** Dhoti sales in January
**Time:** 8.52s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> Looking at this, there were no Dhoti sales in January of 2025. The data shows zero sales for that period.

---

### Test #99 (EN) - PASS

**Category:** Edge Case
**Query:** abcdefg
**Time:** 3.03s
**Rows:** 0
**Table Used:** 
**Query Type:** 

**Response:**
> Hey! Great to see you! What would you like to look at today?

---

### Test #100 (EN) - WARN

**Category:** Edge Case
**Query:** Show me nothing
**Time:** 4.91s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> Okay, I've got nothing to show from the data. Is there anything specific you'd like to explore?

---

### Test #101 (EN) - WARN

**Category:** Edge Case
**Query:** What is the sales of product ABC123?
**Time:** 6.44s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** filter

**Response:**
> Hmm, I couldn't find any data for that! Want to try a different filter or spelling?

---

### Test #102 (EN) - PASS

**Category:** Edge Case
**Query:** Revenue for branch Timbuktu
**Time:** 6.60s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** lookup

**Response:**
> Hmm, I couldn't find any data for that! Want to try a different filter or spelling?

---

### Test #103 (EN) - PASS

**Category:** Edge Case
**Query:** Employee named Superman
**Time:** 3.01s
**Rows:** 0
**Table Used:** 
**Query Type:** 

**Response:**
> Hey! Great to see you! What would you like to look at today?

---

### Test #104 (EN) - PASS

**Category:** Edge Case
**Query:** Attendance for February 2020
**Time:** 2.04s
**Rows:** 0
**Table Used:** 
**Query Type:** 

**Response:**
> Okay, February - noted! Now, what can I help you find?

---

### Test #105 (EN) - PASS

**Category:** Greeting
**Query:** Hello, how are you?
**Time:** 2.92s
**Rows:** 0
**Table Used:** 
**Query Type:** 

**Response:**
> I'm doing well, thanks for asking! How can I help you with your data today?

---

### Test #1 (TA) - PASS

**Category:** Daily Sales
**Query:** அனைத்து transaction-களின் மொத்த sale amount என்ன?
**Time:** 6.97s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> இதைப் பார்க்கும்போது, "டிம்பக்டு" என்று பொருந்தக்கூடிய எந்த கிளைக்கும் வருவாய் தரவு இல்லை. எந்தவொரு பொருந்தக்கூடிய கிளை பெயர்களையும் கணினி கண்டுபிடிக்கவில்லை.

---

### Test #2 (TA) - PASS

**Category:** Daily Sales
**Query:** அதிகமான மொத்த விற்பனை கொண்ட branch எது?
**Time:** 9.00s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்க்கும்போது, ஜோத்பூர் கிளை அதிக மொத்த விற்பனையைக் கொண்டுள்ளது. இது ஏறக்குறைய மூன்று லட்சத்து இருபதாயிரம் இருக்கும்.

---

### Test #3 (TA) - PASS

**Category:** Daily Sales
**Query:** UPI மூலம் எத்தனை transactions செய்யப்பட்டுள்ளன?
**Time:** 9.35s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> இதைப் பார்க்கும்போது, UPI மூலம் சுமார் இரண்டாயிரத்து நானூறு பரிவர்த்தனைகள் நடந்துள்ளன. அது கிடைக்கக்கூடிய தரவுகளின் அடிப்படையில்.

---

### Test #4 (TA) - PASS

**Category:** Daily Sales
**Query:** ஒவ்வொரு state-க்கும் மொத்த profit amount-ஐ காட்டு.
**Time:** 10.58s
**Rows:** 12
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> இதைப் பார்க்கையில், மொத்த லாபத்தில் தமிழ்நாடு சுமார் நாற்பது லட்சம் ரூபாயுடன் முன்னிலையில் உள்ளது. கர்நாடகா தோராயமாக பதினெட்டு லட்சம் ரூபாயுடன் அதைத் தொடர்கிறது, மற்றும் ஆந்திரப் பிரதேசம் சுமார் பதினைந்து லட்சம் ரூபாயாக உள்ளது.

---

### Test #5 (TA) - PASS

**Category:** Daily Sales
**Query:** அதிக profit உருவாக்கிய category எது?
**Time:** 6.20s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, டிஎன் பூஜ்ஜியம் இருபத்தி மூன்று கிளை சுமார் எட்டு லட்சத்து எண்பதாயிரம் லாபத்துடன் முன்னிலையில் உள்ளது. ஏபி பூஜ்ஜியம் பூஜ்ஜியம் நான்கு அடுத்ததாக, தோராயமாக எட்டு லட்சத்து அறுபதாயிரம் லாபத்துடன் உள்ளது.

---

### Test #6 (TA) - PASS

**Category:** Daily Sales
**Query:** சராசரி profit margin percentage என்ன?
**Time:** 9.76s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, சராசரி லாப வரம்பு சுமார் அறுபது சதவீதம். இது எல்லா இடங்களிலும் ஒரே மாதிரியாக உள்ளது. அவ்வளவு மோசமில்லை, சரியா?

---

### Test #7 (TA) - PASS

**Category:** Daily Sales
**Query:** Quantity 10-க்கு மேல் உள்ள transactions-ஐ காட்டு.
**Time:** 10.69s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** filter

**Response:**
> இதைப் பார்க்கும்போது, இவை பத்து பொருட்களுக்கு மேல் உள்ள பரிவர்த்தனைகள். உதாரணமாக, ஒரு பரிவர்த்தனையில் பதினான்கு நைட்வேர் பொருட்கள் வாராங்கலில் விற்பனையானதாகக் காட்டுகிறது.

---

### Test #8 (TA) - PASS

**Category:** Daily Sales
**Query:** மொத்தமாக வசூலிக்கப்பட்ட GST எவ்வளவு?
**Time:** 9.94s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> இதனைப் பார்க்கும்போது, வசூலிக்கப்பட்ட மொத்த ஜிஎஸ்டி ஏறத்தாழ ஐந்து புள்ளி ஐந்து கோடி ஆகும். அது பன்னிரெண்டாயிரத்துக்கு மேற்பட்ட பரிவர்த்தனைகளின் அடிப்படையில் கணக்கிடப்பட்டது, இதில் தனிப்பட்ட தொகைகள் ஏறத்தாழ இருநூறிலிருந்து இருபத்திரண்டாயிரம் வரை வேறுபடுகின்றன.

---

### Test #9 (TA) - PASS

**Category:** Daily Sales
**Query:** அதிகமான மொத்த விற்பனை கொண்ட SKU எது?
**Time:** 10.72s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> இதைப் பார்க்கையில், சேலைகள் ஏறக்குறைய ஒரு கோடியே இருபத்தைந்து லட்சம் விற்பனையுடன் முதலிடத்தில் உள்ளன. எத்னிக் குர்தாக்கள் அடுத்ததாக, சுமார் எழுபத்தைந்து லட்சத்தில் உள்ளன.

---

### Test #10 (TA) - PASS

**Category:** Daily Sales
**Query:** Payment mode அடிப்படையில் sales amount-ஐ காட்டு.
**Time:** 11.26s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, காசோலை கொடுப்பனவுகள் ஏறத்தாழ ஒன்று புள்ளி ஒன்று கோடி உடன் முன்னணியில் உள்ளன, அதைத் தொடர்ந்து அட்டை கொடுப்பனவுகளும் ஏறத்தாழ ஒன்று புள்ளி ஒன்று கோடி உடன் நெருக்கமாக உள்ளன. யுபிஐ, இணையம் மற்றும் ரொக்கக் கொடுப்பனவுகளும் ஒவ்வொன்றும் ஏறத்தாழ ஒன்று புள்ளி ஒன்று கோடி ஆக உள்ளன.

---

### Test #11 (TA) - PASS

**Category:** Daily Sales
**Query:** அதிக profit amount கொண்ட transaction எது?
**Time:** 7.27s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> சரியா, காசோலை செலுத்துதல்கள் ஏறத்தாழ ஒரு கோடியே பத்து இலட்சம் விற்பனையுடன் முன்னணியில் உள்ளன. அட்டை, யூபிஐ, மற்றும் இணையவழி செலுத்துதல்கள் அனைத்தும் கிட்டத்தட்ட ஒரே அளவில், ஒவ்வொன்றும் ஒரு கோடியே பத்து இலட்சம் என்ற அளவில் உள்ளன.

---

### Test #12 (TA) - PASS

**Category:** Daily Sales
**Query:** அனைத்து sales-களின் மொத்த cost amount என்ன?
**Time:** 10.33s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> இதைப் பார்க்கும்போது, அனைத்து விற்பனைகளுக்கான மொத்த செலவுத் தொகை சுமார் இரண்டு கோடியே இருபது லட்சம் இருக்கும். அது பன்னிரண்டாயிரத்துக்கும் அதிகமான பரிவர்த்தனைகளின் அடிப்படையில் கணக்கிடப்பட்டது, இதில் தனிப்பட்ட செலவுகள் சுமார் எண்பதில் இருந்து சுமார் எண்ணாயிரத்து தொள்ளாயிரம் வரை இருக்கும்.

---

### Test #13 (TA) - PASS

**Category:** Daily Sales
**Query:** Category வாரியாக சராசரி unit price-ஐ காட்டு.
**Time:** 6.25s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** aggregation_on_subset

**Response:**
> இதைப் பார்க்கையில், அனைத்து விற்பனைகளின் மொத்த விலை சுமார் நாற்பத்திரண்டு லட்சத்து எண்பதாயிரம். செலவுகள், விற்பனை பிரிவுகளின் அடிப்படையில் சுமார் மூன்று லட்சத்து இருபதாயிரத்திலிருந்து அதிகபட்சமாக சுமார் ஐந்து லட்சத்து தொண்ணூறாயிரம் வரை உள்ளன.

---

### Test #14 (TA) - PASS

**Category:** Daily Sales
**Query:** எத்தனை தனித்தனி branches உள்ளன?
**Time:** 9.15s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** aggregation_on_subset

**Response:**
> சற்று கவனியுங்கள், இந்த தரவுத் தொகுப்பில் தொண்ணூற்று ஐந்து தனித்துவமான கிளைகள் உள்ளன. கிளையின் அடையாள எண்கள் ஏபி பூஜ்ஜியம் பூஜ்ஜியம் ஒன்று என்பதிலிருந்து டபிள்யூபி பூஜ்ஜியம் பூஜ்ஜியம் நான்கு வரை உள்ளன.

---

### Test #15 (TA) - PASS

**Category:** Daily Sales
**Query:** இரண்டு state-களின் மொத்த sales-ஐ ஒப்பிடு.
**Time:** 8.03s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, மாநிலம் அ ஏறத்தாழ எழுபது லட்சம் விற்பனையில் முன்னணியில் உள்ளது. மாநிலம் ஆ ஏறத்தாழ முப்பத்தொன்று லட்சம் விற்பனையில் உள்ளது - இது ஏறத்தாழ முப்பத்தொன்பது லட்சம் வித்தியாசம் ஆகும்.

---

### Test #16 (TA) - PASS

**Category:** Monthly Analysis
**Query:** ஒவ்வொரு மாதத்திற்கும் மொத்த வருமானம் என்ன?
**Time:** 9.34s
**Rows:** 6
**Table Used:** Dataset_1_Sales_Monthly_Overall_Summary
**Query Type:** rank

**Response:**
> சரி, இதோ மொழிபெயர்ப்பு:

இதைப் பார்க்கும்போது, செப்டம்பர் மாதம் நாற்பது லட்ச ரூபாய் வருவாயுடன் அதிக வருவாய் ஈட்டியுள்ளது. ஒட்டுமொத்தமாக, மாத வருவாய் சுமார் முப்பத்து எட்டு லட்ச ரூபாய்க்கும் நாற்பது லட்ச ரூபாய்க்கும் இடையில் உள்ளது.

---

### Test #17 (TA) - PASS

**Category:** Monthly Analysis
**Query:** அதிக profit பெற்ற மாதம் எது?
**Time:** 8.75s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Monthly_Overall_Summary
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்த்தால், செப்டம்பர் இரண்டாயிரத்து இருபத்தைந்து அதிக லாபம் ஈட்டிய மாதம். இது சுமார் இருபத்து நான்கு லட்சம்.

---

### Test #18 (TA) - PASS

**Category:** Monthly Analysis
**Query:** ஒவ்வொரு மாதத்திற்கும் category வாரியான revenue-ஐ காட்டு.
**Time:** 6.91s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, அனைத்து வகைகளிலும் அறுபது சதவீத லாப வரம்பு உள்ளது. உள்ளாடைகள் சுமார் பன்னிரெண்டு லட்சத்து இரண்டு நூறாயிரம் ரூபாய்கள் வருவாய் ஈட்டுகின்றன, அதே சமயம் பாரம்பரிய சட்டைகள் அறுநூற்று எழுபத்தைந்து ரூபாயில் மிக உயர்ந்த சராசரி அலகு விலையைக் கொண்டுள்ளன.

---

### Test #19 (TA) - PASS

**Category:** Monthly Analysis
**Query:** மொத்தமாக அதிக profit margin கொண்ட category எது?
**Time:** 6.62s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, உள்ளாடைகளுக்கு சுமார் பன்னிரெண்டு லட்சத்து இருபதாயிரம் ரூபாய் வருவாய் அதிகமாக உள்ளது. குழந்தைகள் உடைகள் பதினோரு லட்சத்து தொண்ணூறாயிரம் ரூபாய் வருவாயுடன் இரண்டாவது இடத்தில் உள்ளது.

---

### Test #20 (TA) - PASS

**Category:** Monthly Analysis
**Query:** ஒவ்வொரு category-க்கும் மொத்த profit என்ன?
**Time:** 6.56s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> இதைப் பார்க்கையில், உள்ளாடைகள் தோராயமாக பன்னிரண்டு லட்சத்து இருபதாயிரம் வருவாய் ஈட்டுகின்றன. ஆண்களுக்கான டீ-ஷர்ட்டுகள் மற்றும் வேஷ்டிகள் கிட்டத்தட்ட அதே வரிசையில் உள்ளன, ஒவ்வொன்றும் தோராயமாக பதினொரு லட்சம் வருவாய் ஈட்டுகின்றன.

---

### Test #21 (TA) - PASS

**Category:** Monthly Analysis
**Query:** இரண்டு category-களின் revenue-ஐ ஒப்பிடு.
**Time:** 6.70s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, உள்ளாடைகள் மற்றும் ஆண்களுக்கான டி-ஷர்ட்டுகள் அதிக வருவாயைக் கொண்டுள்ளன, இரண்டும் சுமார் பன்னிரண்டு லட்சம். வேட்டி மற்றும் குழந்தைகளுக்கான ஆடைகள் அடுத்த இடத்தில் உள்ளன, ஒவ்வொன்றும் சுமார் பதினோரு லட்சம் வருவாயைக் கொண்டுள்ளன.

---

### Test #22 (TA) - PASS

**Category:** Monthly Analysis
**Query:** அதிக transactions நடந்த மாதம் எது?
**Time:** 9.19s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, அக்டோபர் இரண்டாயிரத்து இருபத்தைந்து அதிகமான பரிவர்த்தனைகளைக் கொண்டிருந்தது, சுமார் இரண்டாயிரத்து முந்நூறுடன். அது தரவுத் தொகுப்பில் உள்ள மிக உயர்ந்த எண்ணிக்கை.

---

### Test #23 (TA) - PASS

**Category:** Monthly Analysis
**Query:** மாதம் வாரியாக sales growth-ஐ காட்டு.
**Time:** 9.52s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> இதைப் பார்க்கும்போது, விற்பனை ஒட்டுமொத்தமாக மிகவும் நிலையாக உள்ளது. இது தோராயமாக மூன்று லட்சத்து முப்பதாயிரத்தில் தொடங்கி மூன்று லட்சத்து நாற்பதாயிரத்தில் முடிந்தது. அக்டோபரில் தோராயமாக நான்கு லட்சத்து அறுபதாயிரத்தில் உச்சம் இருந்தது.

---

### Test #24 (TA) - PASS

**Category:** Monthly Analysis
**Query:** ஒவ்வொரு மாதத்திற்கும் சராசரி profit margin என்ன?
**Time:** 9.90s
**Rows:** 6
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, சராசரி லாப வரம்பு மாதம் மாதம் ஏறக்குறைய நிலையாக உள்ளது. இது சுமார் இரண்டு புள்ளி ஏழு ஆயிரம் ஆக உள்ளது. டிசம்பரில் மட்டும் இரண்டு புள்ளி ஆறு ஆயிரம் ஆக சற்று குறைந்துள்ளது.

---

### Test #25 (TA) - PASS

**Category:** Monthly Analysis
**Query:** profit அடிப்படையில் மிகக் குறைந்த category எது?
**Time:** 5.97s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, சராசரி இலாப வரம்பு அனைத்து வகைகளிலும் அறுபது சதவீதம் ஆகும். அதில் புடவைகள், வேஷ்டி, உள்ளாடைகள், அணிகலன்கள் மற்றும் இரவு உடைகள் ஆகியவை அடங்கும்.

---

### Test #31 (TA) - PASS

**Category:** State Performance
**Query:** அதிக மொத்த revenue கொண்ட state எது?
**Time:** 8.85s
**Rows:** 1
**Table Used:** Dataset_1_Sales_State_Performance
**Query Type:** extrema_lookup

**Response:**
> பயனர் தமிழில் கேட்பது போல் தெரிகிறது, அதனால் நான் ஆங்கிலத்தில் பதிலளிக்கிறேன், ஆனால் தமிழின் தோற்றத்தை ஒப்புக்கொள்கிறேன்.

இதை பார்க்கும்போது, மேற்கு வங்காளம் அதிக வருவாயை கொண்டுள்ளது. இது சுமார் பதினேழு புள்ளி எட்டு லட்சம்.

---

### Test #32 (TA) - PASS

**Category:** State Performance
**Query:** State வாரியாக profit margin-ஐ காட்டு.
**Time:** 8.81s
**Rows:** 12
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, தமிழ்நாடு ஏறக்குறைய பதினேழு லட்சத்தில் அதிக லாப வரம்பைக் கொண்டுள்ளது. கர்நாடகா ஏறக்குறைய ஏழு லட்சத்து இருபதாயிரம் லாப வரம்புடன் பின்தொடர்கிறது.

---

### Test #33 (TA) - PASS

**Category:** Branch Performance
**Query:** அதிக profit கொண்ட branch எது?
**Time:** 8.26s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்க்கையில், நாசிக் கிளை அதிக லாபம் ஈட்டியுள்ளது. அதன் மொத்த லாபம் சுமார் ஒன்று புள்ளி ஒன்பது லட்சம். அவ்வளவு மோசமில்லை, சரியா?

---

### Test #34 (TA) - PASS

**Category:** Branch Performance
**Query:** Revenue அடிப்படையில் top 5 branches-ஐ காட்டு.
**Time:** 9.08s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, நெல்லூர் கிளை சுமார் ஐந்தரை இலட்சத்து எழுபதாயிரம் வருவாயுடன் முன்னணியில் உள்ளது. ஹைதராபாத் அடுத்ததாக சுமார் ஐந்து லட்சம் உள்ளது.

---

### Test #35 (TA) - PASS

**Category:** Branch Performance
**Query:** இரண்டு branch-களின் revenue-ஐ ஒப்பிடு.
**Time:** 9.55s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, கிளை ஏ மற்றும் கிளை பி ஆகிய இரண்டிற்கும் சுமார் இரண்டு கோடியே நாற்பது லட்சம் ரூபாய் வருவாய் இருக்கிறது. ஆகவே, இரண்டு கிளைகளுக்கும் ஒரே மாதிரியான வருவாய் உள்ளது.

---

### Test #36 (TA) - PASS

**Category:** Branch Performance
**Query:** ஒவ்வொரு branch-க்கும் சராசரி profit என்ன?
**Time:** 9.42s
**Rows:** 50
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, நாசிக் கிளை ஏறத்தாழ ஒன்று புள்ளி ஒன்பது லட்சத்தில் மிக அதிகமான சராசரி லாபத்தைக் கொண்டுள்ளது. அவுரங்காபாத் மற்றும் திருநெல்வேலியும் ஏறத்தாழ ஒன்று புள்ளி ஒன்பது லட்சம் ஒவ்வொன்றிலும் நன்றாகச் செயல்படுகின்றன.

---

### Test #37 (TA) - WARN

**Category:** Branch Performance
**Query:** நஷ்டம் ஏற்பட்ட branches எவை?
**Time:** 7.43s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** filter

**Response:**
> சரியான பலன் கிடைக்கவில்லை! அந்தத் தரவு வேறொரு பெயரில் இருக்கலாம் - நான் உனக்கு அதைத் தேட உதவட்டுமா?

---

### Test #38 (TA) - PASS

**Category:** Branch Performance
**Query:** ஒவ்வொரு state-இல் எத்தனை branches உள்ளன?
**Time:** 8.46s
**Rows:** 12
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** rank

**Response:**
> சரி, தமிழ்நாடு தான் மிக அதிகமான கிளைகளைக் கொண்டுள்ளது, சுமார் இருபத்தி எட்டு கிளைகளுடன். கர்நாடகா அடுத்ததாக சுமார் பன்னிரண்டு கிளைகளுடன் உள்ளது.

---

### Test #41 (TA) - PASS

**Category:** Payment Analysis
**Query:** அதிக transactions கொண்ட payment mode எது?
**Time:** 10.05s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, காசோலை அதிக பரிவர்த்தனைகளைக் கொண்ட செலுத்தும் முறையாக உள்ளது. எண்ணிக்கை சுமார் இரண்டாயிரத்து ஐநூறு.

---

### Test #42 (TA) - PASS

**Category:** Payment Analysis
**Query:** Payment mode வாரியாக revenue-ஐ காட்டு.
**Time:** 9.89s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, காசோலை செலுத்துதல்கள் சுமார் ஒரு கோடியே பதினொரு இலட்சத்துடன் முன்னிலையில் உள்ளன, அதைத் தொடர்ந்து அட்டை செலுத்துதல்கள் சுமார் ஒரு கோடியே பத்து இலட்சத்துடன் நெருக்கமாக உள்ளன. யுபிஐ மற்றும் ஆன்லைன் செலுத்துதல்களும் குறிப்பிடத்தக்கவை, ஒவ்வொன்றும் சுமார் ஒரு கோடியே ஒன்பது இலட்சம் பங்களிக்கின்றன.

---

### Test #43 (TA) - PASS

**Category:** Cost Analysis
**Query:** மொத்த cost மற்றும் மொத்த revenue ஒப்பீடு என்ன?
**Time:** 10.08s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, மொத்த வருவாய் மொத்த செலவை விட கணிசமாக அதிகமாக உள்ளது. வருவாய் சுமார் இரண்டு கோடியே நாற்பத்திரண்டு லட்சம், அதே சமயம் செலவு சுமார் தொண்ணூற்று இரண்டு லட்சம். அது சுமார் ஒரு கோடியே ஐம்பது லட்சம் வித்தியாசம்!

---

### Test #44 (TA) - PASS

**Category:** Cost Analysis
**Query:** அதிக cost ஏற்பட்ட மாதம் எது?
**Time:** 10.79s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Monthly_Overall_Summary
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்க்கும்போது, செப்டம்பர் இரண்டாயிரத்து இருபத்தைந்து அதிக செலவைக் கொண்டிருந்தது. அந்த மாதத்திற்கான மொத்த செலவு சுமார் பதினாறு லட்சம்.

---

### Test #45 (TA) - WARN

**Category:** Quarterly Analysis
**Query:** Quarter வாரியாக profit margin trend-ஐ காட்டு.
**Time:** 7.97s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** trend

**Response:**
> சாரி! அப்படிப் பொருந்தும் தரவு எதுவும் இருப்பதாகத் தெரியவில்லை. ஒருவேளை வேறு தேதிகளை முயற்சி செய்து பார்க்கவும் அல்லது எழுத்துச் சரிபார்க்கவும்?

---

### Test #46 (TA) - PASS

**Category:** Quarterly Analysis
**Query:** அதிக profit பெற்ற quarter எது?
**Time:** 8.64s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்க்கும்போது, மூன்றாம் காலாண்டு இரண்டாயிரத்து இருபத்தி ஐந்தில் அதிக லாபம் இருந்தது. அது ஏறக்குறைய எழுபத்தி ஒரு லட்சம்.

---

### Test #47 (TA) - PASS

**Category:** Quarterly Analysis
**Query:** ஒவ்வொரு quarter-க்கும் மொத்த profit என்ன?
**Time:** 8.87s
**Rows:** 3
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** rank

**Response:**
> சரி, ஒவ்வொரு காலாண்டுக்கான மொத்த லாபத்தைப் பார்க்கும்போது, Q3 இரண்டாயிரத்து இருபத்தைந்து சுமார் எழுபத்தியொரு லட்சமாக இருந்தது. பின்னர் Q4 இல் சற்று குறைந்து, Q1 இரண்டாயிரத்து இருபத்தாறில் சுமார் பதிமூன்று லட்சமாக கணிசமாகக் குறைந்தது.

---

### Test #48 (TA) - PASS

**Category:** SKU Analysis
**Query:** அதிக units விற்கப்பட்ட SKU எது?
**Time:** 8.54s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்க்கும்போது, SKU_MTS_பூஜ்யம் பூஜ்யம் ஒன்று அதிக யூனிட்கள் விற்பனையாகியுள்ளது. அதனால் அதுவே உங்களுடைய சிறந்த சாதனையாளர்!

---

### Test #49 (TA) - PASS

**Category:** SKU Analysis
**Query:** Revenue அடிப்படையில் top 5 SKU-களை காட்டு.
**Time:** 11.15s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, சேலைகள் சுமார் ஒரு கோடியே இருபத்தி ஐந்து லட்சம் வருவாயுடன் முதல் SKU ஆகும். எத்னிக் குர்தாக்கள் அடுத்த இடத்தில் எழுபத்தி ஐந்து லட்சம் விற்பனையுடன் உள்ளன.

---

### Test #50 (TA) - PASS

**Category:** SKU Analysis
**Query:** அதிக profit margin கொண்ட SKU எது?
**Time:** 8.80s
**Rows:** 1
**Table Used:** Dataset_1_Sales_SKU_Performance
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்க்கும்போது, தோத்தி SKU, ID SKU_DHT_பூஜ்ஜியம் பூஜ்ஜியம் ஒன்று, அறுபது சதவீதம் அளவில் அதிக லாப வரம்பைக் கொண்டுள்ளது. அவ்வளவு மோசமில்லை, சரியா?

---

### Test #51 (TA) - PASS

**Category:** SKU Analysis
**Query:** ஒவ்வொரு SKU-க்கும் revenue மற்றும் cost-ஐ ஒப்பிடு.
**Time:** 9.43s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, ஒவ்வொரு SKU-வுக்கும் வருவாய் செலவை விட அதிகமாக உள்ளது. உதாரணமாக, SKU_NWR_002-ன் விற்பனைத் தொகை ஏறத்தாழ ஐந்தாயிரத்து நூறு ஆக உள்ளது, அதே சமயம் செலவு சுமார் இரண்டாயிரம் ஆகும்.

---

### Test #52 (TA) - WARN

**Category:** SKU Analysis
**Query:** நஷ்டத்தில் உள்ள SKU-களை கண்டறி.
**Time:** 3.30s
**Rows:** 0
**Table Used:** 
**Query Type:** 

**Response:**
> வணக்கம்! நஷ்டத்தில் உள்ள SKU-களை பார்க்கலாமா? இதோ results: நஷ்டத்தில் உள்ள முதல் 5 SKU-கள் இதோ. வேற என்ன பாக்கணும்?

---

### Test #53 (TA) - PASS

**Category:** SKU Analysis
**Query:** அனைத்து SKU-களின் சராசரி cost per unit என்ன?
**Time:** 10.30s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, அனைத்து SKUக்களுக்கான ஒரு யூனிட்டின் சராசரி விலை சுமார் ஆயிரத்து இருநூறு. செலவுகள் சுமார் ஐந்நூறிலிருந்து சுமார் இரண்டாயிரத்து நூறு வரை மாறுபடும்.

---

### Test #54 (TA) - PASS

**Category:** SKU Analysis
**Query:** Category வாரியாக SKU profit contribution-ஐ காட்டு.
**Time:** 5.47s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> இதைப் பார்த்தால், அனைத்து எஸ்கே யூக்களுக்கான சராசரி அலகு விலை சுமார் நானூற்று நாற்பது ரூபாய். சில மாறுபாடுகள் உள்ளன, ஆனால் அதுவே பொதுவான விலைப்புள்ளி.

---

### Test #55 (TA) - PASS

**Category:** Category Analysis
**Query:** மொத்த revenue-க்கு அதிக பங்களிப்பு தரும் category எது?
**Time:** 5.47s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, அனைத்து SKUs க்கும் சராசரி அலகு விலை சுமார் நானூற்று இருபது ரூபாய் ஆகும். சில மாறுபாடுகள் உள்ளன, ஆனால் அதுதான் ஒட்டுமொத்த சராசரி.

---

### Test #56 (TA) - WARN

**Category:** Quarterly Analysis
**Query:** Quarter வாரியான revenue growth-ஐ ஒப்பிடு.
**Time:** 8.10s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** trend

**Response:**
> சரி! நீங்கள் கொடுத்த வாக்கியத்தை தமிழுக்கு மாற்றுகிறேன். அனைத்து எண்களையும் தமிழ் வார்த்தைகளில் மாற்ற வேண்டும் என்பதை நினைவில் கொள்கிறேன்.

வாக்கியம்: Oops! Looks like there's no data matching that. Maybe try a different date range or check the spelling?

மொழிமாற்றம்: ஊப்ஸ்! அப்படி எந்த தரவும் பொருந்தவில்லை போலிருக்கிறது. ஒருவேளை வேறு தேதி வரம்பை முயற்சிக்கவும் அல்லது எழுத்துப்பிழையைச் சரிபார்க்கவும்?

---

### Test #57 (TA) - PASS

**Category:** Analysis
**Query:** ஒரு குறிப்பிட்ட மாதத்தில் profit குறைவாக இருப்பதற்கான காரணத்தை விளக்கு.
**Time:** 8.93s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> தரவைப் பார்க்கும்போது, ​​எந்த மாதத்தைப் பற்றிக் கேட்கிறீர்கள் என்று தெரியாமல் குறிப்பிட்ட மாதத்தில் குறைந்த லாபம் வந்ததற்கான காரணத்தை என்னால் நேரடியாக விளக்க முடியாது. நீங்கள் எந்த மாதத்தைப் பற்றி தெரிந்து கொள்ள விரும்புகிறீர்கள் என்பதைத் தெரிவிக்க முடியுமா? பிறகு அந்த காலகட்டத்திற்கான தரவை நான் சரிபார்க்க முடியும்.

---

### Test #58 (TA) - PASS

**Category:** Trend Analysis
**Query:** காலப்போக்கில் sales trend எப்படி உள்ளது?
**Time:** 9.05s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> இதைப் பார்க்கும்போது, விற்பனை போக்கு ஒட்டுமொத்தமாக மிகவும் நிலையானதாக இருக்கிறது. இது சுமார் மூன்று லட்சத்து முப்பதாயிரத்தில் தொடங்கி மூன்று லட்சத்து நாற்பதாயிரத்தில் முடிந்தது. அக்டோபர் மாதத்தின் நடுப்பகுதியில் சுமார் நான்கு லட்சத்து அறுபதாயிரம் வரை உச்சம் இருந்தது.

---

### Test #59 (TA) - PASS

**Category:** Analysis
**Query:** Profit-ஐ அதிகமாக பாதிக்கும் காரணி cost-ஆ அல்லது sales-ஆ?
**Time:** 8.19s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, விற்பனை செலவைக் காட்டிலும் லாபத்தில் அதிக தாக்கத்தை ஏற்படுத்துவதாகத் தெரிகிறது. அதிக விற்பனை அளவுகள் தொடர்ந்து அதிக லாப அளவுகளுக்கு வழிவகுக்கின்றன.

---

### Test #60 (TA) - PASS

**Category:** Summary
**Query:** இந்த dataset-க்கு ஒரு high-level business summary கொடு.
**Time:** 5.86s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Monthly_Category_Summary
**Query Type:** list

**Response:**
> இதைப் பார்க்கையில், உள்ளாடை ஏறக்குறைய நான்கு புள்ளி ஆறு லட்சம் வருவாயுடன் முதல் வகையாக உள்ளது, மேலும் ஏறக்குறைய இரண்டு புள்ளி எட்டு லட்சம் லாபம் ஈட்டுகிறது. வேட்டி விற்பனையும் சிறப்பாக உள்ளது, ஏறக்குறைய நான்கு புள்ளி நான்கு லட்சம் வருவாயை ஈட்டுகிறது.

---

### Test #61 (TA) - PASS

**Category:** Trend
**Query:** சென்னை நகரத்தில் sales உயர்கிறதா குறைகிறதா?
**Time:** 8.74s
**Rows:** 36
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> சென்னை பார்க்கும்போது, விற்பனை பொதுவாகக் குறைந்து வருகிறது. இது சுமார் ஐந்தாயிரத்து நானூறு ஆயிரத்தில் தொடங்கி மூன்றாயிரத்து இருநூறு ஆயிரத்தில் முடிந்தது. அக்டோபரில் பன்னிரண்டாயிரத்து எழுநூறு ஆயிரத்தில் ஒரு உச்சம் இருந்தது.

---

### Test #62 (TA) - PASS

**Category:** Trend
**Query:** எந்த state-இல் sales trend குறைந்து வருகிறது?
**Time:** 9.59s
**Rows:** 93
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> சரி, எனக்கு கிடைத்த தகவல் இதுதான். கிளைகளில், திருப்பூர் தொண்ணூற்று நான்கு சதவீதம் விற்பனை சரிவுடன் அதிக சரிவை காட்டுகிறது. புதுக்கோட்டை மற்றும் திருவாரூர் ஆகியவையும் குறைந்து வரும் போக்குகளைக் காட்டுகின்றன.

---

### Test #63 (TA) - WARN

**Category:** Trend
**Query:** எந்த category மாதம் முழுவதும் நிலையான வளர்ச்சியை காட்டுகிறது?
**Time:** 4.76s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** trend

**Response:**
> ம்ம்ம், எனக்கான எந்த விவரமும் கிடைக்கவில்லை! வேறொரு வடிகட்டியை அல்லது எழுத்துக்கூட்டை முயற்சி செய்ய விரும்புகிறீர்களா?

---

### Test #64 (TA) - PASS

**Category:** Trend
**Query:** profit காலப்போக்கில் நிலையானதா அல்லது மாறுபடுகிறதா?
**Time:** 8.89s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> இதைப் பார்க்கும்போது, லாபப் போக்கு மிகவும் நிலையானதாக இருக்கிறது. இது சுமார் ஒன்று புள்ளி தொண்ணூற்று ஏழு லட்சம் ரூபாயில் தொடங்கி இரண்டு புள்ளி சைஃபர் ஆறு லட்சம் ரூபாயில் முடிந்தது. அக்டோபர் மாதத்தில் சுமார் இரண்டு புள்ளி ஏழு லட்சம் ரூபாயில் உச்சம் இருந்தது.

---

### Test #65 (TA) - PASS

**Category:** Trend
**Query:** எந்த மாதத்தில் sales திடீரென அதிகரித்தது?
**Time:** 9.31s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> சரி, அக்டோபர் மாதத்தின் நடுப்பகுதியில் விற்பனை திடீரென அதிகரித்தது. உச்சம் அக்டோபர் பதினேழாம் தேதி, சுமார் நான்கு லட்சத்து அறுபதாயிரம் வரை எட்டியது. ஒட்டுமொத்தமாக, போக்கு நிலையானது, ஆனால் அப்போது ஒரு தெளிவான உயர்வு இருந்தது.

---

### Test #66 (TA) - PASS

**Category:** Trend
**Query:** சில மாதங்களில் revenue அதிகமாக இருக்கிறதா?
**Time:** 8.61s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> இதைப் பார்க்கும்போது, வருவாய் போக்கு ஒட்டுமொத்தமாக மிகவும் நிலையாக உள்ளது. இது சுமார் மூன்று லட்சத்து முப்பதாயிரத்தில் தொடங்கி மூன்று லட்சத்து நாற்பதாயிரத்தில் முடிந்தது, ஆனால் அக்டோபர் மாத மத்தியில் சுமார் நான்கு லட்சத்து அறுபதாயிரம் என்ற உச்சத்தை எட்டியது. மோசமில்லை, இல்லையா?

---

### Test #67 (TA) - PASS

**Category:** Trend
**Query:** எந்த branch செயல்திறன் குறைந்து வருகிறது?
**Time:** 8.94s
**Rows:** 93
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> இதைப் பார்க்கும்போது, திருப்பூர்தான் மிகவும் மோசமான சரிவைக் காட்டுகிறது. இது சுமார் தொண்ணூற்று நான்கு சதவீதம் குறைந்து, சுமார் இருபத்தி நான்காயிரத்திலிருந்து சுமார் ஆயிரத்து ஐநூறுக்குச் சென்றுவிட்டது.

---

### Test #68 (TA) - WARN

**Category:** Trend
**Query:** எந்த category மாதம் மாதமாக revenue இழக்கிறது?
**Time:** 4.73s
**Rows:** 0
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** trend

**Response:**
> சரி! அப்படித் தோன்றுகிறது, அந்த விவரங்களுடன் பொருந்தும் எந்தத் தரவும் இல்லை. ஒருவேளை வேறு தேதி வரம்பை முயற்சி செய்யுங்கள் அல்லது எழுத்துப்பிழையை சரிபார்க்கவும்?

---

### Test #69 (TA) - PASS

**Category:** Trend
**Query:** revenue-விட cost வேகமாக உயருகிறதா?
**Time:** 8.66s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, வருவாய் செலவை விட வேகமாக அதிகரிக்கிறது. வருவாய் சுமார் நூற்று ஐம்பது சதவீதம் அதிகரித்துள்ளது, அதே நேரத்தில் செலவுத் தரவு கிடைக்கவில்லை.

---

### Test #70 (TA) - PASS

**Category:** Trend
**Query:** மொத்தமாக எந்த quarter மோசமாக செயல்பட்டது?
**Time:** 8.57s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Quarterly_Performance
**Query Type:** extrema_lookup

**Response:**
> சரி, இதை பார்க்கும்போது, முதல் காலாண்டு இரண்டாயிரத்து இருபத்தி ஆறு மிக மோசமாக செயல்பட்டது. மொத்த வருவாய் சுமார் இருபத்தியொரு லட்சங்கள், மொத்த லாபம் சுமார் பன்னிரண்டரை லட்சத்து அறுபதாயிரம்.

---

### Test #71 (TA) - PASS

**Category:** Projection Chain 1
**Query:** நவம்பர் மற்றும் டிசம்பர் மாத sales-ஐ ஒப்பிடு.
**Time:** 10.59s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, டிசம்பர் மாத விற்பனை நவம்பர் மாதத்தை விட சற்று அதிகமாக உள்ளது. டிசம்பர் விற்பனை ஏறக்குறைய ஒரு கோடி, நவம்பர் மாதத்தின் தொண்ணூற்று ஒன்பது லட்சத்துடன் ஒப்பிடும்போது - இது ஏறக்குறைய ஒரு சதவீதம் அதிகரிப்பு.

---

### Test #72 (TA) - PASS

**Category:** Projection Chain 1
**Query:** அதே trend தொடர்ந்தால் ஜனவரிக்கான projected sales என்ன?
**Time:** 2.03s
**Rows:** 1
**Table Used:** 
**Query Type:** 

**Response:**
> தற்போதைய போக்கின் அடிப்படையில், January விற்பனை சுமார் 0 ஆக இருக்கும் என்று எதிர்பார்க்கப்படுகிறது. போக்கு நிலையானதாக இருப்பதால், மதிப்பு மாறாமல் இருக்கும்.

---

### Test #73 (TA) - PASS

**Category:** Projection Chain 2
**Query:** சென்னை நகரத்தின் மாத sales trend-ஐ காட்டு.
**Time:** 9.23s
**Rows:** 36
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> இதைப் பார்க்கும்போது, சென்னையில் விற்பனை போக்கு குறைந்து வருகிறது, ஆனால் குறைந்த நம்பிக்கையுடன். இது சுமார் ஐந்தாயிரத்து நானூறுஇல் தொடங்கி மூவாயிரத்து இருநூறில் முடிந்தது. அக்டோபர் இரண்டாயிரத்து இருபத்தைந்தில் சுமார் பன்னிரண்டாயிரத்து எழுநூறில் உச்சம் இருந்தது.

---

### Test #74 (TA) - PASS

**Category:** Projection Chain 2
**Query:** இந்த trend அடிப்படையில் அடுத்த மாத sales-ஐ மதிப்பிடு.
**Time:** 2.05s
**Rows:** 1
**Table Used:** 
**Query Type:** 

**Response:**
> தற்போதைய போக்கின் அடிப்படையில், Next Period விற்பனை சுமார் 0 ஆக இருக்கும் என்று எதிர்பார்க்கப்படுகிறது. இது தற்போதைய around 3 thousand இலிருந்து சுமார் around 3 thousand (100%) குறைவு.

---

### Test #75 (TA) - PASS

**Category:** Projection Chain 3
**Query:** கடந்த மூன்று மாதங்களுக்கான category வாரியான sales-ஐ காட்டு.
**Time:** 5.76s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** trend

**Response:**
> சரி, இந்த டிரெண்ட் படி பார்த்தால், விற்பனை குறைந்து வருகிறது. ஆரம்பத்தில் சுமார் பதினான்கு லட்சமாக இருந்தது, இப்போது ஒன்பது லட்சத்து முப்பதாயிரமாக குறைந்துள்ளது. இது ஏறக்குறைய முப்பத்து மூன்று சதவீதம் குறைவு.

---

### Test #76 (TA) - PASS

**Category:** Projection Chain 3
**Query:** முன்னணி category இதே pattern தொடர்ந்தால் அடுத்த மாத sales என்ன?
**Time:** 5.79s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** trend

**Response:**
> சரி, இந்த trend தொடர்ந்தால், அடுத்த மாத sales சுமார் ஒன்பது லட்சத்து முப்பதாயிரமாக இருக்கும். இதுக்கு முன்னாடி இருந்ததை விட கொஞ்சம் குறைய வாய்ப்பு இருக்கு.

---

### Test #77 (TA) - PASS

**Category:** Projection Chain 4
**Query:** ஒரு branch-ன் தொடர்ச்சியான இரண்டு மாத revenue-ஐ ஒப்பிடு.
**Time:** 9.70s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, இந்த மாதம் வருவாய் சற்று அதிகரித்துள்ளது. இது சுமார் ஒரு சதவிகிதம் அதிகரித்தது, அதாவது சுமார் தொண்ணூற்று ஒன்பது லட்சத்திலிருந்து சுமார் ஒரு கோடி வரை உயர்ந்தது. பரவாயில்லை, இல்லையா?

---

### Test #78 (TA) - PASS

**Category:** Projection Chain 4
**Query:** அதே மாற்றம் தொடர்ந்தால் அடுத்த மாத revenue-ஐ கணிக்கவும்.
**Time:** 2.05s
**Rows:** 1
**Table Used:** 
**Query Type:** 

**Response:**
> தற்போதைய போக்கின் அடிப்படையில், Next Period விற்பனை சுமார் 0 ஆக இருக்கும் என்று எதிர்பார்க்கப்படுகிறது. போக்கு நிலையானதாக இருப்பதால், மதிப்பு மாறாமல் இருக்கும்.

---

### Test #79 (TA) - PASS

**Category:** Projection Chain 5
**Query:** ஒரு SKU-க்கு கடந்த 3 மாத sales-ஐ காட்டு.
**Time:** 8.92s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> இதைப் பார்க்கையில், விற்பனை போக்கு மிகவும் நிலையானதாக இருக்கிறது. இது ஏறத்தாழ மூன்று லட்சத்து முப்பதாயிரத்தில் தொடங்கி மூன்று லட்சத்து நாற்பதாயிரத்தில் முடிந்தது, ஆனால் அக்டோபரில் நான்கு லட்சத்து அறுபதாயிரம் வரை ஒரு உச்சம் இருந்தது. அவ்வளவு மோசமில்லை, இல்லையா?

---

### Test #80 (TA) - PASS

**Category:** Projection Chain 5
**Query:** இந்த trend தொடர்ந்தால் அடுத்த மாத sales என்ன?
**Time:** 2.06s
**Rows:** 1
**Table Used:** 
**Query Type:** 

**Response:**
> வலுவான போக்கின் அடிப்படையில், Next Period விற்பனை சுமார் about 3.4 lakhs ஆக இருக்கும் என்று எதிர்பார்க்கப்படுகிறது. இது தற்போதைய about 3.4 lakhs இலிருந்து சுமார் 17.97 (0%) அதிகரிப்பு.

---

### Test #81 (TA) - PASS

**Category:** Follow-up Chain 1
**Query:** தமிழ்நாட்டில் மொத்த sales என்ன?
**Time:** 9.45s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** aggregation_on_subset

**Response:**
> இதைப் பார்க்கும்போது, ​​தமிழ்நாட்டில் மொத்த விற்பனை சுமார் நாற்பத்தி ஆறு லட்சங்கள். விற்பனை பரிவர்த்தனை ஒன்றுக்கு சுமார் முந்நூற்று இருபது முதல் சுமார் இருபத்தியோராயிரம் வரை உள்ளது.

---

### Test #82 (TA) - PASS

**Category:** Follow-up Chain 1
**Query:** கர்நாடகாவுடன் ஒப்பிடும்போது இது அதிகமா குறைவா?
**Time:** 9.51s
**Rows:** 2
**Table Used:** Dataset_1_Sales_State_Performance
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, மொத்த மதிப்பு கர்நாடகாவை விட அதிகமாக உள்ளது. ஒட்டுமொத்த மதிப்பு ஏறத்தாழ ஒரு கோடியே எண்பத்தைந்து லட்சம், அதே சமயம் கர்நாடகா சுமார் பதிமூன்று லட்சம். அது ஒரு பெரிய வித்தியாசம்!

---

### Test #83 (TA) - PASS

**Category:** Follow-up Chain 2
**Query:** அதிக மொத்த sales கொண்ட category எது?
**Time:** 6.60s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, எல்லா பிராந்தியங்களிலும் மொத்த விற்பனை சுமார் ஒரு கோடியே இருபது லட்சம். அது கர்நாடகாவின் விற்பனையை விட கணிசமாக அதிகம், கர்நாடகாவின் விற்பனை சுமார் முப்பத்தைந்து லட்சம்.

---

### Test #84 (TA) - PASS

**Category:** Follow-up Chain 2
**Query:** இந்த category-க்கு sales காலப்போக்கில் அதிகரித்ததா குறைந்ததா?
**Time:** 7.04s
**Rows:** 2
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** comparison

**Response:**
> இதைப் பார்க்கும்போது, "All"க்கான விற்பனை கர்நாடகாவை விட அதிகமாக உள்ளது. கர்நாடகாவுக்கு சுமார் முப்பத்தைந்து லட்சமாக இருக்க, "All"க்கு சுமார் ஒரு கோடியே இருபது லட்சம் இருக்கிறது, அதனால் இது ஒரு பெரிய வித்தியாசம். இது ஏறக்குறைய இருநூற்று முப்பத்தி ஒன்பது சதவீதம் அதிகரிப்பு.

---

### Test #85 (TA) - PASS

**Category:** Follow-up Chain 3
**Query:** மொத்தமாக அதிக revenue கொண்ட branch எது?
**Time:** 7.81s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Branch_Details
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்க்கும்போது, ஜோத்பூர் கிளை அதிக மொத்த வருவாயைக் கொண்டுள்ளது. இது சுமார் மூன்று லட்சத்து இருபதாயிரம் இருக்கும்.

---

### Test #86 (TA) - PASS

**Category:** Follow-up Chain 3
**Query:** இந்த branch மற்ற branch-களின் சராசரியை விட சிறப்பாக செயல்படுகிறதா அல்லது இல்லை?
**Time:** 5.99s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> பயனருக்கு குழப்பம் இருப்பதாக தெரிகிறது.

இதைப் பார்க்கும்போது, ஃபரிதாபாத் கிளை அதிக மொத்த வருவாயைக் கொண்டுள்ளது. அது சுமார் இருபத்திரண்டு லட்சத்து எழுபதாயிரம் ஆகும். உங்களுக்கு வேறு ஏதேனும் கேள்விகள் இருந்தால் தெளிவுபடுத்துகிறேன்.

---

### Test #87 (TA) - PASS

**Category:** Follow-up Chain 4
**Query:** அதிக sales amount கொண்ட payment mode எது?
**Time:** 8.32s
**Rows:** 1
**Table Used:** Dataset_1_Sales_Payment_Mode_Analysis
**Query Type:** extrema_lookup

**Response:**
> இதைப் பார்க்கும்போது, ரொக்கம் அதிகம் பயன்படுத்தப்படும் கட்டண முறையாகும், இதன் வருவாய் தோராயமாக ஒரு கோடியே பத்து லட்சம் ரூபாய். இது மற்ற கட்டண முறைகளை விட கணிசமாக அதிகம்.

---

### Test #88 (TA) - PASS

**Category:** Follow-up Chain 4
**Query:** இந்த payment mode பயன்பாடு மாதங்களாக உயர்ந்ததா?
**Time:** 9.25s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> கட்டண முறைகளை பார்க்கும்போது, அவை பெரும்பாலும் நிலையாக இருக்கின்றன. ரொக்கம் மிகப்பெரிய அதிகரிப்பைக் கண்டது, சுமார் நூற்று எண்பத்தேழு சதவீதம் அதிகரித்தது. யுபிஐ, மறுபுறம், தோராயமாக அறுபத்தாறு சதவீதம் குறைந்தது.

---

### Test #89 (TA) - PASS

**Category:** Follow-up Chain 5
**Query:** அதிக மொத்த revenue கொண்ட SKU எது?
**Time:** 8.43s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** rank

**Response:**
> இதைப் பார்க்கும்போது, புடவைகள் தோராயமாக ஒன்று புள்ளி இரண்டு ஐந்து கோடி ரூபாயில் அதிக வருவாய் ஈட்டும் பொருளாக இருக்கிறது. அது மற்ற வகைகளை விட கணிசமாக அதிகமாகும்.

---

### Test #90 (TA) - PASS

**Category:** Follow-up Chain 5
**Query:** இந்த SKU-ன் sales trend தொடர்ந்து உயருகிறதா?
**Time:** 8.52s
**Rows:** 168
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** trend

**Response:**
> இதைப் பார்க்கும்போது, விற்பனை போக்கு ஒட்டுமொத்தமாக நிலையாக உள்ளது. இது சுமார் மூன்று லட்சத்து முப்பதாயிரத்தில் தொடங்கி மூன்று லட்சத்து நாற்பதாயிரத்தில் முடிந்தது. அக்டோபர் மாத மத்தியில் சுமார் நான்கு லட்சத்து அறுபதாயிரத்தில் உச்சம் இருந்தது.

---

### Test #91 (TA) - PASS

**Category:** Advanced
**Query:** ஆரம்ப மாதங்களில் top 3 revenue contributor ஆக இருந்தாலும், பின்னர் மாதங்களில் bottom 3 ஆக மாறிய state எது?
**Time:** 8.41s
**Rows:** 50
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> இதைப் பார்த்தால், தெலுங்கானா அந்த விளக்கத்திற்குப் பொருந்துகிறது. அது ஆரம்பத்தில் ஒரு சிறந்த வருவாய் மாநிலமாக இருந்தது, ஆனால் பின்னர் கடைசி மூன்று இடங்களுக்குத் தள்ளப்பட்டது.

---

### Test #92 (TA) - PASS

**Category:** Advanced
**Query:** மொத்த sales amount அதிகமாக இருந்தாலும், மொத்த profit குறைவாக உள்ள category ஏதேனும் உள்ளதா?
**Time:** 6.36s
**Rows:** 10
**Table Used:** Dataset_1_Sales_Category_Performance
**Query Type:** list

**Response:**
> சரி, எந்தப் பிரிவில் அதிக விற்பனை இருந்தும் குறைந்த லாபம் உள்ளதா என்று கேட்கிறீர்கள் என்று புரிகிறது. என்னிடம் லாபத் தரவு எதுவும் இல்லை, ஆனால் அதிக விற்பனையாகும் பிரிவுகளை நான் உங்களுக்குச் சொல்ல முடியும்: இன்னர் வேர் சுமார் பன்னிரண்டு லட்சத்துடன் முன்னிலை வகிக்கிறது, அதைத் தொடர்ந்து கிட்ஸ் வேர் சுமார் பதினோரு லட்சத்து தொண்ணூறாயிரத்தில் உள்ளது.

---

### Test #93 (TA) - PASS

**Category:** Advanced
**Query:** ஒரே payment mode மூலம் 50%-க்கு மேல் sales வரும் branches ஏதேனும் உள்ளதா?
**Time:** 9.19s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, ஆம், சில கிளைகளில் ஒரு குறிப்பிட்ட பணப் பரிவர்த்தனை முறை ஐம்பது சதவீதத்திற்கும் அதிகமான விற்பனையை கொண்டுள்ளது. உதாரணமாக, வாரங்கலில், ரொக்கப் பரிவர்த்தனைகள் கணிசமான விற்பனைப் பங்கைக் கொண்டுள்ளன.

---

### Test #94 (TA) - PASS

**Category:** Advanced
**Query:** Revenue அடிப்படையில் top 5 SKU-களில், revenue-க்கு ஒப்பிடும்போது அதிக cost கொண்ட SKU எது?
**Time:** 8.73s
**Rows:** 5
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> இதனைப் பார்க்கும்போது, SKU_NWR_பூஜ்யம் பூஜ்யம் இரண்டு ஆனது முதல் ஐந்து SKUs மத்தியில் வருவாயுடன் ஒப்பிடும்போது அதிக செலவைக் கொண்டுள்ளது. இதன் செலவு சுமார் இரண்டாயிரத்து ஐம்பத்து நான்கு, வருவாய் சுமார் ஐந்தாயிரத்து நூற்று முப்பத்து ஆறு ஆக உள்ளது.

---

### Test #95 (TA) - PASS

**Category:** Advanced
**Query:** முந்தைய மாதத்துடன் ஒப்பிடும்போது sales உயர்ந்தாலும், profit குறைந்த மாதம் ஏதேனும் உள்ளதா?
**Time:** 8.22s
**Rows:** 100
**Table Used:** Dataset_1_Sales_Daily_Sales_Transactions
**Query Type:** list

**Response:**
> இதைப் பார்க்கும்போது, விற்பனை அதிகரித்த ஆனால் லாபம் குறைந்த எந்த மாதமும் இல்லை. விற்பனையும் லாபமும் ஒன்றுக்கொன்று சேர்ந்தே நகர்கின்றன. எனவே, விற்பனை அதிகரிக்கும்போது, லாபமும் அதிகரிக்கிறது.

---

### Test #105 (TA) - PASS

**Category:** Greeting
**Query:** வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?
**Time:** 2.98s
**Rows:** 0
**Table Used:** 
**Query Type:** 

**Response:**
> வணக்கம்! நான் நல்லா இருக்கேன், நன்றி! நீங்க எப்படி இருக்கீங்க? Enna data paakanum?

---

