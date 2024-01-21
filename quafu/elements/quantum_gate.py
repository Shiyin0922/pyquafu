#  (C) Copyright 2023 Beijing Academy of Quantum Information Sciences
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import copy
from abc import ABC, abstractmethod
from typing import Callable, Dict, Iterable, List, Optional, Union

import numpy as np
from numpy import ndarray
from quafu.elements.matrices.mat_utils import reorder_matrix

from .instruction import Instruction, PosType
from .parameters import ParameterType
from .utils import extract_float

__all__ = [
    "QuantumGate",
    "FixedGate",
    "ParametricGate",
    "SingleQubitGate",
    "MultiQubitGate",
    "ControlledGate",
]

HERMITIAN = [
    "id",
    "x",
    "y",
    "z",
    "h",
    "w",
    "cx",
    "cz",
    "cy",
    "cnot",
    "swap",
    "mcx",
    "mxy",
    "mcz",
]
ROTATION = ["rx", "ry", "rz", "p", "rxx", "ryy", "rzz", "cp"]
paired = {k: k + "dg" for k in ["sx", "sy", "s", "t", "sw"]}
PAIRED = {**paired, **{v: k for k, v in paired.items()}}

MatrixType = Union[np.ndarray, Callable]


class QuantumGate(Instruction):
    """Base class for standard and combined quantum gates, namely unitary operation
    upon quantum states.

    Attributes:
        pos: Position of this gate in the circuit.
        paras: Parameters of this gate.

    Properties:
        symbol: Text symbolic representation of this gate.
        matrix: Matrix representation of this gate.

    Functions:
        register_gate: Register a new gate class.
        to_qasm: Convert this gate to QASM format.
        update_paras: Update the parameters of this gate.

    """

    gate_classes = {}

    def __init__(
            self,
            name: str,
            pos: List[int],
            paras: List[ParameterType] = [],
            matrix: Optional[Union[ndarray, Callable]] = None,
    ):
        super().__init__(pos, paras)
        self._name = name
        self._symbol = None
        self._raw_matrix = matrix

    def __str__(self):
        # only when the gate is a known(named) gate, the matrix is not shown
        if self.name.lower() in self.gate_classes:
            properties_names = ["pos", "paras"]
        else:
            properties_names = ["pos", "paras", "matrix"]
        properties_values = [getattr(self, x) for x in properties_names]
        return "%s:\n%s" % (
            self.__class__.__name__,
            "\n".join(
                [
                    f"{x} = {repr(properties_values[i])}"
                    for i, x in enumerate(properties_names)
                ]
            ),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}"

    @property
    def name(self):
        return self._name 
    
    @name.setter
    def name(self, __name):
        self._name = __name
    
    @property
    def pos(self):
        return  self._pos
    
    @pos.setter
    def pos(self, __pos):
        self._pos = copy.deepcopy(__pos)

    @classmethod
    def register_gate(cls, subclass, name: str = None):
        """Register a new gate class into gate_classes.

        This method is used as a decorator.
        """
        assert issubclass(subclass, cls)

        name = str(subclass.name).lower() if name is None else name
        assert isinstance(name, str)

        if name in cls.gate_classes:
            raise ValueError(f"Name {name} already exists.")
        cls.gate_classes[name] = subclass
        Instruction.register_ins(subclass, name)

    @classmethod
    def register(cls, name: str = None):
        """Decorator for register_gate."""

        def wrapper(subclass):
            cls.register_gate(subclass, name)
            return subclass

        return wrapper

    @property
    def _paras(self):
        return extract_float(self.paras)

    @property
    def symbol(self) -> str:
        """Symbol used in text-drawing."""
        # TODO: Use latex repr for Parameter
        if len(self.paras) > 0:
            symbol = "%s(" %self.name + ",".join(["%.3f" %para for para in self._paras]) + ")"
            return symbol
        else:
            return "%s" %self.name

    @symbol.setter
    def symbol(self, symbol: str):
        self._symbol = symbol

    @property
    def matrix(self):
        raw_mat = self._raw_matrix
        if isinstance(self._raw_matrix, Callable):
            raw_mat = self._raw_matrix(self._paras)

        if len(self.pos) > 1:
            return reorder_matrix(raw_mat, self.pos)
        else:
            return raw_mat
    
    def _get_raw_matrix(self, reverse_order=False):
        raw_mat = self._raw_matrix
        if isinstance(self._raw_matrix, Callable):
            raw_mat = self._raw_matrix(self._paras)
        if reverse_order and len(self.pos) > 1:
            return reorder_matrix(raw_mat, np.arange(len(self.pos))[::-1])
        else:
           return raw_mat
        
    # @property
    # @abstractmethod
    # def matrix(self):
    #     if self._matrix is not None:
    #         return self._matrix
    #     else:
    #         raise NotImplementedError(
    #             "Matrix is not implemented for %s" % self.__class__.__name__
    #             + ", this should never happen."
    #         )

    def to_qasm(self) -> str:
        """OPENQASM 2.0"""
        # TODO: support register naming
        qstr = "%s" %self.name.lower()
        if self.paras:
            qstr += "(" + ",".join(["%s" %para for para in self._paras]) + ")"
        qstr += " "
        qstr += ",".join(["q[%d]" % p for p in self.pos])
        return qstr

    def update_params(self, paras: Union[ParameterType, List[ParameterType]]):
        """Update parameters of this gate"""
        if paras is None:
            return
        self.paras = paras

    # # # # # # # # # # # # algebraic operations # # # # # # # # # # # #
    def power(self, n) -> "QuantumGate":
        """Return another gate equivalent to n-times operation of the present gate."""
        name = self.name.lower()
        name = 'sz' if name == 's' else name

        order4 = ["sx", "sy", "s", 'sw']
        order4 += [_+'dg' for _ in order4]
        order8 = ["t", "tdg"]

        if name in HERMITIAN:
            if n % 2 == 0:
                return self.gate_classes["id"](self.pos)
            else:
                return copy.deepcopy(self)
        elif name in order4:  # ["sx", "sy", "s", "t", "sw"]
            if n % 4 == 0:
                return self.gate_classes["id"](self.pos)
            elif n % 4 == 1:
                return copy.deepcopy(self)
            elif n % 4 == 2:
                _square_name = 'z' if name == 's' else name[1:]
                return self.gate_classes[_square_name](self.pos)
            elif n % 4 == 3:
                _conj_name = PAIRED[name]
                return self.gate_classes[_conj_name](self.pos)
        elif name in order8:  # ["t", "tdg"]
            # note: here we transform a fixed gate into a parametric gate
            #       which might cause error in future
            theta = np.pi / 4
            if name.endswith("dg"):
                theta = -theta
            return self.gate_classes["rz"](self.pos, theta * n)
        elif name in ROTATION:
            return self.gate_classes[name](self.pos, self.paras[0] * n)
        else:
            name = self.name + "^%d" %n
            raw_matrix = self._raw_matrix 
            if isinstance(self._raw_matrix, Callable):
                raw_matrix = lambda paras: np.linalg.matrix_power(self._raw_matrix(paras), n)
            else:
                raw_matrix = np.linalg.matrix_power(self._raw_matrix, n)
            return QuantumGate(name, self.pos, self.paras, raw_matrix)

    def dagger(self) -> "QuantumGate":
        """Return the hermitian conjugate gate with same the position."""
        name = self.name
        if name in HERMITIAN:  # Hermitian gate
            return copy.deepcopy(self)
        if name in ROTATION:  # rotation gate
            return self.gate_classes[name](self.pos, -self.paras[0])
        elif name in PAIRED:  # pairwise-occurrence gate
            _conj_name = PAIRED[name]
            return self.gate_classes[_conj_name](self.pos)
        else:
            name = self.name + "^†"
            raw_matrix = self._raw_matrix 
            if isinstance(self._raw_matrix, Callable):
                raw_matrix = lambda paras: self._raw_matrix(paras).conj().T
            else:
                raw_matrix = raw_matrix.conj().T
            return QuantumGate(name, self.pos, self.paras, raw_matrix)

    def ctrl_by(self, ctrls: Union[int, List[int]]) -> "QuantumGate":
        """Return a controlled gate with present gate as the controlled target."""
        ctrls = [ctrls] if not isinstance(ctrls, list) else ctrls
        pos = [self.pos] if not isinstance(self.pos, list) else self.pos
        name = self.name.lower()

        if isinstance(self, ControlledGate):
            """
            [m1]control-([m2]control-U) = [m1+m2]control-U
            """
            ctrls = list(set(self.ctrls) | set(ctrls))
        elif set(ctrls) & set(pos):
            raise ValueError("Control qubits should not be overlap with target qubits.")

        if len(ctrls) == 1 and len(pos) == 1:  # ctrl-single-qubit gate
            cname = "c" + name
            if cname not in self.gate_classes:
                raise NotImplementedError(
                    f"ctrl-by is not implemented for {self.__class__.__name__}"
                )
            else:
                return self.gate_classes[cname](ctrls[0], pos[0])
        elif name in ["mcx", "mcy", "mcz"]:
            cname = name
            return self.gate_classes[cname](ctrls, self.pos)
        elif name in ["x", "y", "z"]:
            cname = "mc" + self.name.lower()
            return self.gate_classes[cname](ctrls, self.pos)
        else:
            if isinstance(self, ControlledGate):
                cop = ControlledGate("mc"+self._targ_name, self._targ_name, ctrls+self.ctrls, self.targs, self.paras, self._targ_matrix)
                return cop
            else:
                return ControlledU("c"+self.name, ctrls, self)
                        


