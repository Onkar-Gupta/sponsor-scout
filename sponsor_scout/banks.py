"""Phrase and template banks for the synthetic advert generator.

Everything here was written for this repo. Nothing is copied from a job board. The "held out" markers fix which
style families, sponsorship phrasings, job families and towns appear only in the held-out slice of the test split.

Template rule: each template is a list of lines. A line is dropped when any slot it uses is empty, so one template
serves every combination of null and non-null fields. A line with no slot is always kept.
Slots: title, Org, org, employer, agency, town, pattern, salary, skills, skills_bullets, exp, closing, start,
posted, interview, ref, sponsor_1, sponsor_2, benefit_1, benefit_2, about, filler.
"""

# --------------------------------------------------------------------------------------------- towns
TOWNS = (
    "Leeds", "Bristol", "Manchester", "Sheffield", "Birmingham", "Liverpool", "Nottingham", "Leicester",
    "Coventry", "Newcastle", "Cardiff", "Swansea", "Glasgow", "Edinburgh", "Aberdeen", "Belfast", "Norwich",
    "Cambridge", "Oxford", "Exeter", "Plymouth", "Southampton", "Portsmouth", "Brighton", "York", "Preston",
    "Derby", "Swindon", "Gloucester", "Ipswich", "Milton Keynes", "Luton", "Warrington", "Sunderland",
    "Carlisle", "Lancaster", "Inverness", "Peterborough", "Guildford", "Harrogate",
)
HELD_OUT_TOWNS = (
    "Aberdeen", "Swansea", "Carlisle", "Inverness", "Harrogate", "Ipswich", "Lancaster", "Peterborough",
    "Gloucester", "Sunderland",
)

