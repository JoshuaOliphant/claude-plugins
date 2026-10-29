"""Number formatting conventions for display output.

These conventions are used for reports meant to be read by people
(Markdown, HTML, the terminal summary). Data exports keep the plain
machine representation from :meth:`Money.plain`.
"""

from __future__ import annotations

import os

from ledgerkit.money import Money, exponent_for

_LOCALES: dict[str, type["NumberLocale"]] = {}

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "CHF "}


class NumberLocale:
    code = "C"
    decimal = "."
    group = ""
    symbol_first = True
    negative_parens = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _LOCALES[cls.code] = cls

    @classmethod
    def group_digits(cls, digits: str) -> str:
        if not cls.group or len(digits) <= 3:
            return digits
        parts = []
        while len(digits) > 3:
            parts.append(digits[-3:])
            digits = digits[:-3]
        parts.append(digits)
        return cls.group.join(reversed(parts))

    @classmethod
    def number(cls, money: Money) -> str:
        exp = exponent_for(money.currency)
        text = f"{abs(money.amount):.{exp}f}"
        whole, _, frac = text.partition(".")
        body = cls.group_digits(whole)
        if frac:
            body = f"{body}{cls.decimal}{frac}"
        return body

    @classmethod
    def money(cls, money: Money, with_symbol: bool = True) -> str:
        body = cls.number(money)
        if with_symbol:
            symbol = CURRENCY_SYMBOLS.get(money.currency)
            if symbol and cls.symbol_first:
                body = f"{symbol}{body}"
            elif symbol:
                body = f"{body} {symbol.strip()}"
            else:
                body = f"{body} {money.currency}"
        if money.is_negative:
            return f"({body})" if cls.negative_parens else f"-{body}"
        return body


_LOCALES[NumberLocale.code] = NumberLocale


class EnglishUS(NumberLocale):
    code = "en_US"
    group = ","


class EnglishGB(NumberLocale):
    code = "en_GB"
    group = ","


class Accounting(NumberLocale):
    code = "accounting"
    group = ","
    negative_parens = True


class German(NumberLocale):
    code = "de_DE"
    decimal = ","
    group = "."
    symbol_first = False


class French(NumberLocale):
    code = "fr_FR"
    decimal = ","
    group = " "
    symbol_first = False


class SwissGerman(NumberLocale):
    code = "de_CH"
    decimal = "."
    group = "'"


def get_locale(code: str | None) -> type[NumberLocale]:
    """Resolve ``de_DE.UTF-8`` → ``de_DE`` → any ``de_*`` → ``C``."""
    if not code:
        return _LOCALES["C"]
    base = code.split(".", 1)[0].split("@", 1)[0]
    if base in _LOCALES:
        return _LOCALES[base]
    language = base.split("_", 1)[0].lower()
    for known in sorted(_LOCALES):
        if known.split("_", 1)[0].lower() == language:
            return _LOCALES[known]
    return _LOCALES["C"]


def locale_from_environment(config_value: str | None = None) -> type[NumberLocale]:
    explicit = os.environ.get("LEDGERKIT_LOCALE")
    if explicit:
        return get_locale(explicit)
    if config_value and config_value.lower() != "auto":
        return get_locale(config_value)
    return get_locale(os.environ.get("LC_NUMERIC") or os.environ.get("LANG"))


def available_locales() -> list[str]:
    return sorted(_LOCALES)
