def get_user_uri(request) -> str | None:
    """
    Helper function which returns user's uri
    It supports both session auth and PAT, which must not store any info in session (because they may be revoked later)
    """
    return request.session.get("user_reference_uri") or getattr(
        request, "user_uri", None
    )
