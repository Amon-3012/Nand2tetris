import sys
import os
import re

class TokenType:
    KEYWORD = "KEYWORD"
    SYMBOL = "SYMBOL"
    IDENTIFIER = "IDENTIFIER"
    INT_CONST = "INT_CONST"
    STRING_CONST = "STRING_CONST"

class Keyword:
    CLASS, METHOD, FUNCTION, CONSTRUCTOR, INT, BOOLEAN, CHAR, VOID, VAR, \
    STATIC, FIELD, LET, DO, IF, ELSE, WHILE, RETURN, TRUE, FALSE, NULL, THIS = range(21)

class JackTokenizer:
    KEYWORD_MAP = {
        'class': Keyword.CLASS, 'constructor': Keyword.CONSTRUCTOR, 'function': Keyword.FUNCTION,
        'method': Keyword.METHOD, 'field': Keyword.FIELD, 'static': Keyword.STATIC,
        'var': Keyword.VAR, 'int': Keyword.INT, 'char': Keyword.CHAR, 'boolean': Keyword.BOOLEAN,
        'void': Keyword.VOID, 'true': Keyword.TRUE, 'false': Keyword.FALSE,
        'null': Keyword.NULL, 'this': Keyword.THIS, 'let': Keyword.LET, 'do': Keyword.DO,
        'if': Keyword.IF, 'else': Keyword.ELSE, 'while': Keyword.WHILE, 'return': Keyword.RETURN
    }
    
    SYMBOL_SET = set(r'{}()[].,;+-*/&|<>=~')
    
    XML_ESCAPE_MAP = {
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        '"': '&quot;'
    }

    def __init__(self, input_file_path):
        with open(input_file_path, 'r') as f:
            content = f.read()
        
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        token_patterns = []
        token_patterns.append(r'(?P<KEYWORD>class|constructor|function|method|field|static|var|int|char|boolean|void|true|false|null|this|let|do|if|else|while|return)\b')
        token_patterns.append(r'(?P<IDENTIFIER>[a-zA-Z_][a-zA-Z0-9_]*)')
        token_patterns.append(r'(?P<INT_CONST>\d+)')
        token_patterns.append(r'(?P<STRING_CONST>\"[^\"]*\")')
        token_patterns.append(r'(?P<SYMBOL>[{}()\[\].,;+\-*/&|<>=~])')
        
        tokenizer_regex = re.compile('|'.join(token_patterns))
        self._tokens = [match for match in tokenizer_regex.finditer(content)]
        
        self._current_token_index = 0
        self.current_token = None
        self._token_type = None
        self._token_value = None
        
        self._load_current_token() 

    def _load_current_token(self):
        if not self.has_more_tokens():
            self.current_token = None
            self._token_type = None
            self._token_value = None
            return

        match = self._tokens[self._current_token_index]
        group_name = match.lastgroup
        token_str = match.group()
        
        self._token_type = group_name
        self.current_token = token_str 
        
        if group_name == TokenType.KEYWORD:
            self._token_value = self.KEYWORD_MAP[token_str]
        elif group_name == TokenType.SYMBOL:
            self._token_value = self.XML_ESCAPE_MAP.get(token_str, token_str)
        elif group_name == TokenType.IDENTIFIER:
            self._token_value = token_str
        elif group_name == TokenType.INT_CONST:
            self._token_value = int(token_str)
        elif group_name == TokenType.STRING_CONST:
            self._token_value = token_str[1:-1]

    def has_more_tokens(self):
        return self._current_token_index < len(self._tokens)

    def advance(self):
        if not self.has_more_tokens():
            return
        self._current_token_index += 1
        self._load_current_token()

    def token_type(self):
        return self._token_type

    def get_token_value(self):
        return self._token_value
    
    def get_token_tag(self):
        if self._token_type == TokenType.KEYWORD:
            return "keyword"
        if self._token_type == TokenType.SYMBOL:
            return "symbol"
        if self._token_type == TokenType.IDENTIFIER:
            return "identifier"
        if self._token_type == TokenType.INT_CONST:
            return "integerConstant"
        if self._token_type == TokenType.STRING_CONST:
            return "stringConstant"
    
    def get_xml_escaped_value(self):
        if self._token_type == TokenType.STRING_CONST:
            return self._token_value
        elif self._token_type == TokenType.SYMBOL:
            return self._token_value 
        elif self._token_type == TokenType.INT_CONST:
            return str(self._token_value)
        elif self._token_type == TokenType.IDENTIFIER:
            return self._token_value
        elif self._token_type == TokenType.KEYWORD:
            return self.current_token

