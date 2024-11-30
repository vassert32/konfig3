import argparse
import copy
import re
import sys
import yaml

class Lexer:
    def __init__(self, input_text):
        self.text = input_text
        self.position = 0
        self.tokens = []
        self.token_specification = [
            ('COMMENT_START', r'/\*'),
            ('COMMENT_END', r'\*/'),
            ('ASSIGN', r':='),
            ('SEMICOLON', r';'),
            ('EVAL_START', r'\$\('),
            ('EVAL_END', r'\)'),
            ('ARRAY_START', r'<<'),
            ('ARRAY_END', r'>>'),
            ('COMMA', r','),
            ('NUMBER', r'\d+'),
            ('STRING', r"'[^']*'"),
            ('NAME', r'[A-Z][A-Z0-9_]*'),
            ('SKIP', r'[ \t\n]+'),
            ('MISMATCH', r'.'),
        ]
        self.token_regex = '|'.join('(?P<%s>%s)' % pair for pair in self.token_specification)

    def generate_tokens(self):
        pattern = re.compile(self.token_regex)
        pos = 0
        in_comment = False
        while pos < len(self.text):
            if in_comment:
                comment_end = self.text.find('*/', pos)
                if comment_end == -1:
                    raise SyntaxError("Не завершен многострочный комментарий")
                pos = comment_end + 2
                in_comment = False
                continue
            match = pattern.match(self.text, pos)
            if not match:
                raise SyntaxError(f"Недопустимый символ в позиции {pos}")
            kind = match.lastgroup
            value = match.group()
            if kind == 'COMMENT_START':
                in_comment = True
                pos = match.end()
            elif kind == 'COMMENT_END':
                raise SyntaxError("Неожиданный конец комментария")
            elif kind == 'SKIP':
                pos = match.end()
            elif kind == 'MISMATCH':
                raise SyntaxError(f"Неожиданный токен '{value}' в позиции {pos}")
            else:
                self.tokens.append((kind, value))
                pos = match.end()
        return self.tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0
        self.constants = {}
        self.ast = []

    def parse(self):
        while self.position < len(self.tokens):
            self.ast.append(self.declaration())
        return self.ast

    def declaration(self):
        kind, value = self.tokens[self.position]
        if kind != 'NAME':
            self.error("Ожидалось имя константы")
        name = value
        self.position += 1
        kind, value = self.tokens[self.position]
        if kind != 'ASSIGN':
            self.error("Ожидалось ':=' при объявлении константы")
        self.position += 1
        value = self.value()
        kind, token_value = self.tokens[self.position]
        if kind != 'SEMICOLON':
            self.error("Ожидалось ';' в конце объявления")
        self.position += 1
        self.constants[name] = value
        return (name, value)

    def value(self):
        if self.position >= len(self.tokens):
            self.error("Неожиданный конец входных данных")
        kind, value = self.tokens[self.position]
        if kind == 'NUMBER':
            self.position += 1
            return int(value)
        elif kind == 'STRING':
            self.position += 1
            return value.strip("'")
        elif kind == 'ARRAY_START':
            return self.array()
        elif kind == 'EVAL_START':
            return self.evaluation()
        else:
            self.error(f"Неожиданный токен '{value}'")

    def array(self):
        self.position += 1  # Пропускаем '<<'
        items = []
        while True:
            items.append(self.value())
            kind, value = self.tokens[self.position]
            if kind == 'COMMA':
                self.position += 1
                continue
            elif kind == 'ARRAY_END':
                self.position += 1
                break
            else:
                self.error("Ожидалось ',' или '>>' в массиве")
        return items

    def evaluation(self):
        self.position += 1  # Пропускаем '$('
        kind, name = self.tokens[self.position]
        if kind != 'NAME':
            self.error("Ожидалось имя константы при вычислении")
        self.position += 1
        kind, value = self.tokens[self.position]
        if kind != 'EVAL_END':
            self.error("Ожидалось ')' при вычислении")
        self.position += 1
        if name not in self.constants:
            self.error(f"Неопределенная константа '{name}'")
        return self.constants[name]

    def error(self, message):
        raise SyntaxError(f"Синтаксическая ошибка на токене {self.position}: {message}")

def main():
    arg_parser = argparse.ArgumentParser(description='Парсер конфигурационного языка')
    arg_parser.add_argument('-i', '--input', required=True, help='Путь к входному файлу')
    args = arg_parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_text = f.read()
        lexer = Lexer(input_text)
        tokens = lexer.generate_tokens()
        config_parser = Parser(tokens)
        ast = config_parser.parse()
        yaml_output = {}
        for name, value in config_parser.constants.items():
            yaml_output[name] = copy.deepcopy(value)
        print(yaml.dump(yaml_output, sort_keys=False, allow_unicode=True))
    except SyntaxError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{args.input}' не найден", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

