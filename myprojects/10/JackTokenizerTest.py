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
            return self.XML_ESCAPE_MAP.get(self._token_value, self._token_value)
        elif self._token_type == TokenType.SYMBOL:
            return self._token_value 
        elif self._token_type == TokenType.INT_CONST:
            return str(self._token_value)
        elif self._token_type == TokenType.IDENTIFIER:
            return self._token_value
        elif self._token_type == TokenType.KEYWORD:
            return self.current_token

def analyze_file_for_tokens(file_path):
    output_path = file_path.replace('.jack', 'T.xml')
    print(f"Tokenizing {file_path} -> {output_path}")
    
    try:
        tokenizer = JackTokenizer(file_path)
        with open(output_path, 'w') as output_file:
            output_file.write("<tokens>\n")
            
            while tokenizer.has_more_tokens():
                tag = tokenizer.get_token_tag()
                value = tokenizer.get_xml_escaped_value()
                output_file.write(f"  <{tag}> {value} </{tag}>\n")
                tokenizer.advance()
                
            output_file.write("</tokens>\n")
            
    except Exception as e:
        print(f"Error tokenizing {file_path}: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) != 2:
        print("Usage: python JackTokenizerTest.py <file.jack or directory>")
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
            analyze_file_for_tokens(file_path)
    elif os.path.isfile(input_path) and input_path.endswith('.jack'):
        analyze_file_for_tokens(input_path)
    else:
        print(f"Error: {input_path} is not a .jack file or a directory.")

if __name__ == "__main__":
    main()
