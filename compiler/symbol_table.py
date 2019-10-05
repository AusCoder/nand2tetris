import itertools
from collections import deque
from dataclasses import dataclass
from enum import Enum


class SymbolTableError(RuntimeError):
    pass


class SymbolNotFoundError(SymbolTableError):
    pass


class Kind(Enum):
    FIELD = 0
    STATIC = 1
    LOCAL = 2
    ARGUMENT = 3


@dataclass
class Type:
    pass


@dataclass
class TypeInt(Type):
    pass


@dataclass
class TypeBool(Type):
    pass


@dataclass
class TypeChar(Type):
    pass


@dataclass
class TypeClass(Type):
    value: str


@dataclass
class Symbol:
    name: str
    type_: Type
    kind: Kind
    index: int


class SymbolTable:
    def __init__(self):
        self._table = dict()

    def add(self, name: str, type_: Type, kind: Kind):
        index = (
            max((s.index for s in self._table.values() if s.kind == kind), default=-1)
            + 1
        )
        if name in self._table:
            raise SymbolTableError(f"Symbol already exists: {name}")
        self._table[name] = Symbol(name, type_, kind, index)

    def lookup(self, name: str):
        try:
            return self._table[name]
        except KeyError:
            raise SymbolNotFoundError(f"Symbol not found: {name}")

    def __iter__(self):
        return iter(self._table.values())


class SymbolTables:
    def __init__(self):
        self._tables = deque()

    def push_new(self) -> None:
        self._tables.appendleft(SymbolTable())

    def pop(self) -> None:
        self._tables.popleft()

    def add(self, name: str, type_: Type, kind: Kind) -> None:
        try:
            self._tables[0].add(name, type_, kind)
        except IndexError:
            raise SymbolTableError("No symbol tables pushed")

    def lookup(self, name: str) -> Symbol:
        for symbol_table in self._tables:
            try:
                return symbol_table.lookup(name)
            except SymbolNotFoundError:
                pass
        raise SymbolNotFoundError(f"Symbol not found: {name}")

    def __iter__(self):
        return itertools.chain.from_iterable(self._tables)
