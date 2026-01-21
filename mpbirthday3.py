import pandas as pd
import random
from SPARQLWrapper import SPARQLWrapper, JSON
from atproto import Client, client_utils

# Add your credentials here:
client = Client()
client.login("account", "password")

def load_data(path="stammdaten.csv"):
    df = pd.read_csv(path)
    for col in ["geburtsdatum", "sterbedatum", "historie"]:
        df[col] = pd.to_datetime(df[col])
    return df

def pick_birthday_mp(df):
    today = pd.Timestamp.today().strftime("%d-%m")
    df["geburtsdatum_ddmm"] = df["geburtsdatum"].dt.strftime("%d-%m")

    df_birthdays = df[
        (df["geburtsdatum_ddmm"] == today) &
        (df["partei"] != "AfD")
    ]

    if df_birthdays.empty:
        return None

    return df_birthdays.sample(1).iloc[0]

def build_skeet_text(row):
    
    congrats = random.choice(
        ["Herzliche Gratulation!", "Herzlichen Glückwunsch!", "Congrats!", "Alles Gute!", "🎂🎁🥳"]
    )

    name = f"{row['vorname']} {row['nachname']}"
    alter = pd.Timestamp.today().year - row["geburtsdatum"].year
    pron = "Er" if row["geschlecht"] == "männlich" else "Sie"

    header = f"{name} ({row['partei']}) hat heute Geburtstag!"

    if pd.notna(row["sterbedatum"]):
        body = (
            f"{pron} wäre {alter} Jahre alt geworden.\n"
            f"{pron} hat ab {row['historie'].year} für "
            f"{row['anzahl_wp']} "
            f"{'Wahlperioden' if row['anzahl_wp'] > 1 else 'Wahlperiode'} "
            "im Bundestag gewirkt.\n"
        )
    else:
        body = f"{pron} wird {alter} Jahre alt.\n{congrats}"

    return "\n".join([header, body])

def get_wikipedia_article(name):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    query = f"""
    SELECT ?article WHERE {{
      ?person wdt:P31 wd:Q5 ;
              wdt:P106 wd:Q82955 ;
              rdfs:label "{name}"@de .
      OPTIONAL {{
        ?article schema:about ?person ;
                 schema:isPartOf <https://de.wikipedia.org/> .
      }}
    }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    for r in results["results"]["bindings"]:
        return r.get("article", {}).get("value")

    return None
    
df = load_data()
row = pick_birthday_mp(df)

if row is None:
    print("Heute keine Geburtstage.")
    raise SystemExit

skeet_text = build_skeet_text(row)
article = get_wikipedia_article(f"{row['vorname']} {row['nachname']}")

tb = client_utils.TextBuilder().text(skeet_text)
if article:
    tb = tb.link(article, article)

client.send_post(tb)

print(skeet_text, article)
