#!/usr/bin/env python3
"""Transpile the character engine's geometry and views from Python to JavaScript.

Python is the single source of truth. This tool walks the AST of the listed
functions (and module constants) and emits JavaScript, so the editor draws
exactly what the engine draws. It handles only the small integer subset those
functions are written in, and it refuses anything else loudly instead of
guessing:

    a // b -> F(a, b)       floor division, Python semantics
    a % b  -> MOD(a, b)     floor modulo, Python semantics
    x in (..)               -> [..].includes(x)
    d.get(k, v)             -> get(d, k, v)
    s.append(x) / insert    -> push / splice;  s.pop() -> s.pop()
    rng.below / chance / range  -> the same Rng methods in pg-core.js
    len(x), list(x), dict(x), bytearray(n), [v] * n
    x is None / is not None -> === null / !== null
    for / while / break / continue / raise / += and friends

Every local is hoisted to the top of its function (Python scoping), and a
range() loop evaluates its bounds once, as Python does.

Output: editor/pg-rig.gen.js (derived; gate B13 fails if it is stale).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "editor" / "pg-rig.gen.js"
SOURCES = [
    ("pixelgoblin/gen/rig.py", [], ["build_shapes", "_goggles", "_face", "_hair", "_headwear", "_held", "_held_data",
                                    "signature", "shade_index", "zoom_plan"], ["SIGNATURE_ORDER", "POW2_16"]),
    ("pixelgoblin/gen/rig3d.py", [], ["isin", "icos", "_solid", "_box3", "_profile", "_column", "_in_cap", "front_z", "_host",
                                      "lift", "_shift2", "move", "voxelize", "occupied_box", "camera", "canvas_size", "trace",
                                      "normal", "light_at", "decal_at", "paint"],
     ["ZC", "SIN90", "DECAL_FEATS", "WRAP_FEATS", "HEADWEAR_FEATS", "HELD_DEPTH"]),
    ("pixelgoblin/gen/beast.py", [], ["_ell", "_cap", "beast_solids", "seat", "seat_rider"], ["EXT", "BX", "BZ", "BGROUND"]),
    ("pixelgoblin/sandbox.py", [], ["_disc", "reachable", "plan_world", "quests", "speed"], ["T_GROUND", "T_WATER", "T_ROCK", "CARRY_GRAMS"]),
]
SHAPES = {"E", "R", "C", "T", "A"}
BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}
CMP = {ast.Eq: "===", ast.NotEq: "!==", ast.Lt: "<", ast.Gt: ">", ast.LtE: "<=", ast.GtE: ">="}


class Unsupported(Exception):
    pass


class Emitter:
    def __init__(self):
        self.funcs: set = set()
        self.tmp = 0
        self.hoist: list = []

    def fresh(self) -> str:
        self.tmp += 1
        name = f"_e{self.tmp}"
        self.hoist.append(name)
        return name

    def expr(self, n) -> str:
        if isinstance(n, ast.Constant):
            if n.value is None:
                return "null"
            if isinstance(n.value, bool):
                return "true" if n.value else "false"
            if isinstance(n.value, int):
                return repr(n.value)
            if isinstance(n.value, str):
                return '"' + n.value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        if isinstance(n, ast.Name):
            return {"True": "true", "False": "false", "None": "null"}.get(n.id, n.id)
        if isinstance(n, ast.Attribute):
            return f"{self.expr(n.value)}.{n.attr}"
        if isinstance(n, ast.BinOp):
            if isinstance(n.op, ast.Mult) and isinstance(n.left, ast.List) and len(n.left.elts) == 1:
                return f"new Array({self.expr(n.right)}).fill({self.expr(n.left.elts[0])})"
            if isinstance(n.op, ast.LShift):
                return f"({self.expr(n.left)} * Math.pow(2, {self.expr(n.right)}))"
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
                elif isinstance(op, (ast.Is, ast.IsNot)):
                    parts.append(f"({self.expr(left)} {'===' if isinstance(op, ast.Is) else '!=='} {self.expr(right)})")
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
                if n.keywords:
                    raise Unsupported(ast.unparse(n))
                if f.id in ("max", "min"):
                    return f"Math.{f.id}({', '.join(args)})"
                if f.id == "abs":
                    return f"Math.abs({args[0]})"
                if f.id == "len":
                    return f"{args[0]}.length"
                if f.id == "list":
                    return f"Array.from({args[0]})"
                if f.id == "dict":
                    return f"Object.assign({{}}, {args[0]})"
                if f.id == "bytearray":
                    return f"new Uint8Array({args[0]})"
                if f.id == "set":
                    return f"Array.from(new Set({args[0]}))"
                if f.id in self.funcs or f.id in ("isqrt", "_snap", "_bbox", "_inside"):
                    return f"{f.id}({', '.join(args)})"
            if isinstance(f, ast.Attribute):
                if f.attr == "get":
                    return f"get({self.expr(f.value)}, {', '.join(args)})"
                if f.attr == "append":
                    return f"{self.expr(f.value)}.push({', '.join(args)})"
                if f.attr == "insert":
                    return f"{self.expr(f.value)}.splice({args[0]}, 0, {args[1]})"
                if f.attr == "pop" and not args:
                    return f"{self.expr(f.value)}.pop()"
                if f.attr in ("below", "chance", "range"):   # the engine's Rng: the same methods in both languages
                    return f"{self.expr(f.value)}.{f.attr}({', '.join(args)})"
            raise Unsupported(ast.unparse(n))
        raise Unsupported(ast.unparse(n))

    def target(self, t) -> str:
        if isinstance(t, ast.Name):
            return t.id
        if isinstance(t, ast.Tuple):
            return "[" + ", ".join(self.target(e) for e in t.elts) + "]"
        if isinstance(t, (ast.Subscript, ast.Attribute)):
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

    def cond(self, test) -> str:
        t = self.expr(test)
        return t if t.startswith("(") and t.endswith(")") else "(" + t + ")"

    def stmt(self, st, ind: str) -> list[str]:
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant):
            return []  # docstring
        if isinstance(st, ast.Expr):
            return [f"{ind}{self.expr(st.value)};"]
        if isinstance(st, (ast.Assign, ast.AnnAssign)):
            tgt = st.targets[0] if isinstance(st, ast.Assign) else st.target
            return [f"{ind}{self.target(tgt)} = {self.expr(st.value)};"]
        if isinstance(st, ast.AugAssign):
            tgt = self.target(st.target)
            if isinstance(st.op, ast.FloorDiv):
                return [f"{ind}{tgt} = F({tgt}, {self.expr(st.value)});"]
            if type(st.op) not in BIN:
                raise Unsupported(ast.unparse(st))
            return [f"{ind}{tgt} {BIN[type(st.op)]}= {self.expr(st.value)};"]
        if isinstance(st, ast.If):
            out = [f"{ind}if {self.cond(st.test)} {{"]
            out += self.block(st.body, ind + "  ")
            orelse = st.orelse
            while orelse:
                if len(orelse) == 1 and isinstance(orelse[0], ast.If):
                    e = orelse[0]
                    out.append(f"{ind}}} else if {self.cond(e.test)} {{")
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
                lo, hi = (a[0], a[1]) if len(a) >= 2 else ("0", a[0])
                step = a[2] if len(a) == 3 else "1"
                end = self.fresh()
                head = f"{ind}for ({tgt} = {lo}, {end} = {hi}; {tgt} < {end}; {tgt} += {step}) {{"
            else:
                head = f"{ind}for ({tgt} of {self.expr(it)}) {{"
            return [head] + self.block(st.body, ind + "  ") + [f"{ind}}}"]
        if isinstance(st, ast.While):
            return [f"{ind}while {self.cond(st.test)} {{"] + self.block(st.body, ind + "  ") + [f"{ind}}}"]
        if isinstance(st, ast.Break):
            return [f"{ind}break;"]
        if isinstance(st, ast.Continue):
            return [f"{ind}continue;"]
        if isinstance(st, ast.Raise):
            msg = st.exc.args[0] if isinstance(st.exc, ast.Call) and st.exc.args else ast.Constant("error")
            return [f"{ind}throw new Error({self.expr(msg)});"]
        if isinstance(st, ast.Return):
            return [f"{ind}return{(' ' + self.expr(st.value)) if st.value is not None else ''};"]
        raise Unsupported(ast.unparse(st))

    def function(self, fn: ast.FunctionDef) -> str:
        params = []
        defaults = [None] * (len(fn.args.args) - len(fn.args.defaults)) + list(fn.args.defaults)
        for a, d in zip(fn.args.args, defaults):
            params.append(a.arg + (f" = {self.expr(d)}" if d is not None else ""))
        body = [st for st in fn.body if not (isinstance(st, ast.For) and ast.unparse(st.target) == "sh" and fn.name == "build_shapes")]
        params_set = {a.arg for a in fn.args.args}
        local = []
        for n in ast.walk(ast.Module(body=body, type_ignores=[])):
            tgts = []
            if isinstance(n, ast.Assign):
                tgts = n.targets
            elif isinstance(n, (ast.AnnAssign, ast.AugAssign, ast.For)):
                tgts = [n.target]
            for t in tgts:
                for nm in self.names(t):
                    if nm not in params_set and nm not in local:
                        local.append(nm)
        self.hoist = []
        lines = self.block(body, "  ")
        decl = local + self.hoist
        return f"function {fn.name}({', '.join(params)}) {{\n" + (f"  let {', '.join(decl)};\n" if decl else "") + "\n".join(lines) + "\n}\n"


def main() -> str:
    em = Emitter()
    trees = []
    for src, _, funcs, consts in SOURCES:
        tree = ast.parse((ROOT / src).read_text(encoding="utf-8"))
        trees.append((src, tree, funcs, consts))
        em.funcs |= set(funcs)
    parts = ["/* GENERATED by tools/transpile_rig.py from pixelgoblin/gen/{rig,rig3d,beast}.py. Do not edit.",
             "   Gate B13 regenerates this file and fails if the committed copy differs. */", ""]
    for src, tree, funcs, consts in trees:
        parts.append(f"// ---- from {src}")
        top = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
                top[n.targets[0].id] = n
        for c in consts:
            parts.append(f"const {c} = {em.expr(top[c].value)};")
        fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        for name in funcs:
            parts.append(em.function(fns[name]))
    return "\n".join(parts)


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):  # a pipe on Windows defaults to cp1252; write UTF-8 everywhere
        _s.reconfigure(encoding="utf-8")
    text = main()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text(encoding="utf-8") == text else 1)
    OUT.write_text(text, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}  {len(text.splitlines())} lines")