# Gate types below are statically implemented to support type identification
# and provide shared attributes. However, single/multi qubit may be
# inferred from ``pos``, while para/fixed type may be inferred by ``paras``.
# Therefore, these types may be (partly) deprecated in the future.


class SingleQubitGate(QuantumGate, ABC):
    def __init__(self, pos: int, paras: Optional[ParameterType] = None):
        QuantumGate.__init__(self, pos=pos, paras=paras)

    def get_targ_matrix(self):
        return self.matrix

    @property
    def named_pos(self) -> Dict:
        return {"pos": self.pos}


class MultiQubitGate(QuantumGate, ABC):
    def __init__(self, pos: List, paras: Optional[ParameterType] = None):
        QuantumGate.__init__(self, pos, paras)

    def get_targ_matrix(self, reverse_order=False):
        """ """
        targ_matrix = self.matrix

        if reverse_order and (len(self.pos) > 1):
            qnum = len(self.pos)
            dim = 2 ** qnum
            order = np.array(range(len(self.pos))[::-1])
            order = np.concatenate([order, order + qnum])
            tensorm = targ_matrix.reshape([2] * 2 * qnum)
            targ_matrix = np.transpose(tensorm, order).reshape([dim, dim])
        return targ_matrix


class ParametricGate(QuantumGate, ABC):
    def __init__(self, pos: PosType, paras: Union[ParameterType, List[ParameterType]]):
        if paras is None:
            raise ValueError("`paras` can not be None for ParametricGate")
        super().__init__(pos, paras)

    @property
    def named_paras(self) -> Dict:
        return {"paras": self.paras}

    @property
    def named_pos(self) -> Dict:
        return {"pos": self.pos}


