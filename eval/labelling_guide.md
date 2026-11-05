# Labelling guide

Written 5 Nov 2026 by Onkar Gupta. This guide is committed before any data exists. It fixes what the correct label is for every field of `schema.json`. The generator, the scorer and the private real-advert labels all follow it. Changes after data exists go in the Amendments section of `eval/protocol.md`.

General rules:
- Label only what the advert text says. Do not use outside knowledge about the employer.
- If the text does not state a value, the label is null (or `not_stated` for sponsorship, or an empty list for skills).
- Text fields are compared after casefolding, trimming and collapsing spaces.

## title
The job title as advertised, without reference codes, grade numbers or location suffixes. Never null.

## employer
The hiring organisation named in the advert. Null when an agency hides the client ("our client, a leading retailer"). If the advert names both an agency and a client, the client is the employer. If only the agency is named and it is also the hirer, the agency is the employer.

## location
The town or city of the place of work, as a UK town name ("Leeds", not "West Yorkshire"). Use the value `remote` only when the advert says the job is fully remote (then `work_pattern` is also `remote`). Hybrid adverts give the town and `work_pattern` hybrid. Several towns or no town: null.

## work_pattern
One of `on-site`, `hybrid`, `remote`. Null if the advert does not state it. "Office based" is `on-site`. "Flexible working" alone is null.

## salary_min and salary_max
Pounds sterling per year, as numbers, rounded to the nearest pound. Ignore bonuses, pension, overtime and benefits.

Fixed conversion rules:
- Hourly rate: rate x 37.5 hours x 52 weeks. Worked example: "£22.50 per hour" gives 22.50 x 37.5 x 52 = 43,875, so min and max are both 43875.
- Daily rate: rate x 230 working days. Worked example: "£350 per day" gives 350 x 230 = 80,500, so min and max are both 80500.
- "k" means thousand: "£45k" is 45000.

Hard cases:

| Advert text | salary_min | salary_max |
|---|---|---|
| "£40,000 - £50,000" | 40000 | 50000 |
| "£45k-£55k DOE" | 45000 | 55000 |
| "£50,000" | 50000 | 50000 |
| "up to 45k" | null | 45000 |
| "from £30,000" | 30000 | null |
| "competitive" | null | null |
| "negotiable" | null | null |
| "£22.50 per hour" | 43875 | 43875 |
| "£18 - £20 per hour" | 18 x 37.5 x 52 = 35100 | 20 x 37.5 x 52 = 39000 |
| "£350 per day" | 80500 | 80500 |
| "£25,000 pro rata for 3 days a week" | 25000 | 25000 (the figure as printed, no adjustment) |
| "£30,000 plus 8% pension" | 30000 | 30000 |

## skills
Named tools, technologies and professional skills the advert asks for, as a list of strings in lower case ("python", "sql", "project management"). Exclude benefits, perks, company values and generic soft-skill filler ("team player", "good communicator", "self-starter"). Skills mentioned only in an about-us paragraph and not asked of the candidate are excluded. No duplicates. An advert with none gives an empty list.

## years_experience_min
The lowest number of years of experience the advert states as required, as an integer. "3+ years" is 3. "3 to 5 years" is 3. "At least 2 years" is 2. Null if not stated. "Recent graduate" or "entry level" is null. Years of company history ("we have 20 years of experience") are not a requirement.

## closing_date
The application deadline only, as an ISO date `yyyy-mm-dd`. Never the start date, the interview date or the posting date. Relative dates with no anchor ("in two weeks", "closes Friday") are null. "Closing date: 14 December 2026" is `2026-12-14`. Null if none is stated.

## sponsorship
One of `offers`, `excludes`, `not_stated`, `unclear`. Never null.

| Advert text | Label |
|---|---|
| "We are unable to offer sponsorship" | excludes |
| "No sponsorship" | excludes |
| "Candidates must have the right to work in the UK" (nothing else on sponsorship) | excludes |
| "Sponsorship available" | offers |
| "We hold a sponsor licence and will sponsor the right person" | offers |
| "Sponsorship may be considered for the right candidate" | unclear |
| "Sponsorship subject to eligibility" | unclear |
| "Visa support available for some roles" | unclear |
| No mention of sponsorship or right to work | not_stated |
| "No sponsorship available" in one paragraph and "we sponsor skilled workers" in another | unclear |

Rules:
- An explicit sponsorship statement wins over a right-to-work line. "Must have the right to work in the UK, but we can sponsor the right candidate" is `offers`.
- Two contradictory statements give `unclear`.
- Conditional or hedged wording ("may", "subject to", "in some cases") gives `unclear`.
- Mentioning that the employer holds a licence, with nothing about this job, is `unclear`.

## Scope

The same guide labels the private real adverts. The labeller must label every private advert with this guide before any model sees it.
