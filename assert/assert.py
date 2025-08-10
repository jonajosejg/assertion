import re
import math
import types
import inspect
import builtins
from typing import Any, Optional, Union, Callable, Pattern, Type, Tuple, Dict, List

class AssertError(Exception):
    def __init__(
        self,
        message: Optional[str] = None,
        actual: Any = None,
        expected: Any = None,
        operator: str = 'fail',
        generated_message: bool = False,
        stack_start_fn: Optional[Callable] = None
    ):
        if message is None:
            if operator == 'fail':
                message = 'Assertion failed.'
            else:
                actual_str = stringify(actual)
                expected_str = stringify(expected)
                message = f'{actual_str} {operator} {expected_str}'
            generated_message = True

        super().__init__(message)

        self.generated_message = generated_message
        self.code = 'ERR_ASSERTION'
        self.actual = actual
        self.expected = expected
        self.operator = operator
        self.name = 'AssertError'

        # Capture stack trace
        if stack_start_fn:
            try:
                # Remove current function from stack
                stack = inspect.stack()
                start_index = 0
                for i, frame in enumerate(stack):
                    if frame.function == stack_start_fn.__name__:
                        start_index = i + 1
                        break
                self.stack = ''.join(frame[4] for frame in stack[start_index:])
            except Exception:
                pass

    def __str__(self) -> str:
        return f'{self.name} [{self.code}]: {super().__str__()}'

def assert_(value: Any, message: Optional[Union[str, Exception]] = None) -> None:
    if not value:
        generated_message = False
        if message is None:
            message = 'Assertion failed.' if value is not None else 'No value argument passed to `assert()`.'
            generated_message = True
        elif isinstance(message, Exception):
            raise message

        raise AssertionError(
            message=message,
            actual=value,
            expected=True,
            operator='==',
            generated_message=generated_message,
            stack_start_fn=assert_
        )

def equal(actual: Any, expected: Any, message: Optional[Union[str, Exception]] = None) -> None:
    if not object_is(actual, expected):
        if isinstance(message, Exception):
            raise message
            
        raise AssertionError(
            message=message,
            actual=actual,
            expected=expected,
            operator='strictEqual',
            stack_start_fn=equal
        )

def not_equal(actual: Any, expected: Any, message: Optional[Union[str, Exception]] = None) -> None:
    if object_is(actual, expected):
        if isinstance(message, Exception):
            raise message
            
        raise AssertionError(
            message=message,
            actual=actual,
            expected=expected,
            operator='notStrictEqual',
            stack_start_fn=not_equal
        )

def fail(message: Optional[Union[str, Exception]] = None) -> None:
    generated_message = False
    if message is None:
        message = 'Assertion failed.'
        generated_message = True
    elif isinstance(message, Exception):
        raise message

    raise AssertionError(
        message=message,
        actual=False,
        expected=True,
        operator='fail',
        generated_message=generated_message,
        stack_start_fn=fail
    )

def throws(
    func: Callable,
    expected: Optional[Union[Type[Exception], Callable, Pattern, dict]] = None,
    message: Optional[str] = None
) -> None:
    if isinstance(expected, (str, Pattern)):
        message, expected = expected, None

    try:
        func()
        thrown = False
    except Exception as e:
        thrown = True
        err = e

    if not thrown:
        raise AssertionError(
            message=message or 'Missing expected exception.',
            actual=None,
            expected=expected,
            operator='throws',
            generated_message=message is None,
            stack_start_fn=throws
        )

    if expected and not test_error(err, expected, message, throws):
        raise err

def does_not_throw(
    func: Callable,
    expected: Optional[Union[Type[Exception], Callable, Pattern, dict]] = None,
    message: Optional[str] = None
) -> None:
    if isinstance(expected, (str, Pattern)):
        message, expected = expected, None

    try:
        func()
    except Exception as e:
        if test_error(e, expected, message, does_not_throw):
            raise AssertionError(
                message=message or 'Got unwanted exception.',
                actual=e,
                expected=expected,
                operator='doesNotThrow',
                generated_message=message is None,
                stack_start_fn=does_not_throw
            ) from None
        raise

def if_error(err: Optional[Exception]) -> None:
    if err is not None:
        msg = f'ifError got unwanted exception: {stringify(err)}'
        raise AssertionError(
            message=msg,
            actual=err,
            expected=None,
            operator='ifError',
            generated_message=True,
            stack_start_fn=if_error
        )

def deep_equal(actual: Any, expected: Any, message: Optional[str] = None) -> None:
    if not is_deep_equal(actual, expected):
        if isinstance(message, Exception):
            raise message
            
        raise AssertionError(
            message=message,
            actual=actual,
            expected=expected,
            operator='deepStrictEqual',
            stack_start_fn=deep_equal
        )

