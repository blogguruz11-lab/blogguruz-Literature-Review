
def _read_item(raw, name: str, issues: list[str]) -> dict | None:
    if raw is None:
        return None

    if isinstance(raw, dict):
        text, page, excerpt = raw.get("text"), raw.get("page"), raw.get("excerpt")

        ok = (
            isinstance(text, str)
            and text.strip()
            and len(text) <= getattr(config, "MAX_ITEM_TEXT_CHARS", 10000)
            and isinstance(excerpt, str)
            and excerpt.strip()
            and len(excerpt) <= getattr(config, "MAX_EXCERPT_CHARS", 5000)
            and isinstance(page, int)
            and not isinstance(page, bool)
        )

        if ok:
            relevant = raw.get("relevant")
            return {
                "text": text.strip(),
                "page": page,
                "excerpt": excerpt.strip(),
                "relevant": relevant if isinstance(relevant, bool) else None,
            }

    issues.append(
        f"{name}: the model returned an item in the wrong format, so it was left out."
    )
    return None
