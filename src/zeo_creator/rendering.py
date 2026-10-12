"""Provider-neutral, accessible email body rendering.

The result is an HTML fragment for a template's content slot, never a full
document: the template owns the frame, brand styling and footer. Rendering is
pure and deterministic, and its digests match ``EmailDeliveryMaterial``.
"""

import re
from html import escape
from typing import Literal, Self

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, canonical_digest
from zeo_creator.contracts.email_marketing import check_public_link

_LANGUAGE = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_DIRECTIONS = ("ltr", "rtl")
_HIDDEN = (
    "display:none;max-height:0;max-width:0;overflow:hidden;"
    "opacity:0;font-size:1px;line-height:1px;mso-hide:all"
)
_IMAGE = "display:block;max-width:100%;height:auto;border:0"


def _https(url: str) -> str:
    # The same rule as EmailLink, so the fragment never carries a link the delivery
    # manifest would refuse, plus a bound on length and no control characters.
    if len(url) > 2048 or _CONTROL.search(url):
        raise ValueError("links require clean absolute HTTPS URLs of at most 2048 characters")
    check_public_link(url)
    return url


def _text(value: str) -> str:
    # Escape for HTML text and double-quoted attributes. Braces become entities, so
    # a template language evaluating the slot (HubSpot's HubL) never sees {{ }}.
    return escape(value, quote=True).replace("{", "&#123;").replace("}", "&#125;")


def _same_target(label: str, url: str) -> bool:
    return label.casefold().rstrip("/") == url.casefold().rstrip("/")


class BodyLink(CreatorModel):
    label: str = Field(min_length=1)
    url: str = Field(min_length=1)

    @model_validator(mode="after")
    def descriptive_https_link(self) -> Self:
        _https(self.url)
        if _same_target(self.label, self.url):
            raise ValueError("a link label must describe its target, not repeat the URL")
        return self


class BodyImage(CreatorModel):
    src: str = Field(min_length=1)
    width: int = Field(gt=0, le=1200)
    alt: str = ""
    decorative: bool = False

    @model_validator(mode="after")
    def alternative_text(self) -> Self:
        _https(self.src)
        if self.decorative and self.alt:
            raise ValueError("a decorative image carries empty alternative text")
        if not self.decorative and not self.alt:
            raise ValueError("an informative image needs alternative text")
        return self


class BodyBlock(CreatorModel):
    heading: str | None = None
    heading_href: str | None = None
    paragraphs: tuple[str, ...] = ()
    links: tuple[BodyLink, ...] = ()
    image: BodyImage | None = None

    @model_validator(mode="after")
    def has_content(self) -> Self:
        if not (self.heading or self.paragraphs or self.links or self.image):
            raise ValueError("an email body block needs content")
        if any(not item for item in self.paragraphs):
            raise ValueError("email paragraphs must not be empty")
        if self.heading_href is not None:
            if not self.heading:
                raise ValueError("a heading link needs a heading")
            _https(self.heading_href)
            if _same_target(self.heading, self.heading_href):
                raise ValueError("a link label must describe its target, not repeat the URL")
        return self


class RenderedEmailBody(CreatorModel):
    html: str = Field(min_length=1)
    plain_text: str = Field(min_length=1)
    links: tuple[BodyLink, ...] = ()
    html_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plain_text_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def digests_bind_the_text(self) -> Self:
        if self.html_digest != canonical_digest(self.html) or (
            self.plain_text_digest != canonical_digest(self.plain_text)
        ):
            raise ValueError("rendered digests must bind the exact html and plain text")
        return self


def _links(blocks: tuple[BodyBlock, ...]) -> list[BodyLink]:
    found: list[BodyLink] = []
    for block in blocks:
        if block.heading and block.heading_href:
            found.append(BodyLink(label=block.heading, url=block.heading_href))
        found.extend(block.links)
    return found


def render_email_body(
    *,
    language: str,
    blocks: tuple[BodyBlock, ...],
    direction: Literal["ltr", "rtl"] = "ltr",
    preheader: str | None = None,
) -> RenderedEmailBody:
    """Render blocks to an escaped HTML fragment and its plain-text twin."""
    if not _LANGUAGE.fullmatch(language):
        raise ValueError("language must be a BCP 47 tag")
    if direction not in _DIRECTIONS:
        raise ValueError("direction must be ltr or rtl")
    if not blocks:
        raise ValueError("an email body needs at least one block")
    html: list[str] = [f'<div lang="{_text(language)}" dir="{_text(direction)}">']
    plain: list[str] = []
    if preheader:
        html.append(f'<div style="{_HIDDEN}" aria-hidden="true">{_text(preheader)}</div>')
    for block in blocks:
        html.append("<section>")
        text: list[str] = []
        if block.heading and block.heading_href:
            html.append(
                f'<h2><a href="{_text(block.heading_href)}">{_text(block.heading)}</a></h2>'
            )
            text.append(f"{block.heading}: {block.heading_href}")
        elif block.heading:
            html.append(f"<h2>{_text(block.heading)}</h2>")
            text.append(block.heading)
        if block.image:
            image = block.image
            html.append(
                f'<img src="{_text(image.src)}" alt="{_text(image.alt)}"'
                f' width="{image.width}" style="{_IMAGE}">'
            )
            if not image.decorative:
                text.append(f"Image: {image.alt}")
        for paragraph in block.paragraphs:
            html.append(f"<p>{_text(paragraph)}</p>")
            text.append(paragraph)
        for link in block.links:
            html.append(f'<p><a href="{_text(link.url)}">{_text(link.label)}</a></p>')
            text.append(f"{link.label}: {link.url}")
        html.append("</section>")
        plain.append("\n\n".join(text))
    html.append("</div>")
    rendered_html = "".join(html)
    plain_text = "\n\n".join(item for item in plain if item)
    if not plain_text:
        raise ValueError("an email body needs readable plain text")
    return RenderedEmailBody(
        html=rendered_html,
        plain_text=plain_text,
        links=tuple(_links(blocks)),
        html_digest=canonical_digest(rendered_html),
        plain_text_digest=canonical_digest(plain_text),
    )
