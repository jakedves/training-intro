from __future__ import annotations

from typing import List

from xdsl.dialects.builtin import IntegerAttr, StringAttr, ArrayAttr, AnyAttr, FloatAttr
from xdsl.ir import Data, Operation, ParametrizedAttribute, Dialect, TypeAttribute
from xdsl.irdl import (AnyOf, region_def, Block, Region, irdl_attr_definition,
                        irdl_op_definition, prop_def, IRDLOperation)
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.traits import NoTerminator, IsTerminator

"""
This is our bespoke Python dialect that we are calling tiny_py. As you will see it is
rather limited but is sufficient for our needs, and being simple means that we can easily
navigate it and understand what is going on.
"""


@irdl_attr_definition
class BoolType(Data[bool]):
    """
    Represents a boolean, MLIR does not by default have a boolean (it uses integer 1 and 0)
    and-so this can be useful in your own dialects
    """
    name = "tiny_py.bool"
    data: bool

    @staticmethod
    def parse_parameter(parser: Parser) -> BoolType:
        data = parser.parse_str_literal()
        if data == "True": return True
        if data == "False": return False
        raise Exception(f"bool parsing resulted in {data}")
        return None

    def print_parameter(self, printer: Printer) -> None:
        printer.print_string(f'"{self.data}"')

    @staticmethod
    def from_bool(data: bool) -> BoolType:
        return BoolType(data)


@irdl_attr_definition
class EmptyType(ParametrizedAttribute, TypeAttribute):
    """
    This represents an empty value, can be useful where you
    need a placeholder to explicitly denote that something is not filled
    """
    name = "tiny_py.empty"


@irdl_op_definition
class Module(IRDLOperation):
    """
    A Python module, this is the top level Python container which is a region
    """
    name = "tiny_py.module"
    traits = frozenset(
        [
            NoTerminator(),
            IsTerminator()
        ]
    )

    children = region_def()

    def __init__(self, contents: List[Operation], verify_op: bool = True):
        super().__init__(regions=[contents])

        if verify_op:
            self.verify(verify_nested_ops=False)


@irdl_op_definition
class Function(IRDLOperation):
    """
    A Python function, our handling here is simplistic and limited but sufficient
    for the exercise (and keeps this simple!) You can see how we have a mixture of
    attributes and a region for the body
    """
    name = "tiny_py.function"
    traits = frozenset([NoTerminator()])

    fn_name = prop_def(StringAttr)
    args = prop_def(ArrayAttr)
    return_var = prop_def(AnyAttr())
    body = region_def()

    def __init__(
        self,
        fn_name: str | StringAttr,
        return_var: Operation | None,
        args: List[Operation],
        body: List[Operation],
        verify_op: bool = True
    ):
        if isinstance(fn_name, str):
            # If fn_name is a string then wrap it in StringAttr
            fn_name = StringAttr(fn_name)

        if return_var is None:
            # If return is None then use the empty token placeholder
            return_var = EmptyType()

        super().__init__(
            properties={"fn_name": fn_name, "return_var": return_var, "args": ArrayAttr(args)},
            regions=[Region([Block(body)])]
        )

        if verify_op:
            # We don't verify nested operations since they might have already been verified
            self.verify(verify_nested_ops=False)


@irdl_op_definition
class Assign(IRDLOperation):
    """
    Represents variable assignment, where the LHS is the variable and RHS an expression. Note
    that we are fairly limited here to representing one variable on the LHS only.
    We also make life simpler by just storing the variable name as a string, rather than a reference
    to the token which is also referenced directly by other parts of the code. The later is
    more flexible, but adds additional complexity in the code so we keep it simple here.
    """
    name = "tiny_py.assign"
    traits = frozenset([NoTerminator()])

    var_name = prop_def(StringAttr)
    value = region_def()

    def __init__(self,
                 var_name: str | StringAttr,
                 value: Operation,
                 verify_op: bool = True):
        if isinstance(var_name, str):
            # If var_name is a string then wrap it in StringAttr
            var_name = StringAttr(var_name)

        super().__init__(properties={"var_name": var_name}, regions=[Region([Block([value])])])

        if verify_op:
            # We don't verify nested operations since they might have already been verified
            self.verify(verify_nested_ops=False)


