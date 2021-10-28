import pandas as pd
import os
import json


CWD = os.getcwd()

def get_data():
    return pd.read_csv("https://datavaccin-covid.ameli.fr/explore/dataset/donnees-vaccination-par-tranche-dage-type-de-vaccin-et-departement/download/?format=csv&timezone=Europe/Berlin&lang=fr&use_labels_for_header=true&csv_separator=%3B", sep=";")

def prepare_data(df):
    df = df[df["type_vaccin"]=="Tout vaccin"]
    df = df[df["classe_age"]=="TOUT_AGE"]
    df["semaine_injection_jour"] = pd.to_datetime(df["semaine_injection"]+"-0", format="%Y-%W-%w")
    #df = df[df["semaine_injection_jour"] == df["semaine_injection_jour"].max()]
    df = df.sort_values(by="semaine_injection_jour")
    return df

def df_to_json(df):
    dict_json = {}
    for dep in df["departement_residence"]:
        df_dep = df[df["departement_residence"]==dep]
        N = len(df_dep)
        dict_json[dep] = {
            "dates": df_dep["semaine_injection_jour"].dt.strftime('%Y-%m-%d'),
            "taux_cumu_1_inj": df_dep["taux_cumu_1_inj"].fillna(0).to_list()[N-1],
            "taux_cumu_1_inj_temps": df_dep["taux_cumu_1_inj"].fillna(0).to_list()*100,
            "taux_cumu_termine": df_dep["taux_cumu_termine"].fillna(0).to_list()[N-1],
            "effectif_1_inj": df_dep["effectif_1_inj"].fillna(0).to_list()[N-1],
            "effectif_termine": df_dep["effectif_termine"].fillna(0).to_list()[N-1]}
    dict_json["dates"] = df["semaine_injection_jour"].dt.strftime('%Y-%m-%d')
    return dict_json

def export_to_json(data_json):
    with open(CWD + '/data/output/' + 'donnees-vaccination-par-tranche-dage-type-de-vaccin-et-departement.json', 'w', encoding='utf-8') as f:
        json.dump(data_json, f, ensure_ascii=False, indent=4)

def main():
    df = get_data()
    df = prepare_data(df)
    dict_data = df_to_json(df)
    export_to_json(dict_data)
    print(df)


if __name__ == "__main__":
    main()