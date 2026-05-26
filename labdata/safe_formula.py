"""Safe mathematical formula evaluation for derived lab fields.

Formulas are entered by staff users in DataField.calculation_formula and are
computed row-by-row from variable names defined on the experiment fields.
"""

from __future__ import annotations

import ast
import math
import operator as op
from decimal import Decimal
from typing import Any, Mapping


class FormulaError(ValueError):
    """Raised when a formula is invalid or cannot be evaluated."""


_ALLOWED_BINARY_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.FloorDiv: op.floordiv,
}

_ALLOWED_UNARY_OPERATORS = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}

_ALLOWED_FUNCTIONS = {
    name: getattr(math, name)
    for name in [
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
        'sinh', 'cosh', 'tanh',
        'sqrt', 'log', 'log10', 'log2', 'exp',
        'degrees', 'radians',
        'ceil', 'floor', 'fabs', 'factorial',
    ]
}
_ALLOWED_FUNCTIONS.update({
    'abs': abs,
    'round': round,
    'min': min,
    'max': max,
})

_ALLOWED_CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
}


def _to_number(value: Any, variable_name: str) -> float:
    if value in ('', None):
        raise FormulaError(f'Missing value for variable "{variable_name}".')
    try:
        return float(Decimal(str(value)))
    except Exception as exc:
        raise FormulaError(f'Variable "{variable_name}" must be numeric.') from exc


def _eval_node(node: ast.AST, variables: Mapping[str, Any]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaError('Only numeric constants are allowed in formulas.')

    # Python <3.8 compatibility if ever needed.
    if isinstance(node, ast.Num):  # pragma: no cover
        return float(node.n)

    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_CONSTANTS:
            return float(_ALLOWED_CONSTANTS[node.id])
        if node.id in variables:
            return _to_number(variables[node.id], node.id)
        raise FormulaError(f'Unknown variable or constant "{node.id}".')

    if isinstance(node, ast.BinOp):
        operator_type = type(node.op)
        if operator_type not in _ALLOWED_BINARY_OPERATORS:
            raise FormulaError('This mathematical operator is not allowed.')
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        return _ALLOWED_BINARY_OPERATORS[operator_type](left, right)

    if isinstance(node, ast.UnaryOp):
        operator_type = type(node.op)
        if operator_type not in _ALLOWED_UNARY_OPERATORS:
            raise FormulaError('This unary operator is not allowed.')
        return _ALLOWED_UNARY_OPERATORS[operator_type](_eval_node(node.operand, variables))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise FormulaError('Only direct function calls such as sin(x) are allowed.')
        function_name = node.func.id
        if function_name not in _ALLOWED_FUNCTIONS:
            raise FormulaError(f'Function "{function_name}" is not allowed.')
        if node.keywords:
            raise FormulaError('Keyword arguments are not allowed in formulas.')
        args = [_eval_node(arg, variables) for arg in node.args]
        try:
            return float(_ALLOWED_FUNCTIONS[function_name](*args))
        except Exception as exc:
            raise FormulaError(f'Could not evaluate function "{function_name}".') from exc

    raise FormulaError('Unsupported expression in formula.')


def evaluate_formula(formula: str, variables: Mapping[str, Any]) -> float:
    """Evaluate a formula using only safe mathematical operations.

    Examples:
        length / time
        2*pi*r
        m*g*h
        sin(theta*pi/180)
        sqrt(x**2 + y**2)
    """
    if not formula or not formula.strip():
        raise FormulaError('A derived field must have a formula.')
    try:
        tree = ast.parse(formula, mode='eval')
    except SyntaxError as exc:
        raise FormulaError('Formula syntax is invalid.') from exc
    return _eval_node(tree, variables)


def format_result(value: float) -> str:
    """Format calculated values compactly without losing useful precision."""
    if math.isnan(value) or math.isinf(value):
        raise FormulaError('Formula produced a non-finite result.')
    return f'{value:.10g}'
