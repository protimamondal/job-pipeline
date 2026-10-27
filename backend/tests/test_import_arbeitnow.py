"""The Arbeitnow import, without the network: cleaning, filtering, no duplicates."""

from import_arbeitnow import html_to_text, is_english, select_jobs


def _raw(url: str, description: str, title: str = "Engineer") -> dict:
    return {
        "company_name": "Acme",
        "title": title,
        "location": "Berlin",
        "url": url,
        "description": description,
    }


ENGLISH = "<p>We build the tools and services for teams.</p>"
GERMAN = "<p>Wir suchen einen Entwickler für unser Team.</p>"


def test_html_to_text_keeps_blocks_on_separate_lines():
    raw = "<h2>Tasks</h2><ul><li><p>Build &amp; ship</p></li><li>Review</li></ul>"
    assert html_to_text(raw) == "Tasks\nBuild & ship\n\nReview"


def test_html_to_text_strips_escaped_tags_and_the_footer():
    raw = "&lt;p&gt;Build the API&lt;/p&gt;Find more English Speaking Jobs in Germany on Arbeitnow"
    assert html_to_text(raw) == "Build the API"


def test_is_english_drops_german():
    assert is_english(html_to_text(ENGLISH))
    assert not is_english(html_to_text(GERMAN))


def test_select_jobs_skips_german_and_known_urls():
    raw_jobs = [
        _raw("a", ENGLISH, "A"),
        _raw("b", GERMAN, "B"),
        _raw("c", ENGLISH, "C"),
    ]
    jobs = select_jobs(raw_jobs, existing_urls={"a"}, existing_keys=set(), limit=10)
    assert [job.url for job in jobs] == ["c"]
    assert "<p>" not in jobs[0].description


def test_select_jobs_skips_the_same_job_under_another_url():
    raw_jobs = [_raw("a", ENGLISH), _raw("a-remote", ENGLISH)]
    jobs = select_jobs(raw_jobs, existing_urls=set(), existing_keys=set(), limit=10)
    assert [job.url for job in jobs] == ["a"]


def test_select_jobs_stops_at_limit():
    raw_jobs = [_raw(url, ENGLISH, url) for url in ["a", "b", "c"]]
    jobs = select_jobs(raw_jobs, existing_urls=set(), existing_keys=set(), limit=2)
    assert [job.url for job in jobs] == ["a", "b"]
