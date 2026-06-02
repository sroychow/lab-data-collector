"""Safe mathematical formula evaluation for lab fields and final results."""
from __future__ import annotations

import ast
import math
import operator as op
from decimal import Decimal
from statistics import mean as statistics_mean, pstdev
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
        'sinh', 'cosh', 'tanh', 'sqrt', 'log', 'log10', 'log2',
        'exp', 'degrees', 'radians', 'ceil', 'floor', 'fabs', 'factorial',
    ]
}
_ALLOWED_FUNCTIONS.update({'abs': abs, 'round': round, 'min': min, 'max': max})
_ALLOWED_CONSTANTS = {'pi': math.pi, 'e': math.e, 'tau': math.tau}


def _to_number(value: Any, variable_name: str) -> float:
    if value in ('', None):
        raise FormulaError(f'Missing value for variable "{variable_name}".')
    try:
        return float(Decimal(str(value).replace(',', '.')))
    except Exception as exc:
        raise FormulaError(f'Variable "{variable_name}" must be numeric.') from exc


def _to_number_list(value: Any, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)):
        raise FormulaError(f'"{label}" is not a table column.')
    numbers = []
    for item in value:
        if item not in ('', None):
            numbers.append(_to_number(item, label))
    if not numbers:
        raise FormulaError(f'No numeric values found for "{label}".')
    return numbers


def _resolve_attribute(node: ast.Attribute, variables: Mapping[str, Any]) -> tuple[str, Any]:
    parts = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        raise FormulaError('Only table.field references are allowed.')
    parts.append(current.id)
    parts.reverse()

    value: Any = variables
    path = []
    for part in parts:
        path.append(part)
        if isinstance(value, Mapping) and part in value:
            value = value[part]
        else:
            raise FormulaError(f'Unknown variable or table column "{".".join(path)}".')
    return '.'.join(parts), value


def _aggregate(function_name: str, value: Any, label: str) -> float:
    numbers = _to_number_list(value, label)
    if function_name == 'mean':
        return float(statistics_mean(numbers))
    if function_name == 'sum':
        return float(sum(numbers))
    if function_name == 'min':
        return float(min(numbers))
    if function_name == 'max':
        return float(max(numbers))
    if function_name == 'count':
        return float(len(numbers))
    if function_name == 'first':
        return float(numbers[0])
    if function_name == 'last':
        return float(numbers[-1])
    if function_name == 'std':
        return float(pstdev(numbers)) if len(numbers) > 1 else 0.0
    raise FormulaError(f'Aggregate function "{function_name}" is not allowed.')


def _eval_node(node: ast.AST, variables: Mapping[str, Any]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaError('Only numeric constants are allowed in formulas.')

    if isinstance(node, ast.Num):  # pragma: no cover
        return float(node.n)

    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_CONSTANTS:
            return float(_ALLOWED_CONSTANTS[node.id])
        if node.id in variables:
            return _to_number(variables[node.id], node.id)
        raise FormulaError(f'Unknown variable or constant "{node.id}".')

    if isinstance(node, ast.Attribute):
        label, value = _resolve_attribute(node, variables)
        if isinstance(value, (list, tuple)):
            raise FormulaError(f'Use an aggregate such as mean({label}) for table columns.')
        return _to_number(value, label)

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
        if node.keywords:
            raise FormulaError('Keyword arguments are not allowed in formulas.')

        aggregate_names = {'mean', 'sum', 'count', 'first', 'last', 'std'}
        if function_name in aggregate_names:
            if len(node.args) != 1:
                raise FormulaError(f'{function_name}() takes exactly one table column.')
            arg = node.args[0]
            if not isinstance(arg, ast.Attribute):
                raise FormulaError(f'{function_name}() must be used as {function_name}(table.field).')
            label, value = _resolve_attribute(arg, variables)
            return _aggregate(function_name, value, label)

        if function_name in {'min', 'max'} and len(node.args) == 1 and isinstance(node.args[0], ast.Attribute):
            label, value = _resolve_attribute(node.args[0], variables)
            return _aggregate(function_name, value, label)

        if function_name not in _ALLOWED_FUNCTIONS:
            raise FormulaError(f'Function "{function_name}" is not allowed.')
        args = [_eval_node(arg, variables) for arg in node.args]
        try:
            return float(_ALLOWED_FUNCTIONS[function_name](*args))
        except Exception as exc:
            raise FormulaError(f'Could not evaluate function "{function_name}".') from exc

    raise FormulaError('Unsupported expression in formula.')


def evaluate_formula(formula: str, variables: Mapping[str, Any]) -> float:
    if not formula or not formula.strip():
        raise FormulaError('A calculated field must have a formula.')
    try:
        tree = ast.parse(formula, mode='eval')
    except SyntaxError as exc:
        raise FormulaError('Formula syntax is invalid.') from exc
    return _eval_node(tree, variables)


def format_result(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        raise FormulaError('Formula produced a non-finite result.')
    return f'{value:.10g}'
