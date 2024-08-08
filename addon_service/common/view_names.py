"""helpers for a consistent view naming scheme"""


def detail_view(resource_type: str):
    """detail view for the given resource type"""
    return f"{resource_type}-detail"


def related_view(resource_type: str):
    """related view for the given resource type"""
    return f"{resource_type}-related"
