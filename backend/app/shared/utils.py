from math import ceil


def build_pagination(page: int, size: int, total: int) -> dict:
    pages = ceil(total / size) if total > 0 else 0
    return {
        "page": page,
        "size": size,
        "total": total,
        "pages": pages,
    }
