#!/usr/bin/env python3
"""
Fórmulas de combate do rAthena (modo Renewal) reescritas em Python.

Reimplementação fiel do código-fonte C++ para facilitar entender/depurar/simular
sem precisar recompilar o servidor. Cada função cita a referência arquivo:linha.

NÃO é usado pelo servidor — é ferramenta de estudo. Os documentos irmãos
(01/02/03 .md) explicam a teoria; aqui estão os números executáveis.

Uso rápido:
    python3 formulas.py                 # roda a demonstração (tabelas)
    from formulas import *              # usa as funções interativamente
    >>> attacks_per_second(agi=120, dex=40, base_aspd=49)
"""

import math

# ---------------------------------------------------------------------------
# Constantes do engine (src/map/status.hpp)
# ---------------------------------------------------------------------------
AMOTION_ZERO_ASPD = 2000   # status.hpp:65
AMOTION_INTERVAL = 10      # status.hpp:67
AMOTION_DIVIDER_PC = 2     # status.hpp:61
MIN_ASPD = 8000            # status.hpp:44
DEFAULT_MAX_ASPD = 190     # battle.cpp:8400 (config max_aspd)
DEFAULT_MIN_HITRATE = 5    # battle.cpp:8421
DEFAULT_MAX_HITRATE = 100  # battle.cpp:8422

# Tipos de arma considerados "longo alcance" para a fórmula de ASPD
# (arco, instrumento, chicote, revólver, rifle, gatling, shotgun, granada).
# src/map/status.cpp:2371-2379
LONGRANGE_WEAPONS = {"bow", "musical", "whip", "revolver",
                     "rifle", "gatling", "shotgun", "grenade"}


# ===========================================================================
# 1. VELOCIDADE DE ATAQUE  (doc 01)
# ===========================================================================

def aspd_stats(agi, dex, base_aspd, weapon="sword",
               skill_buff_bonus=0, shield_base=0):
    """
    Valor de ASPD a partir dos stats (Renewal).
    Reimplementa src/map/status.cpp:2355-2398 (status_base_amotion_pc).

    base_aspd: BaseASPD da classe para o tipo de arma (db/re/job_aspd.yml).
    weapon: nome do tipo (só importa se está em LONGRANGE_WEAPONS).
    skill_buff_bonus: soma de bônus de skill/buff de ASPD (0 = personagem "puro").
    shield_base: BaseASPD do escudo, se usar escudo (senão 0).
    """
    if weapon.lower() in LONGRANGE_WEAPONS:
        temp = dex * dex / 7.0 + agi * agi / 2.0
    else:
        temp = dex * dex / 5.0 + agi * agi / 2.0
    temp_aspd = math.sqrt(temp) * 0.25 + 196

    weapon_base = base_aspd + shield_base
    aspd = temp_aspd + skill_buff_bonus * agi / 200.0 - min(weapon_base, 200)
    return aspd


def amotion(agi, dex, base_aspd, weapon="sword", skill_buff_bonus=0,
            shield_base=0, max_aspd=DEFAULT_MAX_ASPD):
    """
    'amotion' final (metade do delay entre ataques).
    Reimplementa a conversão em src/map/status.cpp:4615-4620.
    """
    a = aspd_stats(agi, dex, base_aspd, weapon, skill_buff_bonus, shield_base)
    i = AMOTION_ZERO_ASPD - a * AMOTION_INTERVAL
    lower = max_aspd / AMOTION_DIVIDER_PC
    upper = MIN_ASPD / AMOTION_DIVIDER_PC
    return max(min(i, upper), lower)


def attack_delay_ms(agi, dex, base_aspd, **kw):
    """Delay REAL em milissegundos entre dois ataques. adelay = 2 * amotion."""
    return AMOTION_DIVIDER_PC * amotion(agi, dex, base_aspd, **kw)


def attacks_per_second(agi, dex, base_aspd, **kw):
    """Frequência de ataque (ataques por segundo)."""
    return 1000.0 / attack_delay_ms(agi, dex, base_aspd, **kw)


def displayed_aspd(agi, dex, base_aspd, **kw):
    """Número de ASPD que aparece na janela do client (0 a ~193)."""
    return (AMOTION_ZERO_ASPD - amotion(agi, dex, base_aspd, **kw)) / 10.0


def agi_needed_for_frequency(mult, dex, base_aspd, weapon="sword",
                             agi_base=1, agi_cap=255, **kw):
    """
    Menor AGI que atinge 'mult' vezes a frequência inicial (em agi_base).
    Retorna None se nem no agi_cap atinge.
    """
    f0 = attacks_per_second(agi_base, dex, base_aspd, weapon=weapon, **kw)
    for agi in range(agi_base, agi_cap + 1):
        if attacks_per_second(agi, dex, base_aspd, weapon=weapon, **kw) >= f0 * mult:
            return agi
    return None


# ===========================================================================
# 2. MIRA (HIT) E DESVIO (FLEE)  (doc 02)
# ===========================================================================

