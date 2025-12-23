import sys
from pathlib import Path
from typing import List, Dict, Set, Optional


SYMBOLS: Set[str] = set("{}()[].,;+-*/&|<>=~")
KEYWORDS: Set[str] = {
    "class", "constructor", "function", "method", "field", "static", "var",
    "int", "char", "boolean", "void", "true", "false", "null", "this",
    "let", "do", "if", "else", "while", "return"
}


class Token:
    """Represents a single Jack token."""
    def __init__(self, type: str = "", val: str = ""):
        self.type = type
        self.val = val
    def __repr__(self) -> str:
        return f"Token(type='{self.type}', val='{self.val}')"

class Sym:
    """Represents an entry in the Symbol Table."""
    def __init__(self, type: str, kind: str, idx: int):
        self.type = type
        self.kind = kind
        self.idx = idx
    def __repr__(self) -> str:
        return f"Sym(type='{self.type}', kind='{self.kind}', idx={self.idx})"

class SymTable:
    """Manages class-level and subroutine-level symbol tables."""
    def __init__(self):
        self.cls: Dict[str, Sym] = {}
        self.sub: Dict[str, Sym] = {}
        self.stat: int = 0
        self.field: int = 0
        self.arg: int = 0
        self.var: int = 0

    def startSub(self):
        """Resets the subroutine symbol table."""
        self.sub.clear()
        self.arg = 0
        self.var = 0

    def define(self, n: str, t: str, k: str):
        """Defines a new symbol in the appropriate table."""
        if k == "static":
            self.cls[n] = Sym(t, k, self.stat)
            self.stat += 1
        elif k == "field":
            self.cls[n] = Sym(t, k, self.field)
            self.field += 1
        elif k == "arg":
            self.sub[n] = Sym(t, k, self.arg)
            self.arg += 1
        elif k == "var":
            self.sub[n] = Sym(t, k, self.var)
            self.var += 1

    def has(self, n: str) -> bool:
        """Checks if a symbol exists in either table."""
        return n in self.sub or n in self.cls

    def get(self, n: str) -> Sym:
        """Gets a symbol from the tables (subroutine takes precedence)."""
        return self.sub.get(n, self.cls.get(n))

    def count(self, k: str) -> int:
        """Returns the count of a specific kind of symbol."""
        if k == "field":
            return self.field
        if k == "var":
            return self.var
        return 0

def seg(k: str) -> str:
    """Maps symbol kinds to VM memory segments."""
    if k == "static":
        return "static"
    if k == "field":
        return "this"
    if k == "arg":
        return "argument"
    if k == "var":
        return "local"
    return ""


def isSymbol(c: str) -> bool:
    return c in SYMBOLS

def isKeyword(s: str) -> bool:
    return s in KEYWORDS

def tokenize(path: str) -> List[Token]:
    """Reads a .jack file and converts it into a list of Tokens."""
    try:
        with open(path, 'r') as f:
            s = f.read()
    except IOError as e:
        print(f"Error reading file {path}: {e}", file=sys.stderr)
        return []

    raw: List[str] = []
    t: str = ""
    str_lit: bool = False
    blk: bool = False
    i: int = 0
    n: int = len(s)

    while i < n:
        if not blk and i + 1 < n and s[i:i+2] == '/*':
            blk = True
            i += 2
            continue
        if blk and i + 1 < n and s[i:i+2] == '*/':
            blk = False
            i += 2
            continue
        if blk:
            i += 1
            continue
        if not blk and i + 1 < n and s[i:i+2] == '//':
            while i < n and s[i] != '\n':
                i += 1
            continue  
        c: str = s[i]

        if str_lit:
            t += c
            if c == '"':
                raw.append(t)
                t = ""
                str_lit = False
            i += 1
        elif c.isspace():
            if t:
                raw.append(t)
                t = ""
            i += 1
        elif isSymbol(c):
            if t:
                raw.append(t)
                t = ""
            raw.append(c)
            i += 1
        elif c == '"':
            if t:
                raw.append(t)
                t = ""
            t = '"'
            str_lit = True
            i += 1
        else:
            t += c
            i += 1
            
    if t:
        raw.append(t)

    tok: List[Token] = []
    for x in raw:
        tk = Token()
        if isKeyword(x):
            tk.type = "keyword"
        elif x and isSymbol(x[0]):
            tk.type = "symbol"
        elif x and x.isdigit():
            tk.type = "int"
        elif x and x[0] == '"':
            tk.type = "string"
            tk.val = x[1:-1]  
            tok.append(tk)
            continue
        else:
            tk.type = "ident"
        
        tk.val = x
        tok.append(tk)
    
    return tok


