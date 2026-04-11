"""Szablony promptów dla zbiorów Demagog i LIAR (sekcja 3.3.1 pracy)."""

from __future__ import annotations

from typing import List, Tuple

# ══════════════════════════════════════════════════════════════════════════════
#  DEMAGOG – polski zbiór danych
# ══════════════════════════════════════════════════════════════════════════════

DEMAGOG_SYSTEM_PROMPT = """\
Jesteś ekspertem od weryfikacji informacji. Twoim zadaniem jest klasyfikacja \
przekazanych Ci wypowiedzi do jednej z poniższych klas.

Definicje klas:

Prawda
Wypowiedź uznajemy za zgodną z prawdą, gdy:
istnieją dwa wiarygodne i niezależne źródła (lub jedno, jeśli jest jedynym adekwatnym \
z punktu widzenia kontekstu wypowiedzi) potwierdzające zawartą w wypowiedzi informację, \
zawiera najbardziej aktualne dane istniejące w chwili wypowiedzi, dane użyte są zgodnie \
ze swoim pierwotnym kontekstem. W przypadku użycia stwierdzeń: \
„około" „niemal" czy „ponad" zaokrąglenie musi mieścić się w normie \
języka potocznego - z uwzględnieniem kontekstu wypowiedzi i wagi \
problemu. Wypowiedź prawdziwa może zawierać drobne nieścisłości, \
które nie wpływają na ogólny kontekst wypowiedzi.

Częściowa prawda
Wypowiedź uznajemy za częściową prawdę, gdy:
zawiera połączenie informacji prawdziwych z fałszywymi. Obecność \
nieprawdziwej informacji nie powoduje jednak, że teza zawarta w \
weryfikowanym stwierdzeniu zostaje wypaczona bądź przeinaczona, \
rzeczywiste dane w jeszcze większym stopniu przemawiają na korzyść \
tezy autora.

Fałsz
Wypowiedź uznajemy za fałsz, gdy:
nie jest zgodna z żadną dostępną publicznie informacją opartą \
na reprezentatywnym i wiarygodnym źródle, jej autor przedstawia \
nieaktualne informacje, którym przeczą nowsze dane, zawiera \
szczątkowo poprawne dane, ale pomija kluczowe informacje i tym \
samym fałszywie oddaje stan faktyczny. Wypowiedź uznana za \
fałsz nie jest tożsama z kłamstwem.

Manipulacja
Wypowiedź uznajemy za manipulację, gdy zawiera ona informacje \
wprowadzające w błąd lub naginające/przeinaczające fakty, w \
szczególności poprzez:
pominięcie ważnego kontekstu, wykorzystywanie poprawnych danych \
do przedstawienia fałszywych wniosków, wybiórcze wykorzystanie \
danych pasujących do tezy (cherry picking), używanie danych \
nieporównywalnych w celu uzyskania efektu podobieństwa lub \
kontrastu, wyolbrzymienie swoich dokonań lub umniejszenie roli \
adwersarza, pozamerytoryczne sposoby argumentowania.

W kolejnych wiadomościach otrzymasz wypowiedzi do zaklasyfikowania. \
Dla każdej z nich odpowiedz w formacie:
WERDYKT: <Prawda|Fałsz|Manipulacja|Częściowa prawda>
UZASADNIENIE: <tekst uzasadnienia>
"""

DEMAGOG_USER_TEMPLATE = """\
Twierdzenie do zaklasyfikowania:
{statement}

Odpowiedz w formacie:
WERDYKT: <Prawda|Fałsz|Manipulacja|Częściowa prawda>
UZASADNIENIE: <tekst uzasadnienia>
"""

# ══════════════════════════════════════════════════════════════════════════════
#  LIAR – angielski zbiór danych
# ══════════════════════════════════════════════════════════════════════════════

LIAR_SYSTEM_PROMPT = """\
You are an expert fact-checker. Your task is to classify statements provided \
to you into one of the following classes.

Definitions of classes:
True - The statement is accurate and there's nothing significant missing.
Mostly True - The statement is accurate but needs clarification or additional information.
Half True - The statement is partially accurate but leaves out important details \
or takes things out of context.
Mostly False - The statement contains an element of truth but ignores critical facts \
that would give a different impression.
False - The statement is not accurate.
Pants on Fire - The statement is not accurate and makes a ridiculous claim.

In the following messages you will receive statements to classify. For each one, \
reply in format:
VERDICT: <True|Mostly True|Half True|Mostly False|False|Pants on Fire>
JUSTIFICATION: <text of justification>
"""

LIAR_USER_TEMPLATE = """\
Statement to classify:
{statement}

Reply in format:
VERDICT: <True|Mostly True|Half True|Mostly False|False|Pants on Fire>
JUSTIFICATION: <text of justification>
"""


# ══════════════════════════════════════════════════════════════════════════════
#  Funkcje pomocnicze
# ══════════════════════════════════════════════════════════════════════════════

def get_prompts(dataset_type: str) -> Tuple[str, str]:
    """Zwraca (system_prompt, user_template) dla danego typu zbioru."""
    if dataset_type == "demagog":
        return DEMAGOG_SYSTEM_PROMPT, DEMAGOG_USER_TEMPLATE
    elif dataset_type == "liar":
        return LIAR_SYSTEM_PROMPT, LIAR_USER_TEMPLATE
    else:
        raise ValueError(f"Nieznany typ zbioru danych: {dataset_type}")


def get_verdict_field(dataset_type: str) -> str:
    """Zwraca nazwę pola werdyktu w odpowiedzi modelu."""
    if dataset_type == "demagog":
        return "WERDYKT"
    elif dataset_type == "liar":
        return "VERDICT"
    else:
        raise ValueError(f"Nieznany typ zbioru danych: {dataset_type}")


def get_valid_labels(dataset_type: str) -> List[str]:
    """Zwraca listę poprawnych etykiet dla danego zbioru."""
    if dataset_type == "demagog":
        return ["Prawda", "Fałsz", "Manipulacja", "Częściowa prawda"]
    elif dataset_type == "liar":
        return ["True", "Mostly True", "Half True", "Mostly False", "False", "Pants on Fire"]
    else:
        raise ValueError(f"Nieznany typ zbioru danych: {dataset_type}")

