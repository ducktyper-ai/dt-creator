"""The email body renderer is escaped, accessible, deterministic and digest-bound."""

import pytest
from pydantic import ValidationError

from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.production import ContentDocument
from zeo_creator.rendering import BodyBlock, BodyImage, BodyLink, render_email_body

BLOCKS = (
    BodyBlock(
        heading="What changed this week",
        paragraphs=("Three releases shipped.", "One <script>alert(1)</script> & more."),
        links=(BodyLink(label="Read the release notes", url="https://example.org/notes?a=1&b=2"),),
    ),
    BodyBlock(
        image=BodyImage(src="https://example.org/chart.png", width=600, alt="Weekly chart"),
        paragraphs=("The chart above shows the trend.",),
    ),
)


def test_renders_an_escaped_fragment_with_language_and_direction() -> None:
    body = render_email_body(language="es-MX", blocks=BLOCKS, preheader="This week <b>")
    assert body.html.startswith('<div lang="es-MX" dir="ltr">')
    assert body.html.endswith("</div>")
    assert "<html" not in body.html and "<body" not in body.html
    assert "<script>" not in body.html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; more." in body.html
    assert 'href="https://example.org/notes?a=1&amp;b=2"' in body.html
    assert 'aria-hidden="true">This week &lt;b&gt;</div>' in body.html
    assert "<h2>What changed this week</h2>" in body.html


def test_plain_text_carries_every_heading_paragraph_and_link() -> None:
    body = render_email_body(language="en", blocks=BLOCKS)
    for text in (
        "What changed this week",
        "Three releases shipped.",
        "Read the release notes: https://example.org/notes?a=1&b=2",
        "Image: Weekly chart",
        "The chart above shows the trend.",
    ):
        assert text in body.plain_text
    assert body.links == BLOCKS[0].links


def test_images_are_responsive_and_described() -> None:
    body = render_email_body(language="en", blocks=BLOCKS)
    assert 'alt="Weekly chart" width="600"' in body.html
    assert "max-width:100%;height:auto;border:0" in body.html
    with pytest.raises(ValidationError, match="alternative text"):
        BodyImage(src="https://example.org/a.png", width=10)
    decorative = BodyImage(src="https://example.org/rule.png", width=10, decorative=True)
    assert decorative.alt == ""


def test_links_must_be_https_and_described() -> None:
    for url in ("http://example.org", "javascript:alert(1)", "data:text/html,x"):
        with pytest.raises(ValidationError, match="HTTPS"):
            BodyLink(label="Open", url=url)
    with pytest.raises(ValidationError, match="describe"):
        BodyLink(label="https://example.org", url="https://example.org")


def test_digests_match_the_delivery_contract_and_are_deterministic() -> None:
    first = render_email_body(language="en", blocks=BLOCKS, preheader="p")
    second = render_email_body(language="en", blocks=BLOCKS, preheader="p")
    assert first == second
    assert first.html_digest == canonical_digest(first.html)
    assert first.plain_text_digest == canonical_digest(first.plain_text)
    # The fragment feeds a newsletter issue's documents unchanged.
    assert ContentDocument(media_type="text/html", content=first.html).content == first.html


def test_refuses_bad_input() -> None:
    with pytest.raises(ValueError, match="BCP 47"):
        render_email_body(language="english language", blocks=BLOCKS)
    with pytest.raises(ValueError, match="at least one block"):
        render_email_body(language="en", blocks=())
    with pytest.raises(ValidationError, match="needs content"):
        BodyBlock()
    decorative_only = (
        BodyBlock(image=BodyImage(src="https://example.org/x.png", width=1, decorative=True)),
    )
    with pytest.raises(ValueError, match="readable plain text"):
        render_email_body(language="en", blocks=decorative_only)


def test_a_heading_can_link_to_its_piece() -> None:
    block = BodyBlock(
        heading="A reminder & its receipt",
        heading_href="https://example.org/piece",
        paragraphs=("Two sentences.",),
    )
    body = render_email_body(language="en-GB", blocks=(block,))
    assert (
        '<h2><a href="https://example.org/piece">A reminder &amp; its receipt</a></h2>' in body.html
    )
    assert "A reminder & its receipt: https://example.org/piece" in body.plain_text
    assert body.links == (
        BodyLink(label="A reminder & its receipt", url="https://example.org/piece"),
    )
    with pytest.raises(ValidationError, match="HTTPS"):
        BodyBlock(heading="x", heading_href="http://example.org")
    with pytest.raises(ValidationError, match="needs a heading"):
        BodyBlock(heading_href="https://example.org", paragraphs=("p",))


BREAKER = '"><img src=x onerror=alert(1)>'


def test_attribute_breakers_are_escaped_everywhere() -> None:
    block = BodyBlock(
        heading=f"Heading {BREAKER}",
        heading_href="https://example.org/h",
        paragraphs=(f"Text {BREAKER}",),
        links=(BodyLink(label=f"Label {BREAKER}", url="https://example.org/l"),),
        image=BodyImage(src="https://example.org/i.png", width=10, alt=f"Alt {BREAKER}"),
    )
    body = render_email_body(language="en", blocks=(block,), preheader=f"Pre {BREAKER}")
    assert "<img src=x" not in body.html
    assert "onerror=alert(1)>" not in body.html
    assert body.html.count("<img ") == 1


def test_direction_is_refused_unless_ltr_or_rtl() -> None:
    with pytest.raises(ValueError, match="ltr or rtl"):
        render_email_body(language="en", blocks=BLOCKS, direction=f"ltr{BREAKER}")  # type: ignore[arg-type]
    assert render_email_body(language="ar", blocks=BLOCKS, direction="rtl").html.startswith(
        '<div lang="ar" dir="rtl">'
    )


def test_links_follow_the_delivery_manifest_rule() -> None:
    for url in (
        "https:///path",
        "https://trusted.example@evil.example/",
        "https://example.org/{{contact.email}}",
        "https://example.org/?utm_source=x",
        "https://example.org/a\x07b",
        "https://example.org/" + "a" * 2048,
        "https://evil.example\\@trusted.example/",
        "https://example.org\\path",
    ):
        with pytest.raises(ValidationError, match=r"HTTPS|tracking"):
            BodyLink(label="Open", url=url)
    with pytest.raises(ValidationError, match="describe"):
        BodyLink(label="https://example.org/", url="https://example.org")
    with pytest.raises(ValidationError, match="describe"):
        BodyBlock(heading="https://example.org/a", heading_href="https://example.org/a")


def test_template_braces_and_language_edges() -> None:
    braces = BodyBlock(paragraphs=("Hello {{ contact.firstname }}",))
    body = render_email_body(language="en", blocks=(braces,))
    assert "{{" not in body.html and "&#123;&#123; contact.firstname &#125;&#125;" in body.html
    assert "Hello {{ contact.firstname }}" in body.plain_text
    with pytest.raises(ValueError, match="BCP 47"):
        render_email_body(language="en\n", blocks=BLOCKS)


def test_email_link_contract_refuses_a_backslash() -> None:
    from zeo_creator.contracts.email_marketing import EmailLink

    for url in ("https://trusted.example\\.evil.example/", "https://example.org\\path"):
        with pytest.raises(ValidationError, match="HTTPS"):
            EmailLink(link_id="guide", url=url, purpose="content", tracking_required=False)
    EmailLink(
        link_id="guide", url="https://example.org/path", purpose="content", tracking_required=False
    )