@irdl_op_definition
class Loop(IRDLOperation):
    """
    A Python loop, we take a restricted view here that the loop will operate on a variable
    between two bounds (e.g. has been provided with a Python range).

    We have started this dialect definition off for you, and you will need to complete it.
    There should be four members - a variable which is a string attribute and three
    regions (the from and to expressions, and loop body)
    """
    name = "tiny_py.loop"
    traits = frozenset([NoTerminator()])

    variable = prop_def(StringAttr)
    from_expr = region_def()
    to_expr = region_def()
    body = region_def()

    def __init__(self,
                 variable: str | StringAttr,
                 from_expr: Operation,
                 to_expr: Operation,
                 body: List[Operation],
                 verify_op: bool = True):
        # We need to wrap from_expr and to_expr in lists because they are defined as separate regions
        # and a region is a block with a list of operations. This is not needed for body because it is
        # already a list of operations
        if isinstance(variable, str):
            # If variable is a string then wrap it in StringAttr
            variable = StringAttr(variable)

        super().__init__(properties={"variable": variable},
                         regions=[
                             Region([Block([from_expr])]),
                             Region([Block([to_expr])]),
                             Region([Block(body)])
                         ])
        if verify_op:
            # We don't verify nested operations since they might have already been verified
            self.verify(verify_nested_ops=False)


@irdl_op_definition
class Var(IRDLOperation):
    """
    A variable reference in Python, we just use the string name as storage here rather
    than pointing to a token instance of the variable which others would also reference
    directly.
    """
    name = "tiny_py.var"

    variable = prop_def(StringAttr)

    def __init__(self,
                 variable: str | StringAttr,
                 verify_op: bool = True):

        if isinstance(variable, str):
            # If variable is a string then wrap it in StringAttr
            variable = StringAttr(variable)

        super().__init__(properties={"variable": variable})

        if verify_op:
            # We don't verify nested operations since they might have already been verified
            self.verify(verify_nested_ops=False)

@irdl_op_definition
class BinaryOperation(IRDLOperation):
    """
    A Python binary operation, storing the operation type as a string
    and the LHS and RHS expressions as regions
    """
    name = "tiny_py.binaryoperation"
    traits = frozenset([NoTerminator()])

    op = prop_def(StringAttr)
    lhs = region_def()
    rhs = region_def()

    def __init__(self,
                 op: str | StringAttr,
                 lhs: Operation,
                 rhs: Operation,
                 verify_op: bool = True):
        if isinstance(op, str):
            # If op is a string then wrap it in StringAttr
            op = StringAttr(op)

        super().__init__(
            properties={"op": op},
            regions=[Region([Block([lhs])]), Region([Block([rhs])])]
        )

        if verify_op:
            # We don't verify nested operations since they might have already been verified
            self.verify(verify_nested_ops=False)


@irdl_op_definition
class Constant(IRDLOperation):
    """
    A constant value, we currently support integers, floating points, and strings
    """
    name = "tiny_py.constant"
    value = prop_def(AnyOf([StringAttr, IntegerAttr, FloatAttr]))

    def __init__(self,
                 value: None | bool | int | str | float,
                 width: int = 32,
                 verify_op: bool = True):

        if type(value) is int:
            attr = IntegerAttr.from_int_and_width(value, width)
        elif type(value) is float:
            attr = FloatAttr(value, width)
        elif type(value) is str:
            attr = StringAttr(value)
        else:
            raise Exception(f"Unknown constant of type {type(value)}")

        super().__init__(properties={"value": attr})

        if verify_op:
            # We don't verify nested operations since they might have already been verified
            self.verify(verify_nested_ops=False)


@irdl_op_definition
class Return(IRDLOperation):
    """
    Return from a function, we just support return without
    any values/expressions at the moment
    """
    name = "tiny_py.return"


@irdl_op_definition
class CallExpr(IRDLOperation):
    """
    Calling a function, in our example calling the print function, we store the target
    function name and whether this is a builtin function as attributes (the second is
    using the Boolean Attribute that we define in this dialect). The type of the call is
    handled, as this is needed if the call is used as an expression rather than a statement,
    and lastly the arguments to pass which are enclosed in a region.
    """
    name = "tiny_py.call_expr"
    traits = frozenset([NoTerminator()])

    func = prop_def(StringAttr)
    builtin = prop_def(BoolType)
    type = prop_def(AnyOf([AnyAttr(), EmptyType]))
    args = region_def()

    def __init__(self,
                 func: str | StringAttr,
                 args: List[Operation],
                 type=EmptyType(),
                 builtin: bool = False,
                 verify_op: bool = True):

        if isinstance(func, str):
            # If func is a string then wrap it in StringAttr
            func = StringAttr(func)

        builtin = BoolType(builtin)

        super().__init__(
            regions=[Region([Block(args)])],
            properties={"func": func, "type": type, "builtin": builtin}
        )

        if verify_op:
            # We don't verify nested operations since they might have already been verified
            self.verify(verify_nested_ops=False)


tinyPyIR = Dialect(
    "tiny_py",
    [
        Module,
        Function,
        Return,
        Constant,
        Assign,
        Loop,
        Var,
        BinaryOperation,
        CallExpr,
    ], [
        BoolType,
        EmptyType,
    ]
)