class CompilationEngine:
    def __init__(self, tokenizer, output_file):
        self._tokenizer = tokenizer
        self._output_file = output_file
        self._indent = 0
        self._binary_ops = {'+', '-', '*', '/', '&', '|', '<', '>', '='}
        
        self.compile_class()

    def _write_tag(self, tag, opening):
        if opening:
            self._write(f"<{tag}>")
            self._indent += 1
        else:
            self._indent -= 1
            self._write(f"</{tag}>")

    def _write(self, s):
        self._output_file.write("  " * self._indent + s + "\n")

    def _eat(self, expected_token=None):
        if not self._tokenizer.has_more_tokens():
            raise Exception("Unexpected end of file")
        
        if expected_token and self._tokenizer.current_token != expected_token:
            raise Exception(f"Expected '{expected_token}', got '{self._tokenizer.current_token}'")

        tag = self._tokenizer.get_token_tag()
        value = self._tokenizer.get_xml_escaped_value()

        self._write(f"<{tag}> {value} </{tag}>")

        self._tokenizer.advance()

    def compile_class(self):
        self._write_tag("class", True)
        self._eat("class")
        self._eat() 
        self._eat("{")

        while self._tokenizer.current_token in ('static', 'field'):
            self.compile_class_var_dec()
        
        while self._tokenizer.current_token in ('constructor', 'function', 'method'):
            self.compile_subroutine_dec()

        self._eat("}")
        self._write_tag("class", False)

    def compile_class_var_dec(self):
        self._write_tag("classVarDec", True)
        self._eat() 
        self._eat() 
        self._eat() 

        while self._tokenizer.current_token == ',':
            self._eat(",")
            self._eat() 
        
        self._eat(";")
        self._write_tag("classVarDec", False)

    def compile_subroutine_dec(self):
        self._write_tag("subroutineDec", True)
        self._eat() 
        self._eat() 
        self._eat() 
        self._eat("(")
        self.compile_parameter_list()
        self._eat(")")
        self.compile_subroutine_body()
        self._write_tag("subroutineDec", False)

    def compile_parameter_list(self):
        self._write_tag("parameterList", True)
        
        if self._tokenizer.current_token != ')':
            self._eat() 
            self._eat() 

            while self._tokenizer.current_token == ',':
                self._eat(",")
                self._eat() 
                self._eat() 
        
        self._write_tag("parameterList", False)

    def compile_subroutine_body(self):
        self._write_tag("subroutineBody", True)
        self._eat("{")
        
        while self._tokenizer.current_token == 'var':
            self.compile_var_dec()
            
        self.compile_statements()
        self._eat("}")
        self._write_tag("subroutineBody", False)

    def compile_var_dec(self):
        self._write_tag("varDec", True)
        self._eat("var")
        self._eat() 
        self._eat() 

        while self._tokenizer.current_token == ',':
            self._eat(",")
            self._eat() 
        
        self._eat(";")
        self._write_tag("varDec", False)

    def compile_statements(self):
        self._write_tag("statements", True)
        while self._tokenizer.current_token in ('let', 'if', 'while', 'do', 'return'):
            if self._tokenizer.current_token == 'let':
                self.compile_let()
            elif self._tokenizer.current_token == 'if':
                self.compile_if()
            elif self._tokenizer.current_token == 'while':
                self.compile_while()
            elif self._tokenizer.current_token == 'do':
                self.compile_do()
            elif self._tokenizer.current_token == 'return':
                self.compile_return()
        self._write_tag("statements", False)

    def compile_let(self):
        self._write_tag("letStatement", True)
        self._eat("let")
        self._eat() 

        if self._tokenizer.current_token == '[':
            self._eat("[")
            self.compile_expression()
            self._eat("]")
        
        self._eat("=")
        self.compile_expression()
        self._eat(";")
        self._write_tag("letStatement", False)

    def compile_if(self):
        self._write_tag("ifStatement", True)
        self._eat("if")
        self._eat("(")
        self.compile_expression()
        self._eat(")")
        self._eat("{")
        self.compile_statements()
        self._eat("}")

        if self._tokenizer.current_token == 'else':
            self._eat("else")
            self._eat("{")
            self.compile_statements()
            self._eat("}")
        
        self._write_tag("ifStatement", False)

    def compile_while(self):
        self._write_tag("whileStatement", True)
        self._eat("while")
        self._eat("(")
        self.compile_expression()
        self._eat(")")
        self._eat("{")
        self.compile_statements()
        self._eat("}")
        self._write_tag("whileStatement", False)

    def compile_do(self):
        self._write_tag("doStatement", True)
        self._eat("do")
        self._eat() 

        if self._tokenizer.current_token == '(':
            self._eat("(")
            self.compile_expression_list()
            self._eat(")")
        elif self._tokenizer.current_token == '.':
            self._eat(".")
            self._eat() 
            self._eat("(")
            self.compile_expression_list()
            self._eat(")")
        
        self._eat(";")
        self._write_tag("doStatement", False)

    def compile_return(self):
        self._write_tag("returnStatement", True)
        self._eat("return")
        
        if self._tokenizer.current_token != ';':
            self.compile_expression()
            
        self._eat(";")
        self._write_tag("returnStatement", False)

    def compile_expression(self):
        self._write_tag("expression", True)
        self.compile_term()
        
        while self._tokenizer.current_token in self._binary_ops:
            self._eat() 
            self.compile_term()
            
        self._write_tag("expression", False)

    def compile_term(self):
        self._write_tag("term", True)
        
        if self._tokenizer.token_type() == TokenType.IDENTIFIER:
            self._eat() 
            
            if self._tokenizer.current_token == '[':
                self._eat("[")
                self.compile_expression()
                self._eat("]")
            elif self._tokenizer.current_token == '(':
                self._eat("(")
                self.compile_expression_list()
                self._eat(")")
            elif self._tokenizer.current_token == '.':
                self._eat(".")
                self._eat() 
                self._eat("(")
                self.compile_expression_list()
                self._eat(")")
        
        elif self._tokenizer.token_type() in (TokenType.INT_CONST, TokenType.STRING_CONST) or \
             self._tokenizer.current_token in ('true', 'false', 'null', 'this'):
            self._eat() 
            
        elif self._tokenizer.current_token == '(':
            self._eat("(")
            self.compile_expression()
            self._eat(")")
            
        elif self._tokenizer.current_token in ('-', '~'):
            self._eat() 
            self.compile_term()
            
        self._write_tag("term", False)

    def compile_expression_list(self):
        self._write_tag("expressionList", True)
        
        if self._tokenizer.current_token != ')':
            self.compile_expression()
            while self._tokenizer.current_token == ',':
                self._eat(",")
                self.compile_expression()
                        
        self._write_tag("expressionList", False)

def analyze_file(file_path):
    output_path = file_path.replace('.jack', '.xml')
    print(f"Compiling {file_path} -> {output_path}")
    
    try:
        tokenizer = JackTokenizer(file_path)
        with open(output_path, 'w') as output_file:
            CompilationEngine(tokenizer, output_file)
    except Exception as e:
        print(f"Error compiling {file_path}: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) != 2:
        print("Usage: python JackAnalyzer.py <file.jack or directory>")
        return

    input_path = sys.argv[1]

    if os.path.isdir(input_path):
        jack_files = [
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.endswith('.jack')
        ]
        if not jack_files:
            print(f"No .jack files found in directory: {input_path}")
            return
        for file_path in jack_files:
            analyze_file(file_path)
    elif os.path.isfile(input_path) and input_path.endswith('.jack'):
        analyze_file(file_path)
    else:
        print(f"Error: {input_path} is not a .jack file or a directory.")

if __name__ == "__main__":
    main()