def not_deep_equal(actual: Any, expected: Any, message: Optional[str] = None) -> None:
    if is_deep_equal(actual, expected):
        if isinstance(message, Exception):
            raise message
            
        raise AssertionError(
            message=message,
            actual=actual,
            expected=expected,
            operator='notDeepStrictEqual',
            stack_start_fn=not_deep_equal
        )

def enforce(value: Any, name: Optional[str] = None, type_name: Optional[str] = None) -> None:
    if not value:
        if name is None:
            msg = 'Invalid type for parameter.'
        elif type_name is None:
            msg = f'"{name}" is invalid.'
        else:
            msg = f'"{name}" must be a {type_name}.'
        raise TypeError(msg)

def range_(value: Any, name: Optional[str] = None) -> None:
    if not value:
        msg = f'"{name}" is out of range.' if name else 'Value out of range'
        raise ValueError(msg)

# Helper functions
def object_is(a: Any, b: Any) -> bool:
    """Mimic JavaScript's Object.is() behavior"""
    if a is b:
        return True
    
    # Handle NaN
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    
    # Handle signed zeros
    if a == 0 and b == 0 and (1/a > 0) != (1/b > 0):
        return False
    
    return a == b

def stringify(value: Any) -> str:
    """Convert value to descriptive string"""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return repr(value[:80] + '...' if len(value) > 80 else value)
    if isinstance(value, bytes):
        return f'bytes({len(value)})'
    if isinstance(value, (list, tuple, set, dict)):
        return f'{type(value).__name__}({len(value)})'
    if hasattr(value, '__name__'):
        return f'function {value.__name__}'
    return repr(value)[:80] + ('...' if len(repr(value)) > 80 else '')

def is_deep_equal(a: Any, b: Any) -> bool:
    """Recursive deep equality check"""
    if object_is(a, b):
        return True
    
    if type(a) is not type(b):
        return False
    
    # Handle collections
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(is_deep_equal(x, y) for x, y in zip(a, b))
    
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(is_deep_equal(a[k], b[k]) for k in a)
    
    # Handle sets
    if isinstance(a, set):
        return a == b
    
    # Handle bytes
    if isinstance(a, bytes):
        return a == b
    
    # Handle custom objects
    if hasattr(a, '__dict__') and hasattr(b, '__dict__'):
        return is_deep_equal(a.__dict__, b.__dict__)
    
    return a == b

def test_error(
    err: Exception,
    expected: Union[Type[Exception], Callable, Pattern, dict],
    message: Optional[str],
    fn: Callable
) -> bool:
    """Test if error matches expected criteria"""
    # Handle error type
    if isinstance(expected, type) and issubclass(expected, Exception):
        return isinstance(err, expected)
    
    # Handle regex pattern
    if isinstance(expected, Pattern):
        return bool(expected.search(str(err)))
    
    # Handle validation function
    if callable(expected):
        try:
            return bool(expected(err))
        except Exception:
            return False
    
    # Handle error properties (dict)
    if isinstance(expected, dict):
        for key, value in expected.items():
            if not hasattr(err, key) or not is_deep_equal(getattr(err, key), value):
                return False
        return True
    
    return False

# Alias functions to match Node.js names
def strict_equal(actual: Any, expected: Any, message: Optional[str] = None) -> None:
    equal(actual, expected, message)

def not_strict_equal(actual: Any, expected: Any, message: Optional[str] = None) -> None:
    not_equal(actual, expected, message)

def deep_strict_equal(actual: Any, expected: Any, message: Optional[str] = None) -> None:
    deep_equal(actual, expected, message)

def not_deep_strict_equal(actual: Any, expected: Any, message: Optional[str] = None) -> None:
    not_deep_equal(actual, expected, message)

# Export all functions
__all__ = [
    'assert_', 'AssertError', 'equal', 'not_equal', 'fail', 'throws', 
    'does_not_throw', 'if_error', 'deep_equal', 'not_deep_equal', 'enforce', 
    'range_', 'strict_equal', 'not_strict_equal', 'deep_strict_equal',
    'not_deep_strict_equal'
]

class Assert:
    AssertError = AssertError
    assert = assert_
    strict = assert_
    ok = assert_
    equal = equal
    notEqual = not_equal
    strictEqual = strict_equal
    notStrictEqual = not_strict_equal
    fail = fail
    throws = throws
    doesNotThrow = does_not_throw
    ifError = if_error
    deepEqual = deep_equal
    notDeepEqual = not_deep_equal
    deepStrictEqual = deep_strict_equal
    notDeepStrictEqual = not_deep_strict_equal
    enforce = enforce
    range = range_

assertion = Assert()
