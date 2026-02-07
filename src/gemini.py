from google import genai
import os

def list_models(client):
    for model in client.models.list():
        print(model.name)

# 1. Konfiguracja (najlepiej użyć zmiennej środowiskowej GEMINI_API_KEY)
def main(client):
    chat = client.chats.create(model="models/gemini-2.5-flash-lite")

    initial_prompt = "W kolejnych promprach przedstawię ci wypowiedzi. Zweryfikuj wypowiedź którą ci przedstawię, zakasyfikuj ją jako prawda fałsz lub manipulacja."
    prompts = [
        "Na koniec chciałbym pokazać informację, fragment korespondencji z Ministerstwa Zdrowia odnośnie szczepionek HPV. Oto końcówka pisma podpisanego przez panią Annę Widarską, dyrektor Departamentu Matki i Dziecka. […] „Ministerstwo Zdrowia nie posiada dokumentacji dotyczącej badań naukowych potwierdzających skuteczność i bezpieczeństwo szczepionki przeciwko HPV. Jednocześnie uprzejmie informuję, iż na stronie internetowej Ministerstwa Zdrowia znajdują się wiarygodne i rzetelne informacje na temat szczepionki przeciwko HPV”. No przecież to jest jawna kpina! No nie możemy się zgadzać na to, by administracja państwowa, która jest finansowana z pieniędzy podatników, traktowała polskich obywateli jak idiotów i zamiast chronić ich zdrowie i prawa, organizuje system prześladowań."
    ]

    prompts = [prompt.replace(" ", " ") for prompt in prompts]

    # Pierwsza wiadomość
    response1 = chat.send_message(initial_prompt)
    print(f"Gemini: {response1.text}")

    for prompt in prompts:
        response = chat.send_message(prompt)
        print(f"Prompt: {prompt}")
        print(f"Gemini: {response.text}")

def get_cut_off_date():
    return

if __name__ == "__main__":
    os.environ["GEMINI_API_KEY"] = "AIzaSyChPgbbTNBw3FvrRfFSbt3VbR_Iwbg9Y2A"
    client = genai.Client()
    main(client)