class VM:
    """Writes VM commands to an output file."""
    def __init__(self, f: str):
        try:
            self.o = open(f, 'w')
        except IOError as e:
            print(f"Error opening output file {f}: {e}", file=sys.stderr)
            self.o = None

    def fdef(self, n: str, l: int):
        if self.o: self.o.write(f"function {n} {l}\n")

    def push(self, s: str, i: int):
        if self.o: self.o.write(f"push {s} {i}\n")

    def pop(self, s: str, i: int):
        if self.o: self.o.write(f"pop {s} {i}\n")

    def op(self, c: str):
        if self.o: self.o.write(f"{c}\n")

    def call(self, n: str, a: int):
        if self.o: self.o.write(f"call {n} {a}\n")

    def ret(self):
        if self.o: self.o.write("return\n")

    def label(self, l: str):
        if self.o: self.o.write(f"label {l}\n")

    def go(self, l: str):
        if self.o: self.o.write(f"goto {l}\n")

    def ifgo(self, l: str):
        if self.o: self.o.write(f"if-goto {l}\n")

    def close(self):
        """Closes the output file."""
        if self.o:
            self.o.close()
            self.o = None


class Compiler:
    """Recursive descent parser that generates VM code."""
    def __init__(self, T: List[Token], V: VM):
        self.t: List[Token] = T
        self.p: int = 0
        self.st: SymTable = SymTable()
        self.vm: VM = V
        self.cls: str = ""
        self.L: int = 0

    def cur(self) -> Token:
        """Gets the current token without consuming it."""
        return self.t[self.p] if self.p < len(self.t) else Token()

    def adv(self) -> Token:
        """Consumes and returns the current token."""
        if self.p < len(self.t):
            self.p += 1
            return self.t[self.p - 1]
        return Token()

    def eq(self, s: str) -> bool:
        """Checks if the current token's value matches the string."""
        return self.p < len(self.t) and self.t[self.p].val == s

    def need(self, s: str):
        """Consumes the current token if it matches, else prints an error."""
        if not self.eq(s):
            val = self.cur().val if self.p < len(self.t) else "<eof>"
            print(f"Parse error: expected '{s}' got '{val}'", file=sys.stderr)
        else:
            self.p += 1

    def type(self) -> bool:
        """Checks if the current token is a type (int, char, boolean, or identifier)."""
        if self.p < len(self.t):
            c = self.t[self.p]
            return c.type == "ident" or (c.type == "keyword" and c.val in {"int", "char", "boolean"})
        return False

    def class_(self):
        self.need("class")
        self.cls = self.adv().val
        self.need("{")
        while self.eq("static") or self.eq("field"):
            self.classVar()
        while self.eq("constructor") or self.eq("function") or self.eq("method"):
            self.subr()
        self.need("}")

    def classVar(self):
        k = self.adv().val  
        ty = self.adv().val 
        n = self.adv().val 
        self.st.define(n, ty, k)
        while self.eq(","):
            self.adv()
            n2 = self.adv().val
            self.st.define(n2, ty, k)
        self.need(";")

    def subr(self):
        sk = self.adv().val
        if self.eq("void") or self.type():
            self.adv() 
        name = self.adv().val
        self.st.startSub()
        if sk == "method":
            self.st.define("this", self.cls, "arg")
        self.need("(")
        self.params()
        self.need(")")
        self.need("{")
        while self.eq("var"):
            self.varDec()
        
        self.vm.fdef(f"{self.cls}.{name}", self.st.count("var"))
        
        if sk == "constructor":
            self.vm.push("constant", self.st.count("field"))
            self.vm.call("Memory.alloc", 1)
            self.vm.pop("pointer", 0)
        elif sk == "method":
            self.vm.push("argument", 0)
            self.vm.pop("pointer", 0)
            
        self.stats()
        self.need("}")

    def params(self):
        if self.type():
            ty = self.adv().val
            n = self.adv().val
            self.st.define(n, ty, "arg")
            while self.eq(","):
                self.adv()
                ty2 = self.adv().val
                n2 = self.adv().val
                self.st.define(n2, ty2, "arg")

    def varDec(self):
        self.need("var")
        ty = self.adv().val
        n = self.adv().val
        self.st.define(n, ty, "var")
        while self.eq(","):
            self.adv()
            n2 = self.adv().val
            self.st.define(n2, ty, "var")
        self.need(";")

    def stats(self):
        while True:
            if self.eq("let"):
                self.let_()
            elif self.eq("if"):
                self.if_()
            elif self.eq("while"):
                self.while_()
            elif self.eq("do"):
                self.do_()
            elif self.eq("return"):
                self.ret_()
            else:
                break

    def do_(self):
        self.need("do")
        self.subCall()
        self.need(";")
        self.vm.pop("temp", 0)

    def let_(self):
        self.need("let")
        name = self.adv().val
        is_array = False
        if self.eq("["):
            self.adv()
            self.expr()
            self.need("]")
            s = self.st.get(name)
            self.vm.push(seg(s.kind), s.idx)
            self.vm.op("add")
            is_array = True
        
        self.need("=")
        self.expr()
        self.need(";")
        
        if is_array:
            self.vm.pop("temp", 0)    
            self.vm.pop("pointer", 1) 
            self.vm.push("temp", 0)    
            self.vm.pop("that", 0)   
        else:
            s = self.st.get(name)
            self.vm.pop(seg(s.kind), s.idx)

    def while_(self):
        self.need("while")
        a, b = self.L, self.L + 1
        self.L += 2
        self.vm.label(f"WHILE_EXP{a}")
        self.need("(")
        self.expr()
        self.need(")")
        self.vm.op("not")
        self.vm.ifgo(f"WHILE_END{b}")
        self.need("{")
        self.stats()
        self.need("}")
        self.vm.go(f"WHILE_EXP{a}")
        self.vm.label(f"WHILE_END{b}")

    def if_(self):
        self.need("if")
        self.need("(")
        self.expr()
        self.need(")")
        f, e = self.L, self.L + 1
        self.L += 2
        self.vm.op("not")
        self.vm.ifgo(f"IF_FALSE{f}")
        self.need("{")
        self.stats()
        self.need("}")
        if self.eq("else"):
            self.vm.go(f"IF_END{e}")
            self.vm.label(f"IF_FALSE{f}")
            self.adv()
            self.need("{")
            self.stats()
            self.need("}")
            self.vm.label(f"IF_END{e}")
        else:
            self.vm.label(f"IF_FALSE{f}")

    def ret_(self):
        self.need("return")
        if not self.eq(";"):
            self.expr()
        else:
            self.vm.push("constant", 0)  
        self.need(";")
        self.vm.ret()

    def exprList(self) -> int:
        n = 0
        if not self.eq(")"):
            self.expr()
            n = 1
            while self.eq(","):
                self.adv()
                self.expr()
                n += 1
        return n

    def subCall(self):
        n = self.adv().val
        nargs = 0
        if self.eq("."):
            self.adv() 
            sub = self.adv().val
            self.need("(")
            if self.st.has(n):  
                s = self.st.get(n)
                self.vm.push(seg(s.kind), s.idx)
                nargs = 1 + self.exprList()
                self.need(")")
                self.vm.call(f"{s.type}.{sub}", nargs)
            else:  
                nargs = self.exprList()
                self.need(")")
                self.vm.call(f"{n}.{sub}", nargs)
        else:  
            self.need("(")
            self.vm.push("pointer", 0)  
            nargs = 1 + self.exprList()
            self.need(")")
            self.vm.call(f"{self.cls}.{n}", nargs)

    def expr(self):
        self.term()
        while self.cur().val in {"+", "-", "*", "/", "&", "|", "<", ">", "="}:
            op = self.adv().val
            self.term()
            if op == "+": self.vm.op("add")
            elif op == "-": self.vm.op("sub")
            elif op == "*": self.vm.call("Math.multiply", 2)
            elif op == "/": self.vm.call("Math.divide", 2)
            elif op == "&": self.vm.op("and")
            elif op == "|": self.vm.op("or")
            elif op == "<": self.vm.op("lt")
            elif op == ">": self.vm.op("gt")
            elif op == "=": self.vm.op("eq")

    def term(self):
        x = self.cur()

        if x.type == "int":
            self.adv()
            self.vm.push("constant", int(x.val))
            return

        if x.type == "string":
            self.adv()
            self.vm.push("constant", len(x.val))
            self.vm.call("String.new", 1)
            for c in x.val:
                self.vm.push("constant", ord(c))
                self.vm.call("String.appendChar", 2)
            return

        if x.type == "keyword":
            self.adv()
            if x.val == "true":
                self.vm.push("constant", 1)
                self.vm.op("neg")
            elif x.val == "false" or x.val == "null":
                self.vm.push("constant", 0)
            elif x.val == "this":
                self.vm.push("pointer", 0)
            return

        if x.val == "(":
            self.adv()
            self.expr()
            self.need(")")
            return

        if x.val == "-" or x.val == "~":
            self.adv()
            self.term()
            self.vm.op("neg" if x.val == "-" else "not")
            return

        if x.type == "ident":
            
            name = self.adv().val
            if self.eq("["): 
                self.adv()
                self.expr()
                self.need("]")
                s = self.st.get(name)
                self.vm.push(seg(s.kind), s.idx)
                self.vm.op("add")
                self.vm.pop("pointer", 1)
                self.vm.push("that", 0)
                return
            
            if self.eq("(") or self.eq("."):  
                self.p -= 1  
                self.subCall()
                return

            if self.st.has(name): 
                s = self.st.get(name)
                self.vm.push(seg(s.kind), s.idx)
            return

def main():
    if len(sys.argv) < 2:
        print("Usage: JackCompiler.py <file.jack|directory>", file=sys.stderr)
        sys.exit(1)

    in_path = Path(sys.argv[1])
    files: List[Path] = []

    if in_path.is_dir():
        files = list(in_path.glob("*.jack"))
    elif in_path.suffix == ".jack":
        files.append(in_path)

    if not files:
        print(f"No .jack files found in {in_path}", file=sys.stderr)
        sys.exit(1)

    for f in files:
        tok = tokenize(str(f))
        if not tok:
            print(f"Could not tokenize {f.name}", file=sys.stderr)
            continue
        
        vm_path = f.with_suffix(".vm")
        vm = VM(str(vm_path))
        
        if vm.o is None:
            continue
            
        comp = Compiler(tok, vm)
        comp.class_()
        vm.close()
        
        print(f"Compiled {f.name} -> {vm_path.name}")

if __name__ == "__main__":
    main()