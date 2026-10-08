from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from originsort.models import SourceIdentity

ECLASS_DOMAIN = "eclass.dongguk.edu"


def parse_eclass_source(url: str | None) -> SourceIdentity | None:
    if not url:
        return None

    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    if parsed.hostname != ECLASS_DOMAIN:
        return None
    if parsed.path.rstrip("/") != "/mod/ubboard/article.php":
        return None

    resource_ids = parse_qs(parsed.query).get("id")
    if not resource_ids or not resource_ids[0].isdigit():
        return None

    return SourceIdentity(
        parser="dongguk_eclass",
        kind="ubboard",
        resource_id=resource_ids[0],
        domain=ECLASS_DOMAIN,
    )

