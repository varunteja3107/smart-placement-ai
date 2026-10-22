from urllib.parse import quote_plus

JOB_BOARDS = [
    {
        "source": "LinkedIn",
        "url": "https://www.linkedin.com/jobs/search/?keywords={query}",
    },
    {
        "source": "Internshala",
        "url": "https://internshala.com/internships/keywords-{slug}/",
    },
    {
        "source": "Naukri",
        "url": "https://www.naukri.com/{slug}-jobs",
    },
    {
        "source": "Wellfound",
        "url": "https://wellfound.com/jobs",
    },
    {
        "source": "Indeed",
        "url": "https://in.indeed.com/jobs?q={query}",
    },
    {
        "source": "Unstop",
        "url": "https://unstop.com/internships",
    },
    {
        "source": "Apna",
        "url": "https://apna.co/jobs",
    },
    {
        "source": "Foundit",
        "url": "https://www.foundit.in/srp/results?query={query}",
    },
    {
        "source": "AICTE Internship Portal",
        "url": "https://internship.aicte-india.org/",
    },
    {
        "source": "Naukri Campus",
        "url": "https://www.naukri.com/campus",
    },
    {
        "source": "Cutshort",
        "url": "https://cutshort.io/jobs",
    },
    {
        "source": "Freshersworld",
        "url": "https://www.freshersworld.com/jobs",
    },
    {
        "source": "Glassdoor",
        "url": "https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={query}",
    },
    {
        "source": "National Career Service",
        "url": "https://www.ncs.gov.in/",
    },
    {
        "source": "Company Careers",
        "url": "https://www.google.com/search?q={query}+company+careers",
    },
]

def get_job_board_links(query: str):
    query = query.strip()
    encoded_query = quote_plus(query)
    slug = "-".join(query.lower().split())

    results = []

    for board in JOB_BOARDS:
        url = board["url"].format(
            query=encoded_query,
            slug=quote_plus(slug).replace("+", "-"),
        )

        results.append({
            "source": board["source"],
            "url": url,
            "query": query,
            "type": "external_search_link",
        })

    return results