def hit_stat(level, dex, luk, con=0):
    """Hit (mira) de jogador. src/map/status.cpp:2640-2642."""
    return level + dex + luk // 3 + 175 + 2 * con


def flee_stat(level, agi, luk, con=0):
    """Flee (desvio) de jogador. src/map/status.cpp:2645-2647."""
    return level + agi + luk // 5 + 100 + 2 * con


def perfect_dodge_pct(luk):
    """Perfect Dodge (Flee2) em %, independente da mira. status.cpp:2737."""
    return (luk + 10) / 10.0  # flee2 em décimos -> /10 = %


def hit_chance_pct(atk_hit, target_flee,
                   min_hitrate=DEFAULT_MIN_HITRATE,
                   max_hitrate=DEFAULT_MAX_HITRATE):
    """
    Chance de acerto de um ataque normal (Renewal), em %.
    src/map/battle.cpp:3258-3316. NÃO considera crítico nem perfect dodge
    (esses são checados antes; ver módulo de crítico).
    """
    hitrate = 0  # base Renewal (pré-Renewal seria 80)
    hitrate += atk_hit - target_flee
    return max(min(hitrate, max_hitrate), min_hitrate)


# ===========================================================================
# 3. SORTE E CRÍTICO  (doc 03)
# ===========================================================================

def crit_stat_permil(luk, level):
    """
    Cri base em milésimos (Renewal). src/map/status.cpp:2725-2730.
    Divida por 10 para ter %.
    """
    return 10 + luk * 3 + level // 10


def crit_chance_pct(luk, level, target_luk=0, weapon_card_bonus_permil=0,
                    is_pc_attacker=True, target_is_pc=False):
    """
    Chance real de crítico em %, já descontando a sorte do alvo.
    src/map/battle.cpp:3046-3152.

    weapon_card_bonus_permil: bônus de crítico de carta/arma, em milésimos.
    O alvo reduz: cri -= LUK_alvo * (3 se mob ataca pc, senão 2).
    """
    cri = crit_stat_permil(luk, level) + weapon_card_bonus_permil
    factor = 3 if (not is_pc_attacker and target_is_pc) else 2
    cri -= target_luk * factor
    cri = max(0, min(cri, 1000))
    return cri / 10.0


def luk_needed_for_crit(target_pct, level, agi_cap=255):
    """Menor LUK para atingir 'target_pct' % de crítico (sem alvo). None se > cap."""
    for luk in range(0, agi_cap + 1):
        if crit_chance_pct(luk, level) >= target_pct:
            return luk
    return None


# ===========================================================================
# 4. FORÇA, ATK DA ARMA E DANO FINAL  (doc 04)
# ===========================================================================

