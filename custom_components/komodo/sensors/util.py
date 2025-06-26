from typing import List, Optional

def find_by_name[T](list: List[T], name: str) -> Optional[T]:
    """Find an element in the list with matching name."""
    for item in list:
        if hasattr(item, "name") and getattr(item, "name") == name:
            return item
    return None