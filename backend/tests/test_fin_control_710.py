"""V7.10: controle financeiro do @financas (dívidas, contas, cartão, orçamento, metas, plano, avisos)."""
from datetime import date, datetime

import pytest

from modules import fin_control as fc
from modules import finances


def test_debt_payments_count_and_finish():
    fc.divida_add("Financiamento do carro", saldo=1800, parcela=900, total_parcelas=12, pagas=10, juros_mes=1.2, dia=10)
    d = fc.divida_pagar("carro")  # sem valor = a parcela
    assert d["saldo"] == 900 and d["pagas"] == 11 and not d["quitada"]
    d = fc.divida_pagar("carro")
    assert d["quitada"] and d["saldo"] == 0 and d["pagas"] == 12
    with pytest.raises(ValueError):
        fc.divida_pagar("carro")  # já quitada


def test_fixed_bills_paid_per_month():
    fc.conta_add("Luz", 180, 15)
    today = date(2026, 11, 13)
    v = fc.vencimentos(30, today)
    assert any(x["nome"] == "Luz" and x["data"] == "2026-11-15" and not x["pago"] for x in v)
    fc.conta_pagar("luz", now=datetime(2026, 11, 13, 10))
    v = fc.vencimentos(40, today)
    assert next(x for x in v if x["data"] == "2026-11-15")["pago"]
    assert next(x for x in v if x["data"] == "2026-12-15")["pago"] is False  # o mês que vem continua em aberto


def test_card_installments_fall_in_right_invoices():
    fc.cartao_add("Nubank", fechamento=3, vencimento=10)
    # compra dia 13/11 (depois do fechamento dia 3): 1ª parcela na fatura que vence 10/12
    c = fc.cartao_compra("nubank", 300, "tênis", 3, now=datetime(2026, 11, 13, 12))
    assert c["primeira"] == "2026-12-10"
    card = fc._load()["cartoes"][0]  # noqa: SLF001
    f = fc.faturas(card, 4, date(2026, 11, 13))
    assert [(x["vencimento"], x["valor"]) for x in f] == [("2026-12-10", 100.0), ("2027-01-10", 100.0), ("2027-02-10", 100.0), ("2027-03-10", 0.0)]
    # compra antes do fechamento cai na fatura deste ciclo
    assert fc.cartao_compra("nubank", 50, "café", 1, now=datetime(2026, 12, 2, 9))["primeira"] == "2026-12-10"


def test_plan_compares_and_recommends():
    fc.divida_add("Cartão rotativo", saldo=3000, parcela=300, juros_mes=12, dia=5)
    fc.divida_add("Loja", saldo=600, parcela=100, juros_mes=1, dia=20)
    p = fc.plano(extra=200)
    assert p["bola_de_neve"]["foco"][0] == "Loja"  # menor saldo primeiro
    assert p["avalanche"]["foco"][0] == "Cartão rotativo"  # maior juros primeiro
    assert p["avalanche"]["juros"] < p["bola_de_neve"]["juros"]
    assert p["recomendado"] == "avalanche" and "economiza" in p["motivo"]
    assert "meses" in fc.plano_texto(p) and "Recomendo" in fc.plano_texto(p)
    assert fc.plano(0)["bola_de_neve"]["meses"] > p["bola_de_neve"]["meses"]  # sem extra demora mais


def test_alerts_three_days_before_and_on_the_day_once():
    fc.divida_add("Banco", saldo=5000, parcela=450, dia=20)
    assert any("em 3 dias" in a and "Banco" in a for a in fc.due_alerts(date(2026, 11, 17)))
    assert fc.due_alerts(date(2026, 11, 17)) == []  # não repete
    assert any("hoje" in a and "R$ 450,00" in a for a in fc.due_alerts(date(2026, 11, 20)))
    fc.divida_pagar("banco", now=datetime(2026, 12, 19, 9))
    assert not any("Banco" in a for a in fc.due_alerts(date(2026, 12, 20)))  # paga: sem aviso


def test_budget_and_goals(monkeypatch):
    fc.orcamento_set("Mercado", 500)
    finances.add("out", 420, "mercado")
    assert fc.orcamento_status()[0] == {"categoria": "Mercado", "limite": 500.0, "gasto": 420.0, "pct": 84}
    assert any("orçamento de Mercado chegou a 84%" in a for a in fc.due_alerts())
    fc.meta_add("Reserva", 6000)
    assert fc.meta_guardar("reserva", 1500)["guardado"] == 1500


def test_actions_and_confirmation_rules():
    a = fc.clean_action({"tipo": "divida_add", "nome": "Banco X", "saldo": "5.000,00", "parcela": "450", "total_parcelas": 12, "dia": 40})
    assert a["saldo"] == 5000 and a["dia"] == 31 and not fc.needs_confirm(a)
    assert fc.needs_confirm({"tipo": "divida_quitar", "nome": "x"})
    assert fc.needs_confirm(fc.clean_action({"tipo": "divida_pagar", "nome": "x", "valor": 2500}))
    assert not fc.needs_confirm(fc.clean_action({"tipo": "divida_pagar", "nome": "x", "valor": 300}))
    assert fc.clean_action({"tipo": "apagar_tudo"}) is None and fc.clean_action({"tipo": "conta_add", "nome": "x"}) is None
    assert "Dívida cadastrada" in fc.run(a)
    assert fc.resumo()["total_devido"] == 5000
    assert fc.money(1234.5) == "R$ 1.234,50"


def test_cloud_gets_only_summary_and_pc_applies_phone_notes():
    from modules import cloud_sync

    fc.divida_add("Carro", saldo=1800, parcela=900, total_parcelas=12, pagas=10, juros_mes=1.2, dia=10)
    snap = cloud_sync.snapshot()["financas"]
    assert snap["total_devido"] == 1800 and snap["dividas"] == ["Carro"]
    assert "saldo" not in str(snap["proximos"]) and "juros" not in str(snap)  # sem detalhes
    assert cloud_sync.apply_op({"op": "fin_action", "acao": {"tipo": "divida_pagar", "nome": "carro"}})
    assert fc.resumo()["total_devido"] == 900
    assert not cloud_sync.apply_op({"op": "fin_action", "acao": {"tipo": "apagar_tudo"}})


def test_dashboard_route():
    from fastapi.testclient import TestClient

    import main
    from modules import access

    access.reset_for_tests(access.UNLOCKED)
    fc.divida_add("Loja", saldo=600, parcela=100, juros_mes=1, dia=20)
    d = TestClient(main.app).get("/api/finance/dashboard", params={"extra": 100}).json()
    assert d["total_devido"] == 600 and d["plano"]["extra"] == 100 and "Recomendo" in d["plano_texto"]
