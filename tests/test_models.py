import pytest
from pydantic import ValidationError

from app.extraction import person_fields, portal_url
from app.models import Query


@pytest.mark.parametrize("value,expected", [("  Maria   Teste ", "Maria Teste"), ("123.456.789-00", "12345678900"), ("00000000000", "00000000000")])
def test_normalize(value, expected):
    assert Query(termo=value).termo == expected


@pytest.mark.parametrize("value", ["", "   ", "1", "1234", "--", "!@#"])
def test_invalid(value):
    with pytest.raises(ValidationError):
        Query(termo=value)


def test_links_are_restricted():
    assert portal_url("/pessoa-fisica/1").endswith("/pessoa-fisica/1")
    assert portal_url("https://evil.example/pessoa-fisica/1") is None
    assert portal_url("javascript:alert(1)") is None
    assert portal_url("https://portaldatransparencia.gov.br.evil.example") is None


def test_preserves_masked_cpf_and_missing_fields():
    assert person_fields("Nome\nMARIA TESTE\nCPF\n***.123.456-**", {}) == {
        "nome": "MARIA TESTE", "cpf": "***.123.456-**", "nis": None, "localidade": None,
    }
