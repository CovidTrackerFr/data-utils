import pandas as pd
import os
import json

CWD = os.getcwd()

def get_data():
    return pd.read_csv("https://www.data.gouv.fr/fr/datasets/r/b8260846-2a71-4e1b-822f-398a36f39f9f", sep=";").sort_values(by="date")

def df_to_json(df):
    dict_json = {}
    for col in df.columns:
        dict_json[col] = df[col].fillna(0).to_list()
    return dict_json

def export_json(data_json):
    with open(CWD + '/data/' + 'fr-en-situation_nationale_covid.json', 'w', encoding='utf-8') as f:
        json.dump(data_json, f, ensure_ascii=False, indent=4)


def main():
    df = get_data()
    data_json = df_to_json(df)
    export_json(data_json)

if __name__ == "__main__":
    main()