class FixedGate(QuantumGate, ABC):
    def __init__(self, pos):
        super().__init__(pos=pos, paras=None)

    @property
    def named_paras(self) -> Dict:
        return {}


class ControlledGate(QuantumGate):
    """Controlled gate class, where the matrix act non-trivially on target qubits"""

    def __init__(
            self,
            targ_name: str,
            ctrls: List[int],
            targs: List[int],
            paras: List[float] = [],
            targ_matrix: MatrixType = None,
    ):
        self.ctrls = copy.deepcopy(ctrls)
        self.targs = copy.deepcopy(targs)
        self.targ_name = targ_name
        super().__init__(self.name, ctrls+targs, paras, targ_matrix)
        self._targ_matrix = targ_matrix
        self._raw_matrix = self._rawmatfunc

    @property
    def symbol(self):
        if len(self.paras) > 0:
            symbol = "%s(" %self._targ_name + ",".join(["%.3f" %para for para in self._paras]) + ")"
            return symbol
        else:
            return "%s" %self._targ_name
        
   
    def _rawmatfunc(self, paras:List[float]):
        targ_dim = 2**(len(self.targs))
        qnum = len(self.pos)
        dim = 2**(qnum)
        raw_matrix =  np.zeros((dim , dim), dtype=complex)
        targ_matrix = self._targ_matrix
        if isinstance(self._targ_matrix, Callable):
            targ_matrix = self._targ_matrix(paras)

        if targ_matrix.shape[0] != targ_dim:
            raise ValueError("Dimension dismatch")
        else:
            control_dim = 2**len(self.pos) - targ_dim
            for i in range(control_dim):
                raw_matrix[i, i] = 1.
            
            raw_matrix[control_dim:, control_dim:] = targ_matrix

        return raw_matrix
    
    @property
    def name(self) -> str:
        return "c" + self.targ_name

    @property
    def symbol(self):
        if self._symbol is not None:
            return self._symbol
        else:
            return self.targ_name

    @symbol.setter
    def symbol(self, symbol):
        self._symbol = symbol

    @property
    def matrix(self):
        # TODO: update matrix when paras of controlled-gate changed
        return self._matrix

    @property
    def ct_nums(self):
        targ_num = len(self.targs)
        ctrl_num = len(self.ctrls)
        num = targ_num + ctrl_num
        return ctrl_num, targ_num, num
        
    def _get_targ_matrix(self, reverse_order=False):
        targ_mat = self._targ_matrix
        if isinstance(self._targ_matrix, Callable):
            targ_mat = self._targ_matrix(self._paras)
        if reverse_order and (len(self.targs) > 1): 
            return reorder_matrix(targ_mat, np.array(range(len(self.targs))[::-1]))
        else:
            return targ_mat
    

    @property
    def named_pos(self) -> Dict:
        return {"ctrls": self.ctrls, "targs": self.targs}

    @property
    def named_paras(self) -> Dict:
        return {"paras": self.paras}

    @classmethod
    def from_target(cls, targ: QuantumGate, ctrls: PosType):
        """Shoud use controlledU"""
        return cls(targ.name, ctrls, targ.pos, targ.paras, targ._raw_matrix)

