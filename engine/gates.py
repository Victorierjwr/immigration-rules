"""gates 前置判定引擎：按 YAML 声明的布尔表达式逐项判定一票否决项。

表达式语言（安全实现，不使用 eval）：
  比较：> >= < <= == !=；逻辑：not / and / or；算术：+ -（限数值）
  变量：点分路径进入画像字典（canonical + 派生），路径缺失 → None
  None 与数值比较（如 None >= 7）判定为 False（即不通过）
"""
from __future__ import annotations

import re

TOKEN_RE = re.compile(
    r"""
    \s*(?:
      (?P<num>\d+\.\d+|\d+)
    | (?P<str>'[^']*'|"[^"]*")
    | (?P<op>>=|<=|==|!=|>|<)
    | (?P<plus>\+)
    | (?P<minus>-)
    | (?P<ident>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)
    | (?P<lparen>\()
    | (?P<rparen>\))
    )
    """,
    re.X,
)


class GateExprError(ValueError):
    pass


def tokenize(src: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(src):
        if src[pos].isspace():
            pos += 1
            continue
        m = TOKEN_RE.match(src, pos)
        if not m or m.end() == pos:
            raise GateExprError(f"无法识别的字符: {src[pos:pos+10]!r}（位置 {pos}）")
        kind = m.lastgroup or ""
        text = m.group()
        if kind == "num":
            tokens.append(("num", float(text)))
        elif kind == "str":
            tokens.append(("str", text[1:-1]))
        elif kind == "op":
            tokens.append(("op", text))
        elif kind == "plus":
            tokens.append(("op", "+"))
        elif kind == "minus":
            tokens.append(("op", "-"))
        elif kind == "lparen":
            tokens.append(("lparen", "("))
        elif kind == "rparen":
            tokens.append(("rparen", ")"))
        else:
            tokens.append(("kw", text))
        pos = m.end()
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]], src: str):
        self.tokens = tokens
        self.pos = 0
        self.src = src

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise GateExprError(f"表达式意外结束: {self.src}")
        self.pos += 1
        return tok

    def expect(self, kind: str, value: str | None = None) -> tuple[str, str]:
        tok = self.peek()
        if tok is None or tok[0] != kind or (value is not None and tok[1] != value):
            raise GateExprError(f"期望 {value or kind}，实际 {tok!r}: {self.src}")
        self.pos += 1
        return tok

    def is_keyword(self, tok: tuple[str, str] | None, word: str) -> bool:
        return tok is not None and tok[0] == "kw" and tok[1].lower() == word

    def parse(self):
        node = self.or_expr()
        if self.peek() is not None:
            raise GateExprError(f"表达式尾部多余内容: {self.src}")
        return node

    def or_expr(self):
        node = self.and_expr()
        while self.is_keyword(self.peek(), "or"):
            self.take()
            node = ("or", node, self.and_expr())
        return node

    def and_expr(self):
        node = self.not_expr()
        while self.is_keyword(self.peek(), "and"):
            self.take()
            node = ("and", node, self.not_expr())
        return node

    def not_expr(self):
        if self.is_keyword(self.peek(), "not"):
            self.take()
            return ("not", self.not_expr())
        return self.comparison()

    def comparison(self):
        left = self.additive()
        tok = self.peek()
        if tok and tok[0] == "op" and tok[1] in (">=", "<=", ">", "<", "==", "!="):
            self.take()
            right = self.additive()
            return ("cmp", tok[1], left, right)
        return left

    def additive(self):
        node = self.unary()
        while self.peek() and self.peek()[0] == "op" and self.peek()[1] in ("+", "-"):
            op = self.take()[1]
            node = ("arith", op, node, self.unary())
        return node

    def unary(self):
        tok = self.peek()
        if tok and tok[0] == "op" and tok[1] == "-":
            self.take()
            return ("arith", "-", ("num", 0.0), self.unary())
        return self.primary()

    def primary(self):
        tok = self.take()
        kind, value = tok
        if kind == "num":
            return ("num", value)
        if kind == "str":
            return ("str", value)
        if kind == "lparen":
            node = self.or_expr()
            self.expect("rparen")
            return node
        if kind == "kw":
            if value.lower() == "true":
                return ("bool", True)
            if value.lower() == "false":
                return ("bool", False)
            if value.lower() == "none":
                return ("none", None)
        return ("attr", tuple(value.split(".")))


def _lookup(profile: dict, parts: tuple[str, ...]):
    node = profile
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _coerce_num(v) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def _truthy(v) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return bool(v)


def evaluate(node, profile: dict):
    kind = node[0]
    if kind in ("num", "str", "bool", "none"):
        return node[1]
    if kind == "attr":
        return _lookup(profile, node[1])
    if kind == "not":
        return not _truthy(evaluate(node[1], profile))
    if kind == "and":
        return _truthy(evaluate(node[1], profile)) and _truthy(evaluate(node[2], profile))
    if kind == "or":
        return _truthy(evaluate(node[1], profile)) or _truthy(evaluate(node[2], profile))
    if kind == "arith":
        left = _coerce_num(evaluate(node[2], profile))
        right = _coerce_num(evaluate(node[3], profile))
        if left is None or right is None:
            return None
        return left - right if node[1] == "-" else left + right
    if kind == "cmp":
        op = node[1]
        left = evaluate(node[2], profile)
        right = evaluate(node[3], profile)
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if left is None or right is None:
            return False  # 排序比较：缺失值不满足
        left_n, right_n = _coerce_num(left), _coerce_num(right)
        if left_n is None or right_n is None:
            return False
        if op == ">=":
            return left_n >= right_n
        if op == "<=":
            return left_n <= right_n
        if op == ">":
            return left_n > right_n
        if op == "<":
            return left_n < right_n
        raise GateExprError(f"未知操作符 {op}")
    raise GateExprError(f"未知节点 {kind}")


def compile_expr(src: str):
    tokens = tokenize(src)
    return _Parser(tokens, src).parse()


def run_gates(gates: list[dict], eff_profile: dict) -> list[dict]:
    """逐门判定。返回失败清单（空 = 全过）。"""
    failures = []
    for gate in gates or []:
        try:
            node = compile_expr(gate["test"])
            passed = evaluate(node, eff_profile)
            if not _truthy(passed):
                failures.append({
                    "id": gate["id"],
                    "fail_output": gate.get("fail_output", "未满足前置条件"),
                    "remedy_hint": gate.get("remedy_hint", ""),
                    "source_url": gate.get("source_url", ""),
                })
        except GateExprError as exc:
            failures.append({
                "id": gate["id"],
                "fail_output": f"门禁表达式错误（{exc}）——规则文件需人工修复",
                "remedy_hint": "",
                "source_url": gate.get("source_url", ""),
            })
    return failures


def gates_passed(failures: list[dict]) -> bool:
    return not failures
