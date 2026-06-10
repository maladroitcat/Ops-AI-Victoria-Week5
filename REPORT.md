# Week 5 TechCorp Agent Report

## How To Run Locally

1. Create and activate the local virtual environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
.venv/bin/python -m pip install -r week5/requirements.txt
```

3. Set your Google AI API key:

```bash
export GOOGLE_API_KEY="your-key-here"
```

4. If `gemini-2.5-pro` returns a quota error, use the model override:

```bash
export GEMINI_MODEL="gemini-2.5-flash"
```

5. Run the agent with an initial question:

```bash
python week5/app_starter.py "What is the travel policy?"
```

6. Continue asking questions at the prompt. Type `quit` or `exit` to stop:

```text
Ask a TechCorp question: quit
```

## Runtime Notes

- The script loads the SQLite database from `week5/data/techcorp.db`.
- Policy search uses `week5/data/documents.json`.
- Expense approval limits use `week5/data/policies.json`.
- Access-control role data comes from `week5/data/access_control.json`.
- Cumulative usage metrics are saved locally to `week5/data/metrics.json`.
- `week5/data/metrics.json` is ignored by Git so local usage history is not committed.

## Test Questions and Responses

Use these questions to test all tools. The set covers each tool at least twice. Responses from running each question are below each question. Screenshots of responses can be found in the `screenshots/` folder.

1. `What is the travel policy?`
   - Expected tool: `policy_search`

Answer: Here is the travel policy:

All business travel must be pre-approved by your manager.

**Domestic Travel Limits:**
*   **IC1-IC2:** $3,000/trip limit, $15,000/year limit
*   **IC3-IC4:** $5,000/trip limit, $25,000/year limit
*   **IC5+:** $10,000/trip limit, no annual limit
*   **Managers:** $5,000/trip limit, $30,000/year limit
*   **Directors+:** $10,000/trip limit, no annual limit

**International Travel:**
*   Requires VP approval.
*   Budget limits are 50% higher than the domestic equivalent.

**Airfare Guidelines:**
*   Book flights at least 7 days in advance.
*   Use economy class for flights under 6 hours.
*   Business class is permitted for flights over 8 hours (requires VP approval).
*   Use the company travel portal for all bookings.
Tokens: 2185
Cost: $0.000227
Metrics: {'total_queries': 14, 'total_tokens': 39227, 'total_cost': 0.0034327500000000005, 'avg_cost_per_query': 0.0002451964285714286}

2. `How many weeks of parental leave does TechCorp provide?`
   - Expected tool: `policy_search`

Answer: TechCorp provides the following parental leave:
*   Primary caregiver: 16 weeks paid
*   Secondary caregiver: 8 weeks paid
*   Adoption: 8 weeks paid
Tokens: 1269
Cost: $0.000112
Metrics: {'total_queries': 15, 'total_tokens': 40496, 'total_cost': 0.0035450250000000003, 'avg_cost_per_query': 0.000236335}

3. `What is TechCorp's remote work policy?`
   - Expected tool: `policy_search`

Answer: TechCorp's remote work policy is as follows:

**Eligibility:** All employees are eligible for remote work, except those in roles requiring physical presence (Office Management, Facilities, Reception).

**Work Arrangements:**
*   **Full Remote:**
    *   Available to all eligible employees.
    *   Must work core hours: 10am-3pm PT.
    *   Participate in in-person events quarterly.
*   **Hybrid:**
    *   3 days in office, 2 days remote.
    *   Preferred for managers with direct reports.
    *   Office days: Monday-Wednesday.
*   **In-Office:**
    *   Select roles (to be determined by department).
    *   Office is located in SF, NYC, and Seattle.

**Equipment Allowance:**
*   Full remote: $2,000/year home office budget.
*   Hybrid: $500/year equipment budget.
*   In-office: Provided by company.

**IT Security:** Remote workers must use company-provided security measures (details not fully provided in the snippet).
Tokens: 2204
Cost: $0.000228
Metrics: {'total_queries': 16, 'total_tokens': 42700, 'total_cost': 0.0037726500000000002, 'avg_cost_per_query': 0.00023579062500000001}