# ------------------------------------------------------------------------------------- job families
# Each skill must not be a substring of another skill or of any title in its own family (a test checks this).
JOB_FAMILIES = {
    "software": {
        "titles": ["Software Engineer", "Backend Developer", "Frontend Developer", "Full Stack Developer",
                   "DevOps Engineer", "Mobile App Developer"],
        "skills": ["python", "typescript", "react", "django", "postgresql", "docker", "kubernetes", "git",
                   "rest apis", "terraform", "linux", "golang"],
        "band": (32000, 85000),
    },
    "data": {
        "titles": ["Data Analyst", "Data Engineer", "Business Intelligence Analyst", "Machine Learning Engineer",
                   "Analytics Manager", "Reporting Analyst"],
        "skills": ["sql", "python", "power bi", "tableau", "excel", "pandas", "spark", "airflow", "statistics",
                   "dbt", "looker", "data modelling"],
        "band": (30000, 80000),
    },
    "finance": {
        "titles": ["Management Accountant", "Financial Analyst", "Credit Controller", "Audit Associate",
                   "Payroll Officer", "Finance Business Partner"],
        "skills": ["sage", "xero", "vat returns", "month end close", "budgeting", "forecasting", "reconciliations",
                   "ifrs", "accounts payable", "cima", "acca", "management reporting"],
        "band": (26000, 70000),
    },
    "nursing": {
        "titles": ["Staff Nurse", "Healthcare Assistant", "Senior Care Worker", "Community Nurse",
                   "Theatre Practitioner", "Ward Sister"],
        "skills": ["iv cannulation", "wound care", "medication administration", "safeguarding", "phlebotomy",
                   "care planning", "catheterisation", "dementia care", "basic life support", "nmc registration",
                   "infection control", "clinical audit"],
        "band": (22000, 48000),
    },
    "teaching": {
        "titles": ["Primary Teacher", "Maths Teacher", "Science Teacher", "Teaching Assistant", "SEN Coordinator",
                   "Head of Department"],
        "skills": ["qts", "lesson planning", "classroom management", "phonics", "behaviour management",
                   "send support", "assessment for learning", "google classroom", "curriculum design",
                   "differentiation", "pastoral care", "ks2 teaching"],
        "band": (24000, 52000),
    },
    "mech_eng": {
        "titles": ["Mechanical Design Engineer", "Maintenance Engineer", "Project Engineer", "Quality Engineer",
                   "CAD Technician", "Process Engineer"],
        "skills": ["solidworks", "autocad", "finite element analysis", "lean manufacturing", "six sigma",
                   "iso 9001", "plc programming", "hydraulics", "root cause analysis", "technical drawing",
                   "cnc machining", "pneumatics"],
        "band": (28000, 65000),
    },
    "marketing": {
        "titles": ["Digital Marketing Executive", "Content Manager", "SEO Specialist", "Brand Manager",
                   "Social Media Manager", "Marketing Coordinator"],
        "skills": ["google analytics", "hubspot", "mailchimp", "copywriting", "adobe creative suite",
                   "email campaigns", "ppc", "content strategy", "canva", "market research", "wordpress",
                   "a/b testing"],
        "band": (24000, 62000),
    },
    "hr": {
        "titles": ["HR Advisor", "Recruitment Coordinator", "Learning and Development Partner",
                   "Benefits Officer", "HR Business Partner", "Talent Acquisition Specialist"],
        "skills": ["employee relations", "cipd", "workday", "hr policy", "onboarding", "applicant tracking",
                   "employment law", "performance management", "job evaluation", "hris", "absence management",
                   "disciplinary procedures"],
        "band": (25000, 65000),
    },
    "sales": {
        "titles": ["Sales Executive", "Business Development Manager", "Account Manager",
                   "Inside Sales Representative", "Key Account Manager", "Sales Coordinator"],
        "skills": ["salesforce", "lead generation", "cold calling", "negotiation", "pipeline management",
                   "b2b sales", "account planning", "hubspot", "upselling", "tender writing", "crm",
                   "presentation skills"],
        "band": (24000, 70000),
    },
    "logistics": {
        "titles": ["Warehouse Supervisor", "Transport Planner", "Supply Chain Analyst", "Logistics Coordinator",
                   "Forklift Operator", "Fleet Manager"],
        "skills": ["sap", "wms", "forklift licence", "route planning", "inventory control", "demand planning",
                   "import export documentation", "health and safety", "stock management", "customs clearance",
                   "hgv licence", "shipment tracking"],
        "band": (21000, 52000),
    },
    "hospitality": {
        "titles": ["Restaurant Manager", "Head Chef", "Sous Chef", "Hotel Receptionist", "Bar Supervisor",
                   "Events Coordinator"],
        "skills": ["food hygiene", "rota planning", "menu costing", "opera pms", "stock control",
                   "cocktail making", "allergen management", "banqueting", "till operation", "guest relations",
                   "wine knowledge", "table service"],
        "band": (20000, 45000),
    },
    "retail": {
        "titles": ["Store Manager", "Sales Assistant", "Visual Merchandiser", "Assistant Store Manager",
                   "Stock Controller", "Retail Buyer"],
        "skills": ["visual merchandising", "epos systems", "stock replenishment", "cash handling",
                   "loss prevention", "rota management", "planogram", "kpi reporting", "supplier negotiation",
                   "click and collect", "customer returns", "promotional planning"],
        "band": (20000, 48000),
    },
    "construction": {
        "titles": ["Site Manager", "Quantity Surveyor", "Electrician", "Plasterer", "Site Engineer",
                   "Health and Safety Advisor"],
        "skills": ["cscs card", "sssts", "nec contracts", "bim", "revit", "setting out", "cost planning",
                   "first fix wiring", "18th edition", "inspection and testing", "scaffold inspection", "rics"],
        "band": (24000, 68000),
    },
    "legal": {
        "titles": ["Paralegal", "Solicitor", "Legal Secretary", "Conveyancer", "Contracts Manager",
                   "Compliance Officer"],
        "skills": ["legal research", "contract drafting", "case management", "westlaw", "due diligence", "gdpr",
                   "dictation", "litigation support", "anti money laundering", "client onboarding", "probate",
                   "e-disclosure"],
        "band": (24000, 75000),
    },
    "customer_service": {
        "titles": ["Customer Service Advisor", "Contact Centre Agent", "Complaints Handler",
                   "Customer Success Manager", "Support Specialist", "Helpdesk Analyst"],
        "skills": ["zendesk", "live chat", "complaint resolution", "call handling", "freshdesk",
                   "service level agreements", "ticketing systems", "order processing", "intercom",
                   "escalation handling", "knowledge base writing", "refunds processing"],
        "band": (21000, 45000),
    },
    "lab_science": {
        "titles": ["Research Scientist", "Laboratory Technician", "Quality Control Analyst", "Microbiologist",
                   "Analytical Chemist", "Clinical Trials Assistant"],
        "skills": ["hplc", "pcr", "cell culture", "mass spectrometry", "gmp", "aseptic technique", "elisa", "lims",
                   "western blotting", "gas chromatography", "good laboratory practice", "sample preparation"],
        "band": (23000, 58000),
    },
}
HELD_OUT_FAMILIES = ("logistics", "hospitality", "legal", "lab_science")