def status_atk(str_, dex, luk, level, pow_=0):
    """
    statusAtk — ATK vindo da Força, independente da arma equipada.
    src/map/status.cpp:2477 + src/map/battle.cpp:3899-3910 (dobrado no fim).
    """
    str_adj = (str_ * 10 + dex * 10 // 5 + luk * 10 // 3 + level * 10 // 4) / 10.0 + 5 * pow_
    return str_adj * 2  # "Right-hand status attack is doubled" battle.cpp:3910


def weapon_atk_range(item_atk, refine_bonus, weapon_level, str_or_dex,
                     longrange=False):
    """
    Intervalo (min, max) do weaponAtk — o pote que interage multiplicativamente
    com STR (ou DEX para armas de longo alcance).
    src/map/battle.cpp:2443-2492.

    item_atk: campo Atk do item (item_db).
    refine_bonus: bônus de refino (rhw.atk2), da tabela refine.yml.
    weapon_level: nível da arma (1-4, campo WeaponLv do item).
    str_or_dex: STR do atacante (ou DEX se longrange=True).
    """
    watk = item_atk + refine_bonus
    variance = 5.0 * item_atk * weapon_level / 100.0
    bonus_stat = item_atk * str_or_dex / 200.0  # <- o termo que MULTIPLICA arma x STR

    atk_min = max(0, watk - variance + bonus_stat)
    atk_max = watk + variance + bonus_stat
    return atk_min, atk_max


def weapon_atk_avg(item_atk, refine_bonus, weapon_level, str_or_dex, longrange=False):
    """Média do intervalo de weaponAtk (para estimativas rápidas)."""
    lo, hi = weapon_atk_range(item_atk, refine_bonus, weapon_level, str_or_dex, longrange)
    return (lo + hi) / 2.0


def percent_atk(weapon_atk, equip_atk, atk_rate_pct):
    """
    percentAtk — bônus de "%ATK" (bAtkRate). Só multiplica weaponAtk+equipAtk,
    NÃO toca no statusAtk (Força pura). src/map/battle.cpp:3941-3944.
    """
    return (weapon_atk + equip_atk) * atk_rate_pct / 100.0


def total_damage_estimate(str_, dex, luk, level, item_atk, refine_bonus,
                          weapon_level, equip_atk=0, atk_rate_pct=0,
                          mastery_atk=0, pow_=0, longrange=False):
    """
    Estimativa do dano de um ataque normal, somando os 5 potes.
    src/map/battle.cpp:5525 + 5538 -> dano = statusAtk+weaponAtk+equipAtk+percentAtk+masteryAtk
    (usa a MÉDIA do weaponAtk, já que ele varia por ataque).
    """
    s_atk = status_atk(str_, dex, luk, level, pow_)
    str_or_dex = dex if longrange else str_
    w_atk = weapon_atk_avg(item_atk, refine_bonus, weapon_level, str_or_dex, longrange)
    p_atk = percent_atk(w_atk, equip_atk, atk_rate_pct)
    return {
        "statusAtk": s_atk,
        "weaponAtk": w_atk,
        "equipAtk": equip_atk,
        "percentAtk": p_atk,
        "masteryAtk": mastery_atk,
        "total": s_atk + w_atk + equip_atk + p_atk + mastery_atk,
    }


# ===========================================================================
# Demonstração
# ===========================================================================

def _demo():
    print("=" * 64)
    print("VELOCIDADE — Lord Knight, DEX 40 (BaseASPD real de db/re/job_aspd.yml)")
    print("=" * 64)
    for label, base in [("Adaga (leve, base 49)", 49),
                        ("Lança 2M (pesada, base 60)", 60)]:
        f0 = attacks_per_second(1, 40, base)
        print(f"\n{label}  — freq inicial {f0:.2f} atk/s")
        print(f"  {'AGI':>4}  {'atk/s':>6}  {'x inicial':>9}  {'ASPD tela':>9}")
        for agi in (1, 50, 100, 150, 200, 255):
            f = attacks_per_second(agi, 40, base)
            print(f"  {agi:>4}  {f:>6.2f}  {f/f0:>8.2f}x  {displayed_aspd(agi,40,base):>9.1f}")
        print(f"  dobrar (2x): AGI {agi_needed_for_frequency(2, 40, base)}"
              f"  | quadruplicar (4x): AGI {agi_needed_for_frequency(4, 40, base)}")
    print("\n  Peso da arma NAO afeta ASPD — só o tipo (BaseASPD). Confirmado no código.")

    print("\n" + "=" * 64)
    print("CRÍTICO — por faixa de LUK (sem bônus de arma)")
    print("=" * 64)
    print(f"  {'LUK':>4}  {'crit@lv100':>11}  {'crit@lv250':>11}")
    for luk in (0, 50, 100, 150, 200, 255):
        print(f"  {luk:>4}  {crit_chance_pct(luk,100):>10.1f}%  {crit_chance_pct(luk,250):>10.1f}%")
    print("  Linear: +0.3%/LUK. No cap 255 chega a ~80% (100% puro exigiria LUK 322).")

    print("\n" + "=" * 64)
    print("MIRA vs DESVIO — exemplo")
    print("=" * 64)
    h = hit_stat(level=120, dex=40, luk=40)
    f = flee_stat(level=100, agi=60, luk=20)
    print(f"  Hit atacante (lv120, DEX40, LUK40) = {h}")
    print(f"  Flee alvo   (lv100, AGI60, LUK20) = {f}")
    print(f"  chance de acerto = {hit_chance_pct(h, f):.0f}%  (crítico ignoraria isso e acertaria sempre)")

    print("\n" + "=" * 64)
    print("FORÇA x ATK DA ARMA — mesma arma (Espada 1M, Atk 150, refino +0, wlv 3),")
    print("comparando STR baixo vs alto")
    print("=" * 64)
    for str_ in (10, 50, 100, 150, 200, 255):
        d = total_damage_estimate(str_=str_, dex=1, luk=1, level=150,
                                  item_atk=150, refine_bonus=0, weapon_level=3)
        share_weapon = 100 * d["weaponAtk"] / d["total"]
        print(f"  STR {str_:>3}: statusAtk={d['statusAtk']:>6.1f}  weaponAtk={d['weaponAtk']:>6.1f}"
              f"  total={d['total']:>7.1f}  (arma = {share_weapon:4.1f}% do dano)")
    print("\n  Repare: weaponAtk CRESCE junto com STR (termo Atk_item x STR/200).")
    print("  A arma nao 'perde valor' — statusAtk so cresce mais rapido em termos absolutos.")

    print("\n  Agora comparando arma fraca (Atk 50) vs forte (Atk 200) no MESMO STR alto (200):")
    for atk in (50, 100, 150, 200):
        d = total_damage_estimate(str_=200, dex=1, luk=1, level=150,
                                  item_atk=atk, refine_bonus=0, weapon_level=3)
        print(f"  Atk_item {atk:>3}: weaponAtk={d['weaponAtk']:>6.1f}  total={d['total']:>7.1f}")
    print("  Trocar de arma continua sendo um multiplicador direto do dano, em qualquer STR.")


if __name__ == "__main__":
    _demo()
