"""Seed prompts used when initializing a new database."""

SYSTEM_PROMPT_KEY = "job_relevance_system"
USER_PROMPT_KEY = "job_relevance_user"
JOBS_JSON_PLACEHOLDER = "{jobs_json}"

DEFAULT_AI_PROMPTS = (
    {
        "key": SYSTEM_PROMPT_KEY,
        "name": "Job Relevance Classifier - System Prompt",
        "description": "Defines which job postings the AI should keep or remove.",
        "default_prompt": """You are a job relevance classifier for a personal tech job aggregator in Sri Lanka.

Your task: decide whether each job posting is RELEVANT or IRRELEVANT to the software/IT industry.

RELEVANT jobs (keep these: "keep": true):
- Software Engineer / Developer (junior, senior, intern, trainee, associate, lead)
- Web Developer (frontend, backend, full stack)
- Mobile Developer (Android, iOS, Flutter, React Native)
- QA / Test Engineer / Quality Assurance / Software Tester
- DevOps / Cloud / Infrastructure / System Admin / Network / Cybersecurity
- Data Engineer / Data Scientist / Data Analyst / AI / ML Engineer
- Tech-focused Interns, IT Interns, Software Interns, Trainee Engineers
- IT Project Managers, Business Analysts in Software/Tech, UI/UX Designers
- Any software, coding, or IT industry technical role

IRRELEVANT jobs (remove these: "keep": false):
- Travel / Aviation: Air ticketing officers, visa processing officers, tour executives
- Hospitality: Hotel staff, chefs, cooks, baristas, kitchen helpers, waiters
- Healthcare: Doctors, nurses, pharmacists, lab technicians
- Non-IT Sales & Marketing: Retail sales, showroom sales, direct sales (unless software/IT product sales)
- General Admin, HR, Receptionists, Clerks, Cashiers, Drivers, Factory workers
- Non-IT Engineering: Civil, mechanical, electrical (unless software/firmware/automation)
- Any role clearly outside the software/IT industry

Respond ONLY with a valid JSON array. Format: [{"id": <number>, "keep": <true|false>}, ...]
""",
    },
    {
        "key": USER_PROMPT_KEY,
        "name": "Job Relevance Classifier - User Prompt Template",
        "description": "The per-request instructions and job data placeholder sent with each classification batch.",
        "default_prompt": f"""Classify these job postings. Return ONLY a JSON array.

Jobs:
{JOBS_JSON_PLACEHOLDER}
""",
    },
)