# ------------------------------------------------------------------------------------ employer names
NAME_START = ["Vel", "Mor", "Tal", "Quen", "Bry", "Fen", "Sol", "Kes", "Lun", "Dar", "Pyr", "Orn", "Wex", "Zil",
              "Hal", "Cor", "Tam", "Ryn", "Glo", "Vek"]
NAME_MIDDLE = ["a", "o", "i", "e", "an", "en", "ar", "or", "il", "av", "um", "ex"]
NAME_END = ["dyne", "mere", "tex", "nova", "lix", "wick", "ford", "ton", "vale", "gate", "ra", "ma", "zen", "rith"]
SUFFIXES = {
    "default": ["Ltd", "Group", "Systems", "Solutions", "Partners", "Labs", "Services", "Holdings", "Limited"],
    "public_sector": ["Borough Council", "County Council", "City Council"],
    "university": ["University"],  # rendered as "University of <name>"
    "nhs_trust": ["Health Trust", "Hospitals Trust", "Community Care Trust"],
    "charity": ["Foundation", "Trust", "Alliance"],
    "engineering_firm": ["Engineering", "Dynamics", "Works", "Technologies"],
    "retail": ["Stores", "Retail", "Outfitters", "& Co"],
    "finance": ["Capital", "Advisory", "Wealth", "Financial Services"],
    "startup": ["Labs", "Technologies", "Ltd", "Systems"],
}
AGENCY_SUFFIXES = ["Recruitment", "Talent", "Staffing", "Resourcing"]
HIDE_EMPLOYER = {"agency": 0.7, "finance": 0.15}  # probability the client is hidden; others use 0.03
HIDE_EMPLOYER_DEFAULT = 0.03

# ------------------------------------------------------------------------------------ small phrase banks
PATTERNS = {
    "on-site": ["on-site", "office based", "on site, Monday to Friday"],
    "hybrid": ["hybrid, three days in the office", "hybrid working with two days in the office", "hybrid"],
    "remote": ["fully remote", "remote (UK based)", "remote, with an annual team day"],
}
BENEFITS = [
    "8% employer pension contribution", "5% employer pension contribution", "25 days annual leave plus bank holidays",
    "27 days holiday rising with service", "£500 a year for training", "£300 wellbeing allowance",
    "Life cover worth 4 times salary", "Cycle to work scheme", "Free parking for all staff", "Staff discount of 15%",
    "Employee assistance programme", "Annual bonus of up to 10%", "Private dental cover after 6 months",
    "An extra day off for your birthday", "Competitive benefits package", "Monthly team lunch",
]
FILLER = [
    "You will be a team player and a good communicator.",
    "We want a self-starter who enjoys a busy team.",
    "A friendly manner and a positive attitude matter to us.",
    "You are a good communicator who likes working with others.",
]
ABOUT_HISTORY = [
    "{Org} has been trading for {n} years and employs around {m} people.",
    "Founded {n} years ago, {org} now has {m} staff.",
    "With {n} years behind us, we have grown to a team of {m}.",
]
ABOUT_SKILLS = [
    "Our teams use {x} every day.", "Across the business we work with {x}.", "Day to day our people use {x}.",
]
ACRONYM_WORDS = {"sql", "ppc", "hplc", "pcr", "gmp", "elisa", "lims", "gdpr", "bim", "crm", "sap", "wms", "cipd",
                 "hris", "ifrs", "cima", "acca", "qts", "rics", "dbt", "cscs", "sssts", "nec", "nmc", "iso", "cnc",
                 "plc", "hgv", "epos", "kpi", "send", "pms", "iv", "ks2", "b2b", "apis"}

# --------------------------------------------------------------------------- sponsorship phrase banks
# id -> (class, parts, held_out). Two parts go in two different places in the advert (contradictory pairs).
SPONSOR_PHRASES = {}


def _add(prefix, cls, items, held):
    for i, parts in enumerate(items, 1):
        pid = f"{prefix}{i:02d}"
        SPONSOR_PHRASES[pid] = (cls, (parts,) if isinstance(parts, str) else tuple(parts), pid in held)