class ControlledU(ControlledGate):
    def __init__(self, name, ctrls: List[int], U: QuantumGate):
        self.targ_gate = U
        targs = U.pos
        super().__init__(name, U.name, ctrls, targs, U.paras, targ_matrix=self.targ_gate._raw_matrix)

# TODO(ChenWei): update OracleGate so that compatible with CtrlGate
# class CircuitWrapper(QuantumGate):
#     def __init__(self, name: str, circ, qbits=[]):
#         self.name = name
#         self.pos = list(range(circ.num))
#         self.circuit = copy.deepcopy(circ)
#
#         # TODO:Handle wrapper paras
#         # if hasattr(circ, "paras"):
#         #     self._paras = circ.paras
#         # else:
#         #     self._paras = []
#         #     for op in self.circuit.operations:
#         #         self._paras.extend(op.paras)
#
#         if qbits:
#             self._reallocate(qbits)
#
#     # @property
#     # def paras(self):
#     #     return self._paras
#
#     # @paras.setter
#     # def paras(self, __paras):
#     #     self._paras = __paras
#     #     self.circuit.paras = __paras
#
#     def _reallocate(self, qbits):
#         num = max(self.circuit.num - 1, max(qbits)) + 1
#         self.pos = qbits
#         self.circuit._reallocate(num, qbits)
#
#     @property
#     def symbol(self):
#         return "%s" % self.name
#
#     def add_controls(self, ctrls: List[int] = []) -> QuantumGate:
#         return ControlCircuitWrapper("MC" + self.name, self, ctrls)
#
#     def power(self, n: int):
#         self.name += "^%d" % n
#         self.circuit = self.circuit.power(n)
#         return self
#
#     def dagger(self):
#         self.name += "^†"
#         self.circuit = self.circuit.dagger()
#         return self
#
#     def to_qasm(self):
#         qasm = ""
#         for operation in self.circuit.operations:
#             qasm += operation.to_qasm() + ";\n"
#         return qasm
#
#
# class ControlCircuitWrapper(CircuitWrapper):
#     def __init__(self, name: str, circwrp: CircuitWrapper, ctrls: List[int]):
#         self.name = name
#         self.ctrls = ctrls
#         self.targs = circwrp.pos
#         self.circuit = circwrp.circuit.add_controls(len(ctrls), ctrls, self.targs)
#         self.pos = list(range(self.circuit.num))
#         self._targ_name = circwrp.name
#
#     @property
#     def symbol(self):
#         return "%s" % self._targ_name
#
#     # def power(self, n: int):
#     #     self._targ_name += "^%d" % n
#     #     return super().power(n)
#     #
#     # def dagger(self):
#     #     self.name += "^†"
#     #     return super().dagger()
#
#     def _reallocate(self, qbits):
#         num = max(self.circuit.num - 1, max(qbits)) + 1
#         self.pos = qbits
#         self.circuit._reallocate(num, qbits)
#         qbits_map = dict(zip(range(len(qbits)), qbits))
#         for i in range(len(self.ctrls)):
#             self.ctrls[i] = qbits_map[self.ctrls[i]]
#
#         for i in range(len(self.targs)):
#             self.targs[i] = qbits_map[self.targs[i]]
