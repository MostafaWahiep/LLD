from tokenizer import Tokenizer, Token, TokenType, RESERVED_WORDS
from query import AndQuery, NotQuery, OrQuery, Query, TermQuery, PhraseQuery, PrefixQuery

class Parser:
    # query -> AND binary_operation | OR binary_operation | NOT uniary_operation | Term
    # binary_operation -> ( query , query )
    # uniary_operation -> ( query )
    # Term -> "\w+"
    
    @staticmethod
    def _match(tokens: list[Token], index: int, token_type: TokenType) -> int:
        if index >= len(tokens):
            raise IndexError(f"Missing Token of Type: {token_type.value}")

        token = tokens[index]

        if token.token_type != token_type:
            raise ValueError(f"Expected Token Type: {token_type.value}")

        return index + 1

    @staticmethod
    def _binary_operation(tokens: list[Token], index: int) -> tuple[Query, Query, int]:
        # binary_operation -> ( query , query )
        index: int = Parser._match(tokens, index, TokenType.LEFT_PARENTHESIS)

        left_query: Query
        left_query, index = Parser.parse_query(tokens, index)

        index: int = Parser._match(tokens, index, TokenType.COMMA)

        right_query: Query
        right_query, index = Parser.parse_query(tokens, index)

        index: int = Parser._match(tokens, index, TokenType.RIGHT_PARENTHESIS)

        return left_query, right_query, index

    @staticmethod
    def _unary_operation(tokens: list[Token], index: int) -> tuple[Query, int]:
        # unary_operation -> ( query )
        index: int = Parser._match(tokens, index, TokenType.LEFT_PARENTHESIS)

        query: Query
        query, index = Parser.parse_query(tokens, index)

        index: int = Parser._match(tokens, index, TokenType.RIGHT_PARENTHESIS)

        return query, index

    @staticmethod
    def _and(tokens: list[Token], index: int) -> tuple[AndQuery, int]:
        left_query, right_query, index = Parser._binary_operation(tokens, index)
        and_query: AndQuery = AndQuery(left_query, right_query)
        return and_query, index

    @staticmethod
    def _or(tokens: list[Token], index: int) -> tuple[OrQuery, int]:
        left_query, right_query, index = Parser._binary_operation(tokens, index)
        or_query: OrQuery = OrQuery(left_query, right_query)
        return or_query, index

    @staticmethod
    def _not(tokens: list[Token], index: int) -> tuple[NotQuery, int]:
        query, index = Parser._unary_operation(tokens, index)
        not_query: NotQuery = NotQuery(query)
        return not_query, index

    @staticmethod
    def _prefix(tokens: list[Token], index: int) -> tuple[PrefixQuery, int]:
        query, index = Parser._unary_operation(tokens, index)

        if not isinstance(query, TermQuery):
            raise SyntaxError("Nesting queries with Prefix operation is not allowed")
        
        not_query: PrefixQuery = PrefixQuery(query.term)
        return not_query, index

    @staticmethod
    def _phrase(tokens: list[Token], index: int) -> tuple[PhraseQuery, int]:
        query, index = Parser._unary_operation(tokens, index)

        if not isinstance(query, TermQuery):
            raise SyntaxError("Nesting queries with Phrase operation is not allowed")
        
        not_query: PhraseQuery = PhraseQuery(query.term)
        return not_query, index

    @staticmethod
    def parse_query(tokens: list[Token], index: int) -> tuple[Query, int]:
        if index >= len(tokens):
            raise ValueError("Expected a query but reached end of input")
        
        token: Token = tokens[index]
        if token.token_type == TokenType.OPERATOR:
            if token.value == RESERVED_WORDS.AND.value_str:
                return Parser._and(tokens, index + 1)
            elif token.value == RESERVED_WORDS.OR.value_str:
                return Parser._or(tokens, index + 1)
            elif token.value == RESERVED_WORDS.NOT.value_str:
                return Parser._not(tokens, index + 1)
            elif token.value == RESERVED_WORDS.PREFIX.value_str:
                return Parser._prefix(tokens, index + 1)
            elif token.value == RESERVED_WORDS.PHRASE.value_str:
                return Parser._phrase(tokens, index + 1)
            else:
                raise ValueError(f"Unexpected Operator {token.value} in the query.")
        elif token.token_type == TokenType.TERM:
            return TermQuery(token.value), index + 1
        else:
            raise ValueError(f"Unexpected Token: {token}")

    @staticmethod
    def parse(query_str: str) -> Query:
        tokens: list[Token] = Tokenizer.tokenize(query_str)
        
        query, index = Parser.parse_query(tokens, 0)

        if index != len(tokens):
            raise ValueError(f"Parsing went wrong")

        return query