_add("off", "offers", [
    "Sponsorship available.",
    "We hold a sponsor licence and will sponsor the right person.",
    "Applicants who need a visa are welcome: we will sponsor the right candidate.",
    "Must have the right to work in the UK, but we can sponsor the right candidate.",
    "Skilled Worker sponsorship is offered for this role.",
    "We will provide visa sponsorship to the successful candidate.",
    "This role is eligible for Skilled Worker visa sponsorship.",
    "We are a licensed sponsor and are happy to sponsor this post.",
    "Relocation help and visa sponsorship are available.",
    "If you need sponsorship to work in the UK, we will support your application.",
    "International candidates: we offer sponsorship.",
    "Sponsorship is provided for the right applicant.",
], {"off03", "off06", "off09", "off12"})
_add("exc", "excludes", [
    "We are unable to offer sponsorship.",
    "No sponsorship.",
    "Candidates must have the right to work in the UK.",
    "Applicants must already have the right to work in the UK.",
    "Please note we cannot provide visa sponsorship.",
    "Sponsorship is not available for this role.",
    "No sponsorship available.",
    "We do not sponsor visas.",
    "You must be eligible to work in the UK without sponsorship.",
    "Unfortunately we are not able to support visa applications.",
    "The right to work in the UK is required before you apply.",
    "We cannot sponsor applicants for this vacancy.",
], {"exc03", "exc06", "exc09", "exc12"})
_add("unc", "unclear", [
    "Sponsorship may be considered for the right candidate.",
    "Sponsorship subject to eligibility.",
    "Visa support available for some roles.",
    "In some cases we are able to sponsor, so please ask.",
    "Sponsorship is possible in exceptional circumstances.",
    "We may be able to support a visa application, depending on the role and your circumstances.",
    "We are a licensed sponsor.",
    "Our organisation holds a Skilled Worker sponsor licence.",
    "The company is on the register of licensed sponsors.",
    ("No sponsorship available.", "We sponsor skilled workers."),
    ("Sponsorship is available for this post.", "We cannot sponsor visas."),
    ("We are unable to sponsor candidates for this role.", "We are happy to sponsor the right overseas applicant."),
], {"unc04", "unc08", "unc11", "unc12"})

