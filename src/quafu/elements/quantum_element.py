# This is the file for abstract quantum gates class
from typing import Union, Callable, List, Tuple, Iterable, Any, Optional
import functools
import numpy as np
import qutip


class Barrier(object):
    def __init__(self, pos):
        self.name = "barrier"
        self.__pos = pos

    @property
    def pos(self):
        return self.__pos

    @pos.setter
    def pos(self, pos):
        self.__pos = pos

    def to_QLisp(self):
        return ("Barrier", tuple(["Q%d" % i for i in self.pos]))

    def _operator(self, used_qubits: Optional[List[int]] = None):
        if used_qubits is None:
            used_qubits = self.pos
        num = len(used_qubits)
        assert num >= 1
        return qutip.qeye([2] * num)


class QuantumGate(object):
    def __init__(self, name: str, pos: Union[int, List[int]], paras: Any, matrix):
        self.name = name
        self.pos = pos
        self.paras = paras
        self.matrix = matrix

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, _name):
        self.__name = _name

    @property
    def pos(self):
        return self.__pos

    @pos.setter
    def pos(self, _pos):
        self.__pos = _pos

    @property
    def paras(self):
        return self.__paras

    @paras.setter
    def paras(self, _paras):
        self.__paras = _paras

    @property
    def matrix(self):
        return self.__matrix

    @matrix.setter
    def matrix(self, _matrix):
        self.__matrix = _matrix

    def __str__(self):
        properties_names = ['pos', 'paras', 'matrix']
        properties_values = [getattr(self, x) for x in properties_names]
        return "%s:\n%s" % (self.__class__.__name__, '\n'.join(
            [f"{x} = {repr(properties_values[i])}" for i, x in enumerate(properties_names)]))

    def __repr__(self):
        return f"{self.__class__.__name__}"


class SingleQubitGate(QuantumGate):
    def __init__(self, name: str, pos: int, paras, matrix):
        super().__init__(name, pos, paras=paras, matrix=matrix)
        self.matrix = matrix

    @property
    def matrix(self):
        return self.__matrix

    @matrix.setter
    def matrix(self, _matrix):
        if isinstance(_matrix, (np.ndarray, List, qutip.Qobj)):
            if np.shape(_matrix) == (2, 2):
                self.__matrix = np.asarray(_matrix, dtype=complex)
            else:
                raise ValueError(f'`{self.__class__.__name__}.matrix.shape` must be (2, 2)')
        elif isinstance(_matrix, type(None)):
            self.__matrix = _matrix
        else:
            raise TypeError("Unsupported `matrix` type")

    def _operator(self, num: int = 1):
        return _oper1q_local_to_global(self, num)

    def to_QLisp(self):
        return ((self.name, "Q%d" % self.pos))

    def to_nodes(self):
        return (1, self.name, 0, self.pos)

    def to_IOP(self):
        return [self.name, self.pos, 0.]


class FixedSingleQubitGate(SingleQubitGate):
    def __init__(self, name, pos, matrix):
        super().__init__(name, pos, paras=None, matrix=matrix)


class ParaSingleQubitGate(SingleQubitGate):
    def __init__(self, name, pos, paras, matrix):
        super().__init__(name, pos, paras=paras, matrix=matrix)
        # self.matrix = matrix

    @property
    def matrix(self):
        return self.__matrix

    @matrix.setter
    def matrix(self, _matrix):
        if isinstance(_matrix, Callable):
            self.__matrix = _matrix(self.paras)
        elif isinstance(_matrix, (np.ndarray, List, qutip.Qobj)):
            if np.shape(_matrix) == (2, 2):
                self.__matrix = np.asarray(_matrix, dtype=complex)
            else:
                raise ValueError(f'`{self.__class__.__name__}.matrix.shape` must be (2, 2)')
        elif isinstance(_matrix, type(None)):
            self.__matrix = _matrix
        else:
            raise TypeError("Unsupported `matrix` type")

    def to_QLisp(self):
        if isinstance(self.paras, Iterable):
            return ((self.name, *self.paras), "Q%d" % self.pos)
        else:
            return ((self.name, self.paras), "Q%d" % self.pos)

    def to_nodes(self):
        return (1, self.name, self.paras, self.pos)

    def to_IOP(self):
        if isinstance(self.paras, Iterable):
            return [self.name, self.pos, *self.paras]
        else:
            return [self.name, self.pos, self.paras]


