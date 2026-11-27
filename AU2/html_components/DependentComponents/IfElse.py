from abc import ABC, abstractmethod
from typing import Dict, Generic, List, Sequence, Tuple, TypeVar

from AU2.html_components import HTMLComponent

T = TypeVar("T")


class Expression(ABC, Generic[T]):
    """
    An abstract representation of an expression as part of an if-else condition.
    This allows the same logic to be translated to JavaScript in a HTML rendering of the IfElse component
    """
    @abstractmethod
    def evaluate(self, dependency_context) -> T:
        """Determine the true/false value of the condition (for Python-based frontends)"""

    @abstractmethod
    def to_js(self) -> str:
        """Render this expression as JavaScript."""


class Equal(Expression[bool]):
    def __init__(self, left: Expression, right: Expression):
        self.left = left
        self.right = right

    def evaluate(self, dependency_context) -> bool:
        return self.left.evaluate(dependency_context) == self.right.evaluate(dependency_context)

    def to_js(self) -> str:
        return f"({self.left.to_js()} == {self.right.to_js()})"


class Not(Expression[bool]):
    def __init__(self, expression: Expression[bool]):
        self.expression = expression

    def evaluate(self, dependency_context) -> bool:
        return not self.expression.evaluate(dependency_context)

    def to_js(self) -> str:
        return f"!({self.expression.to_js()})"


class ComponentValue(Expression[T]):
    def __init__(self, component_identifier: str):
        self.component_identifier = component_identifier

    def evaluate(self, dependency_context) -> T:
        return dependency_context[self.component_identifier]

    def to_js(self) -> str:
        # precise implementation to be decided...
        raise NotImplemented()


class Literal(Expression[T]):
    def __init__(self, value: T):
        self.value = value

    def evaluate(self, dependency_context) -> T:
        return self.value

    def to_js(self) -> str:
        # implement string escaping etc.
        raise NotImplemented()


class IfElse(HTMLComponent):
    name: str = "IfElse"

    def __init__(self, condition: Expression[bool],
                 then: Sequence[HTMLComponent], otherwise: Sequence[HTMLComponent] = (),
                 noInteraction: bool = False):
        self.condition = condition
        self.then = then
        self.otherwise = otherwise
        self.noInteraction = noInteraction
        super().__init__()
