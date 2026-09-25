#!/usr/bin/env python3
"""Transpile the rig's geometry functions from Python to JavaScript.

Python is the single source of truth for character geometry. This tool walks
the AST of pixelgoblin/gen/rig.py and emits JavaScript for the functions that
build a character's shapes, so the editor draws exactly what the engine
draws. It handles only the small integer subset those functions use, and it
refuses anything else loudly instead of guessing:

    // -> F(a, b)  (floor division, Python semantics)
    %  -> MOD(a, b) (floor modulo, Python semantics)
    x in (..)  -> [..].includes(x)
    d.get(k, v) -> get(d, k, v)
    s.append(x) -> s.push(x)

Output: editor/pg-rig.gen.js (derived; gate B13 fails if it is stale).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "pixelgoblin" / "gen" / "rig.py"
OUT = ROOT / "editor" / "pg-rig.gen.js"
FUNCS = ["build_shapes", "_goggles", "_face", "_hair", "_headwear", "_held"]
SHAPES = {"E", "R", "C", "T", "A"}
BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}
CMP = {ast.Eq: "===", ast.NotEq: "!==", ast.Lt: "<", ast.Gt: ">", ast.LtE: "<=", ast.GtE: ">="}


class Unsupported(Exception):
    pass


class Emitter:

    def expr(self, n) -> str:
        if isinstance(n, ast.Constant):
            if n.value is None:
                return "null"
            if isinstance(n.value, bool):
                return "true" if n.value else "false"
            if isinstance(n.value, (int, str)):
                return repr(n.value) if isinstance(n.value, int) else '"' + n.value + '"'
        if isinstance(n, ast.Name):
            return {"True": "true", "False": "false", "None": "null"}.get(n.id, n.id)
        if isinstance(n, ast.BinOp):
            a, b = self.expr(n.left), self.expr(n.right)
            if isinstance(n.op, ast.FloorDiv):
                return f"F({a}, {b})"
            if isinstance(n.op, ast.Mod):
                return f"MOD({a}, {b})"
            if type(n.op) in BIN:
                return f"({a} {BIN[type(n.op)]} {b})"
        if isinstance(n, ast.UnaryOp):
            if isinstance(n.op, ast.USub):
                return f"(-{self.expr(n.operand)})"
            if isinstance(n.op, ast.Not):
                return f"(!{self.expr(n.operand)})"
        if isinstance(n, ast.BoolOp):
            op = " && " if isinstance(n.op, ast.And) else " || "
            return "(" + op.join(self.expr(v) for v in n.values) + ")"
        if isinstance(n, ast.Compare):
            parts, left = [], n.left
            for op, right in zip(n.ops, n.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    s = f"{self.expr(right)}.includes({self.expr(left)})"
                    parts.append(s if isinstance(op, ast.In) else f"!{s}")
                elif type(op) in CMP:
                    parts.append(f"({self.expr(left)} {CMP[type(op)]} {self.expr(right)})")
                else:
                    raise Unsupported(ast.dump(op))
                left = right
            return "(" + " && ".join(parts) + ")"
        if isinstance(n, ast.IfExp):
            return f"({self.expr(n.test)} ? {self.expr(n.body)} : {self.expr(n.orelse)})"
        if isinstance(n, (ast.Tuple, ast.List)):
            return "[" + ", ".join(self.expr(e) for e in n.elts) + "]"
        if isinstance(n, ast.Dict):
            return "({" + ", ".join(f"[{self.expr(k)}]: {self.expr(v)}" for k, v in zip(n.keys, n.values)) + "})"
        if isinstance(n, ast.Subscript):
            return f"{self.expr(n.value)}[{self.expr(n.slice)}]"
        if isinstance(n, ast.Call):
            f = n.func
            args = [self.expr(a) for a in n.args]
            if isinstance(f, ast.Name):
                if f.id in SHAPES:
                    opts = ", ".join(f"{k.arg}: {self.expr(k.value)}" for k in n.keywords)
                    return f"{f.id}({', '.join(args)}" + (f", {{{opts}}})" if opts else ")")
                if f.id in ("max", "min"):
                    return f"Math.{f.id}({', '.join(args)})"
                if f.id == "abs":
                    return f"Math.abs({args[0]})"
                if f.id == "set":
                    return f"Array.from(new Set({args[0]}))"
                if f.id in FUNCS:
                    return f"{f.id}({', '.join(args)})"
            if isinstance(f, ast.Attribute):
                if f.attr == "get":
                    return f"get({self.expr(f.value)}, {', '.join(args)})"
                if f.attr == "append":
                    return f"{self.expr(f.value)}.push({', '.join(args)})"
            raise Unsupported(ast.unparse(n))
        raise Unsupported(ast.unparse(n))

    def target(self, t) -> str:
        if isinstance(t, ast.Name):
            return t.id
        if isinstance(t, ast.Tuple):
            return "[" + ", ".join(self.target(e) for e in t.elts) + "]"
        if isinstance(t, ast.Subscript):
            return self.expr(t)
        raise Unsupported(ast.unparse(t))

    def names(self, t) -> list[str]:
        if isinstance(t, ast.Name):
            return [t.id]
        if isinstance(t, ast.Tuple):
            return [x for e in t.elts for x in self.names(e)]
        return []

    def block(self, body, ind: str) -> list[str]:
        out = []
        for st in body:
            out += self.stmt(st, ind)
        return out

    def stmt(self, st, ind: str) -> list[str]:
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant):
            return []  # docstring
        if isinstance(st, ast.Expr):
            return [f"{ind}{self.expr(st.value)};"]
        if isinstance(st, (ast.Assign, ast.AnnAssign)):
            tgt = st.targets[0] if isinstance(st, ast.Assign) else st.target
            # every local is hoisted to the top of the function (Python scoping:
            # a name bound inside an `if` is visible after it)
            return [f"{ind}{self.target(tgt)} = {self.expr(st.value)};"]
        if isinstance(st, ast.If):
            out = [f"{ind}if {self.expr(st.test)} {{"] if self.expr(st.test).startswith("(") else [f"{ind}if ({self.expr(st.test)}) {{"]
            out += self.block(st.body, ind + "  ")
            orelse = st.orelse
            while orelse:
                if len(orelse) == 1 and isinstance(orelse[0], ast.If):
                    e = orelse[0]
                    t = self.expr(e.test)
                    out.append(f"{ind}}} else if {t if t.startswith('(') else '(' + t + ')'} {{")
                    out += self.block(e.body, ind + "  ")
                    orelse = e.orelse
                else:
                    out.append(f"{ind}}} else {{")
                    out += self.block(orelse, ind + "  ")
                    orelse = []
            out.append(f"{ind}}}")
            return out
        if isinstance(st, ast.For):
            it = st.iter
            tgt = self.target(st.target)
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                a = [self.expr(x) for x in it.args]
                lo, hi = (a[0], a[1]) if len(a) == 2 else ("0", a[0])
                head = f"{ind}for (let {tgt} = {lo}; {tgt} < {hi}; {tgt}++) {{"
            else:
                head = f"{ind}for (const {tgt} of {self.expr(it)}) {{"
            body = self.block(st.body, ind + "  ")
            return [head] + body + [f"{ind}}}"]
        if isinstance(st, ast.Continue):
            return [f"{ind}continue;"]
        if isinstance(st, ast.Return):
            return [f"{ind}return{(' ' + self.expr(st.value)) if st.value is not None else ''};"]
        raise Unsupported(ast.unparse(st))

    def function(self, fn: ast.FunctionDef) -> str:
        params = []
        defaults = [None] * (len(fn.args.args) - len(fn.args.defaults)) + list(fn.args.defaults)
        for a, d in zip(fn.args.args, defaults):
            params.append(a.arg + (f" = {self.expr(d)}" if d is not None else ""))
        body = [st for st in fn.body if not (isinstance(st, ast.For) and ast.unparse(st.target) == "sh")]
        params_set = {a.arg for a in fn.args.args}
        loop_names = {nm for n in ast.walk(fn) if isinstance(n, ast.For) for nm in self.names(n.target)}
        local = []
        for n in ast.walk(ast.Module(body=body, type_ignores=[])):
            tgts = n.targets if isinstance(n, ast.Assign) else [n.target] if isinstance(n, ast.AnnAssign) else []
            for t in tgts:
                for nm in self.names(t):
                    if nm not in params_set and nm not in local:
                        local.append(nm)
        clash = loop_names & set(local)
        if clash:
            raise Unsupported(f"{fn.name}: loop variable also assigned outside the loop: {sorted(clash)}")
        lines = ([f"  let {', '.join(local)};"] if local else []) + self.block(body, "  ")
        return f"function {fn.name}({', '.join(params)}) {{\n" + "\n".join(lines) + "\n}\n"


def main() -> str:
    tree = ast.parse(SRC.read_text())
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    em = Emitter()
    parts = ["/* GENERATED by tools/transpile_rig.py from pixelgoblin/gen/rig.py. Do not edit.",
             "   Gate B13 regenerates this file and fails if the committed copy differs. */", ""]
    for name in FUNCS:
        parts.append(em.function(fns[name]))
    return "\n".join(parts)


if __name__ == "__main__":
    text = main()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text() == text else 1)
    OUT.write_text(text)
    print(f"{OUT.relative_to(ROOT)}  {len(text.splitlines())} lines from {', '.join(FUNCS)}")