# ----------------------------------------------------------------------------------- style templates
STYLES = {
    "corporate": [
        ["{title}", "{Org}", "Location: {town}", "Working pattern: {pattern}", "Salary: {salary}",
         "About the role\n{filler}", "Experience required: {exp}", "Skills required: {skills}",
         "What we offer: {benefit_1}. {benefit_2}.", "{about}", "{sponsor_1}", "Closing date: {closing}",
         "Planned start date: {start}", "{sponsor_2}", "Reference: {ref}"],
        ["Vacancy: {title}", "Employer: {employer}", "Place of work: {town}", "Hours and pattern: {pattern}",
         "Remuneration: {salary}", "You bring {exp} of relevant experience.", "You are confident with {skills}.",
         "{filler}", "Benefits include {benefit_1} and {benefit_2}.", "{about}", "Posted on {posted}.",
         "{sponsor_1}", "Applications close on {closing}.", "Interviews are expected on {interview}.",
         "{sponsor_2}"],
        ["{Org} is seeking an experienced professional for the position of {title}.",
         "The position is based in {town}. Working pattern: {pattern}.", "The salary is {salary}.",
         "Applicants need {exp} in a similar post, together with {skills}.", "{filler}",
         "In return we provide {benefit_1}, and {benefit_2}.", "{about}", "Note: {sponsor_1}",
         "To apply, send your CV by {closing}.", "The successful applicant will start on {start}.",
         "Note: {sponsor_2}", "Our reference is {ref}."],
    ],
    "agency": [
        ["{agency} is delighted to be working with {org} on a new vacancy.", "Role: {title}",
         "Client: {employer}", "Where: {town}", "Pattern: {pattern}", "Package: {salary}",
         "The ideal candidate has {exp} behind them and knows {skills}.", "{filler}",
         "Perks: {benefit_1}, {benefit_2}.", "{about}", "{sponsor_1}", "CVs by {closing} please.",
         "Advert posted {posted}.", "{sponsor_2}", "Job ref {ref}"],
        ["NEW ROLE: {title}", "Our client, {employer}, is expanding.", "Based: {town}", "Style of working: {pattern}",
         "Rate: {salary}", "What you need\n{skills_bullets}", "Track record: {exp}", "{filler}",
         "The client offers {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}",
         "Shortlisting begins after {closing}.", "Client interviews planned for {interview}.", "{sponsor_2}",
         "Contact {agency} quoting {ref}."],
        ["{agency}: we find people for the businesses we like.", "Today we are recruiting for {title}.",
         "{Org} needs someone in {town}.", "They work {pattern}.", "Pay on offer: {salary}.",
         "Must have {exp}. Must know {skills}.", "{filler}", "{benefit_1}. {benefit_2}.", "{about}",
         "{sponsor_1}", "Last day to apply: {closing}.", "Start: {start}.", "{sponsor_2}", "Ref: {ref}"],
    ],
    "startup": [
        ["We are {org} and we are hiring.", "Job: {title}", "Where: {town}", "How we work: {pattern}",
         "Pay: {salary}", "You have {exp} and have shipped real work with {skills}.", "{filler}",
         "You get {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}",
         "Send your application before {closing}.", "We want you in the seat by {start}.", "{sponsor_2}"],
        ["{title} wanted at {org}", "Small team, big plans. {about}", "Our base: {town}", "Way of working: {pattern}",
         "Salary: {salary}", "Bring {exp}.", "Our stack and tools: {skills}.", "{filler}", "Perks: {benefit_1}.",
         "{benefit_2}.", "{sponsor_1}", "Applications shut on {closing}.", "Posted {posted}.", "{sponsor_2}"],
        ["Join {org} as our next {title}!", "Think you can help us grow? We are in {town}.",
         "We are {pattern}.", "We pay {salary}.", "Needed: {exp}, plus {skills}.", "{filler}",
         "What you get: {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}", "Apply by {closing}.",
         "First day: {start}.", "{sponsor_2}"],
    ],
    "public_sector": [
        ["{employer}", "Post: {title}", "Directorate base: {town}", "Working arrangement: {pattern}",
         "Pay: {salary}", "Person specification", "Experience: {exp}", "Skills and knowledge: {skills}",
         "{filler}", "Terms: {benefit_1}; {benefit_2}.", "{about}", "{sponsor_1}",
         "Closing date for applications: {closing}", "Interview date: {interview}", "{sponsor_2}",
         "Post number {ref}"],
        ["{Org} invites applications for the post of {title}.", "The successful candidate will work from {town}.",
         "Arrangement: {pattern}.", "Grade and pay: {salary}.", "Applicants should show {exp}.",
         "Knowledge of {skills} is required.", "Employment terms include {benefit_1} and {benefit_2}.",
         "{about}", "{sponsor_1}", "Please return forms by {closing}.", "Advertised on {posted}.",
         "{sponsor_2}", "Quote {ref}."],
        ["Job title: {title}", "Employer: {employer}", "Office address town: {town}", "Pattern: {pattern}",
         "Salary range: {salary}", "Essential criteria\nExperience of {exp}\nSkills: {skills}", "{filler}",
         "Benefits: {benefit_1}. {benefit_2}.", "{about}", "{sponsor_1}", "Closes: {closing}",
         "Start date: {start}", "{sponsor_2}"],
    ],
    "university": [
        ["{title}", "{employer}", "Campus: {town}", "Mode of working: {pattern}", "Salary: {salary}",
         "About you: you have {exp} in a university or similar setting and you can use {skills}.", "{filler}",
         "We offer {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}",
         "The closing date is {closing}.", "Interviews will be held on {interview}.", "{sponsor_2}",
         "Vacancy reference {ref}"],
        ["The role of {title} has arisen at {org}.", "Our campus is in {town}.", "We work {pattern}.",
         "Starting salary: {salary}.", "You will have {exp}.", "You will use {skills} regularly.",
         "Staff benefits: {benefit_1}, {benefit_2}.", "{filler}", "{about}", "{sponsor_1}",
         "Please apply by {closing}.", "Expected start: {start}.", "{sponsor_2}"],
        ["Academic and professional services vacancy", "Post: {title}", "Employer: {employer}",
         "Location: {town}", "Pattern: {pattern}", "Grade and salary: {salary}", "Experience wanted: {exp}",
         "Skills wanted: {skills}", "Staff package: {benefit_1}. {benefit_2}.", "{about}", "{sponsor_1}",
         "Posted: {posted}", "Closing date: {closing}", "{sponsor_2}", "Ref: {ref}"],
    ],
    "nhs_trust": [
        ["{title}", "{employer}", "Site: {town}", "Working pattern: {pattern}", "Pay: {salary}",
         "We are looking for a caring and reliable colleague with {exp}.", "Key skills: {skills}.", "{filler}",
         "Staff benefits: {benefit_1}. {benefit_2}.", "{about}", "{sponsor_1}",
         "Applications close at midnight on {closing}.", "Interview date: {interview}", "{sponsor_2}",
         "Our reference: {ref}"],
        ["Come and work for {org}.", "Job: {title}", "Your base will be {town}.", "Working style: {pattern}.",
         "Band and pay: {salary}.", "You will have {exp}.", "You will be able to use {skills}.", "{filler}",
         "You will enjoy {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}",
         "Closing date {closing}.", "Posted {posted}.", "{sponsor_2}"],
        ["{Org} is recruiting.", "Post title: {title}", "Hospital or clinic town: {town}",
         "Pattern: {pattern}", "Salary: {salary}", "Needed: {exp}", "Skills and registrations\n{skills_bullets}",
         "{benefit_1}", "{benefit_2}", "{about}", "{sponsor_1}", "Last date for applications: {closing}",
         "Start date: {start}", "{sponsor_2}", "Job ID {ref}"],
    ],
    "terse_list": [
        ["ROLE: {title}", "CO: {employer}", "LOC: {town}", "MODE: {pattern}", "PAY: {salary}",
         "NEED:\n{skills_bullets}", "EXP: {exp}", "PERKS: {benefit_1} / {benefit_2}", "NOTE: {sponsor_1}",
         "CLOSES: {closing}", "POSTED: {posted}", "NOTE: {sponsor_2}", "REF: {ref}"],
        ["{title}", "- {org}", "- {town}", "- {pattern}", "- {salary}", "- {exp}", "- {skills}", "- {benefit_1}",
         "- {benefit_2}", "- {sponsor_1}", "- apply by {closing}", "- starts {start}", "- {sponsor_2}",
         "- ref {ref}"],
        ["{title}", "[{org}]", "[{town}]", "[{pattern}]", "[{salary}]", "Must have: {skills}", "Years: {exp}",
         "Also: {benefit_1}; {benefit_2}", "Info: {sponsor_1}", "Deadline {closing}", "Info: {sponsor_2}",
         "#{ref}"],
    ],
    "chatty": [
        ["Hi there! Fancy a new job?", "We are {org} and we need to fill {title}.", "Where will you be? {town}.",
         "And how will you work? {pattern}.", "The pay? {salary}.", "Here is what we are after: {skills}.",
         "You will have done this for {exp}.", "{filler}", "Oh, and you get {benefit_1} and {benefit_2}.",
         "{about}", "{sponsor_1}", "Pop your details in before {closing}.", "We would love you to start on {start}.",
         "{sponsor_2}", "Quote {ref} when you write."],
        ["Looking for a change? Read on.", "{Org} has a vacancy: {title}.", "It is in {town}.",
         "The working pattern is {pattern}.", "Salary: {salary}.", "You know {skills} like the back of your hand.",
         "You have spent {exp} getting good at it.", "{filler}", "Perks? {benefit_1}. Also {benefit_2}.",
         "{about}", "{sponsor_1}", "Hurry, we stop looking on {closing}!", "Interviews are on {interview}.",
         "{sponsor_2}"],
        ["Big news from {org}: we are hiring for {title}!", "Come and join us in {town}.", "We are {pattern}.",
         "We will pay {salary}.", "You will need {exp} and a handle on {skills}.", "{filler}",
         "We throw in {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}", "Last chance to apply is {closing}.",
         "We posted this on {posted}.", "{sponsor_2}", "(ref {ref})"],
    ],
    "charity": [
        ["{title}", "{employer}", "Based in {town}", "Working pattern: {pattern}", "Salary: {salary}",
         "Every role here helps people in need. {filler}", "We are looking for {exp} and skills in {skills}.",
         "In return we offer {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}",
         "Closing date: {closing}", "Start date: {start}", "{sponsor_2}", "Ref {ref}"],
        ["Make a difference as our {title}.", "{Org} is a charity with a big heart and a small team.",
         "Our office is in {town}.", "How we work: {pattern}.", "Pay: {salary}.", "You have {exp}.",
         "You are comfortable with {skills}.", "{filler}", "We offer {benefit_1}. {benefit_2}.", "{about}",
         "{sponsor_1}", "Apply by {closing}.", "Interviews on {interview}.", "{sponsor_2}"],
        ["Vacancy at {org}", "Job title: {title}", "Town: {town}", "Pattern: {pattern}", "Pay: {salary}",
         "About you\nExperience: {exp}\nSkills: {skills}", "{filler}", "Benefits: {benefit_1}; {benefit_2}.",
         "{about}", "{sponsor_1}", "Closing date: {closing}", "Posted: {posted}", "{sponsor_2}"],
    ],
    "engineering_firm": [
        ["{Org}: engineers wanted.", "Position: {title}", "Site location: {town}", "Working pattern: {pattern}",
         "Salary: {salary}", "Technical requirements: {skills}.", "Experience: {exp}.", "{filler}",
         "Package: {benefit_1}, {benefit_2}.", "{about}", "{sponsor_1}", "Closing date: {closing}",
         "Start date: {start}", "{sponsor_2}", "Ref {ref}"],
        ["Engineering vacancy", "{title} at {org}", "Our works are near {town}.", "Pattern: {pattern}",
         "Rate: {salary}", "You must have {exp} and hands-on use of {skills}.", "{filler}",
         "We provide {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}", "Apply by {closing}.",
         "Site visits and interviews: {interview}.", "{sponsor_2}"],
        ["{Org} designs and builds precision parts.", "We need to fill {title}.", "The workshop is in {town}.", "The job is {pattern}.",
         "Pay: {salary}.", "You need {exp}.", "You use {skills} as part of the normal week.", "{filler}",
         "{benefit_1}. {benefit_2}.", "{about}", "{sponsor_1}", "Applications close {closing}.",
         "Advert date {posted}.", "{sponsor_2}", "{ref}"],
    ],
    "retail": [
        ["{title} - {org}", "Store area: {town}", "Working pattern: {pattern}", "Pay: {salary}",
         "We want someone with {exp} who is comfortable with {skills}.", "{filler}",
         "Colleague perks: {benefit_1}, {benefit_2}.", "{about}", "{sponsor_1}", "Closing date: {closing}",
         "Start date: {start}", "{sponsor_2}", "Job code {ref}"],
        ["Retail vacancy: {title}", "Company: {employer}", "Town: {town}", "Pattern: {pattern}",
         "Hourly or annual pay: {salary}", "Experience needed: {exp}", "Systems and skills: {skills}", "{filler}",
         "Perks: {benefit_1}. {benefit_2}.", "{about}", "{sponsor_1}", "Apply before {closing}.",
         "Posted {posted}.", "{sponsor_2}"],
        ["Join the {org} team as {title}.", "Our shop is in {town}.", "You will be {pattern}.",
         "We pay {salary}.", "Bring {exp} and knowledge of {skills}.", "{filler}",
         "You get {benefit_1} and {benefit_2}.", "{about}", "{sponsor_1}", "Last day to apply: {closing}.",
         "We open our doors to you on {start}.", "{sponsor_2}"],
    ],
    "finance": [
        ["{title}", "{Org}", "Office: {town}", "Pattern: {pattern}", "Compensation: {salary}",
         "Requirements: {exp}; {skills}.", "{filler}", "Package: {benefit_1} and {benefit_2}.", "{about}",
         "{sponsor_1}", "Closing date: {closing}", "Start: {start}", "{sponsor_2}", "Req ID {ref}"],
        ["A leading adviser seeks to fill {title}.", "Employer: {employer}", "City or town: {town}",
         "Working pattern: {pattern}", "Salary: {salary}", "You hold {exp} in a regulated setting.",
         "Technical skills: {skills}.", "{filler}", "Perks: {benefit_1}. {benefit_2}.", "{about}", "{sponsor_1}",
         "Deadline: {closing}", "Interview slots on {interview}.", "{sponsor_2}"],
        ["Opportunity: {title} at {org}", "Based in {town}", "Operating model: {pattern}", "Reward: {salary}",
         "Profile\n- {exp}\n- {skills}", "{filler}", "Benefits: {benefit_1}; {benefit_2}.", "{about}",
         "{sponsor_1}", "Apply by {closing}.", "Posted: {posted}", "{sponsor_2}", "Ref: {ref}"],
    ],
}
STYLE_NAMES = tuple(STYLES)
HELD_OUT_STYLES = ("nhs_trust", "chatty", "charity", "terse_list")