class TwoQubitGate(QuantumGate):
    def __init__(self, name: str, pos: List[int], paras, matrix):
        super().__init__(name, pos, paras=paras, matrix=matrix)
        if not len(pos) == 2:
            raise ValueError("Two positions of a two-qubit gate should be provided")

    @property
    def matrix(self):
        return self.__matrix

    @matrix.setter
    def matrix(self, _matrix):
        if isinstance(_matrix, np.ndarray) and _matrix.shape == (4, 4):
            self.__matrix = _matrix
        elif isinstance(_matrix, List) and np.shape(_matrix) == (4, 4):
            self.__matrix = np.array(_matrix, dtype=complex)
        else:
            raise TypeError("Unsupported `matrix` type")

    def _operator(self, num: int = 2):
        return _oper2q_local_to_global(self, num)

    def to_QLisp(self):
        return (self.name, ("Q%d" % self.pos[0], "Q%d" % self.pos[1]))

    def to_nodes(self):
        return (2, self.name, self.pos[0], self.pos[1])

    def to_IOP(self):
        return [self.name, self.pos]


class FixedTwoQubitGate(TwoQubitGate):
    def __init__(self, name: str, pos: List[int], matrix):
        super().__init__(name, pos, paras=None, matrix=matrix)


class ParaTwoQubitGate(TwoQubitGate):
    def __init__(self, name, pos, paras, matrix):
        super().__init__(name, pos, paras, matrix=matrix)
        if not len(pos) == 2:
            raise ValueError("Two postion of a two-qubit gate should be provided")

    @property
    def matrix(self):
        return self.__matrix

    @matrix.setter
    def matrix(self, _matrix):
        if isinstance(_matrix, Callable):
            self.__matrix = _matrix(self.paras)
        elif isinstance(_matrix, (np.ndarray, List, qutip.Qobj)):
            if np.shape(_matrix) == (4, 4):
                self.__matrix = np.asarray(_matrix, dtype=complex)
            else:
                raise ValueError(f'`{self.__class__.__name__}.matrix.shape` must be (4, 4)')
        elif isinstance(_matrix, type(None)):
            self.__matrix = _matrix
        else:
            raise TypeError("Unsupported `matrix` type")

    def to_QLisp(self):
        if isinstance(self.paras, Iterable):
            return ((self.name, *self.paras), ("Q%d" % self.pos[0], "Q%d" % self.pos[1]))
        else:
            return ((self.name, self.paras), ("Q%d" % self.pos[0], "Q%d" % self.pos[1]))

    def to_nodes(self):
        return (2, self.name, self.paras, self.pos[0], self.pos[1])

    def to_IOP(self):
        if isinstance(self.paras, Iterable):
            return [self.name, self.pos, *self.paras]
        else:
            return [self.name, self.pos, self.paras]


class ControlGate(FixedTwoQubitGate):
    def __init__(self, name, ctrl, targ, matrix):
        super().__init__(name, [ctrl, targ], matrix)
        self.__ctrl = ctrl
        self.__targ = targ
        self.targ_name = ""

    @property
    def ctrl(self):
        return self.__ctrl

    @property
    def targ(self):
        return self.__targ

    @ctrl.setter
    def ctrl(self, ctrl):
        self.__ctrl = ctrl

    @targ.setter
    def targ(self, targ):
        self.__targ = targ

    def to_QLisp(self):
        return (self.name, ("Q%d" % self.ctrl, "Q%d" % self.targ))

    def to_nodes(self):
        return (2, self.name, self.ctrl, self.targ)

    def to_IOP(self):
        return [self.name, [self.ctrl, self.targ]]