4. `What is the approval limit for a manager?`
   - Expected tool: `expense_query`

Answer: The approval limit for a manager is $5000.
Tokens: 445
Cost: $0.000044
Metrics: {'total_queries': 17, 'total_tokens': 43145, 'total_cost': 0.0038168250000000003, 'avg_cost_per_query': 0.00022451911764705883}


5. `What expense amount can a director approve?`
   - Expected tool: `expense_query`

Answer: A director can approve an expense amount of $25000.
Tokens: 446
Cost: $0.000045
Metrics: {'total_queries': 18, 'total_tokens': 43591, 'total_cost': 0.003861525, 'avg_cost_per_query': 0.00021452916666666667}

6. `What is the approval limit for an IC3 employee?`
   - Expected tool: `expense_query`

Answer: The approval limit for an IC3 employee is $2000.
Tokens: 454
Cost: $0.000046
Metrics: {'total_queries': 20, 'total_tokens': 44486, 'total_cost': 0.00394935, 'avg_cost_per_query': 0.0001974675}

7. `Look up employee Brian Yang.`
   - Expected tool: `employee_lookup`

Answer: Here is the information for Brian Yang:

*   **Name:** Brian Yang
*   **Email:** johnsonjoshua@example.org
*   **Department:** Engineering
*   **Job Level:** E1
*   **Title:** VP Engineering (Executive)
*   **Phone:** 001-765-642-3511x615
*   **Hire Date:** 2020-10-25T14:35:58.011755
Tokens: 735
Cost: $0.000087
Metrics: {'total_queries': 21, 'total_tokens': 45221, 'total_cost': 0.00403665, 'avg_cost_per_query': 0.00019222142857142858}

8. `Find employee ID 1.`
   - Expected tool: `employee_lookup`

Answer: Here is the information for employee ID 1:

*   **ID:** 1
*   **Name:** Brian Yang
*   **Email:** johnsonjoshua@example.org
*   **Department:** Engineering (ID: 1)
*   **Job Level:** E1
*   **Title:** VP Engineering (Executive)
*   **Phone:** 001-765-642-3511x615
*   **Hire Date:** 2020-10-25T14:35:58.011755
*   **Manager ID:** null
*   **Bonus Eligible:** Yes
Tokens: 778
Cost: $0.000100
Metrics: {'total_queries': 22, 'total_tokens': 45999, 'total_cost': 0.0041370750000000005, 'avg_cost_per_query': 0.00018804886363636366}

9. `What is Brian Yang's email and title?`
   - Expected tool: `employee_lookup`

Answer: Brian Yang's email is johnsonjoshua@example.org and their title is VP Engineering (Executive).
Tokens: 661
Cost: $0.000063
Metrics: {'total_queries': 23, 'total_tokens': 46660, 'total_cost': 0.004200375, 'avg_cost_per_query': 0.000182625}

10. `What are the company mission and values?`
    - Expected tool: `policy_search`
    
Answer: TechCorp's mission is:
To empower businesses through innovative technology solutions that drive growth, efficiency, and sustainability.

Our values are:
*   **Innovation:** We invest in R&D and encourage employees to experiment and take calculated risks.
*   **Excellence:** We maintain high standards in everything we do.
*   **Integrity:** We operate with honesty and transparency.
*   **Collaboration:** We believe great things happen when diverse teams work together.
*   **Sustainability:** We're committed to environmental and social responsibility.
Tokens: 1785
Cost: $0.000165
Metrics: {'total_queries': 24, 'total_tokens': 48445, 'total_cost': 0.00436575, 'avg_cost_per_query': 0.00018190625}


## Verification Checklist

- The agent initializes successfully.
- The first Gemini API call returns `HTTP/1.1 200 OK`.
- The second Gemini API call returns `HTTP/1.1 200 OK`.
- Answers are grounded in the local tool results.
- Token and cost values are printed after each answer.
- `get_metrics()` totals increase across questions.
- Metrics persist across script runs through `week5/data/metrics.json`.
