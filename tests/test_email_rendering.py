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
        with pytest.raises(ValidationError, match="https"):
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
    assert "A reminder & its receipt\nhttps://example.org/piece" in body.plain_text
    assert body.links == (
        BodyLink(label="A reminder & its receipt", url="https://example.org/piece"),
    )
    with pytest.raises(ValidationError, match="https"):
        BodyBlock(heading="x", heading_href="http://example.org")
    with pytest.raises(ValidationError, match="needs a heading"):
        BodyBlock(heading_href="https://example.org", paragraphs=("p",))