class MultiQubitGate(QuantumGate):
    def __init__(self, name, pos, paras, matrix):
        super().__init__(name, pos, paras, matrix)
    
class FixedMultiQubitGate(MultiQubitGate):
    def __init__(self, name, pos, matrix):
        super().__init__(name, pos, None, matrix)

class ParaMultiQubitGate(MultiQubitGate):
    def __init__(self, name, pos, paras, matrix):
        super().__init__(name, pos, paras, matrix)


def _oper1q_local_to_global(_gate: SingleQubitGate, used_qubits: Optional[List[int]] = None):
    """
    Single-qubit operator from local to global

    Parameters
    ----------
    _gate: SingleQubitGate
    used_qubits: list
        The total qubits used.
    Returns
    -------
    oper: qutip.Qobj
    """

    pos = _gate.pos
    if used_qubits is None:
        used_qubits = [pos]

    num = len(used_qubits)
    assert num >= 1 and pos in used_qubits

    q_idx = used_qubits.index(pos)
    gate = qutip.Qobj(_gate.matrix, dims=[[2], [2]])
    ops = []
    for idx in range(num):
        if idx != q_idx:
            ops.append(qutip.qeye(2))
        else:
            ops.append(gate)
    oper = functools.reduce(qutip.tensor, ops)
    return oper


def _oper2q_local_to_global(_gate: TwoQubitGate, used_qubits: Optional[List[int]] = None):
    """
    Two-qubit operator from local to global

    Parameters
    ----------
    _gate: TwoQubitGate
    used_qubits: list
        The total qubits used.

    Returns
    -------
    oper: qutip.Qobj
    """
    pos = np.sort(_gate.pos).tolist()
    if used_qubits is None:
        used_qubits = pos
    num = len(used_qubits)
    assert num >= 2 and all(pos_i in used_qubits for pos_i in pos)
    pos0, pos1 = used_qubits.index(pos[0]), used_qubits.index(pos[1])
    gate = qutip.Qobj(_gate.matrix, dims=[[2, 2], [2, 2]])

    pos_diff_abs = abs(pos1 - pos0)
    if pos_diff_abs == 1:
        # two nearest neighbor qubits
        if pos0 == 0:
            if pos1 == int(num - 1):
                oper = gate
            else:
                qeye_right = qutip.qeye([2] * int(num - 1 - pos1))
                oper = qutip.tensor(gate, qeye_right)
        else:
            qeye_left = qutip.qeye([2] * int(pos0))
            if pos1 == int(num - 1):
                oper = qutip.tensor(qeye_left, gate)
            else:
                qeye_right = qutip.qeye([2] * int(num - 1 - pos1))
                oper = qutip.tensor(qeye_left, gate, qeye_right)

    else:
        # two non-nearest neighbor qubits
        oper = qutip.tensor(gate, qutip.qeye([2] * int(pos_diff_abs - 1)))
        idxs = list(range(pos_diff_abs + 1))
        idxs[1], idxs[-1] = idxs[-1], idxs[1]
        oper = oper.permute(idxs)

        if pos0 == 0:
            if pos1 < int(num - 1):
                qeye_right = qutip.qeye([2] * int(num - 1 - pos1))
                oper = qutip.tensor(oper, qeye_right)
        else:
            qeye_left = qutip.qeye([2] * int(pos0))
            if pos1 == int(num - 1):
                oper = qutip.tensor(qeye_left, oper)
            else:
                qeye_right = qutip.qeye([2] * int(num - 1 - pos1))
                oper = qutip.tensor(qeye_left, gate, qeye_right)

    return oper


if __name__ == '__main__':
    pass
