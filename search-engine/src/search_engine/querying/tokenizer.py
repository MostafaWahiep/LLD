from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable
import re

class TokenType(Enum):
    OPERATOR = auto()
    TERM = auto()
    COMMA = auto()
    LEFT_PARENTHESIS = auto()
    RIGHT_PARENTHESIS = auto()
    SKIP = auto()
    MISMATCH = auto()

@dataclass(frozen=True)
class TokenSpec:
    token_type: TokenType
    pattern: str
    transform: Callable[[str], str] = lambda s: s
    
@dataclass(frozen=True)
class Token:
    value: str
    token_type: TokenType

    def __repr__(self) -> str:
        return f"Token(value={self.value!r}, token_type={self.token_type!r})"

class RESERVED_WORDS(Enum):
    AND = ("AND", TokenType.OPERATOR)
    OR  = ("OR",  TokenType.OPERATOR)
    NOT = ("NOT", TokenType.OPERATOR)
    PREFIX = ("PREFIX", TokenType.OPERATOR)
    PHRASE = ("PHRASE", TokenType.OPERATOR)

    def __init__(self, value_str: str, token_type: TokenType):
        self.value_str = value_str
        self.token_type = token_type

TOKEN_SPECS = [
    TokenSpec(TokenType.OPERATOR, r'\b(AND|OR|NOT|PREFIX|PHRASE)\b'),
    TokenSpec(TokenType.TERM, r'"([^"]*)"', transform=lambda s: s[1:-1]),
    TokenSpec(TokenType.COMMA, r','),
    TokenSpec(TokenType.LEFT_PARENTHESIS, r'\('),
    TokenSpec(TokenType.RIGHT_PARENTHESIS, r'\)'),
    TokenSpec(TokenType.SKIP, r'[ \t\n\r]+'),
    TokenSpec(TokenType.MISMATCH, r'.'),
]
SPEC_MAP = {spec.token_type.name: spec for spec in TOKEN_SPECS}

class Tokenizer:
    @staticmethod
    def tokenize(query: str) -> list[Token]:
        # Combine patterns into a single regex using Enum names as group identifiers
        master_pattern = '|'.join(
            f'(?P<{spec.token_type.name}>{spec.pattern})' for spec in TOKEN_SPECS
        )

        tokens = []
        for match in re.finditer(master_pattern, query):
            group_name = match.lastgroup
            spec = SPEC_MAP[group_name]
            token_type = spec.token_type
            value = spec.transform(match.group())
            
            if token_type == TokenType.SKIP:
                continue
            elif token_type == TokenType.MISMATCH:
                raise ValueError(f"Unexpected character: {value!r}")
                
            tokens.append(Token(token_type=token_type, value=value))
            
        return tokens
