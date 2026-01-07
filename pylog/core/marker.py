from typing import List, Optional, Set

class Marker:
    """
    Markers are used to tag log events with specific characteristics.
    They can be used for filtering or routing.
    Markers can have parents, forming a hierarchy.
    """
    def __init__(self, name: str, parents: Optional[List['Marker']] = None):
        self.name = name
        self.parents = parents or []

    def is_instance_of(self, name: str) -> bool:
        """Check if this marker is instance of 'name' (inclusive of parents)"""
        if self.name == name:
            return True
        for p in self.parents:
            if p.is_instance_of(name):
                return True
        return False
    
    def get_all_names(self) -> Set[str]:
        """Get all marker names in the hierarchy"""
        names = {self.name}
        for p in self.parents:
            names.update(p.get_all_names())
        return names

    def __repr__(self):
        return f"Marker({self.name})"

    def __eq__(self, other):
        if not isinstance(other, Marker):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)
